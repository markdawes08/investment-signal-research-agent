"""Measured acceptance scenarios, separate from the unittest regression suite."""

from copy import deepcopy
import platform
from pathlib import Path
import tempfile
import time

from .backtester import Backtester
from .coordinator import Coordinator, DEFAULT_TOPIC, write_json
from .data_engineer import DataEngineer
from .hypothesis import HypothesisGenerator, verify_lock
from .journal import HashChainJournal, verify_entries
from .models import ResearchError, SAFETY_NOTICES
from .retrieval import LiteratureRetriever
from .safety import check_request


def console_summary(result):
    lines = [f"Evaluation: {result['passed']}/{result['total']} passed; {result['failed']} failed",
             f"Elapsed: {result['elapsed_seconds']:.3f} seconds",
             f"Synthetic fixture verdict: {result['sample']['verdict']}",
             f"Synthetic monthly observations: {result['sample']['metrics'].get('observation_count', 0)}"]
    for case in result["cases"]:
        lines.append(f"[{'PASS' if case['passed'] else 'FAIL'}] {case['name']}")
    return "\n".join(lines)


def evaluate(output_dir):
    started = time.perf_counter()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    cases = []

    def check(name, callback):
        begin = time.perf_counter()
        try:
            passed = bool(callback())
            detail = "Expected invariant observed." if passed else "Expected invariant was not observed."
        except Exception as exc:  # Record unexpected failures and keep evaluating.
            passed, detail = False, f"Scenario raised {type(exc).__name__}."
        cases.append({"name": name, "passed": passed, "detail": detail,
                      "elapsed_seconds": round(time.perf_counter() - begin, 6)})

    try:
        sample = Coordinator().run(DEFAULT_TOPIC, output / "sample_run")
    except Exception:
        sample = {}
    if not sample.get("hypothesis_lock") or not sample.get("backtest"):
        check("baseline_setup", lambda: False)
        result = {"schema_version": "1.0", "safety_notices": list(SAFETY_NOTICES),
                  "purpose": "Software acceptance checks; not investment efficacy or real-market validation.",
                  "python_version": platform.python_version(), "total": 1, "passed": 0, "failed": 1,
                  "cases": cases, "elapsed_seconds": round(time.perf_counter() - started, 6),
                  "sample": {"verdict": "rejected", "metrics": {}},
                  "requires_human_intervention": True,
                  "reason": "Baseline setup failed; dependent scenarios could not run."}
        write_json(output / "evaluation_results.json", result)
        (output / "sample_console_output.txt").write_text(
            " | ".join(SAFETY_NOTICES) + "\n" + console_summary(result) + "\n", encoding="utf-8")
        return result
    lock = sample["hypothesis_lock"]
    spec = lock["specification"]
    engineer = DataEngineer()
    rows = engineer.generate(spec)
    validation = engineer.validate(rows, spec)
    audit = HashChainJournal(output / "sample_run" / "audit.jsonl").entries()
    latest_start = max(index for index, entry in enumerate(audit)
                       if entry["payload"]["event"] == "request_accepted")
    segment = audit[latest_start:]
    events = [entry["payload"]["event"] for entry in segment]
    check("end_to_end_completion", lambda: sample["status"] == "completed" and not sample["requires_human_intervention"])
    check("all_five_roles", lambda: {entry["payload"]["role"] for entry in segment} == {
        "Coordinator", "Hypothesis Generator", "Data Engineer", "Backtester", "Skeptic"})
    check("retrieval_grounding", lambda: len(sample["evidence"]) >= 3 and
          set(spec["source_ids"]) <= {source["id"] for source in LiteratureRetriever().sources})
    search = sample["hypothesis_search"]
    check("bounded_pre_outcome_search", lambda: search["nodes_visited"] <= search["max_nodes"] == 5
          and search["outcome_access"] is False and len(search["revisions"]) <= 1
          and events.index("search_completed") < events.index("hypothesis_locked") <
          events.index("data_generated") < events.index("backtest_started"))
    check("valid_baseline_data", lambda: validation["passed"] and all(row["synthetic"] is True for row in rows))

    with tempfile.TemporaryDirectory(prefix="signal-evaluation-") as temporary:
        temp = Path(temporary)

        def replay():
            left = Coordinator().run(DEFAULT_TOPIC, temp / "replay_a")
            right = Coordinator().run(DEFAULT_TOPIC, temp / "replay_b")
            return left == right and all((temp / "replay_a" / name).read_bytes() ==
                                         (temp / "replay_b" / name).read_bytes() for name in
                                         ("result.json", "research_report.md", "audit.jsonl", "research_journal.jsonl"))

        check("deterministic_replay", replay)
        requests = {
            "brokerage_action_refusal": "Connect to my brokerage and explore volatility stocks",
            "trade_execution_refusal": "Execute an order for lower volatility stocks",
            "personalized_advice_refusal": "Explore low volatility stocks for my retirement portfolio",
            "private_data_refusal": "Explore volatility using confidential proprietary customer data",
            "empty_request_refusal": "",
            "ambiguous_request_refusal": "Find something useful",
        }
        for name, topic in requests.items():
            check(name, lambda topic=topic: not check_request(topic)["allowed"] and
                  check_request(topic)["requires_human_intervention"])

        def corrupt_data(name, mutate):
            def scenario():
                changed = deepcopy(rows)
                mutate(changed)
                return not engineer.validate(changed, spec)["passed"]
            check(name, scenario)

        corrupt_data("duplicate_row_detection", lambda panel: panel.append(deepcopy(panel[0])))
        corrupt_data("missing_value_detection", lambda panel: panel[0].update(price=None))
        corrupt_data("nonpositive_price_detection", lambda panel: panel[0].update(price=0))
        corrupt_data("nonfinite_price_detection", lambda panel: panel[0].update(price=float("nan")))
        corrupt_data("minimum_history_detection", lambda panel: panel.__delitem__(slice(0, 1000)))
        corrupt_data("unequal_history_detection", lambda panel: panel.pop())
        corrupt_data("as_of_date_leakage_detection", lambda panel: panel[-1].update(date="2025-01-31"))
        corrupt_data("availability_leakage_detection", lambda panel: panel[0].update(available_at="2015-01-01"))
        corrupt_data("synthetic_label_enforcement", lambda panel: panel[0].update(synthetic=False))

        def tamper():
            changed = deepcopy(lock)
            changed["specification"]["lookback_months"] = 6
            if verify_lock(changed):
                return False
            try:
                Backtester().run(changed, rows, validation)
            except ResearchError:
                return True
            return False

        check("hypothesis_tampering_detection", tamper)
        check("audit_chain_integrity", lambda: verify_entries(audit))

        def chain_tamper():
            changed = deepcopy(audit)
            changed[0]["payload"]["event"] = "altered"
            return not verify_entries(changed)

        check("audit_edit_detection", chain_tamper)

        def blocked_gate():
            class BrokenEngineer(DataEngineer):
                def generate(self, specification):
                    panel = super().generate(specification)
                    panel.append(deepcopy(panel[0]))
                    return panel

            class Tripwire:
                called = False

                def run(self, *args):
                    self.called = True
                    raise AssertionError("Backtester must not be reached")

            backtester = Tripwire()
            run = Coordinator(data_engineer=BrokenEngineer(), backtester=backtester).run(DEFAULT_TOPIC, temp / "failed_gate")
            return run["verdict"] == "rejected" and run["requires_human_intervention"] and not backtester.called

        check("failed_validation_stops_backtester", blocked_gate)
        check("insufficient_grounding_escalates", lambda: HypothesisGenerator().generate(DEFAULT_TOPIC, [])[
            "requires_human_intervention"])

        def conflict():
            evidence = deepcopy(sample["evidence"])
            evidence[0]["stance"] = "conflicting"
            return HypothesisGenerator().generate(DEFAULT_TOPIC, evidence)["requires_human_intervention"]

        check("conflicting_grounding_escalates", conflict)

        def future_invariance():
            changed = deepcopy(rows)
            for row in changed:
                if row["date"] == "2024-12-31":
                    row["price"] *= 1.5
            other = Backtester().run(lock, changed, engineer.validate(changed, spec))
            original = sample["backtest"]["observations"]
            return all(a["signals"] == b["signals"] and a["selected_assets"] == b["selected_assets"]
                       for a, b in zip(original, other["observations"]))

        check("future_prices_do_not_change_earlier_signals", future_invariance)
        check("costs_charged_to_both_portfolios", lambda: all(
            sample["backtest"]["metrics"][label]["total_cost_fraction"] > 0
            for label in ("strategy", "benchmark")))
        check("sufficient_observation_count", lambda: sample["backtest"]["metrics"]["observation_count"] ==
              spec["n_months"] - spec["lookback_months"] - 1 >= spec["min_observations"])
        check("all_artifacts_and_notices", lambda: all((output / "sample_run" / name).is_file() for name in
              ("result.json", "research_report.md", "audit.jsonl", "research_journal.jsonl")) and
              all(notice in (output / "sample_run" / "research_report.md").read_text(encoding="utf-8")
                  for notice in SAFETY_NOTICES))

    result = {"schema_version": "1.0", "safety_notices": list(SAFETY_NOTICES),
              "purpose": "Software acceptance checks; not investment efficacy or real-market validation.",
              "python_version": platform.python_version(), "total": len(cases),
              "passed": sum(case["passed"] for case in cases),
              "failed": sum(not case["passed"] for case in cases), "cases": cases,
              "elapsed_seconds": round(time.perf_counter() - started, 6),
              "sample": {"verdict": sample["verdict"], "hypothesis_id": lock["hypothesis_id"],
                         "data_hash": validation["data_hash"], "metrics": sample["backtest"]["metrics"]}}
    write_json(output / "evaluation_results.json", result)
    (output / "sample_console_output.txt").write_text(
        " | ".join(SAFETY_NOTICES) + "\n" + console_summary(result) + "\n", encoding="utf-8")
    return result
