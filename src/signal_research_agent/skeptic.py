"""Independent, deterministic review of provenance and synthetic calculations."""

from __future__ import annotations

import math
import statistics
from calendar import monthrange
from datetime import date as Date

from .journal import verify_entries
from .models import content_hash
from .retrieval import LiteratureRetriever


class Skeptic:
    """Recompute audit and numerical invariants without calling the backtester."""

    role = "Skeptic"

    def review(
        self,
        lock: dict,
        evidence: list[dict],
        validation: dict,
        backtest: dict,
        audit_entries: list[dict],
        rows: list[dict] | None = None,
    ) -> dict:
        """Fail closed with a bounded verdict even for malformed injected inputs."""
        try:
            return self._review(lock, evidence, validation, backtest, audit_entries, rows)
        except (AttributeError, KeyError, TypeError, ValueError, IndexError, OverflowError, ZeroDivisionError, RecursionError):
            return {
                "verdict": "rejected",
                "objections": ["Malformed review inputs prevent a reliable independent conclusion."],
                "limitations": [
                    "Offline MVP. Deterministic synthetic data. Historical research only.",
                    "Not investment advice. No trade execution. Not evidence of future performance.",
                    "No conclusion about synthetic or real-market performance is supported by this review.",
                ],
                "confidence": "low",
                "requires_human_intervention": True,
                "checks": {"structured_review_inputs": False},
            }

    def _review(
        self,
        lock: dict,
        evidence: list[dict],
        validation: dict,
        backtest: dict,
        audit_entries: list[dict],
        rows: list[dict] | None = None,
    ) -> dict:
        checks: dict[str, bool] = {}
        objections: list[str] = []

        def check(name: str, value: bool, objection: str) -> None:
            checks[name] = bool(value)
            if not value:
                objections.append(objection)

        specification = lock.get("specification", {})
        digest = _safe_hash(specification)
        check(
            "hypothesis_lock",
            lock.get("locked") is True
            and digest == lock.get("content_hash")
            and lock.get("hypothesis_id") == "hyp-v1-" + digest[:16],
            "The hypothesis lock, content hash, or stable identifier is invalid.",
        )
        check("grounding", _grounding(specification, evidence), "Grounding is insufficient, conflicting, or differs from the trusted local corpus.")
        check("audit_chain", verify_entries(audit_entries), "The supplied audit chain is malformed or altered.")
        payloads = [entry.get("payload", {}) for entry in audit_entries if isinstance(entry, dict)]
        starts = [index for index, item in enumerate(payloads) if item.get("event") == "request_accepted"]
        current = payloads[starts[-1]:] if starts else []
        audit = _audit_checks(current, lock, evidence, validation, backtest, rows)
        for name, passed in audit.items():
            check(name, passed, "The audit does not establish " + name.replace("_", " ") + ".")
        check(
            "data_validation",
            validation.get("passed") is True
            and validation.get("errors") == []
            and isinstance(validation.get("checks"), dict)
            and bool(validation["checks"])
            and all(value is True for value in validation["checks"].values())
            and isinstance(validation.get("data_hash"), str)
            and validation.get("data_hash") == backtest.get("data_hash"),
            "The data-validation gate failed or its attestation disagrees with the backtest.",
        )
        check(
            "backtest_bound_to_lock",
            backtest.get("hypothesis_hash") == digest
            and backtest.get("hypothesis_id") == lock.get("hypothesis_id"),
            "The backtest does not reference the reviewed immutable hypothesis.",
        )
        check(
            "data_provenance",
            rows is not None
            and _safe_hash(rows) == validation.get("data_hash")
            and validation.get("row_count") == len(rows)
            and _rows_valid(rows, specification),
            "Independent row checks found absent data, inconsistent histories, invalid prices, or availability leakage.",
        )
        try:
            numeric_checks = _review_calculations(backtest, specification, rows or [])
        except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError, OverflowError):
            numeric_checks = {name: False for name in (
                "observation_count", "point_in_time_signal", "portfolio_weights",
                "transaction_costs", "metric_recalculation", "synthetic_interpretation"
            )}
        for name, passed in numeric_checks.items():
            check(name, passed, "Independent review failed: " + name.replace("_", " ") + ".")

        if objections:
            verdict = "rejected"
            confidence = "low"
        else:
            difference = backtest["metrics"]["sharpe_difference"]
            verdict = "supported_in_synthetic_fixture_only" if difference > 0 else "unsupported_in_synthetic_fixture"
            confidence = "limited_to_deterministic_fixture"
        return {
            "verdict": verdict,
            "objections": objections,
            "limitations": [
                "Offline MVP using deterministic synthetic data; historical research only.",
                "Not investment advice. No trade execution. Not evidence of future performance.",
                "Synthetic returns are not empirical evidence about real markets or expected profits.",
                "A single fixture and zero-risk-free Sharpe comparison do not establish statistical significance or causality.",
                "The fixed universe omits delistings, changing constituents, taxes, market impact, and corporate actions.",
                "Data checks attest structure and recorded hashes; the Skeptic does not independently rerun the generator seed.",
                "The Skeptic is independently coded deterministic checking, not an independent human or language model.",
                "Local hash chains lack external checkpoints and cannot detect valid tail deletion or complete chain rewriting.",
            ],
            "confidence": confidence,
            "requires_human_intervention": bool(objections),
            "checks": checks,
        }


