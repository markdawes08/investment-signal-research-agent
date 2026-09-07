"""Grounding, bounded exploration, and lock integrity tests."""

from copy import deepcopy
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from signal_research_agent.hypothesis import HypothesisGenerator, grounding_issues, verify_lock
from signal_research_agent.retrieval import LiteratureRetriever


TOPIC = "Explore whether lower-volatility stocks have better risk-adjusted returns"


class RetrievalHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.retriever = LiteratureRetriever()
        self.evidence = self.retriever.search(TOPIC + " backtesting research protocol overfitting")

    def test_retrieval_grounding_has_six_identifiable_original_summaries(self):
        self.assertEqual(len(self.retriever.sources), 6)
        self.assertEqual(len({item["id"] for item in self.retriever.sources}), 6)
        self.assertEqual(grounding_issues(self.evidence), [])
        for source in self.retriever.sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertFalse(source["contains_numerical_dataset"])
            self.assertLess(len(source["summary"].split()), 100)

    def test_retrieval_semantics_and_determinism(self):
        query = "idiosyncratic residual volatility factor regression"
        results = self.retriever.search(query, limit=3)
        self.assertEqual(results, self.retriever.search(query, limit=3))
        self.assertIn("ang-2004-volatility", [item["id"] for item in results])
        results[0]["title"] = "modified"
        self.assertNotEqual(self.retriever.search(query, limit=3)[0]["title"], "modified")
        self.assertEqual(self.retriever.search(""), [])
        self.assertEqual(self.retriever.search("xyzzyunrelatedword"), [])

    def test_numerical_datasets_cannot_be_indexed_as_prose(self):
        source = deepcopy(self.retriever.sources[0])
        source["kind"] = "numerical_dataset"
        source["contains_numerical_dataset"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "corpus.json"
            path.write_text(json.dumps([source]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "structured data"):
                LiteratureRetriever(path)

    def test_bounded_pre_outcome_search_compares_all_three_definitions(self):
        generated = HypothesisGenerator().generate(TOPIC, self.evidence)
        search = generated["search"]
        self.assertFalse(generated["requires_human_intervention"])
        self.assertEqual({item["definition"] for item in search["alternatives"]},
                         {"total_volatility", "beta", "idiosyncratic_volatility"})
        self.assertLessEqual(search["nodes_visited"], search["max_nodes"])
        self.assertEqual(search["nodes_visited"], 5)
        self.assertFalse(search["outcome_access"])
        self.assertEqual(search["selected"], "total_volatility")
        self.assertEqual(len(search["revisions"]), 1)
        self.assertTrue(all(item["before_lock"] for item in search["revisions"]))
        self.assertTrue(all(item["depth"] <= search["max_depth"] for item in search["trace"]))
        self.assertTrue(all(len(item["retained"]) <= search["beam_width"] for item in search["trace"]))
        self.assertEqual(list(inspect.signature(HypothesisGenerator.generate).parameters), ["self", "topic", "evidence"])

    def test_retrieval_scores_cannot_select_a_different_hypothesis(self):
        changed = deepcopy(self.evidence)
        for source in changed:
            source["score"] = 999999 if source["id"] == "ang-2004-volatility" else -999999
        first = HypothesisGenerator().generate(TOPIC, self.evidence)
        second = HypothesisGenerator().generate(TOPIC, changed)
        self.assertEqual(first, second)

    def test_deterministic_replay_and_stable_versioned_lock(self):
        first = HypothesisGenerator().generate(TOPIC, self.evidence)
        second = HypothesisGenerator().generate(TOPIC, list(reversed(self.evidence)))
        self.assertEqual(first, second)
        self.assertTrue(verify_lock(first["lock"]))
        self.assertTrue(first["lock"]["hypothesis_id"].startswith("hyp-v1-"))
        self.assertEqual(first["lock"]["specification"]["lookback_months"], 12)
        self.assertEqual(len(first["lock"]["specification"]["universe"]), 12)

    def test_hypothesis_tampering_is_detected(self):
        original = HypothesisGenerator().generate(TOPIC, self.evidence)["lock"]
        for field, replacement in [("cost_bps", 0.0), ("lookback_months", 6), ("selection_count", 1)]:
            lock = deepcopy(original)
            lock["specification"][field] = replacement
            self.assertFalse(verify_lock(lock), field)
        lock = deepcopy(original)
        lock["locked"] = False
        self.assertFalse(verify_lock(lock))
        lock = deepcopy(original)
        lock["hypothesis_id"] = "invented"
        self.assertFalse(verify_lock(lock))
        self.assertFalse(verify_lock({}))
        self.assertFalse(verify_lock(None))

    def test_insufficient_grounding_requires_human_intervention(self):
        generated = HypothesisGenerator().generate(TOPIC, self.evidence[:1])
        self.assertIsNone(generated["lock"])
        self.assertTrue(generated["requires_human_intervention"])
        self.assertEqual(generated["search"]["nodes_visited"], 0)

    def test_conflicting_grounding_requires_human_intervention(self):
        evidence = deepcopy(self.evidence)
        evidence[0]["stance"] = "conflicting"
        generated = HypothesisGenerator().generate(TOPIC, evidence)
        self.assertIsNone(generated["lock"])
        self.assertTrue(generated["requires_human_intervention"])
        self.assertTrue(any("conflict" in issue for issue in generated["objections"]))

    def test_source_metadata_tampering_requires_human_intervention(self):
        evidence = deepcopy(self.evidence)
        evidence[0]["summary"] = "Unverified claim."
        generated = HypothesisGenerator().generate(TOPIC, evidence)
        self.assertIsNone(generated["lock"])
        self.assertTrue(generated["requires_human_intervention"])

    def test_outcome_payload_in_evidence_is_rejected(self):
        evidence = deepcopy(self.evidence)
        evidence[0]["backtest_outcome"] = {"sharpe_ratio": 10.0}
        generated = HypothesisGenerator().generate(TOPIC, evidence)
        self.assertIsNone(generated["lock"])
        self.assertTrue(generated["requires_human_intervention"])

    def test_malformed_evidence_fails_closed(self):
        for malformed in (None, [None], [{"id": [], "stance": []}]):
            self.assertTrue(grounding_issues(malformed))


if __name__ == "__main__":
    unittest.main()
