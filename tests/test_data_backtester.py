"""Data gates and independently calculable properties of the fixed harness."""

from copy import deepcopy
import math
import random
import statistics
import unittest

from signal_research_agent.backtester import Backtester, SUPPORTED_SPECIFICATION, summarize_returns
from signal_research_agent.data_engineer import DataEngineer
from signal_research_agent.models import ResearchError, content_hash


def fixture_spec():
    spec = deepcopy(SUPPORTED_SPECIFICATION)
    spec.update({"topic": "Explore whether lower-volatility stocks have better risk-adjusted returns",
                 "assumptions": ["Deterministic synthetic fixture only; same-close execution"],
                 "source_ids": ["ang-2006", "baker-2011", "arnott-2018"]})
    return spec


def fixture_lock(spec):
    digest = content_hash(spec)
    return {"hypothesis_id": "hyp-v1-" + digest[:16], "content_hash": digest,
            "specification": deepcopy(spec), "locked": True}


class DataValidationTests(unittest.TestCase):
    def setUp(self):
        self.engineer = DataEngineer()
        self.spec = fixture_spec()
        self.rows = self.engineer.generate(self.spec)

    def assert_gate_fails(self, rows, check):
        result = self.engineer.validate(rows, self.spec)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"][check], result["errors"])

    def test_valid_baseline_data_acceptance(self):
        result = self.engineer.validate(self.rows, self.spec)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual((result["row_count"], result["asset_count"], result["month_count"]), (1452, 12, 121))
        self.assertEqual(result["data_hash"], content_hash(self.rows))
        self.assertTrue(all(result["checks"].values()))

    def test_deterministic_generation_and_no_global_prng_mutation(self):
        before = random.getstate()
        self.assertEqual(self.rows, self.engineer.generate(self.spec))
        self.assertEqual(before, random.getstate())
        self.assertTrue(all(row["synthetic"] is True for row in self.rows))

    def test_duplicate_row_detection(self):
        self.assert_gate_fails(self.rows + [deepcopy(self.rows[0])], "duplicates")

    def test_missing_value_detection(self):
        self.rows[0]["price"] = None
        self.assert_gate_fails(self.rows, "missing_values")

    def test_nonfinite_price_detection(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, "100", 10 ** 500):
            with self.subTest(value=str(value)[:20]):
                self.rows[0]["price"] = value
                self.assert_gate_fails(self.rows, "finite_prices")

    def test_nonpositive_price_detection(self):
        for value in (0.0, -1.0):
            self.rows[0]["price"] = value
            self.assert_gate_fails(self.rows, "positive_prices")

    def test_minimum_history_detection(self):
        self.assert_gate_fails(self.rows[:12 * 48], "minimum_history")

    def test_unequal_asset_history_detection(self):
        self.assert_gate_fails(self.rows[1:], "equal_asset_histories")

    def test_missing_calendar_month_detection(self):
        self.assert_gate_fails([row for row in self.rows if row["date"] != "2018-05-31"], "monthly_calendar")

    def test_non_month_end_detection(self):
        self.rows[0]["date"] = "2014-12-30"
        self.rows[0]["available_at"] = "2014-12-30"
        self.assert_gate_fails(self.rows, "monthly_calendar")

    def test_as_of_date_leakage_detection(self):
        self.rows[-1]["date"] = "2025-01-31"
        self.rows[-1]["available_at"] = "2025-01-31"
        self.assert_gate_fails(self.rows, "as_of_date_leakage")

    def test_availability_after_as_of_date_detection(self):
        self.rows[-1]["available_at"] = "2025-01-01"
        self.assert_gate_fails(self.rows, "as_of_date_leakage")

    def test_availability_before_observation_and_delays_blocked(self):
        for available in ("2014-12-30", "2015-01-01"):
            self.rows[0]["available_at"] = available
            self.assert_gate_fails(self.rows, "availability_dates")

    def test_expected_universe_detection(self):
        self.rows[0]["asset"] = "REAL_TICKER"
        self.assert_gate_fails(self.rows, "expected_universe")

    def test_missing_synthetic_label_detection(self):
        for value in (False, "true", 1):
            self.rows[0]["synthetic"] = value
            self.assert_gate_fails(self.rows, "synthetic_labels")

    def test_malformed_input_fails_closed_without_exception(self):
        for malformed in (None, {}, [], [None], [{"asset": ["bad"], "date": 4}], [{"price": {"x": 1}}]):
            with self.subTest(malformed=malformed):
                self.assertFalse(self.engineer.validate(malformed, self.spec)["passed"])
        self.assertFalse(self.engineer.validate(self.rows, None)["passed"])

    def test_unknown_generator_version_refused(self):
        self.spec["generator_version"] = "unknown"
        with self.assertRaises(ResearchError):
            self.engineer.generate(self.spec)


