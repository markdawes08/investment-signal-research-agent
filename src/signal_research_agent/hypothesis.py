"""Bounded pre-outcome candidate exploration and content-addressed locks.

The tree contains predefined research choices. Scores are transparent functions
of grounding and implementation feasibility; no prices or outcomes are inputs.
"""

from __future__ import annotations

from copy import deepcopy
import hmac

from .models import content_hash
from .retrieval import LiteratureRetriever


def verify_lock(lock: dict) -> bool:
    """Recompute the entire specification digest and versioned identifier."""
    try:
        if not isinstance(lock, dict) or lock.get("locked") is not True:
            return False
        if not isinstance(lock.get("specification"), dict):
            return False
        digest = content_hash(lock["specification"])
        return (
            isinstance(lock.get("content_hash"), str)
            and hmac.compare_digest(digest, lock["content_hash"])
            and lock.get("hypothesis_id") == "hyp-v1-" + digest[:16]
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def grounding_issues(evidence: list[dict]) -> list[str]:
    """Check attribution against the bundled corpus, never trusting retrieval scores."""
    trusted = {source["id"]: source for source in LiteratureRetriever().sources}
    issues = []
    if not isinstance(evidence, list):
        return ["Grounding sources must be a list of curated literature records."]
    valid = []
    seen = set()
    for source in evidence:
        if not isinstance(source, dict):
            issues.append("A grounding source is malformed.")
            continue
        if source.get("stance") in ("conflicting", "opposes", "contradicts", "negative") or source.get("conflicting"):
            issues.append("Grounding contains an explicit unresolved source conflict.")
        source_id = source.get("id")
        expected = trusted.get(source_id) if isinstance(source_id, str) else None
        if expected is None or any(source.get(key) != value for key, value in expected.items()):
            issues.append("A grounding source is unknown or its curated metadata was altered.")
            continue
        if set(source) - (set(expected) | {"score"}):
            issues.append("Grounding records contain unexpected fields; outcomes and numerical datasets are not accepted.")
            continue
        if source["id"] not in seen:
            valid.append(source)
            seen.add(source["id"])
    if len(valid) < 3:
        issues.append("Insufficient grounding: at least three distinct curated sources are required.")
    if not any(source["stance"] == "supports_total_volatility_research" for source in valid):
        issues.append("Insufficient direct grounding for total-volatility research.")
    if not any(source["stance"] == "methodological_caution" for source in valid):
        issues.append("Insufficient grounding on backtesting protocol or overfitting risk.")
    return sorted(set(issues))


class HypothesisGenerator:
    """Compare three definitions and lock the sole supported offline harness choice."""

    role = "Hypothesis Generator"

    MAX_DEPTH = 2
    BEAM_WIDTH = 2
    MAX_NODES = 5
    MAX_REVISIONS = 1

    def generate(self, topic: str, evidence: list[dict]) -> dict:
        search = {
            "method": "bounded_deterministic_beam_search",
            "description": "Tree-of-Thought-style explicit candidate tree; no LLM is used.",
            "max_depth": self.MAX_DEPTH,
            "beam_width": self.BEAM_WIDTH,
            "max_nodes": self.MAX_NODES,
            "max_revisions": self.MAX_REVISIONS,
            "nodes_visited": 0,
            "outcome_access": False,
            "scoring_inputs": ["source_topic_coverage", "offline_harness_feasibility"],
            "score_rule": "grounding_source_count + 4 * feasibility_score",
            "alternatives": [],
            "trace": [],
            "revisions": [],
            "selected": None,
        }
        issues = grounding_issues(evidence)
        if not isinstance(topic, str) or not topic.strip():
            issues.append("The research direction is empty.")
        if issues:
            return {"search": search, "lock": None, "objections": issues, "requires_human_intervention": True}

        candidates = [
            {
                "definition": "total_volatility",
                "definition_detail": "Dispersion of all stock returns, initially using lagged daily returns.",
                "required_inputs": ["daily_price_panel"],
                "feasibility_score": 0.75,
                "feasible": False,
                "objection": "The offline harness has monthly prices; daily methodology requires a pre-lock adaptation.",
            },
            {
                "definition": "beta",
                "definition_detail": "Covariance with an external market return divided by market variance.",
                "required_inputs": ["monthly_price_panel", "point_in_time_market_factor"],
                "feasibility_score": 0.0,
                "feasible": False,
                "objection": "An independently specified, dated market factor and beta harness are unavailable.",
            },
            {
                "definition": "idiosyncratic_volatility",
                "definition_detail": "Dispersion of residual returns after an explicitly specified factor regression.",
                "required_inputs": ["monthly_price_panel", "point_in_time_factor_panel", "factor_regression"],
                "feasibility_score": 0.0,
                "feasible": False,
                "objection": "Dated factor observations and a fixed regression harness are unavailable; residual risk is not total risk.",
            },
        ]
        for candidate in candidates:
            candidate["depth"] = 1
            candidate["source_ids"] = sorted({
                source["id"] for source in evidence if candidate["definition"] in source["topics"]
            })
            candidate["grounding_score"] = len(candidate["source_ids"])
            candidate["score"] = candidate["grounding_score"] + 4 * candidate["feasibility_score"]
        beam = sorted(candidates, key=lambda node: (-node["score"], node["definition"]))[:self.BEAM_WIDTH]
        search["alternatives"] = deepcopy(candidates)
        search["nodes_visited"] += len(candidates)
        search["trace"].append({"depth": 1, "expanded": [node["definition"] for node in candidates],
                                "retained": [node["definition"] for node in beam]})

        children = []
        for candidate in beam:
            child = deepcopy(candidate)
            child["depth"] = 2
            child["parent"] = candidate["definition"]
            if candidate["definition"] == "total_volatility" and len(search["revisions"]) < self.MAX_REVISIONS:
                child.update({
                    "definition_detail": "Sample standard deviation of 12 trailing monthly simple returns.",
                    "required_inputs": ["monthly_price_panel"],
                    "feasibility_score": 1.0,
                    "feasible": True,
                    "objection": "Monthly lookback is a declared educational adaptation, not replication of daily-return papers.",
                })
                child["score"] = child["grounding_score"] + 4 * child["feasibility_score"]
                search["revisions"].append({
                    "definition": "total_volatility", "from": "lagged_daily_variance",
                    "to": "trailing_sample_std_monthly_returns", "before_lock": True,
                    "reason": "Only monthly synthetic prices and the fixed total-volatility harness are available.",
                })
            children.append(child)
        search["nodes_visited"] += len(children)
        final_beam = sorted(children, key=lambda node: (-node["score"], node["definition"]))[:self.BEAM_WIDTH]
        search["trace"].append({"depth": 2, "expanded": deepcopy(children),
                                "retained": [node["definition"] for node in final_beam]})
        feasible = [node for node in final_beam if node["feasible"] and node["grounding_score"] > 0]
        if not feasible:
            return {"search": search, "lock": None, "objections": ["No grounded, feasible specification survived the search."],
                    "requires_human_intervention": True}
        search["selected"] = feasible[0]["definition"]
        search["stopping_rule"] = "Stop after depth 2 and one pre-lock revision; never rerank using outcomes."
        specification = {
            "version": "1.0", "topic": " ".join(topic.split()),
            "signal": "trailing_sample_std_monthly_returns",
            "universe": [f"SYN{index:02d}" for index in range(1, 13)],
            "lookback_months": 12, "holding_months": 1, "selection_count": 4,
            "benchmark": "monthly_rebalanced_equal_weight_universe",
            "cost_bps": 10.0, "risk_free_rate": 0.0, "as_of_date": "2024-12-31",
            "min_observations": 36, "success_rule": "strategy_net_sharpe > benchmark_net_sharpe",
            "seed": 42, "generator_version": "synthetic-monthly-v1",
            "start_date": "2014-12-31", "n_months": 121,
            "assumptions": [
                "Every price and return is deterministic synthetic data, not observed market history.",
                "Use 12 trailing monthly simple returns known at formation; hold for the following month.",
                "Observe and rebalance at the same synthetic month-end close, assuming zero latency.",
                "Choose the four lowest-volatility assets, equally weighted; break signal ties by asset identifier.",
                "Apply 10 basis points per unit gross traded notional to both portfolios, including initial investment.",
                "Use drifted pre-rebalance weights for turnover; do not charge a final liquidation.",
                "Deduct costs before the holding return: net return = (1 - cost fraction) * (1 + gross return) - 1.",
                "No leverage, short selling, external factors, dividends, taxes, borrowing, or brokerage access.",
                "The fixed complete universe has no entries, exits, delistings, or real-world survivorship coverage.",
                "The risk-free rate is fixed at zero and annualization uses 12 months per year.",
                "Monthly volatility is an educational adaptation; idiosyncratic and total volatility are different signals.",
                "The success rule is a descriptive synthetic-fixture comparison, not a statistical significance test.",
                "Data generation and backtest outcomes are unavailable during candidate selection and locking.",
            ],
            "source_ids": sorted({source["id"] for source in evidence}),
        }
        digest = content_hash(specification)
        lock = {"hypothesis_id": "hyp-v1-" + digest[:16], "content_hash": digest,
                "specification": specification, "locked": True}
        return {
            "search": search, "lock": lock, "requires_human_intervention": False,
            "objections": [node["objection"] for node in candidates] + [feasible[0]["objection"]],
        }
