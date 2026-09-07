"""Regression checks for live-batch failure reporting; no real provider calls."""

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
from pathlib import Path
import unittest

from test_llm_design import proposal_fixture
import test_llm_workflow as workflow_fixtures


class LiveDiagnosticTests(unittest.TestCase):
    setUp = workflow_fixtures.LLMWorkflowTests.setUp
    execute = workflow_fixtures.LLMWorkflowTests.execute
    assert_stopped_before_data = workflow_fixtures.LLMWorkflowTests.assert_stopped_before_data
    events = workflow_fixtures.LLMWorkflowTests.events

    def test_wrong_revision_shape_records_concrete_objections(self):
        wrong_revision = proposal_fixture(6, 3)
        for index, parameters in enumerate(((6, 4), (12, 3)), 2):
            candidate = deepcopy(proposal_fixture(*parameters)["candidates"][0])
            candidate["id"] = f"extra{index}"
            wrong_revision["candidates"].append(candidate)
        result = self.execute(workflow_fixtures.ScriptedProvider(proposal_fixture(9, 3), wrong_revision))
        self.assertEqual(result["status"], "malformed_output")
        self.assert_stopped_before_data(result)
        failure = result["validation_failures"][0]
        self.assertEqual(failure["depth"], 2)
        self.assertIn("Expected action revise at this search depth.", failure["errors"])
        self.assertIn("Revision beam width is limited to two candidates.", failure["errors"])
        self.assertTrue(any("Revision parent_id" in error
                            for row in failure["candidate_errors"] for error in row["errors"]))
        recorded = [event for event in self.events() if event["event"] == "candidate_output_rejected"]
        self.assertEqual(recorded[0]["details"], failure)
        self.assertIn("Round 2 returned 3", result["review"]["objections"][0])

    def test_live_console_includes_status_and_validation_reason(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "run_live_verification.py"
        spec = importlib.util.spec_from_file_location("live_verification_diagnostic_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = io.StringIO()
        with redirect_stdout(output):
            module.print_run_summary({"name": "A_research", "status": "malformed_output",
                                      "actual_provider_calls": 2,
                                      "stop_reasons": ["Round 2 returned 3 candidates; maximum is 2."],
                                      "validation_failures": [{"errors": ["Expected action revise at this search depth."]}]})
        self.assertIn("A_research: malformed_output", output.getvalue())
        self.assertIn("maximum is 2", output.getvalue())
        self.assertIn("Expected action revise", output.getvalue())

    def test_live_console_reports_termination_reason_and_unknowns(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "run_live_verification.py"
        spec = importlib.util.spec_from_file_location("live_verification_termination_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = io.StringIO()
        with redirect_stdout(output):
            module.print_run_summary({"name": "A_research", "status": "provider_incomplete",
                "actual_provider_calls": 1, "provider_execution": {"calls": [{
                    "status": "provider_incomplete", "provider_response_status": "incomplete",
                    "incomplete_reason": "max_output_tokens", "provider_error_code": None,
                    "requested_max_output_tokens": 2500, "usage": {"output_tokens": 0},
                    "message": "RAW_PROVIDER_MESSAGE_MUST_NOT_BE_PRINTED"}]}})
        text = output.getvalue()
        self.assertIn("incomplete_reason: max_output_tokens", text)
        self.assertIn("provider_error_code: unknown", text)
        self.assertIn("Requested output cap: 2500; reported output tokens: 0", text)
        self.assertNotIn("RAW_PROVIDER_MESSAGE_MUST_NOT_BE_PRINTED", text)


if __name__ == "__main__":
    unittest.main()