def _safe_hash(value: object) -> str:
    try:
        return content_hash(value)
    except (TypeError, ValueError, OverflowError):
        return "invalid"


def _grounding(specification: dict, evidence: list[dict]) -> bool:
    try:
        trusted = {item["id"]: item for item in LiteratureRetriever().sources}
        supplied = {item["id"]: item for item in evidence}
        source_ids = specification["source_ids"]
        if len(source_ids) < 3 or len(set(source_ids)) != len(source_ids) or set(source_ids) != set(supplied):
            return False
        for source_id in source_ids:
            if source_id not in trusted or source_id not in supplied:
                return False
            for key, value in trusted[source_id].items():
                if supplied[source_id].get(key) != value:
                    return False
            if set(supplied[source_id]) - (set(trusted[source_id]) | {"score"}):
                return False
        stances = {item["stance"] for item in supplied.values()}
        return "supports_total_volatility_research" in stances and "methodological_caution" in stances and not stances.intersection({"conflicting", "opposes", "contradicts", "negative"})
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _audit_checks(current: list[dict], lock: dict, evidence: list[dict], validation: dict, backtest: dict, rows: list[dict] | None) -> dict[str, bool]:
    expected = [
        ("Coordinator", "request_accepted"),
        ("Hypothesis Generator", "evidence_retrieved"),
        ("Hypothesis Generator", "search_completed"),
        ("Hypothesis Generator", "hypothesis_locked"),
        ("Data Engineer", "data_generated"),
        ("Data Engineer", "data_validated"),
        ("Backtester", "backtest_started"),
        ("Backtester", "backtest_completed"),
    ]
    result = {"outcome_isolation": False, "recorded_lock_unchanged": False,
              "recorded_evidence_unchanged": False, "recorded_validation_unchanged": False,
              "recorded_backtest_unchanged": False, "bounded_search": False}
    if not current:
        return result
    events = [(item.get("role"), item.get("event")) for item in current]
    filtered = [event for event in events if event != ("Hypothesis Generator", "hypothesis_revised")]
    revisions = [index for index, event in enumerate(events) if event == ("Hypothesis Generator", "hypothesis_revised")]
    one_run = len({item.get("run_id") for item in current}) == 1 and isinstance(current[0].get("run_id"), str) and bool(current[0]["run_id"])
    ordered = filtered == expected and len(revisions) <= 1
    if revisions:
        if expected[2] not in events or expected[3] not in events:
            ordered = False
        else:
            ordered = ordered and events.index(expected[2]) < revisions[0] < events.index(expected[3])
    details = {item.get("event"): item.get("details", {}) for item in current}
    generated = details.get("data_generated", {})
    started = details.get("backtest_started", {})
    result["outcome_isolation"] = (
        ordered and one_run and validation.get("passed") is True
        and generated.get("data_hash", generated.get("hash")) == validation.get("data_hash")
        and rows is not None and generated.get("row_count") == len(rows)
        and started.get("hypothesis_hash", started.get("hash")) == lock.get("content_hash")
    )
    result["recorded_lock_unchanged"] = _safe_hash(details.get("hypothesis_locked")) == _safe_hash(lock)
    recorded_evidence = details.get("evidence_retrieved", {})
    result["recorded_evidence_unchanged"] = _safe_hash(recorded_evidence.get("evidence")) == _safe_hash(evidence)
    result["recorded_validation_unchanged"] = _safe_hash(details.get("data_validated")) == _safe_hash(validation)
    result["recorded_backtest_unchanged"] = _safe_hash(details.get("backtest_completed")) == _safe_hash(backtest)
    search = details.get("search_completed", {})
    result["bounded_search"] = _bounded_search(search)
    return result


