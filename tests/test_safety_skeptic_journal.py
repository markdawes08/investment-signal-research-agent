"""Boundary, append-only integrity, and adversarial independent-review tests."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from signal_research_agent.coordinator import Coordinator, DEFAULT_TOPIC
from signal_research_agent.data_engineer import DataEngineer
from signal_research_agent.journal import HashChainJournal, JournalIntegrityError, verify_entries
from signal_research_agent.models import content_hash
from signal_research_agent.safety import check_request
from signal_research_agent.skeptic import Skeptic


def _rechain(entries):
    previous = "0" * 64
    for sequence, entry in enumerate(entries, start=1):
        unsigned = {"sequence": sequence, "previous_hash": previous, "payload": entry["payload"]}
        entry.clear()
        entry.update({**unsigned, "entry_hash": content_hash(unsigned)})
        previous = entry["entry_hash"]
    return entries


class SafetyTests(unittest.TestCase):
    def test_public_research_is_accepted(self):
        self.assertTrue(check_request(DEFAULT_TOPIC)["allowed"])

    def test_brokerage_action_refused(self):
        decision = check_request("Connect to my brokerage and research low volatility stocks")
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["code"], "brokerage_access")

    def test_trade_order_refused(self):
        for topic in ("Buy low volatility stocks", "Execute an order for low volatility stocks", "Place a limit order", "Trade low volatility stocks", "Open a low volatility position"):
            with self.subTest(topic=topic):
                self.assertFalse(check_request(topic)["allowed"])

    def test_personalized_advice_refused(self):
        for topic in (
            "Should I invest my retirement savings in low volatility stocks?",
            "I am 65, explore low volatility stocks suitable for me",
            "Allocate $5000 based on my risk tolerance to low volatility stocks",
            "Research low volatility stocks for my portfolio",
            "Should I hold low volatility stocks?",
            "Which low volatility stocks should I own?",
            "Recommend low volatility stocks to me",
        ):
            with self.subTest(topic=topic):
                decision = check_request(topic)
                self.assertFalse(decision["allowed"])
                self.assertTrue(decision["requires_human_intervention"])

    def test_private_data_refused_without_echo(self):
        for token in ("private", "confidential", "proprietary", "sensitive", "secret", "password"):
            with self.subTest(token=token):
                topic = f"Research low volatility with {token} FIXTURE_REDACTION_SENTINEL"
                decision = check_request(topic)
                self.assertFalse(decision["allowed"])
                self.assertNotIn("FIXTURE_REDACTION_SENTINEL", json.dumps(decision))

    def test_bare_personal_identifiers_refused(self):
        for identifier in ("research-fixture@example.invalid", "000-00-0000"):
            self.assertFalse(check_request(DEFAULT_TOPIC + " " + identifier)["allowed"])

    def test_empty_ambiguous_and_unrelated_refused(self):
        for topic in ("", "  ", "volatility", "help me research", "Explore momentum effects on returns"):
            with self.subTest(topic=topic):
                self.assertFalse(check_request(topic)["allowed"])

    def test_refused_topic_is_absent_from_all_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            topic = "Research low volatility with confidential FIXTURE_REDACTION_SENTINEL"
            result = Coordinator().run(topic, directory)
            self.assertEqual(result["status"], "rejected")
            for path in Path(directory).iterdir():
                self.assertNotIn("FIXTURE_REDACTION_SENTINEL", path.read_text(encoding="utf-8"))


class JournalTests(unittest.TestCase):
    def test_append_and_reopen_preserve_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            journal = HashChainJournal(path)
            journal.append({"event": "first"})
            original = path.read_bytes()
            reopened = HashChainJournal(path)
            reopened.append({"event": "second"})
            self.assertTrue(path.read_bytes().startswith(original))
            self.assertTrue(reopened.verify())
            self.assertEqual(len(reopened.entries()), 2)

    def test_payload_mutation_cannot_change_persisted_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = HashChainJournal(Path(directory) / "audit.jsonl")
            payload = {"nested": {"value": 1}}
            journal.append(payload)
            payload["nested"]["value"] = 2
            self.assertEqual(journal.entries()[0]["payload"]["nested"]["value"], 1)

    def test_tampered_chain_refuses_further_append(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            journal = HashChainJournal(path)
            journal.append({"event": "original"})
            path.write_text(path.read_text().replace("original", "tampered"), encoding="utf-8")
            corrupted = path.read_bytes()
            self.assertFalse(journal.verify())
            with self.assertRaises(JournalIntegrityError):
                journal.append({"event": "later"})
            with self.assertRaises(JournalIntegrityError):
                HashChainJournal(path)
            self.assertEqual(corrupted, path.read_bytes())

    def test_incomplete_final_line_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            journal = HashChainJournal(path)
            journal.append({"event": "first"})
            path.write_bytes(path.read_bytes().rstrip(b"\n"))
            self.assertFalse(journal.verify())

    def test_sequence_and_previous_hash_are_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = HashChainJournal(Path(directory) / "audit.jsonl")
            journal.append({"event": "first"})
            journal.append({"event": "second"})
            entries = journal.entries()
            entries[1]["previous_hash"] = "0" * 64
            self.assertFalse(verify_entries(entries))

    def test_writer_lock_prevents_accidental_concurrent_append(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            journal = HashChainJournal(path)
            path.with_name("audit.jsonl.lock").write_text("", encoding="utf-8")
            with self.assertRaises(JournalIntegrityError):
                journal.append({"event": "blocked"})
            self.assertFalse(path.exists())

    def test_nonfinite_payload_is_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            journal = HashChainJournal(path)
            with self.assertRaises(ValueError):
                journal.append({"value": float("nan")})
            self.assertFalse(path.exists())
            self.assertFalse(path.with_name("audit.jsonl.lock").exists())


class SkepticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.baseline = Coordinator().run(DEFAULT_TOPIC, directory)
            cls.audit = HashChainJournal(Path(directory) / "audit.jsonl").entries()[:-2]
        cls.rows = DataEngineer().generate(cls.baseline["hypothesis_lock"]["specification"])

    def inputs(self):
        return deepcopy({
            "lock": self.baseline["hypothesis_lock"], "evidence": self.baseline["evidence"],
            "validation": self.baseline["data_validation"], "backtest": self.baseline["backtest"],
            "audit_entries": self.audit, "rows": self.rows,
        })

    def replace_recorded(self, inputs, event, details):
        for entry in inputs["audit_entries"]:
            if entry["payload"]["event"] == event:
                entry["payload"]["details"] = deepcopy(details)
        _rechain(inputs["audit_entries"])

    def test_valid_baseline_passes_independent_review(self):
        review = Skeptic().review(**self.inputs())
        self.assertEqual(review["verdict"], "supported_in_synthetic_fixture_only")
        self.assertTrue(all(review["checks"].values()), review["objections"])
        self.assertFalse(review["requires_human_intervention"])

    def test_adverse_synthetic_fixture_can_be_unsupported(self):
        class AdverseFixtureEngineer(DataEngineer):
            def generate(self, specification):
                # Deliberately change the test fixture's drift without changing
                # dates, labels, or the strategy. These are no market observations.
                # Validation attests structure and hashes, not independent replay
                # of the generator seed. This injected unit fixture does not tune
                # or replace the production generator, seed, or example results.
                rows = super().generate(specification)
                dates = sorted({row["date"] for row in rows})
                month_indices = {date: index for index, date in enumerate(dates)}
                for row in rows:
                    factor = 0.97 if int(row["asset"][-2:]) <= 4 else 1.01
                    row["price"] *= factor ** month_indices[row["date"]]
                return rows

        with tempfile.TemporaryDirectory() as directory:
            result = Coordinator(data_engineer=AdverseFixtureEngineer()).run(DEFAULT_TOPIC, directory)
        self.assertLess(result["backtest"]["metrics"]["sharpe_difference"], 0)
        self.assertEqual(result["verdict"], "unsupported_in_synthetic_fixture")
        self.assertTrue(all(result["review"]["checks"].values()), result["review"]["objections"])
        self.assertFalse(result["requires_human_intervention"])

    def test_malformed_review_inputs_produce_bounded_rejection(self):
        for key in ("lock", "evidence", "validation", "backtest", "audit_entries"):
            with self.subTest(field=key):
                inputs = self.inputs()
                inputs[key] = None
                review = Skeptic().review(**inputs)
                self.assertEqual(review["verdict"], "rejected")
                self.assertTrue(review["requires_human_intervention"])

    def test_oversized_price_produces_bounded_rejection(self):
        inputs = self.inputs()
        inputs["rows"][0]["price"] = 10 ** 400
        self.assertEqual(Skeptic().review(**inputs)["verdict"], "rejected")

    def test_hypothesis_tampering_detected(self):
        inputs = self.inputs()
        inputs["lock"]["specification"]["cost_bps"] = 0
        review = Skeptic().review(**inputs)
        self.assertEqual(review["verdict"], "rejected")
        self.assertFalse(review["checks"]["hypothesis_lock"])

    def test_same_hash_altered_lock_rejected_even_with_rechained_audit(self):
        inputs = self.inputs()
        inputs["lock"]["specification"]["cost_bps"] = 0
        self.replace_recorded(inputs, "hypothesis_locked", inputs["lock"])
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["audit_chain"])
        self.assertTrue(review["checks"]["recorded_lock_unchanged"])
        self.assertFalse(review["checks"]["hypothesis_lock"])
        self.assertEqual(review["verdict"], "rejected")

    def test_insufficient_grounding_rejected(self):
        inputs = self.inputs()
        inputs["evidence"] = inputs["evidence"][:1]
        self.assertFalse(Skeptic().review(**inputs)["checks"]["grounding"])

    def test_validation_gate_cannot_be_bypassed(self):
        inputs = self.inputs()
        inputs["validation"]["passed"] = False
        self.replace_recorded(inputs, "data_validated", inputs["validation"])
        review = Skeptic().review(**inputs)
        self.assertFalse(review["checks"]["data_validation"])
        self.assertFalse(review["checks"]["outcome_isolation"])

    def test_short_observation_series_requires_human_intervention(self):
        inputs = self.inputs()
        inputs["backtest"]["observations"] = inputs["backtest"]["observations"][:24]
        self.replace_recorded(inputs, "backtest_completed", inputs["backtest"])
        review = Skeptic().review(**inputs)
        self.assertFalse(review["checks"]["observation_count"])
        self.assertTrue(review["requires_human_intervention"])

    def test_rehashed_later_lock_does_not_replace_original(self):
        inputs = self.inputs()
        inputs["lock"]["specification"]["topic"] = "A later research direction"
        digest = content_hash(inputs["lock"]["specification"])
        inputs["lock"].update(content_hash=digest, hypothesis_id="hyp-v1-" + digest[:16])
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["hypothesis_lock"])
        self.assertFalse(review["checks"]["recorded_lock_unchanged"])

    def test_tampered_trusted_source_detected_with_rehashed_audit(self):
        inputs = self.inputs()
        inputs["evidence"][0]["summary"] = "Changed fixture source summary."
        self.replace_recorded(inputs, "evidence_retrieved", {"evidence": inputs["evidence"]})
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["audit_chain"])
        self.assertFalse(review["checks"]["grounding"])

    def test_backtest_before_lock_detected_with_valid_chain(self):
        inputs = self.inputs()
        entries = inputs["audit_entries"]
        lock_index = next(i for i, entry in enumerate(entries) if entry["payload"]["event"] == "hypothesis_locked")
        backtest_index = next(i for i, entry in enumerate(entries) if entry["payload"]["event"] == "backtest_started")
        entries[lock_index], entries[backtest_index] = entries[backtest_index], entries[lock_index]
        _rechain(entries)
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["audit_chain"])
        self.assertFalse(review["checks"]["outcome_isolation"])

    def test_unbounded_search_detected(self):
        inputs = self.inputs()
        for entry in inputs["audit_entries"]:
            if entry["payload"]["event"] == "search_completed":
                entry["payload"]["details"]["nodes_visited"] = 6
        _rechain(inputs["audit_entries"])
        self.assertFalse(Skeptic().review(**inputs)["checks"]["bounded_search"])

    def test_forged_metric_detected_after_rehashing_audit(self):
        inputs = self.inputs()
        inputs["backtest"]["metrics"]["strategy"]["annualized_return"] += 1
        self.replace_recorded(inputs, "backtest_completed", inputs["backtest"])
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["recorded_backtest_unchanged"])
        self.assertFalse(review["checks"]["metric_recalculation"])

    def test_benchmark_cost_omission_detected(self):
        inputs = self.inputs()
        inputs["backtest"]["observations"][0]["benchmark_cost_fraction"] = 0
        self.replace_recorded(inputs, "backtest_completed", inputs["backtest"])
        self.assertFalse(Skeptic().review(**inputs)["checks"]["transaction_costs"])

    def test_as_of_and_availability_leakage_detected(self):
        inputs = self.inputs()
        inputs["rows"][0]["available_at"] = "2025-01-31"
        review = Skeptic().review(**inputs)
        self.assertFalse(review["checks"]["data_provenance"])
        self.assertTrue(review["requires_human_intervention"])

    def test_missing_price_rows_cannot_be_accepted_by_skeptic(self):
        inputs = self.inputs()
        inputs["rows"] = None
        self.assertEqual(Skeptic().review(**inputs)["verdict"], "rejected")

    def test_real_market_interpretation_rejected(self):
        inputs = self.inputs()
        inputs["backtest"]["methodology"]["inference"] = "Evidence of real-market profits."
        self.replace_recorded(inputs, "backtest_completed", inputs["backtest"])
        self.assertFalse(Skeptic().review(**inputs)["checks"]["synthetic_interpretation"])

    def test_repeated_runs_append_and_review_current_segment(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Coordinator().run(DEFAULT_TOPIC, directory)
            first_bytes = (Path(directory) / "audit.jsonl").read_bytes()
            second = Coordinator().run(DEFAULT_TOPIC, directory)
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertEqual(second["status"], "completed")
            self.assertEqual(first["backtest"], second["backtest"])
            self.assertTrue((Path(directory) / "audit.jsonl").read_bytes().startswith(first_bytes))
            self.assertEqual(len(HashChainJournal(Path(directory) / "research_journal.jsonl").entries()), 4)


if __name__ == "__main__":
    unittest.main()