class BacktesterTests(unittest.TestCase):
    def setUp(self):
        self.engineer = DataEngineer()
        self.spec = fixture_spec()
        self.rows = self.engineer.generate(self.spec)
        self.lock = fixture_lock(self.spec)
        self.validation = self.engineer.validate(self.rows, self.spec)

    def run_backtest(self, rows=None):
        panel = self.rows if rows is None else rows
        return Backtester().run(self.lock, panel, self.engineer.validate(panel, self.spec))

    def test_fixed_backtest_deterministic_replay_and_immutable_lock(self):
        before = deepcopy(self.lock)
        first = self.run_backtest()
        self.assertEqual(first, self.run_backtest())
        self.assertEqual(self.lock, before)
        self.assertEqual(first["metrics"]["observation_count"], 108)
        self.assertEqual(first["observations"][0]["formation_date"], "2015-12-31")
        self.assertEqual(first["observations"][-1]["return_date"], "2024-12-31")

    def test_signal_matches_trailing_sample_standard_deviation(self):
        result = self.run_backtest()
        first = result["observations"][0]
        prices = [row["price"] for row in self.rows if row["asset"] == "SYN01"][:13]
        returns = [prices[index] / prices[index - 1] - 1 for index in range(1, 13)]
        self.assertEqual(first["signals"]["SYN01"], statistics.stdev(returns))
        self.assertEqual(first["signal_latest_input_date"], first["formation_date"])

    def test_future_prices_cannot_change_prior_signals_or_returns(self):
        baseline = self.run_backtest()
        changed = deepcopy(self.rows)
        for row in changed:
            if row["date"] >= "2020-01-31":
                row["price"] *= 1.5 if row["asset"] == "SYN01" else 0.8
        revised = self.run_backtest(changed)
        prior_original = [row for row in baseline["observations"] if row["return_date"] < "2020-01-31"]
        prior_revised = [row for row in revised["observations"] if row["return_date"] < "2020-01-31"]
        self.assertEqual(prior_original, prior_revised)
        january_original = next(row for row in baseline["observations"] if row["return_date"] == "2020-01-31")
        january_revised = next(row for row in revised["observations"] if row["return_date"] == "2020-01-31")
        self.assertEqual(january_original["signals"], january_revised["signals"])
        self.assertEqual(january_original["selected_assets"], january_revised["selected_assets"])

    def test_initial_cost_and_drifted_rebalance_arithmetic(self):
        result = self.run_backtest()
        first, second = result["observations"][:2]
        for label in ("strategy", "benchmark"):
            self.assertAlmostEqual(first[f"{label}_turnover"], 1.0)
            self.assertAlmostEqual(first[f"{label}_cost_fraction"], 0.001)
            gross = sum(first[f"{label}_weights"][asset] * first["asset_returns"][asset]
                        for asset in self.spec["universe"])
            self.assertAlmostEqual(first[f"{label}_net_return"], 0.999 * (1 + gross) - 1)
            drift = {asset: first[f"{label}_weights"][asset] * (1 + first["asset_returns"][asset]) / (1 + gross)
                     for asset in self.spec["universe"]}
            turnover = sum(abs(second[f"{label}_weights"][asset] - drift[asset]) for asset in self.spec["universe"])
            self.assertAlmostEqual(second[f"{label}_turnover"], turnover)
            self.assertAlmostEqual(second[f"{label}_cost_fraction"], turnover * 0.001)
            self.assertLessEqual(second[f"{label}_net_return"], second[f"{label}_gross_return"])

    def test_hand_calculable_summary_and_initial_drawdown(self):
        metrics = summarize_returns([-0.1, 0.1], [1.0, 0.2], [0.001, 0.0002])
        self.assertAlmostEqual(metrics["cumulative_return"], -0.01)
        self.assertAlmostEqual(metrics["annualized_return"], 0.99 ** 6 - 1)
        self.assertAlmostEqual(metrics["annualized_volatility"], math.sqrt(0.02) * math.sqrt(12))
        self.assertEqual(metrics["sharpe_ratio"], 0.0)
        self.assertAlmostEqual(metrics["maximum_drawdown"], -0.1)
        self.assertAlmostEqual(metrics["average_monthly_turnover"], 0.6)
        self.assertAlmostEqual(metrics["total_cost_fraction"], 0.0012)

    def test_zero_variance_returns_have_no_sharpe_conclusion(self):
        self.assertIsNone(summarize_returns([0.01, 0.01], [1, 0], [0.001, 0])["sharpe_ratio"])

    def test_alphabetical_tie_break(self):
        for row in self.rows:
            row["price"] = 100.0
        result = self.run_backtest()
        self.assertEqual(result["observations"][0]["selected_assets"], ["SYN01", "SYN02", "SYN03", "SYN04"])

    def test_hypothesis_tampering_detection(self):
        self.lock["specification"]["selection_count"] = 3
        with self.assertRaisesRegex(ResearchError, "lock|hash"):
            Backtester().run(self.lock, self.rows, self.validation)

    def test_rehashed_unsupported_hypothesis_refused(self):
        self.spec["cost_bps"] = 0.0
        self.lock = fixture_lock(self.spec)
        with self.assertRaises(ResearchError):
            self.run_backtest()

    def test_changed_data_rejects_stale_gate(self):
        self.rows[100]["price"] *= 1.1
        with self.assertRaisesRegex(ResearchError, "validation"):
            Backtester().run(self.lock, self.rows, self.validation)

    def test_forged_validation_cannot_admit_invalid_panel(self):
        self.rows.append(deepcopy(self.rows[0]))
        forged = self.engineer.validate(self.rows, self.spec)
        forged["passed"] = True
        with self.assertRaisesRegex(ResearchError, "validation"):
            Backtester().run(self.lock, self.rows, forged)

    def test_finite_prices_with_overflowing_returns_stop_cleanly(self):
        for row in self.rows:
            if row["asset"] == "SYN01":
                row["price"] = 1e-300 if row["date"] == "2014-12-31" else 1e300
        validation = self.engineer.validate(self.rows, self.spec)
        self.assertTrue(validation["passed"], validation["errors"])
        with self.assertRaisesRegex(ResearchError, "overflow"):
            Backtester().run(self.lock, self.rows, validation)

    def test_wealth_and_annualization_overflow_stop_cleanly(self):
        for returns in ([1e300, 1e300], [1e100, 0.1]):
            with self.subTest(returns=returns):
                with self.assertRaisesRegex(ResearchError, "overflow"):
                    summarize_returns(returns, [1, 0], [0.001, 0])


if __name__ == "__main__":
    unittest.main()