def _bounded_search(search: dict) -> bool:
    """Inspect the search attestation in addition to requiring its pre-lock order."""
    try:
        alternatives = search["alternatives"]
        trace = search["trace"]
        revisions = search["revisions"]
        return (
            search["method"] == "bounded_deterministic_beam_search"
            and search["outcome_access"] is False
            and search["max_depth"] == 2 and search["beam_width"] == 2
            and search["max_nodes"] == 5 and search["max_revisions"] == 1
            and 0 < search["nodes_visited"] <= 5
            and search["scoring_inputs"] == ["source_topic_coverage", "offline_harness_feasibility"]
            and len(alternatives) == 3
            and {item["definition"] for item in alternatives} == {"total_volatility", "beta", "idiosyncratic_volatility"}
            and all(_close(item["score"], item["grounding_score"] + 4 * item["feasibility_score"]) for item in alternatives)
            and all(item["grounding_score"] == len(set(item["source_ids"])) for item in alternatives)
            and len(trace) == 2 and [item["depth"] for item in trace] == [1, 2]
            and all(0 < len(item["retained"]) <= 2 for item in trace)
            and sum(len(item["expanded"]) for item in trace) == search["nodes_visited"]
            and len(revisions) <= 1 and all(item["before_lock"] is True for item in revisions)
            and search["selected"] == "total_volatility"
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _rows_valid(rows: list[dict], specification: dict) -> bool:
    """An independent smaller check of the engineer's data attestation."""
    try:
        histories: dict[str, list[str]] = {}
        keys = set()
        for row in rows:
            asset, date, price = row["asset"], row["date"], row["price"]
            key = asset, date
            if key in keys or row.get("synthetic") is not True:
                return False
            if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
                return False
            if row["available_at"] != date or date > specification["as_of_date"]:
                return False
            parsed_date = Date.fromisoformat(date)
            if parsed_date.day != monthrange(parsed_date.year, parsed_date.month)[1]:
                return False
            keys.add(key)
            histories.setdefault(asset, []).append(date)
        if set(histories) != set(specification["universe"]):
            return False
        dates = [sorted(history) for history in histories.values()]
        if not dates or not all(history == dates[0] for history in dates):
            return False
        if len(dates[0]) != specification["n_months"] or dates[0][0] != specification["start_date"] or dates[0][-1] != specification["as_of_date"]:
            return False
        monthly_indices = [Date.fromisoformat(item).year * 12 + Date.fromisoformat(item).month for item in dates[0]]
        return all(right == left + 1 for left, right in zip(monthly_indices, monthly_indices[1:])) and len(dates[0]) >= specification["lookback_months"] + specification["min_observations"] + 1
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _close(left: float, right: float) -> bool:
    return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=1e-8, abs_tol=1e-10)


def _metrics(returns: list[float], turnovers: list[float], costs: list[float]) -> dict:
    wealth = peak = 1.0
    drawdown = 0.0
    for value in returns:
        wealth *= 1 + value
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1)
    deviation = statistics.stdev(returns)
    return {
        "cumulative_return": wealth - 1,
        "annualized_return": wealth ** (12 / len(returns)) - 1,
        "annualized_volatility": deviation * math.sqrt(12),
        "sharpe_ratio": statistics.mean(returns) / deviation * math.sqrt(12) if deviation else 0.0,
        "maximum_drawdown": drawdown,
        "average_monthly_turnover": statistics.mean(turnovers),
        "total_turnover": sum(turnovers),
        "total_cost_fraction": sum(costs),
        "observation_count": len(returns),
    }


