from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from signal_research_agent.cli import main
from signal_research_agent.coordinator import Coordinator, DEFAULT_TOPIC
from signal_research_agent.evaluation import evaluate
from signal_research_agent.hypothesis import HypothesisGenerator
from signal_research_agent.models import SAFETY_NOTICES


class EvaluationAndCliTests(unittest.TestCase):
    def test_evaluation_records_actual_acceptance_results(self):
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate(directory)
            self.assertGreaterEqual(result["total"], 16)
            self.assertEqual(result["failed"], 0, result["cases"])
            self.assertEqual(result["passed"], len(result["cases"]))
            self.assertGreater(result["elapsed_seconds"], 0)
            disk = json.loads((Path(directory) / "evaluation_results.json").read_text(encoding="utf-8"))
            self.assertEqual(result, disk)
            self.assertTrue((Path(directory) / "sample_console_output.txt").exists())

    def test_failed_baseline_still_emits_machine_readable_evaluation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(Coordinator, "run", side_effect=ValueError):
            result = evaluate(directory)
            self.assertEqual(result["failed"], 1)
            self.assertEqual(result["passed"], 0)
            self.assertTrue(result["requires_human_intervention"])
            self.assertTrue((Path(directory) / "evaluation_results.json").exists())

    def test_corpus_is_json_with_six_sources_and_notices(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["corpus"]), 0)
        value = json.loads(output.getvalue())
        self.assertEqual(len(value["sources"]), 6)
        self.assertEqual(value["safety_notices"], list(SAFETY_NOTICES))

    def test_workflow_needs_no_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(socket, "socket", side_effect=AssertionError("Network prohibited")):
            result = Coordinator().run(DEFAULT_TOPIC, directory)
            self.assertEqual(result["status"], "completed")

    def test_search_budget_and_isolation_fail_before_data_generation(self):
        for field, value in (("nodes_visited", 100), ("max_depth", 3), ("outcome_access", True)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                class AlteredGenerator(HypothesisGenerator):
                    def generate(self, topic, evidence):
                        result = super().generate(topic, evidence)
                        result["search"][field] = value
                        return result

                with patch("signal_research_agent.coordinator.DataEngineer.generate", side_effect=AssertionError("Must not generate data")):
                    result = Coordinator(generator=AlteredGenerator()).run(DEFAULT_TOPIC, directory)
                self.assertEqual(result["verdict"], "rejected")
                self.assertIsNone(result["data_validation"])
                self.assertIsNone(result["backtest"])

    def test_retrieval_error_creates_safe_refusal_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("signal_research_agent.coordinator.LiteratureRetriever.search", side_effect=ValueError("sensitive-injected-message")):
                result = Coordinator().run(DEFAULT_TOPIC, directory)
            self.assertEqual(result["verdict"], "rejected")
            for path in Path(directory).iterdir():
                self.assertNotIn("sensitive-injected-message", path.read_text(encoding="utf-8"))

    def test_operational_cli_error_has_nonzero_exit(self):
        with patch.object(Coordinator, "run", side_effect=ValueError), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["run", "--topic", DEFAULT_TOPIC]), 2)

    def test_all_completed_and_refused_artifacts_have_every_scope_notice(self):
        for topic in (DEFAULT_TOPIC, "Access my brokerage account"):
            with self.subTest(topic=topic), tempfile.TemporaryDirectory() as directory:
                Coordinator().run(topic, directory)
                for name in ("result.json", "research_report.md", "audit.jsonl", "research_journal.jsonl"):
                    text = (Path(directory) / name).read_text(encoding="utf-8")
                    for notice in SAFETY_NOTICES:
                        self.assertIn(notice, text, name)


if __name__ == "__main__":
    unittest.main()
