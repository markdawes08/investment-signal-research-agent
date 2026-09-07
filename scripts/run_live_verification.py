"""One bounded real-provider batch. No test doubles; preserve every attempt.

Run after optional installation and local OPENAI_API_KEY configuration. A missing
key is recorded as blocked, never represented as successful live verification.
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import time

from signal_research_agent.coordinator import Coordinator, DEFAULT_TOPIC, write_json
from signal_research_agent.hypothesis import verify_lock
from signal_research_agent.journal import verify_entries
from signal_research_agent.llm_workflow import output_lease
from signal_research_agent.memory import experiment_fingerprint
from signal_research_agent.models import content_hash, scope_notices
from signal_research_agent.provider import OpenAIProvider


class BatchProvider:
    """Limit the batch to 16 adapter attempts, hence at most 16 SDK calls."""

    def __init__(self, max_attempts=16):
        self.provider = OpenAIProvider()
        self.attempts = 0
        self.max_attempts = max_attempts

    def generate(self, context):
        if self.attempts >= self.max_attempts:
            return {"status": "budget_exhausted", "output": None, "metadata": {
                "provider": "openai", "actual_provider_call": False, "actual_model": None,
                "requested_model": self.provider.model, "response_id": None, "usage": None,
                "cost_usd": None, "status": "budget_exhausted"}}
        self.attempts += 1
        return self.provider.generate(context)


def print_run_summary(run):
    """Show application-owned stop reasons without raw provider messages."""
    print(f"  {run['name']}: {run['status']}; actual provider calls: {run['actual_provider_calls']}")
    for reason in run.get("stop_reasons", [])[:3]:
        print(f"    {reason}")
    for call in run.get("provider_execution", {}).get("calls", []):
        if call.get("status") in ("provider_incomplete", "provider_failed", "provider_unexpected_status"):
            # These fields are SDK enum values allowlisted by the adapter;
            # never print a raw response error or refusal message.
            fields = ("provider_response_status", "incomplete_reason", "provider_error_code")
            details = "; ".join(f"{field}: {call.get(field) or 'unknown'}" for field in fields)
            print(f"    Provider termination: {details}")
            if call.get("incomplete_reason") == "max_output_tokens":
                cap = call.get("requested_max_output_tokens")
                used = (call.get("usage") or {}).get("output_tokens")
                print(f"    Requested output cap: {cap if cap is not None else 'unknown'}; "
                      f"reported output tokens: {used if used is not None else 'unknown'}")
    for failure in run.get("validation_failures", [])[-1:]:
        for reason in failure.get("errors", [])[:4]:
            print(f"    Validation: {reason}")


_RUN_NAMES = ("A_research", "B_duplicate", "C_controlled_feedback", "D_explicit_choices")
_CHECK_NAMES = ("A_genuine_research", "B_persisted_duplicate", "C_controlled_feedback", "D_explicit_supported_choices")


def _strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field in verification evidence.")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("Nonfinite verification evidence.")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def _read_json(path, maximum=2_000_000):
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("Required bounded verification artifact is absent or oversized.")
    return _strict_json(path.read_text(encoding="utf-8"))


def _read_chain(path):
    if not path.is_file() or path.stat().st_size > 10_000_000:
        raise ValueError("Required bounded journal is absent or oversized.")
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        raise ValueError("Verification journal has an incomplete final line.")
    entries = [_strict_json(line) for line in text.splitlines()]
    if not entries or not verify_entries(entries):
        raise ValueError("Verification journal integrity failed.")
    return entries


def _verified_result(source, name):
    directory = source / name
    for filename in ("result.json", "audit.jsonl", "research_journal.jsonl"):
        expected = directory / filename
        if expected.resolve() != expected:
            raise ValueError("Verification source paths must remain inside their exact expected run directory.")
    result = _read_json(directory / "result.json")
    unsigned = deepcopy(result)
    integrity = unsigned.pop("integrity")
    audit = _read_chain(directory / "audit.jsonl")
    journal = _read_chain(directory / "research_journal.jsonl")
    digest = content_hash(unsigned)
    if (integrity["audit_head"] != audit[-1]["entry_hash"]
            or integrity["research_journal_head"] != journal[-1]["entry_hash"]
            or audit[-1]["payload"].get("event") != "workflow_completed"
            or audit[-1]["payload"].get("details", {}).get("result_hash") != digest
            or journal[-1]["payload"].get("event") != "research_concluded"
            or journal[-1]["payload"].get("result_hash") != digest):
        raise ValueError("Verification result and journal checkpoints disagree.")
    payloads = [entry["payload"] for entry in audit]
    if (result.get("execution_mode") != "llm" or not payloads
            or any(item.get("run_id") != result["run_id"] for item in payloads)):
        raise ValueError("Source must be one complete LLM run per expected directory.")
    calls = [item["details"] for item in payloads if item.get("event") == "provider_call_completed"]
    execution = result["provider_execution"]
    if (type(execution["calls_attempted"]) is not int or not 1 <= execution["calls_attempted"] <= 4
            or execution["calls_attempted"] != len(calls)
            or execution["calls"] != [call["metadata"] for call in calls]
            or [call["call_index"] for call in calls] != list(range(1, len(calls) + 1))
            or any(call["metadata"].get("provider") != "openai" for call in calls)
            or any(type(call["metadata"].get("actual_provider_call")) is not bool for call in calls)
            or type(execution["actual_provider_calls"]) is not int
            or execution["actual_provider_calls"] != sum(call["metadata"]["actual_provider_call"] for call in calls)
            or execution["actual_provider_calls"] < 1):
        raise ValueError("Source provider counts or application-recorded provenance disagree.")
    for call in calls:
        if call["status"] != call["metadata"].get("status"):
            raise ValueError("Source provider statuses disagree with the audit.")
    result["_verified_result_hash"] = digest
    return result


def _real_response(result):
    execution = result.get("provider_execution", {})
    calls = execution.get("calls", [])
    return bool(type(execution.get("actual_provider_calls")) is int
                and execution["actual_provider_calls"] > 0 and calls
                and all(call.get("provider") == "openai" for call in calls)
                and calls[-1].get("actual_provider_call") is True
                and calls[-1].get("status") == "completed"
                and isinstance(calls[-1].get("actual_model"), str) and calls[-1]["actual_model"]
                and isinstance(calls[-1].get("response_id"), str) and calls[-1]["response_id"])


def _completed_live(result):
    return (result.get("status") == "completed" and _real_response(result)
            and result["provider_execution"].get("live_execution_verified") is True
            and result.get("requires_human_intervention") is False
            and verify_lock(result.get("hypothesis_lock"))
            and result.get("backtest") is not None
            and result.get("review", {}).get("checks")
            and all(value is True for value in result["review"]["checks"].values()))


def _controlled_passed(result):
    search = result.get("hypothesis_search") or {}
    feedback = search.get("feedback", [])
    contexts = result.get("planning_contexts", [])
    return bool(_real_response(result) and feedback and len(contexts) >= 2
                and contexts[-1].get("context", {}).get("validation_feedback") == feedback[-1]
                and contexts[-1].get("context", {}).get("explicit_constraints") == {"lookback_months": 6, "selection_count": 3}
                and any("Controlled validation condition:" in objection for objection in feedback[-1].get("objections", []))
                and result.get("controlled_validation") == "require_same_close_limitation"
                and (result.get("status") == "model_deferred" or _completed_live(result)))


def _verify_resume_source(source, output):
    """Verify all reusable and failed evidence before constructing any provider.

    Local chains are integrity checks, not externally authenticated attestations.
    Only one original four-run batch with A/B/D passed and C failed is eligible.
    """
    source = source.resolve(strict=True)
    if output.resolve() != source.parent:
        raise ValueError("Resume output must be the source batch's parent directory.")
    summary_path = source / "live_verification_results.json"
    if summary_path.resolve() != summary_path:
        raise ValueError("Source summary cannot redirect outside the source batch.")
    summary = _read_json(summary_path)
    expected_checks = dict(zip(_CHECK_NAMES, (True, True, False, True)))
    if (summary.get("verification_kind") != "real_provider_batch" or summary.get("batch") != source.name
            or summary.get("checks") != expected_checks or summary.get("live_verified") is not False
            or summary.get("hard_provider_attempt_limit") != 16
            or summary.get("status") != "incomplete"
            or not isinstance(summary.get("runs"), list)
            or [run.get("name") for run in summary["runs"]] != list(_RUN_NAMES)):
        raise ValueError("Resume requires an original batch with only C incomplete.")
    results = {}
    for run in summary["runs"]:
        name = run["name"]
        if run.get("result_path") != f"{source.name}/{name}/result.json":
            raise ValueError("Source run reference is outside its exact expected directory.")
        result = _verified_result(source, name)
        for key in ("status", "verdict", "requires_human_intervention", "provider_execution"):
            if run.get(key) != result.get(key):
                raise ValueError("Source summary does not match the verified run.")
        if run.get("actual_provider_calls") != result["provider_execution"]["actual_provider_calls"]:
            raise ValueError("Source summary provider count disagrees with verified provenance.")
        if run.get("stop_reasons", []) != result.get("review", {}).get("objections", []):
            raise ValueError("Source summary stop reasons disagree with verified review.")
        results[name] = result
    a, b, c, d = [results[name] for name in _RUN_NAMES]
    if not _completed_live(a) or not _completed_live(d):
        raise ValueError("A and D must be completed, verified real-provider experiments.")
    reference = b.get("duplicate_reference") or {}
    if (b.get("status") not in ("duplicate_deferred", "model_deferred") or b.get("backtest") is not None
            or not _real_response(b) or reference.get("hypothesis_id") != a["hypothesis_lock"]["hypothesis_id"]
            or reference.get("experiment_fingerprint") != experiment_fingerprint(a["hypothesis_lock"]["specification"])):
        raise ValueError("B must reference A's identical experiment and avoid redundant execution.")
    if (c.get("status") == "completed" or c.get("backtest") is not None
            or c.get("controlled_validation") != "require_same_close_limitation" or _controlled_passed(c)):
        raise ValueError("Only a failed unexecuted controlled C case may be resumed.")
    if any(d["hypothesis_lock"]["specification"][key] != value for key, value in {"lookback_months": 6, "selection_count": 3}.items()):
        raise ValueError("D does not establish the required explicit supported choices.")
    attempts = sum(result["provider_execution"]["calls_attempted"] for result in results.values())
    calls = sum(result["provider_execution"]["actual_provider_calls"] for result in results.values())
    if (type(summary.get("provider_attempts")) is not int or summary["provider_attempts"] != attempts
            or type(summary.get("actual_provider_calls")) is not int or summary["actual_provider_calls"] != calls
            or not 0 < calls <= attempts < 16):
        raise ValueError("Source batch counts do not leave a verified aggregate provider budget.")
    summary_hash = content_hash(summary)
    for reservation_path in output.glob("batch_*/resume_reservation.json"):
        reservation = _read_json(reservation_path, maximum=10_000)
        if reservation.get("source_summary_hash") == summary_hash:
            raise ValueError("This source already has a durable resume reservation; interrupted attempts cannot reset its budget.")
    for prior in output.glob("batch_*/live_verification_results.json"):
        if prior.resolve() == summary_path:
            continue
        previous = _read_json(prior)
        if previous.get("resume_source", {}).get("summary_hash") == summary_hash:
            raise ValueError("This source already has a resume batch; its provider budget cannot be reset.")
    return source, summary, results, summary_hash


def _summarize_run(name, result, result_path, reused=False):
    return {"name": name, "status": result["status"], "verdict": result["verdict"],
            "result_path": result_path, "actual_provider_calls": result["provider_execution"]["actual_provider_calls"],
            "provider_execution": result["provider_execution"], "stop_reasons": result.get("review", {}).get("objections", []),
            "validation_failures": result.get("validation_failures", []),
            "requires_human_intervention": result["requires_human_intervention"], "reused_verified_evidence": reused}


def _failed_checks(checks):
    return [f"{name} did not pass; see the referenced run status and validation observations."
            for name, passed in checks.items() if passed is not True]


def _resume_locked(source, output):
    """The parent-directory lease covers revalidation, reservation and execution."""
    source, previous, verified, summary_hash = _verify_resume_source(source, output)
    index = 1
    while (output / f"batch_{index:03d}").exists():
        index += 1
    batch = output / f"batch_{index:03d}"
    batch.mkdir()
    started = time.perf_counter()
    remaining = 16 - previous["provider_attempts"]
    reserved_attempts = min(4, remaining)
    reservation = {"schema_version": "1.0", "source_summary_hash": summary_hash,
                   "source_summary_path": f"{source.name}/live_verification_results.json",
                   "previous_provider_attempts": previous["provider_attempts"],
                   "previous_provider_calls": previous["actual_provider_calls"],
                   "reserved_max_attempts": reserved_attempts,
                   "aggregate_reserved_max_attempts": previous["provider_attempts"] + reserved_attempts,
                   "reason": "Preserve the provider budget even if this resume is interrupted before its final summary."}
    # This permanent checkpoint precedes provider construction and every attempt.
    # A later failure or process interruption must never remove the reservation.
    write_json(batch / "resume_reservation.json", reservation)
    provider = BatchProvider(max_attempts=reserved_attempts)
    third = Coordinator().run(DEFAULT_TOPIC, batch / "C_controlled_feedback", mode="llm", provider=provider,
                               max_provider_calls=min(4, remaining), journal_dir=batch / "feedback_journal",
                               controlled_validation="require_same_close_limitation",
                               constraints={"lookback_months": 6, "selection_count": 3})
    runs = []
    for name in _RUN_NAMES:
        result = third if name == "C_controlled_feedback" else verified[name]
        location = batch if name == "C_controlled_feedback" else source
        runs.append(_summarize_run(name, result, f"{location.name}/{name}/result.json", location == source))
    checks = dict(zip(_CHECK_NAMES, (True, True, _controlled_passed(third), True)))
    passed = all(value is True for value in checks.values())
    new_calls = third["provider_execution"]["actual_provider_calls"]
    result = {
        "schema_version": "1.1", "verification_kind": "real_provider_resume_batch", "batch": batch.name,
        "safety_notices": list(scope_notices("llm")), "hard_provider_attempt_limit": 16,
        "previous_provider_attempts": previous["provider_attempts"], "new_provider_attempts": provider.attempts,
        "provider_attempts": previous["provider_attempts"] + provider.attempts,
        "previous_provider_calls": previous["actual_provider_calls"], "new_provider_calls": new_calls,
        "actual_provider_calls": previous["actual_provider_calls"] + new_calls,
        "checks": checks, "runs": runs, "prior_runs": deepcopy(previous["runs"]),
        "resume_source": {"summary_path": f"{source.name}/live_verification_results.json", "summary_hash": summary_hash,
                          "verified_results": {name: {"result_path": f"{source.name}/{name}/result.json",
                              "result_hash": item["_verified_result_hash"], "integrity": item["integrity"]}
                              for name, item in verified.items()}},
        "incomplete_checks": _failed_checks(checks), "live_verified": passed,
        "status": "completed" if passed else "blocked_missing_credentials" if third["status"] == "missing_credentials" else "incomplete",
        "required_environment_variable": "OPENAI_API_KEY" if third["status"] == "missing_credentials" else None,
        "controlled_condition": previous["controlled_condition"], "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    write_json(batch / "live_verification_results.json", result)
    write_json(output / "live_verification_results.json", result)
    print(" | ".join(scope_notices("llm")))
    print(f"Live resume: {result['status']}; previous actual calls: {previous['actual_provider_calls']}; "
          f"new actual calls: {new_calls}; aggregate actual calls: {result['actual_provider_calls']}; "
          f"aggregate adapter attempts: {result['provider_attempts']}")
    for run in runs:
        print_run_summary(run)
    if result["required_environment_variable"]:
        print("Configure OPENAI_API_KEY locally; never paste a secret into source, command arguments, logs, or chat.")
    print(f"Evidence: {output / 'live_verification_results.json'}")
    return 0 if passed else 2


def _resume(source, output):
    if output.resolve() != source.resolve(strict=True).parent:
        raise ValueError("Resume output must be the source batch's parent directory.")
    # Revalidate inside the same lease that reserves and consumes the budget;
    # concurrent invocations cannot both pass a stale no-reservation check.
    with output_lease(output):
        return _resume_locked(source, output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir")
    parser.add_argument("--resume-batch", help="Verify and reuse A/B/D, then retry only the failed controlled C case")
    args = parser.parse_args(argv)
    if args.resume_batch:
        source = Path(args.resume_batch)
        output = Path(args.output_dir) if args.output_dir else source.resolve().parent
        try:
            return _resume(source, output)
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            print("Resume stopped: source evidence, paths, eligibility, or aggregate budget failed verification. No source evidence was changed.")
            return 2
    output = Path(args.output_dir or "artifacts/live_verification")
    output.mkdir(parents=True, exist_ok=True)
    index = 1
    while (output / f"batch_{index:03d}").exists():
        index += 1
    batch = output / f"batch_{index:03d}"
    batch.mkdir()
    provider = BatchProvider()
    started = time.perf_counter()
    runs = []

    def execute(name, topic=DEFAULT_TOPIC, **kwargs):
        result = Coordinator().run(topic, batch / name, mode="llm", provider=provider,
                                    max_provider_calls=min(4, 16 - provider.attempts), **kwargs)
        runs.append({"name": name, "status": result["status"], "verdict": result["verdict"],
                     "result_path": f"{batch.name}/{name}/result.json",
                     "actual_provider_calls": result["provider_execution"]["actual_provider_calls"],
                     "provider_execution": result["provider_execution"],
                     "stop_reasons": result.get("review", {}).get("objections", []),
                     "validation_failures": result.get("validation_failures", []),
                     "requires_human_intervention": result["requires_human_intervention"]})
        return result

    first = execute("A_research", journal_dir=batch / "shared_journal")
    passed_a = first["status"] == "completed" and first["provider_execution"]["live_execution_verified"]
    outcomes = {"A_genuine_research": passed_a, "B_persisted_duplicate": None,
                "C_controlled_feedback": None, "D_explicit_supported_choices": None}
    incomplete = []
    if passed_a:
        spec = first["hypothesis_lock"]["specification"]
        second = execute("B_duplicate", "Investigate whether stocks with lower total volatility have better risk-adjusted returns",
                         journal_dir=batch / "shared_journal", constraints={
                             "lookback_months": spec["lookback_months"], "selection_count": spec["selection_count"]})
        outcomes["B_persisted_duplicate"] = (second["status"] in ("duplicate_deferred", "model_deferred")
                                             and second["duplicate_reference"] is not None and second["backtest"] is None)
        third = execute("C_controlled_feedback", journal_dir=batch / "feedback_journal",
                        controlled_validation="require_same_close_limitation", constraints={"lookback_months": 6, "selection_count": 3})
        feedback = (third.get("hypothesis_search") or {}).get("feedback", [])
        outcomes["C_controlled_feedback"] = _controlled_passed(third)
        if not feedback:
            incomplete.append("C did not demonstrate feedback: the first response already met the controlled condition or stopped earlier. No forced retry was made.")
        fourth = execute("D_explicit_choices", journal_dir=batch / "constrained_journal",
                         constraints={"lookback_months": 6, "selection_count": 3})
        outcomes["D_explicit_supported_choices"] = fourth["status"] == "completed" and all(
            fourth["hypothesis_lock"]["specification"][key] == value for key, value in {"lookback_months": 6, "selection_count": 3}.items())
    else:
        incomplete.append("A did not complete a genuine LLM research run; dependent B and remaining C/D were not attempted.")
    result = {"schema_version": "1.0", "verification_kind": "real_provider_batch", "safety_notices": list(scope_notices("llm")),
              "batch": batch.name, "hard_provider_attempt_limit": 16, "provider_attempts": provider.attempts,
              "actual_provider_calls": sum(run["actual_provider_calls"] for run in runs),
              "checks": outcomes, "runs": runs, "incomplete_checks": incomplete + _failed_checks(outcomes),
              "live_verified": all(value is True for value in outcomes.values()),
              "status": "completed" if all(value is True for value in outcomes.values()) else
                        "blocked_missing_credentials" if first["status"] == "missing_credentials" else "incomplete",
              "required_environment_variable": "OPENAI_API_KEY" if first["status"] == "missing_credentials" else None,
              "controlled_condition": "C deliberately adds a pre-lock validation requirement to explicitly name same-close execution and zero latency in limitations. No data, seed, or outcome is changed.",
              "elapsed_seconds": round(time.perf_counter() - started, 6)}
    write_json(batch / "live_verification_results.json", result)
    write_json(output / "live_verification_results.json", result)
    print(" | ".join(scope_notices("llm")))
    print(f"Live verification: {result['status']}; actual provider calls: {result['actual_provider_calls']}; adapter attempts: {provider.attempts}")
    for run in runs:
        print_run_summary(run)
    if result["required_environment_variable"]:
        print("Configure OPENAI_API_KEY locally. Never paste a credential into source, command arguments, logs, or chat.")
    print(f"Evidence: {output / 'live_verification_results.json'}")
    return 0 if result["live_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