def _review_calculations(backtest: dict, specification: dict, rows: list[dict]) -> dict[str, bool]:
    observations = backtest["observations"]
    metrics = backtest["metrics"]
    universe = specification["universe"]
    count = len(observations)
    checks = {
        "observation_count": count >= max(2, specification["min_observations"])
        and count == metrics["observation_count"]
        and count == specification["n_months"] - specification["lookback_months"] - 1,
        "point_in_time_signal": True,
        "portfolio_weights": True,
        "transaction_costs": specification["cost_bps"] > 0,
        "metric_recalculation": True,
        "synthetic_interpretation": backtest["methodology"].get("data_kind") == "deterministic_synthetic"
        and backtest["methodology"].get("inference") == "Descriptive synthetic fixture comparison only; no statistical or real-market inference"
        and specification["success_rule"] == "strategy_net_sharpe > benchmark_net_sharpe",
    }
    prices = {(row["asset"], row["date"]): row["price"] for row in rows}
    dates = sorted({row["date"] for row in rows})
    previous_return_date = None
    previous: dict[str, dict] = {}
    derived_metrics = {}
    for index, observation in enumerate(observations):
        formation, return_date = observation["formation_date"], observation["return_date"]
        formation_index = dates.index(formation)
        checks["point_in_time_signal"] &= (
            observation["signal_as_of_date"] == formation < return_date <= specification["as_of_date"]
            and (previous_return_date is None or formation == previous_return_date)
            and formation_index == specification["lookback_months"] + index
            and return_date == dates[formation_index + 1]
            and observation["signal_window_start_date"] == dates[formation_index - specification["lookback_months"]]
            and observation["signal_latest_input_date"] == formation
        )
        previous_return_date = return_date
        actual_signals = {}
        for asset in universe:
            available_returns = [prices[asset, dates[position]] / prices[asset, dates[position - 1]] - 1 for position in range(formation_index - specification["lookback_months"] + 1, formation_index + 1)]
            actual_signals[asset] = statistics.stdev(available_returns)
            checks["point_in_time_signal"] &= _close(actual_signals[asset], observation["signals"][asset])
            checks["point_in_time_signal"] &= _close(
                observation["asset_returns"][asset], prices[asset, return_date] / prices[asset, formation] - 1
            )
        selected = sorted(universe, key=lambda asset: (actual_signals[asset], asset))[:specification["selection_count"]]
        checks["portfolio_weights"] &= observation["selected_assets"] == selected
        for portfolio in ("strategy", "benchmark"):
            weights = observation[portfolio + "_weights"]
            active = selected if portfolio == "strategy" else universe
            expected_weights = {asset: 1 / len(active) if asset in active else 0.0 for asset in universe}
            checks["portfolio_weights"] &= set(weights).issubset(set(universe)) and all(
                _close(weights.get(asset, 0), expected_weights[asset]) for asset in universe
            )
            gross = sum(expected_weights[asset] * observation["asset_returns"][asset] for asset in universe)
            checks["metric_recalculation"] &= _close(gross, observation[portfolio + "_gross_return"])
            if portfolio not in previous:
                turnover = 1.0
            else:
                prior = previous[portfolio]
                drifted = {
                    asset: prior["weights"].get(asset, 0) * (1 + prior["returns"][asset]) / (1 + prior["gross"])
                    for asset in universe
                }
                turnover = sum(abs(expected_weights[asset] - drifted[asset]) for asset in universe)
            cost = turnover * specification["cost_bps"] / 10000
            net = (1 - cost) * (1 + gross) - 1
            checks["transaction_costs"] &= _close(turnover, observation[portfolio + "_turnover"])
            checks["transaction_costs"] &= _close(cost, observation[portfolio + "_cost_fraction"])
            checks["transaction_costs"] &= _close(net, observation[portfolio + "_net_return"])
            previous[portfolio] = {"weights": expected_weights, "returns": observation["asset_returns"], "gross": gross}
    for portfolio in ("strategy", "benchmark"):
        derived = _metrics(
            [item[portfolio + "_net_return"] for item in observations],
            [item[portfolio + "_turnover"] for item in observations],
            [item[portfolio + "_cost_fraction"] for item in observations],
        )
        derived_metrics[portfolio] = derived
        checks["metric_recalculation"] &= all(_close(value, metrics[portfolio][key]) for key, value in derived.items())
        checks["transaction_costs"] &= derived["total_cost_fraction"] > 0
    checks["metric_recalculation"] &= _close(
        derived_metrics["strategy"]["sharpe_ratio"] - derived_metrics["benchmark"]["sharpe_ratio"], metrics["sharpe_difference"]
    )
    return checks
