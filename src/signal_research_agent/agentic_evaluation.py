"""Explicitly mocked agentic acceptance scenarios; never a live-provider claim."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import time

from .coordinator import Coordinator, DEFAULT_TOPIC, write_json
from .llm_workflow import replay
from .models import scope_notices
from .retrieval import LiteratureRetriever


def proposal_fixture(lookback=6, selection_count=3, *, parent=None, candidate_id="design-a"):
    """Test data for exercising gates; the real provider does not use this function."""
    sources = {source["id"]: source for source in LiteratureRetriever().sources}
    candidate = {"id": candidate_id, "parent_id": parent,
                 "research_claim": "Test whether lower-volatility synthetic stocks have better risk-adjusted returns than an equal-weight benchmark.",
                 "signal": "total_volatility", "lookback_months": lookback, "selection_count": selection_count,
                 "evidence_claims": [{"claim": sources[key]["summary"], "source_id": key,
                                      "summary_excerpt": sources[key]["summary"]}
                                     for key in ("baker-2010-benchmarks", "arnott-2019-protocol")],
                 "assumptions": ["Monthly lookback and selection count are educational design choices."],
                 "decision_rationale": "Compare a grounded feasible monthly volatility hypothesis without inspecting outcomes.",
                 "limitations": ["Synthetic observations cannot establish any real-market investment effect."],
                 "parameter_basis": "agent_design_choice", "adaptation_rationale": None}
    return {"action": "revise" if parent else "propose", "candidates": [candidate],
            "selected_candidate_id": candidate_id, "decision_rationale": candidate["decision_rationale"], "deferral_reason": None}


class ScriptedProvider:
    """Named test double. Metadata explicitly declares zero real provider calls."""

    def __init__(self, outputs):
        self.outputs = outputs
        self.contexts = []

    def generate(self, context):
        self.contexts.append(deepcopy(context))
        output = self.outputs[min(len(self.contexts) - 1, len(self.outputs) - 1)]
        output = output(context) if callable(output) else deepcopy(output)
        return {"status": "completed", "output": output, "metadata": {
            "provider": "scripted_test", "requested_model": None, "actual_model": None,
            "response_id": None, "usage": None, "actual_provider_call": False,
            "status": "completed", "cost_usd": None}}


def evaluate_agentic(output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    # Preserve prior attempts, including failed ones, in numbered batches.
    index = 1
    while (output / f"batch_{index:03d}").exists():
        index += 1
    batch = output / f"batch_{index:03d}"
    batch.mkdir()
    cases = []
    start = time.perf_counter()

    def check(name, operation):
        begin = time.perf_counter()
        try:
            passed = bool(operation())
            detail = "Expected behavior observed." if passed else "Expected behavior was not observed."
        except Exception as exc:
            passed, detail = False, f"Scenario raised {type(exc).__name__}."
        cases.append({"name": name, "passed": passed, "detail": detail,
                      "elapsed_seconds": round(time.perf_counter() - begin, 6)})

    def run(name, provider, **kwargs):
        return Coordinator().run(DEFAULT_TOPIC, batch / name, mode="llm", provider=provider, **kwargs)

    results = {}
    for lookback in (6, 12):
        for count in (3, 4):
            name = f"accepted_{lookback}_months_{count}_assets"
            def choice(name=name, lookback=lookback, count=count):
                result = run(name, ScriptedProvider([proposal_fixture(lookback, count)]))
                results[name] = result
                return (result["status"] == "completed" and result["hypothesis_lock"]["specification"]["lookback_months"] == lookback
                        and result["hypothesis_lock"]["specification"]["selection_count"] == count
                        and result["backtest"]["metrics"]["observation_count"] == 120 - lookback
                        and all(result["review"]["checks"].values()))
            check(name, choice)

    def feedback():
        provider = ScriptedProvider([proposal_fixture(9), proposal_fixture(6, parent="design-a", candidate_id="design-b")])
        result = run("feedback_revision", provider)
        results["feedback_revision"] = result
        return (result["status"] == "completed" and len(provider.contexts) == 2
                and any("6 or 12" in error for error in provider.contexts[1]["validation_feedback"]["objections"])
                and result["hypothesis_search"]["rounds"][0]["candidates"][0]["valid"] is False)
    check("actual_validation_feedback_changes_proposal", feedback)

    def duplicate():
        shared = batch / "shared_journal"
        first = run("memory_first", ScriptedProvider([proposal_fixture()]), journal_dir=shared)
        provider = ScriptedProvider([proposal_fixture()])
        second = run("memory_second", provider, journal_dir=shared)
        results["memory_first"], results["memory_second"] = first, second
        return (first["status"] == "completed" and second["status"] == "duplicate_deferred"
                and second["backtest"] is None and provider.contexts[0]["verified_prior_research"]
                and second["duplicate_reference"]["hypothesis_id"] == first["hypothesis_lock"]["hypothesis_id"])
    check("persisted_memory_prevents_duplicate", duplicate)

    def process_restart():
        code = ("import json,sys; from signal_research_agent.memory import ResearchMemory; "
                "from pathlib import Path; r=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')); "
                "print(json.dumps(ResearchMemory(sys.argv[1]).find_duplicate(r['hypothesis_lock']['specification'])))")
        completed = subprocess.run([sys.executable, "-c", code, str(batch / "shared_journal"), str(batch / "memory_first" / "result.json")],
                                   text=True, capture_output=True, timeout=15)
        reference = json.loads(completed.stdout) if completed.returncode == 0 else None
        write_json(batch / "restart_reference.json", {"test_kind": "mocked_design_real_subprocess_memory_read", "reference": reference,
                                                     "safety_notices": list(scope_notices("llm"))})
        return reference and reference == results["memory_second"]["duplicate_reference"]
    check("new_process_detects_same_experiment", process_restart)

    def grounding():
        class MissingDirectEvidence(LiteratureRetriever):
            def search(self, query, limit=6):
                return [source for source in super().search(query, limit) if source["stance"] != "supports_total_volatility_research"]
        provider = ScriptedProvider([proposal_fixture()])
        result = Coordinator(retriever=MissingDirectEvidence()).run(DEFAULT_TOPIC, batch / "grounding_removed", mode="llm", provider=provider)
        return result["status"] == "grounding_failed" and not provider.contexts and result["backtest"] is None
    check("necessary_grounding_removal_blocks_provider_and_backtest", grounding)

    def no_outcomes():
        contexts = results["memory_second"]["planning_contexts"]
        forbidden = {"metrics", "sharpe_ratio", "cumulative_return", "annualized_return", "verdict", "backtest"}
        def clean(value):
            if isinstance(value, dict):
                return not (set(value) & forbidden) and all(clean(item) for item in value.values())
            return all(clean(item) for item in value) if isinstance(value, list) else True
        return clean(contexts)
    check("current_and_prior_performance_excluded", no_outcomes)

    def saved_replay():
        original = results["accepted_6_months_3_assets"]
        result = replay(Coordinator(), batch / "accepted_6_months_3_assets" / "result.json", batch / "saved_replay")
        return (result["status"] == "completed" and result["provider_execution"]["actual_provider_calls"] == 0
                and result["backtest"] == original["backtest"])
    check("saved_specification_replays_without_provider", saved_replay)

    def refusal():
        provider = ScriptedProvider([proposal_fixture()])
        result = Coordinator().run("Use confidential private customer data to research volatility", batch / "refusal", mode="llm", provider=provider)
        return result["status"] == "request_refused" and not provider.contexts
    check("sensitive_request_has_zero_provider_calls", refusal)
    check("mock_results_never_claim_live_execution", lambda: all(
        result["provider_execution"]["actual_provider_calls"] == 0
        and not result["provider_execution"]["live_execution_verified"] for result in results.values()))

    result = {"schema_version": "1.0", "test_kind": "mocked_provider_acceptance", "real_provider_calls": 0,
              "safety_notices": list(scope_notices("llm")), "batch": batch.name,
              "total": len(cases), "passed": sum(case["passed"] for case in cases),
              "failed": sum(not case["passed"] for case in cases), "cases": cases,
              "elapsed_seconds": round(time.perf_counter() - start, 6)}
    write_json(batch / "evaluation_results.json", result)
    write_json(output / "evaluation_results.json", result)
    summary = f"Mocked agentic evaluation: {result['passed']}/{result['total']} passed; real provider calls: 0\n"
    summary += "\n".join(f"[{'PASS' if case['passed'] else 'FAIL'}] {case['name']}" for case in cases)
    (output / "console_output.txt").write_text(" | ".join(scope_notices("llm")) + "\n" + summary + "\n", encoding="utf-8")
    return result
