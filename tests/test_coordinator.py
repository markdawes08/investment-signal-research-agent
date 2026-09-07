"""Integrated workflow, stopping gates, privacy, and persistent audit behavior."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from signal_research_agent.cli import main
from signal_research_agent.coordinator import Coordinator, DEFAULT_TOPIC
from signal_research_agent.data_engineer import DataEngineer
from signal_research_agent.hypothesis import HypothesisGenerator
from signal_research_agent.journal import HashChainJournal
from signal_research_agent.models import SAFETY_NOTICES


ARTIFACTS = ("result.json", "research_report.md", "audit.jsonl", "research_journal.jsonl")


class DuplicateEngineer(DataEngineer):
    def generate(self, spec):
        rows = super().generate(spec)
        rows.append(deepcopy(rows[0]))
        return rows


class TamperingGenerator(HypothesisGenerator):
    def generate(self, topic, evidence):
        proposal = super().generate(topic, evidence)
        proposal["lock"]["specification"]["selection_count"] = 3
        return proposal


class MutatingValidator(DataEngineer):
    def validate(self, rows, spec):
        result = super().validate(rows, spec)
        spec["cost_bps"] = 0.0
        return result


class OverflowEngineer(DataEngineer):
    def generate(self, spec):
        rows = super().generate(spec)
        for row in rows:
            if row["asset"] == "SYN01":
                row["price"] = 1e-300 if row["date"] == "2014-12-31" else 1e300
        return rows


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_end_to_end_workflow_completion_and_all_artifacts(self):
        result = Coordinator().run(DEFAULT_TOPIC, self.directory)
        self.assertEqual(result["status"], "completed", result["review"])
        self.assertIn(result["verdict"], {"supported_in_synthetic_fixture_only", "unsupported_in_synthetic_fixture"})
        self.assertFalse(result["requires_human_intervention"])
        self.assertEqual(result["backtest"]["metrics"]["observation_count"], 108)
        self.assertTrue(all(result["review"]["checks"].values()), result["review"])
        for name in ARTIFACTS:
            self.assertTrue((self.directory / name).is_file(), name)
        self.assertEqual(json.loads((self.directory / "result.json").read_text(encoding="utf-8")), result)
        report = (self.directory / "research_report.md").read_text(encoding="utf-8")
        for notice in SAFETY_NOTICES:
            self.assertIn(notice, report)
        self.assertFalse((self.directory / ".run.lock").exists())

    def test_all_five_roles_represented_and_outcomes_follow_lock(self):
        Coordinator().run(DEFAULT_TOPIC, self.directory)
        entries = HashChainJournal(self.directory / "audit.jsonl").entries()
        payloads = [entry["payload"] for entry in entries]
        self.assertEqual({item["role"] for item in payloads}, {
            "Coordinator", "Hypothesis Generator", "Data Engineer", "Backtester", "Skeptic",
        })
        events = [item["event"] for item in payloads]
        self.assertLess(events.index("search_completed"), events.index("hypothesis_locked"))
        self.assertLess(events.index("hypothesis_locked"), events.index("data_generated"))
        self.assertLess(events.index("data_validated"), events.index("backtest_started"))
        self.assertLess(events.index("backtest_completed"), events.index("review_completed"))
        search = next(item["details"] for item in payloads if item["event"] == "search_completed")
        self.assertLessEqual(search["nodes_visited"], search["max_nodes"])
        self.assertFalse(search["outcome_access"])

    def test_full_fresh_directory_artifacts_replay_byte_for_byte(self):
        first, second = self.directory / "first", self.directory / "second"
        first_result = Coordinator().run(DEFAULT_TOPIC, first)
        second_result = Coordinator().run(DEFAULT_TOPIC, second)
        self.assertEqual(first_result, second_result)
        for name in ARTIFACTS:
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

    def test_rerun_same_directory_retains_both_journal_prefixes(self):
        first = Coordinator().run(DEFAULT_TOPIC, self.directory)
        journals = ("audit.jsonl", "research_journal.jsonl")
        prefixes = {name: (self.directory / name).read_bytes() for name in journals}
        original_counts = {name: len(HashChainJournal(self.directory / name).entries()) for name in journals}
        second = Coordinator().run(DEFAULT_TOPIC, self.directory)
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["hypothesis_lock"], second["hypothesis_lock"])
        self.assertEqual(first["backtest"], second["backtest"])
        self.assertEqual(second["status"], "completed", second["review"])
        for name in journals:
            self.assertTrue((self.directory / name).read_bytes().startswith(prefixes[name]), name)
            journal = HashChainJournal(self.directory / name)
            self.assertTrue(journal.verify())
            self.assertEqual(len(journal.entries()), 2 * original_counts[name])

    def test_blocked_private_request_emits_all_artifacts_without_raw_input(self):
        marker = "confidential_portfolio_marker_xyz"
        request = "Explore stock volatility using confidential customer data " + marker
        never = Mock()
        result = Coordinator(retriever=never).run(request, self.directory)
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(result["requires_human_intervention"])
        self.assertIsNone(result["topic"])
        self.assertIsNone(result["backtest"])
        never.search.assert_not_called()
        for name in ARTIFACTS:
            text = (self.directory / name).read_text(encoding="utf-8")
            self.assertNotIn(marker, text)
            self.assertNotIn(request, text)

    def test_failed_validation_never_invokes_backtester(self):
        never = Mock()
        result = Coordinator(data_engineer=DuplicateEngineer(), backtester=never).run(DEFAULT_TOPIC, self.directory)
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["data_validation"]["passed"])
        self.assertTrue(result["requires_human_intervention"])
        self.assertIsNone(result["backtest"])
        never.run.assert_not_called()
        events = [entry["payload"]["event"] for entry in HashChainJournal(self.directory / "audit.jsonl").entries()]
        self.assertNotIn("backtest_started", events)
        for name in ARTIFACTS:
            self.assertTrue((self.directory / name).exists())

    def test_altered_lock_rejected_before_data_generation(self):
        never = Mock()
        result = Coordinator(generator=TamperingGenerator(), data_engineer=never).run(DEFAULT_TOPIC, self.directory)
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(result["requires_human_intervention"])
        self.assertIsNone(result["data_validation"])
        never.generate.assert_not_called()

    def test_validator_cannot_mutate_lock_and_proceed(self):
        never = Mock()
        result = Coordinator(data_engineer=MutatingValidator(), backtester=never).run(DEFAULT_TOPIC, self.directory)
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(result["requires_human_intervention"])
        self.assertEqual(result["hypothesis_lock"]["specification"]["cost_bps"], 10.0)
        never.run.assert_not_called()

    def test_derived_numeric_overflow_emits_rejected_artifacts(self):
        result = Coordinator(data_engineer=OverflowEngineer()).run(DEFAULT_TOPIC, self.directory)
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(result["requires_human_intervention"])
        self.assertIsNone(result["backtest"])
        for name in ARTIFACTS:
            self.assertTrue((self.directory / name).is_file(), name)

    def test_corrupt_existing_journals_and_summaries_are_never_overwritten(self):
        for target in ("audit.jsonl", "research_journal.jsonl"):
            with self.subTest(target=target):
                output = self.directory / target.replace(".", "_")
                Coordinator().run(DEFAULT_TOPIC, output)
                with (output / target).open("ab") as handle:
                    handle.write(b'{"corrupted":true}\n')
                before = {name: (output / name).read_bytes() for name in ARTIFACTS}
                with self.assertRaises(ValueError):
                    Coordinator().run(DEFAULT_TOPIC, output)
                self.assertEqual(before, {name: (output / name).read_bytes() for name in ARTIFACTS})
                self.assertFalse((output / ".run.lock").exists())

    def test_active_run_lock_blocks_without_overwriting_files(self):
        lease = self.directory / ".run.lock"
        lease.write_text("existing process marker", encoding="utf-8")
        with self.assertRaises(ValueError):
            Coordinator().run(DEFAULT_TOPIC, self.directory)
        self.assertEqual(lease.read_text(encoding="utf-8"), "existing process marker")
        self.assertFalse((self.directory / "result.json").exists())

    def test_cli_completed_and_refused_exit_codes_and_notices(self):
        for topic, expected in ((DEFAULT_TOPIC, 0), ("Place a market order", 2)):
            with self.subTest(topic=topic):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = main(["run", "--topic", topic, "--output-dir", str(self.directory / str(expected))])
                self.assertEqual(code, expected, stream.getvalue())
                for notice in SAFETY_NOTICES:
                    self.assertIn(notice, stream.getvalue())

    def test_cli_integrity_error_is_concise_and_requires_intervention(self):
        (self.directory / "audit.jsonl").write_text("invalid JSON\n", encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["run", "--topic", DEFAULT_TOPIC, "--output-dir", str(self.directory)])
        self.assertEqual(code, 2)
        self.assertIn("Human intervention required", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertEqual((self.directory / "audit.jsonl").read_text(encoding="utf-8"), "invalid JSON\n")


if __name__ == "__main__":
    unittest.main()
