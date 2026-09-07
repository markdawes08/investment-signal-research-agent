"""Bounded resume tests using fabricated application records and zero HTTP calls.

The fixture emulates OpenAI metadata solely to test provenance validation. None
of the temporary artifacts or tests establishes actual live-provider execution.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_llm_design import proposal_fixture
from test_llm_workflow import ScriptedProvider, revision


def load_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_live_verification.py"
    spec = importlib.util.spec_from_file_location("resume_verification_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EmulatedApplicationProvider(ScriptedProvider):
    """Explicit test-only transport substitute, never an SDK or HTTP client."""

    model = "gpt-test-transport-fixture"

    def __init__(self, *responses, actual_flag=True):
        super().__init__(*responses)
        self.actual_flag = actual_flag

    def generate(self, context):
        result = super().generate(context)
        result["metadata"].update(provider="openai", actual_provider_call=self.actual_flag,
                                  actual_model=self.model, response_id=f"resp_test_only_{len(self.contexts)}",
                                  requested_model=self.model)
        return result


class LiveResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture_directory.cleanup)
        cls.fixture = Path(cls.fixture_directory.name)
        module = load_script()
        provider = EmulatedApplicationProvider(
            proposal_fixture(), proposal_fixture(), proposal_fixture(9, 3),
            lambda context: revision(context, lookback=9), proposal_fixture())
        with patch.object(module, "OpenAIProvider", return_value=provider), redirect_stdout(io.StringIO()):
            status = module.main(["--output-dir", str(cls.fixture)])
        if status != 2 or len(provider.contexts) != 5:
            raise AssertionError("The emulated original A/B/C/D batch did not match the required five-call fixture.")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name)
        self.source = self.output / "batch_001"
        shutil.copytree(self.fixture / "batch_001", self.source)
        self.module = load_script()

    def summary(self, path=None):
        return json.loads((path or self.output / "live_verification_results.json").read_text(encoding="utf-8"))

    def original_bytes(self):
        return {str(path.relative_to(self.source)): path.read_bytes() for path in self.source.rglob("*") if path.is_file()}

    def run_resume(self, provider, *options):
        output = io.StringIO()
        with patch.object(self.module, "OpenAIProvider", return_value=provider), redirect_stdout(output):
            status = self.module.main(["--resume-batch", str(self.source), *options])
        return status, output.getvalue()

    def assert_rejected_without_provider(self):
        with patch.object(self.module, "BatchProvider") as provider, redirect_stdout(io.StringIO()):
            status = self.module.main(["--resume-batch", str(self.source)])
        self.assertEqual(status, 2)
        provider.assert_not_called()
        self.assertFalse((self.output / "batch_002").exists())

    def test_verified_resume_only_calls_c_and_keeps_prior_failures_in_budget(self):
        original = self.original_bytes()
        provider = EmulatedApplicationProvider(proposal_fixture(9, 3), lambda context: revision(context, same_close=True))
        status, console = self.run_resume(provider)
        self.assertEqual(status, 0, console)
        result = self.summary()
        self.assertTrue(result["live_verified"])
        self.assertEqual(result["verification_kind"], "real_provider_resume_batch")
        self.assertEqual((result["previous_provider_calls"], result["new_provider_calls"], result["actual_provider_calls"]), (5, 2, 7))
        self.assertEqual((result["previous_provider_attempts"], result["new_provider_attempts"], result["provider_attempts"]), (5, 2, 7))
        self.assertLessEqual(result["provider_attempts"], 16)
        self.assertEqual(len(provider.contexts), 2)
        self.assertEqual(result["prior_runs"][2]["name"], "C_controlled_feedback")
        self.assertEqual(result["prior_runs"][2]["actual_provider_calls"], 2)
        self.assertEqual(result["prior_runs"][2]["status"], "revision_budget_exhausted")
        for run in result["runs"]:
            self.assertTrue((self.output / run["result_path"]).is_file())
            self.assertEqual(run["reused_verified_evidence"], run["name"] != "C_controlled_feedback")
        self.assertFalse((self.output / "batch_002" / "A_research").exists())
        self.assertFalse((self.output / "batch_002" / "B_duplicate").exists())
        self.assertFalse((self.output / "batch_002" / "D_explicit_choices").exists())
        reservation = self.summary(self.output / "batch_002" / "resume_reservation.json")
        self.assertEqual(reservation["reserved_max_attempts"], 4)
        self.assertEqual(reservation["aggregate_reserved_max_attempts"], 9)
        self.assertEqual(reservation["source_summary_hash"], result["resume_source"]["summary_hash"])
        self.assertEqual(self.original_bytes(), original)
        self.assertIn("aggregate actual calls: 7", console)

    def test_source_validator_accepts_eligible_original_batch_without_a_provider(self):
        with patch.object(self.module, "BatchProvider") as provider:
            source, summary, results, digest = self.module._verify_resume_source(self.source, self.output)
        provider.assert_not_called()
        self.assertEqual(source, self.source.resolve())
        self.assertEqual(summary["provider_attempts"], 5)
        self.assertEqual(set(results), set(self.module._RUN_NAMES))
        self.assertEqual(len(digest), 64)

    def test_changed_result_is_rejected_before_provider(self):
        path = self.source / "A_research" / "result.json"
        result = self.summary(path)
        result["hypothesis_lock"]["specification"]["selection_count"] = 4
        path.write_text(json.dumps(result), encoding="utf-8")
        self.assert_rejected_without_provider()

    def test_changed_audit_or_research_journal_is_rejected_before_provider(self):
        for filename in ("audit.jsonl", "research_journal.jsonl"):
            path = self.source / "C_controlled_feedback" / filename
            original = path.read_bytes()
            path.write_bytes(original.rstrip(b"\n"))
            self.assert_rejected_without_provider()
            path.write_bytes(original)

    def test_changed_summary_count_cannot_drop_previous_failed_calls(self):
        path = self.source / "live_verification_results.json"
        result = self.summary(path)
        result["actual_provider_calls"] = 3
        result["provider_attempts"] = 3
        path.write_text(json.dumps(result), encoding="utf-8")
        self.assert_rejected_without_provider()

    def test_summary_provider_metadata_must_match_audited_application_metadata(self):
        path = self.source / "live_verification_results.json"
        result = self.summary(path)
        result["runs"][0]["provider_execution"]["calls"][0]["actual_model"] = "fabricated-model"
        path.write_text(json.dumps(result), encoding="utf-8")
        self.assert_rejected_without_provider()

    def test_result_reference_cannot_escape_expected_run_directory(self):
        path = self.source / "live_verification_results.json"
        result = self.summary(path)
        result["runs"][0]["result_path"] = "../other_project/result.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        self.assert_rejected_without_provider()

    def test_only_original_batches_with_a_b_d_passed_and_c_failed_are_eligible(self):
        path = self.source / "live_verification_results.json"
        result = self.summary(path)
        result["checks"]["A_genuine_research"] = False
        path.write_text(json.dumps(result), encoding="utf-8")
        self.assert_rejected_without_provider()

    def test_failed_resume_is_preserved_and_reports_specific_incomplete_check(self):
        original = self.original_bytes()
        provider = EmulatedApplicationProvider(proposal_fixture(9, 3), lambda context: revision(context, lookback=9))
        status, _ = self.run_resume(provider)
        self.assertEqual(status, 2)
        result = self.summary()
        self.assertFalse(result["checks"]["C_controlled_feedback"])
        self.assertTrue(any("C_controlled_feedback" in text for text in result["incomplete_checks"]))
        self.assertEqual(result["actual_provider_calls"], 7)
        self.assertEqual(self.original_bytes(), original)

    def test_valid_deferral_after_actual_feedback_is_accepted_for_c(self):
        deferred = {"action": "defer", "candidates": [], "selected_candidate_id": None,
                    "decision_rationale": "The controlled methodology objection requires human review before execution.",
                    "deferral_reason": "I defer this experiment until the requested execution assumption is reviewed."}
        status, console = self.run_resume(EmulatedApplicationProvider(proposal_fixture(9, 3), deferred))
        self.assertEqual(status, 0, console)
        result = self.summary()
        self.assertTrue(result["checks"]["C_controlled_feedback"])
        self.assertEqual(result["runs"][2]["status"], "model_deferred")

    def test_missing_credentials_does_not_claim_new_live_verification(self):
        provider = EmulatedApplicationProvider("missing_credentials", actual_flag=False)
        status, console = self.run_resume(provider)
        self.assertEqual(status, 2)
        result = self.summary()
        self.assertEqual(result["status"], "blocked_missing_credentials")
        self.assertEqual(result["new_provider_calls"], 0)
        self.assertEqual(result["actual_provider_calls"], 5)
        self.assertEqual(result["provider_attempts"], 6)
        self.assertEqual(result["required_environment_variable"], "OPENAI_API_KEY")
        self.assertIn("Configure OPENAI_API_KEY locally", console)

    def test_synthetic_test_transport_cannot_pass_live_c_without_actual_call_flag(self):
        provider = EmulatedApplicationProvider(proposal_fixture(9, 3),
                                                lambda context: revision(context, same_close=True), actual_flag=False)
        status, _ = self.run_resume(provider)
        self.assertEqual(status, 2)
        self.assertFalse(self.summary()["live_verified"])
        self.assertEqual(self.summary()["new_provider_calls"], 0)

    def test_second_resume_cannot_reset_the_original_source_budget(self):
        self.run_resume(EmulatedApplicationProvider(proposal_fixture(9, 3), lambda context: revision(context, lookback=9)))
        with patch.object(self.module, "BatchProvider") as provider, redirect_stdout(io.StringIO()):
            status = self.module.main(["--resume-batch", str(self.source)])
        self.assertEqual(status, 2)
        provider.assert_not_called()
        self.assertFalse((self.output / "batch_003").exists())

    def test_resume_output_cannot_detach_from_verified_relative_references(self):
        with patch.object(self.module, "BatchProvider") as provider, redirect_stdout(io.StringIO()):
            status = self.module.main(["--resume-batch", str(self.source), "--output-dir", str(self.output / "elsewhere")])
        self.assertEqual(status, 2)
        provider.assert_not_called()

    def test_active_or_stale_parent_lease_prevents_provider(self):
        lease = self.output / ".run.lock"
        lease.write_text("", encoding="utf-8")
        with patch.object(self.module, "BatchProvider") as provider, redirect_stdout(io.StringIO()):
            status = self.module.main(["--resume-batch", str(self.source)])
        self.assertEqual(status, 2)
        provider.assert_not_called()
        self.assertTrue(lease.exists())
        self.assertFalse((self.output / "batch_002").exists())

    def test_concurrent_resume_cannot_enter_while_first_holds_parent_lease(self):
        inner_status = []
        def during_first_call(context):
            inner_status.append(self.module.main(["--resume-batch", str(self.source)]))
            return proposal_fixture(9, 3)
        provider = EmulatedApplicationProvider(during_first_call, lambda context: revision(context, same_close=True))
        status, _ = self.run_resume(provider)
        self.assertEqual(status, 0)
        self.assertEqual(inner_status, [2])
        self.assertEqual(len(provider.contexts), 2)
        self.assertFalse((self.output / "batch_003").exists())
        self.assertFalse((self.output / ".run.lock").exists())

    def test_interruption_after_reservation_cannot_reset_provider_budget(self):
        def interrupted_constructor(*args, **kwargs):
            reservation = self.output / "batch_002" / "resume_reservation.json"
            self.assertTrue(reservation.is_file())
            raise RuntimeError("simulated process interruption before summary")
        with patch.object(self.module, "BatchProvider", side_effect=interrupted_constructor):
            with self.assertRaises(RuntimeError):
                self.module.main(["--resume-batch", str(self.source)])
        self.assertFalse((self.output / "batch_002" / "live_verification_results.json").exists())
        self.assertTrue((self.output / "batch_002" / "resume_reservation.json").is_file())
        self.assertFalse((self.output / ".run.lock").exists())
        with patch.object(self.module, "BatchProvider") as provider, redirect_stdout(io.StringIO()):
            status = self.module.main(["--resume-batch", str(self.source)])
        self.assertEqual(status, 2)
        provider.assert_not_called()
        self.assertFalse((self.output / "batch_003").exists())

    def test_original_default_batch_reports_every_incomplete_check(self):
        result = self.summary(self.source / "live_verification_results.json")
        self.assertEqual(result["actual_provider_calls"], 5)
        self.assertEqual(result["checks"], {"A_genuine_research": True, "B_persisted_duplicate": True,
                                          "C_controlled_feedback": False, "D_explicit_supported_choices": True})
        self.assertTrue(any("C_controlled_feedback" in text for text in result["incomplete_checks"]))


if __name__ == "__main__":
    unittest.main()
