"""Fixed point-in-time harness for the precommitted synthetic hypothesis."""

from __future__ import annotations

from copy import deepcopy
import math
import statistics

from .data_engineer import DataEngineer
from .experiment import SUPPORTED_SPECIFICATION, specification_issues
from .models import ResearchError, content_hash


def summarize_returns(returns: list[float], turnovers: list[float],
                      costs: list[float]) -> dict:
    """Summarize net monthly returns, counting the initial wealth peak of one."""
    count = len(returns)
    if count < 2 or len(turnovers) != count or len(costs) != count:
        raise ResearchError("At least two aligned return, turnover, and cost observations are required")
    if not all(math.isfinite(value) for values in (returns, turnovers, costs) for value in values):
        raise ResearchError("Backtest observations must be finite")
    wealth = peak = 1.0
    drawdown = 0.0
    for value in returns:
        if value <= -1:
            raise ResearchError("Net return at or below -100% is not supported")
        wealth *= 1.0 + value
        if not math.isfinite(wealth) or wealth <= 0:
            raise ResearchError("Synthetic wealth overflow or underflow prevents a reliable conclusion")
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    sample_vol = statistics.stdev(returns)
    try:
        annualized_return = wealth ** (12.0 / count) - 1.0
    except OverflowError as exc:
        raise ResearchError("Annualization overflow prevents a reliable conclusion") from exc
    metrics = {
        "cumulative_return": wealth - 1.0,
        "annualized_return": annualized_return,
        "annualized_volatility": sample_vol * math.sqrt(12.0),
        "sharpe_ratio": (statistics.mean(returns) / sample_vol * math.sqrt(12.0)
                         if sample_vol > 0 else None),
        "maximum_drawdown": drawdown,
        "average_monthly_turnover": statistics.mean(turnovers),
        "total_turnover": sum(turnovers),
        "total_cost_fraction": sum(costs),
        "observation_count": count,
    }
    if not all(value is None or math.isfinite(value) for value in metrics.values()):
        raise ResearchError("Nonfinite synthetic metrics prevent a reliable conclusion")
    return metrics


