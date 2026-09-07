"""Independent numerical and provenance checks for the optional design choices.

All provider records here are deliberately mocked; these are not live results.
"""

from copy import deepcopy
import statistics
import unittest

from signal_research_agent.backtester import Backtester, SUPPORTED_SPECIFICATION
from signal_research_agent.coordinator import DEFAULT_TOPIC
from signal_research_agent.data_engineer import DataEngineer
from signal_research_agent.experiment import build_llm_lock, specification_issues, supported_choices
from signal_research_agent.hypothesis import verify_lock
from signal_research_agent.models import ResearchError, content_hash
from signal_research_agent.retrieval import LiteratureRetriever
from signal_research_agent.skeptic import Skeptic, _bounded_search, _supported_specification


def candidate(evidence, lookback=6, count=3):
    claims = []
    for stance in ("supports_total_volatility_research", "methodological_caution"):
        source = next(item for item in evidence if item["stance"] == stance)
        claims.append({"claim": source["summary"], "source_id": source["id"],
                       "summary_excerpt": source["summary"]})
    return {
        "id": "candidate_a", "parent_id": None, "signal": "total_volatility",
        "research_claim": "Lower trailing total volatility has higher net Sharpe in the fixed synthetic fixture.",
        "lookback_months": lookback, "selection_count": count, "evidence_claims": claims,
        "assumptions": ["Monthly returns are an educational design choice with a fixed synthetic fixture."],
        "decision_rationale": "Choose a supported total-volatility comparison motivated by the retrieved research.",
        "limitations": ["A synthetic fixture cannot establish evidence about observed market returns."],
        "parameter_basis": "agent_design_choice", "adaptation_rationale": None,
    }


def mock_search(node):
    proposal = {"action": "propose", "candidates": [node], "selected_candidate_id": node["id"],
                "decision_rationale": "Use a grounded feasible design before any generated prices are available.",
                "deferral_reason": None}
    assessment = {"candidate": node, "valid": True, "errors": [], "score": 10,
                  "score_breakdown": {"grounding": 3, "methodological_suitability": 2,
                                      "feasibility": 3, "question_fit": 2}}
    return {"method": "llm_bounded_candidate_search", "mode": "llm",
            "max_initial_candidates": 3, "beam_width": 2, "max_depth": 2,
            "max_revisions": 1, "max_provider_calls": 4, "provider_calls": 1,
            "outcome_access": False,
            "rounds": [{"depth": 1, "proposal": proposal, "candidates": [assessment], "retained": [node["id"]]}],
            "feedback": [], "selected_candidate_id": node["id"], "selected_candidate": node,
            "replication_rationale": None}


def rechain(payloads):
    entries, previous = [], "0" * 64
    for position, payload in enumerate(payloads, 1):
        unsigned = {"sequence": position, "previous_hash": previous, "payload": payload}
        previous = content_hash(unsigned)
        entries.append({**unsigned, "entry_hash": previous})
    return entries


class ModeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = LiteratureRetriever().search(DEFAULT_TOPIC)

    def reviewed_inputs(self, lookback=6, count=3, node=None, topic=DEFAULT_TOPIC):
        node = node or candidate(self.evidence, lookback, count)
        lock = build_llm_lock(topic, node, self.evidence)
        rows = DataEngineer().generate(lock["specification"])
        validation = DataEngineer().validate(rows, lock["specification"])
        backtest = Backtester().run(lock, rows, validation)
        search = mock_search(node)
        records = [
            ("Coordinator", "request_accepted", {"mode": "llm", "topic": topic}),
            ("Hypothesis Generator", "evidence_retrieved", {"evidence": self.evidence}),
            ("Coordinator", "memory_retrieved", {"records": [], "record_ids": [], "journal_head": "0" * 64}),
            ("Hypothesis Generator", "provider_call_completed", {"call_index": 1, "round": 1,
                "metadata": {"test_double": True}, "status": "completed", "output": search["rounds"][0]["proposal"],
                "context_hash": content_hash({}), "prompt_version": "test", "schema_version": "test"}),
            ("Coordinator", "candidates_assessed", search["rounds"][0]),
            ("Hypothesis Generator", "search_completed", search),
            ("Hypothesis Generator", "hypothesis_locked", lock),
            ("Data Engineer", "data_generated", {"data_hash": content_hash(rows), "row_count": len(rows)}),
            ("Data Engineer", "data_validated", validation),
            ("Backtester", "backtest_started", {"hypothesis_hash": lock["content_hash"]}),
            ("Backtester", "backtest_completed", backtest),
        ]
        payloads = [{"role": role, "event": event, "details": deepcopy(details), "run_id": "mock-run"}
                    for role, event, details in records]
        return {"lock": lock, "evidence": self.evidence, "validation": validation,
                "backtest": backtest, "audit_entries": rechain(payloads), "rows": rows}

    def test_legacy_baseline_is_still_fixed(self):
        self.assertEqual(SUPPORTED_SPECIFICATION["lookback_months"], 12)
        self.assertEqual(SUPPORTED_SPECIFICATION["selection_count"], 4)
        for field, value in (("lookback_months", 6), ("selection_count", 3)):
            spec = deepcopy(SUPPORTED_SPECIFICATION)
            spec[field] = value
            self.assertTrue(specification_issues(spec))
            self.assertFalse(_supported_specification(spec))

    def test_machine_contract_lists_exactly_supported_choices(self):
        choices = supported_choices()
        self.assertEqual(choices["choices"], {"lookback_months": [6, 12], "selection_count": [3, 4]})
        choices["fixed"]["seed"] = 100
        self.assertEqual(supported_choices()["fixed"]["seed"], 42)

    def test_each_parameter_combination_executes_and_is_independently_checked(self):
        designs = []
        for lookback in (6, 12):
            for count in (3, 4):
                with self.subTest(lookback=lookback, count=count):
                    inputs = self.reviewed_inputs(lookback, count)
                    review = Skeptic().review(**inputs)
                    self.assertTrue(all(review["checks"].values()), review["objections"])
                    observations = inputs["backtest"]["observations"]
                    self.assertEqual(len(observations), 120 - lookback)
                    self.assertEqual(len(observations[0]["selected_assets"]), count)
                    self.assertEqual(observations[0]["formation_date"], "2015-06-30" if lookback == 6 else "2015-12-31")
                    for portfolio in ("strategy", "benchmark"):
                        self.assertAlmostEqual(observations[0][portfolio + "_turnover"], 1)
                        self.assertAlmostEqual(observations[0][portfolio + "_cost_fraction"], .001)
                    designs.append(inputs["backtest"]["metrics"])
        self.assertEqual(len({content_hash(item) for item in designs}), 4)

    def test_first_signal_uses_exact_locked_lookback(self):
        inputs = self.reviewed_inputs()
        prices = [row["price"] for row in inputs["rows"] if row["asset"] == "SYN01"]
        expected = statistics.stdev([prices[index] / prices[index - 1] - 1 for index in range(1, 7)])
        self.assertAlmostEqual(inputs["backtest"]["observations"][0]["signals"]["SYN01"], expected)

    def test_mode_contract_rejects_coercions_and_unsupported_values(self):
        for field, values in {"lookback_months": [True, 6.0, "6", 24],
                              "selection_count": [False, 3.0, "3", 5],
                              "cost_bps": [True, 0, 20], "seed": [42.0, True],
                              "design_mode": ["unknown", True]}.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    spec = {**deepcopy(SUPPORTED_SPECIFICATION), "design_mode": "llm", field: value}
                    self.assertTrue(specification_issues(spec))
                    self.assertFalse(_supported_specification(spec))

    def test_llm_lock_binds_parameters_claims_and_design_assumptions(self):
        node = candidate(self.evidence)
        lock = build_llm_lock(DEFAULT_TOPIC, node, self.evidence)
        self.assertTrue(verify_lock(lock))
        self.assertEqual(lock["specification"]["lookback_months"], 6)
        self.assertEqual(lock["specification"]["selection_count"], 3)
        self.assertIn("Use 6 trailing", " ".join(lock["specification"]["assumptions"]))
        self.assertIn("Choose the 3 lowest", " ".join(lock["specification"]["assumptions"]))
        lock["specification"]["decision_rationale"] += " changed"
        self.assertFalse(verify_lock(lock))

    def test_unsupported_definition_cannot_be_silently_relabelled(self):
        for signal in ("beta", "idiosyncratic_volatility"):
            node = candidate(self.evidence)
            node["signal"] = signal
            with self.assertRaises(ResearchError):
                build_llm_lock(DEFAULT_TOPIC, node, self.evidence)

    def test_llm_contract_still_blocks_failed_validation(self):
        inputs = self.reviewed_inputs()
        inputs["validation"]["passed"] = False
        with self.assertRaises(ResearchError):
            Backtester().run(inputs["lock"], inputs["rows"], inputs["validation"])

    def test_llm_contract_still_detects_lock_tampering(self):
        inputs = self.reviewed_inputs()
        inputs["lock"]["specification"]["selection_count"] = 4
        with self.assertRaises(ResearchError):
            Backtester().run(inputs["lock"], inputs["rows"], inputs["validation"])
        self.assertFalse(Skeptic().review(**inputs)["checks"]["hypothesis_lock"])

    def test_skeptic_rejects_changed_proposal_or_forged_call_count(self):
        for alteration in ("parameters", "calls", "extra_event", "outcome_scoring"):
            with self.subTest(alteration=alteration):
                inputs = self.reviewed_inputs()
                payloads = [entry["payload"] for entry in inputs["audit_entries"]]
                search = next(item["details"] for item in payloads if item["event"] == "search_completed")
                if alteration == "parameters":
                    search["selected_candidate"]["selection_count"] = 4
                elif alteration == "calls":
                    search["provider_calls"] = 2
                elif alteration == "extra_event":
                    payloads.insert(4, {"role": "Backtester", "event": "backtest_started", "details": {}, "run_id": "mock-run"})
                else:
                    search["rounds"][0]["candidates"][0]["score_breakdown"]["sharpe"] = 3
                inputs["audit_entries"] = rechain(payloads)
                self.assertEqual(Skeptic().review(**inputs)["verdict"], "rejected")

    def test_skeptic_rejects_invented_or_altered_excerpt(self):
        for field, replacement in (("source_id", "invented-source"), ("summary_excerpt", "An invented source passage with sufficient characters.")):
            inputs = self.reviewed_inputs()
            inputs["lock"]["specification"]["evidence_claims"][0][field] = replacement
            self.assertFalse(Skeptic().review(**inputs)["checks"]["grounding"])

    def test_rehashed_audit_cannot_relabel_total_volatility_as_beta(self):
        node = candidate(self.evidence)
        node["research_claim"] = "Test whether lower-beta synthetic stocks have better risk-adjusted returns."
        node["adaptation_rationale"] = "Use the available monthly prices and an equal-weight benchmark."
        inputs = self.reviewed_inputs(node=node, topic="Explore whether lower-beta stocks have better risk-adjusted returns")
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["hypothesis_lock"])
        self.assertTrue(review["checks"]["audit_chain"])
        self.assertTrue(review["checks"]["recorded_lock_unchanged"])
        self.assertTrue(review["checks"]["metric_recalculation"])
        self.assertFalse(review["checks"]["grounding"])
        self.assertEqual(review["verdict"], "rejected")

    def test_specialized_topic_requires_substantive_adaptation(self):
        for signal in ("beta", "idiosyncratic volatility"):
            node = candidate(self.evidence)
            node["adaptation_rationale"] = "Use the available monthly prices and an equal-weight benchmark."
            inputs = self.reviewed_inputs(node=node, topic=f"Explore {signal} stocks and risk-adjusted returns")
            review = Skeptic().review(**inputs)
            self.assertTrue(review["checks"]["audit_chain"])
            self.assertFalse(review["checks"]["grounding"])

    def test_explicit_distinct_total_volatility_adaptation_is_accepted(self):
        node = candidate(self.evidence)
        node["research_claim"] = "Test whether lower total volatility, not beta, has better risk-adjusted returns in the synthetic fixture."
        node["adaptation_rationale"] = "Beta needs an unavailable market-factor harness; total volatility is a distinct supported alternative."
        inputs = self.reviewed_inputs(node=node, topic="Explore whether lower-beta stocks have better risk-adjusted returns")
        review = Skeptic().review(**inputs)
        self.assertTrue(all(review["checks"].values()), review["objections"])

    def test_rehashed_candidate_cannot_fabricate_prelock_metrics(self):
        for narrative in ("Select this experiment because the synthetic Sharpe=9.99.",
                          "This synthetic experiment achieved annualized return of 50 percent."):
            node = candidate(self.evidence)
            node["decision_rationale"] = narrative
            review = Skeptic().review(**self.reviewed_inputs(node=node))
            self.assertTrue(review["checks"]["hypothesis_lock"])
            self.assertTrue(review["checks"]["audit_chain"])
            self.assertFalse(review["checks"]["grounding"])

    def test_rehashed_proposal_rationale_cannot_fabricate_metrics(self):
        inputs = self.reviewed_inputs()
        payloads = [entry["payload"] for entry in inputs["audit_entries"]]
        narrative = "Select this research design because its calculated Sharpe=9.99."
        for payload in payloads:
            if payload["event"] == "provider_call_completed":
                payload["details"]["output"]["decision_rationale"] = narrative
            elif payload["event"] == "candidates_assessed":
                payload["details"]["proposal"]["decision_rationale"] = narrative
            elif payload["event"] == "search_completed":
                payload["details"]["rounds"][0]["proposal"]["decision_rationale"] = narrative
        inputs["audit_entries"] = rechain(payloads)
        review = Skeptic().review(**inputs)
        self.assertTrue(review["checks"]["audit_chain"])
        self.assertTrue(review["checks"]["outcome_isolation"])
        self.assertTrue(review["checks"]["recorded_lock_unchanged"])
        self.assertFalse(review["checks"]["bounded_search"])

    def test_bounded_search_rejects_phantom_feedback_and_excess_depth(self):
        search = mock_search(candidate(self.evidence))
        self.assertTrue(_bounded_search(search))
        search["feedback"] = ["A prewritten revision without an actual second round"]
        self.assertFalse(_bounded_search(search))
        search["feedback"] = []
        search["max_depth"] = 3
        self.assertFalse(_bounded_search(search))

    def test_actual_feedback_round_and_parent_link_are_reviewed(self):
        inputs = self.reviewed_inputs()
        payloads = [entry["payload"] for entry in inputs["audit_entries"]]
        search = next(item["details"] for item in payloads if item["event"] == "search_completed")
        accepted = deepcopy(search["selected_candidate"])
        rejected = deepcopy(accepted)
        rejected.update(id="initial_unsupported", lookback_months=24)
        initial = mock_search(rejected)["rounds"][0]
        objection = "Supported lookback_months choices are 6 or 12."
        initial["candidates"][0].update(valid=False, errors=[objection], score=7)
        initial["candidates"][0]["score_breakdown"]["feasibility"] = 0
        feedback = {"round": 2, "objections": [objection], "parent_ids": [rejected["id"]], "candidates": [rejected]}
        accepted["parent_id"] = rejected["id"]
        revision = mock_search(accepted)["rounds"][0]
        revision["depth"] = 2
        revision["proposal"]["action"] = "revise"
        search.update(rounds=[initial, revision], provider_calls=2, feedback=[feedback], selected_candidate=accepted)
        payloads[3]["details"]["output"] = initial["proposal"]
        payloads[4]["details"] = initial
        second_call = deepcopy(payloads[3])
        second_call["details"].update(call_index=2, round=2, output=revision["proposal"])
        payloads[5:5] = [
            {"role": "Coordinator", "event": "feedback_issued", "run_id": "mock-run", "details": feedback},
            second_call,
            {"role": "Coordinator", "event": "candidates_assessed", "run_id": "mock-run", "details": revision},
        ]
        inputs["audit_entries"] = rechain(payloads)
        review = Skeptic().review(**inputs)
        self.assertTrue(all(review["checks"].values()), review["objections"])
        feedback["parent_ids"] = ["invented_parent"]
        inputs["audit_entries"] = rechain(payloads)
        self.assertFalse(Skeptic().review(**inputs)["checks"]["bounded_search"])

    def test_replay_audit_binds_saved_search_and_saved_lock(self):
        inputs = self.reviewed_inputs()
        payloads = [entry["payload"] for entry in inputs["audit_entries"]]
        original = next(item["details"] for item in payloads if item["event"] == "search_completed")
        payloads[0]["details"]["mode"] = "replay"
        replay_search = {"method": "saved_specification_replay", "outcome_access": False, "provider_calls": 0,
                         "original_search_hash": content_hash(original), "saved_lock_hash": inputs["lock"]["content_hash"]}
        replay = {"role": "Coordinator", "event": "replay_loaded", "run_id": "mock-run",
                  "details": {"saved_lock_hash": inputs["lock"]["content_hash"], "original_search": original,
                              "original_search_hash": content_hash(original), "source_result_hash": "a" * 64,
                              "original_audit_head": "b" * 64}}
        payloads = payloads[:2] + [replay] + payloads[5:]
        payloads[3]["details"] = replay_search
        inputs["audit_entries"] = rechain(payloads)
        review = Skeptic().review(**inputs)
        self.assertTrue(all(review["checks"].values()), review["objections"])
        replay["details"]["original_search_hash"] = "0" * 64
        inputs["audit_entries"] = rechain(payloads)
        self.assertFalse(Skeptic().review(**inputs)["checks"]["bounded_search"])


if __name__ == "__main__":
    unittest.main()
