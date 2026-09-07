"""One bounded real-provider batch. No test doubles; preserve every attempt.

Run after optional installation and local OPENAI_API_KEY configuration. A missing
key is recorded as blocked, never represented as successful live verification.
"""

import argparse
from pathlib import Path
import time

from signal_research_agent.coordinator import Coordinator, DEFAULT_TOPIC, write_json
from signal_research_agent.models import scope_notices
from signal_research_agent.provider import OpenAIProvider


class BatchProvider:
    """Limit the batch to 16 adapter attempts, hence at most 16 SDK calls."""

    def __init__(self):
        self.provider = OpenAIProvider()
        self.attempts = 0

    def generate(self, context):
        if self.attempts >= 16:
            return {"status": "budget_exhausted", "output": None, "metadata": {
                "provider": "openai", "actual_provider_call": False, "actual_model": None,
                "requested_model": self.provider.model, "response_id": None, "usage": None,
                "cost_usd": None, "status": "budget_exhausted"}}
        self.attempts += 1
        return self.provider.generate(context)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="artifacts/live_verification")
    args = parser.parse_args(argv)
    output = Path(args.output_dir)
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
        outcomes["C_controlled_feedback"] = bool(feedback and len(third["planning_contexts"]) >= 2
            and third["status"] in ("completed", "model_deferred"))
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
              "checks": outcomes, "runs": runs, "incomplete_checks": incomplete,
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
    if result["required_environment_variable"]:
        print("Configure OPENAI_API_KEY locally. Never paste a credential into source, command arguments, logs, or chat.")
    print(f"Evidence: {output / 'live_verification_results.json'}")
    return 0 if result["live_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