class Backtester:
    """Execute one supported strategy; never search, tune, or modify the lock."""

    role = "Backtester"

    def run(self, lock: dict, rows: list[dict], validation: dict) -> dict:
        from .hypothesis import verify_lock

        lock_snapshot = deepcopy(lock)
        verified = verify_lock(lock)
        if isinstance(verified, dict):
            verified = verified.get("passed", verified.get("valid", False))
        if not verified:
            raise ResearchError("Hypothesis lock or content hash is invalid; human intervention required")
        spec = lock["specification"]
        issues = specification_issues(spec)
        if issues:
            raise ResearchError("; ".join(issues))
        actual_validation = DataEngineer().validate(rows, spec)
        if (not isinstance(validation, dict) or validation.get("passed") is not True
                or actual_validation["passed"] is not True
                or validation.get("data_hash") != actual_validation["data_hash"]
                or validation != actual_validation):
            raise ResearchError("Data validation failed or gate does not match actual data; human intervention required")

        assets = spec["universe"]
        panel = {(row["asset"], row["date"]): row for row in rows}
        dates = sorted({row["date"] for row in rows})
        lookback = spec["lookback_months"]
        rate = spec["cost_bps"] / 10000.0
        observations: list[dict] = []
        drifted_strategy = {asset: 0.0 for asset in assets}
        drifted_benchmark = {asset: 0.0 for asset in assets}
        for formation_index in range(lookback, len(dates) - 1):
            formation = dates[formation_index]
            return_date = dates[formation_index + 1]
            signals = {}
            for asset in assets:
                window = [panel[(asset, dates[index])]
                          for index in range(formation_index - lookback, formation_index + 1)]
                if any(row["date"] > formation or row["available_at"] > formation for row in window):
                    raise ResearchError("Point-in-time availability leakage detected; human intervention required")
                trailing = [window[index]["price"] / window[index - 1]["price"] - 1.0
                            for index in range(1, len(window))]
                if not all(math.isfinite(value) and value > -1.0 for value in trailing):
                    raise ResearchError("Derived signal returns overflow or underflow; human intervention required")
                signals[asset] = statistics.stdev(trailing)
                if not math.isfinite(signals[asset]):
                    raise ResearchError("Nonfinite signal; human intervention required")
            selected = sorted(assets, key=lambda asset: (signals[asset], asset))[:spec["selection_count"]]
            strategy_weights = {asset: (1.0 / len(selected) if asset in selected else 0.0)
                                for asset in assets}
            benchmark_weights = {asset: 1.0 / len(assets) for asset in assets}
            forward = {asset: panel[(asset, return_date)]["price"] / panel[(asset, formation)]["price"] - 1.0
                       for asset in assets}
            if not all(math.isfinite(value) and value > -1.0 for value in forward.values()):
                raise ResearchError("Derived holding returns overflow or underflow; human intervention required")
            strategy_gross = sum(strategy_weights[asset] * forward[asset] for asset in assets)
            benchmark_gross = sum(benchmark_weights[asset] * forward[asset] for asset in assets)
            strategy_turnover = sum(abs(strategy_weights[asset] - drifted_strategy[asset]) for asset in assets)
            benchmark_turnover = sum(abs(benchmark_weights[asset] - drifted_benchmark[asset]) for asset in assets)
            strategy_cost = strategy_turnover * rate
            benchmark_cost = benchmark_turnover * rate
            observations.append({
                "formation_date": formation, "return_date": return_date,
                "signal_as_of_date": formation,
                "signal_window_start_date": dates[formation_index - lookback],
                "signal_latest_input_date": formation, "selected_assets": selected,
                "signals": signals, "strategy_weights": strategy_weights,
                "benchmark_weights": benchmark_weights, "asset_returns": forward,
                "strategy_gross_return": strategy_gross,
                "strategy_net_return": (1.0 - strategy_cost) * (1.0 + strategy_gross) - 1.0,
                "strategy_turnover": strategy_turnover, "strategy_cost_fraction": strategy_cost,
                "benchmark_gross_return": benchmark_gross,
                "benchmark_net_return": (1.0 - benchmark_cost) * (1.0 + benchmark_gross) - 1.0,
                "benchmark_turnover": benchmark_turnover, "benchmark_cost_fraction": benchmark_cost,
            })
            drifted_strategy = {asset: strategy_weights[asset] * (1.0 + forward[asset]) / (1.0 + strategy_gross)
                                for asset in assets}
            drifted_benchmark = {asset: benchmark_weights[asset] * (1.0 + forward[asset]) / (1.0 + benchmark_gross)
                                 for asset in assets}

        if len(observations) < spec["min_observations"]:
            raise ResearchError("Insufficient out-of-lookback observations; human intervention required")
        metrics = {}
        for label in ("strategy", "benchmark"):
            metrics[label] = summarize_returns(
                [row[f"{label}_net_return"] for row in observations],
                [row[f"{label}_turnover"] for row in observations],
                [row[f"{label}_cost_fraction"] for row in observations],
            )
        strategy_sharpe = metrics["strategy"]["sharpe_ratio"]
        benchmark_sharpe = metrics["benchmark"]["sharpe_ratio"]
        metrics["sharpe_difference"] = (strategy_sharpe - benchmark_sharpe
                                        if strategy_sharpe is not None and benchmark_sharpe is not None else None)
        metrics["observation_count"] = len(observations)
        if lock != lock_snapshot or content_hash(spec) != lock["content_hash"]:
            raise ResearchError("Locked hypothesis changed during the backtest; human intervention required")
        return {
            "hypothesis_id": lock["hypothesis_id"], "hypothesis_hash": lock["content_hash"],
            "data_hash": actual_validation["data_hash"], "metrics": metrics,
            "observations": observations,
            "methodology": {
                "data_kind": "deterministic_synthetic",
                "formation": f"Trailing {lookback} sample-standard-deviation monthly returns, computed at formation close",
                "execution": "Observe and transact at the same synthetic month-end close with zero latency",
                "holding": "Next one-month simple price return; no dividends or corporate actions",
                "selection": ("Four lowest-volatility assets; alphabetical asset-ID tie break"
                              if spec["selection_count"] == 4 else
                              "Three lowest-volatility assets; alphabetical asset-ID tie break"),
                "weights": "Selected assets equal weighted; benchmark all 12 assets equal weighted monthly",
                "costs": "10 bps times L1 traded weight; initial entry included; both portfolios charged",
                "turnover": "Sum of absolute target minus prior post-return drifted weights; initial value 1",
                "net_return": "(1 - cost_fraction) * (1 + gross_return) - 1",
                "total_cost_fraction": "Sum of monthly fractions of pre-rebalance portfolio wealth; not dollar costs or cumulative wealth drag",
                "terminal_liquidation": False,
                "annualization": "12 monthly periods; sample standard deviation; zero risk-free rate",
                "maximum_drawdown": "Minimum wealth / running peak - 1, including initial wealth of 1",
                "inference": "Descriptive synthetic fixture comparison only; no statistical or real-market inference",
                "limitations": ["Same-close execution assumes zero latency and no slippage beyond fixed costs",
                                "Fixed complete synthetic universe excludes survivorship, delistings, dividends, and liquidity effects",
                                "A single deterministic sample cannot establish real-market validity or future performance"],
            },
        }
