"""Deterministic synthetic prices and a fail-closed data-validation gate."""

from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from datetime import date
import math
import random
from typing import Any

from .models import ResearchError, content_hash


def _date(value: Any) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("dates must be ISO YYYY-MM-DD strings")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("dates must be ISO YYYY-MM-DD strings")
    return parsed


def _month_end(start: date, offset: int) -> date:
    year, month_index = divmod(start.year * 12 + start.month - 1 + offset, 12)
    month = month_index + 1
    return date(year, month, calendar.monthrange(year, month)[1])


class DataEngineer:
    """Generate a reproducible fixture; never fetch or represent real market data."""

    role = "Data Engineer"

    def generate(self, spec: dict) -> list[dict]:
        """Use independent local PRNG state and fixed, documented parameters.

        All assets have the same expected log-return drift, with different
        factor exposures and idiosyncratic volatility. These choices construct
        a software-test fixture and are not fitted to any real market.
        """
        try:
            start = _date(spec["start_date"])
            count = spec["n_months"]
            assets = spec["universe"]
            seed = spec["seed"]
            if (type(count) is not int or not 2 <= count <= 1200
                    or type(seed) is not int or not isinstance(assets, list)
                    or not assets or len(set(assets)) != len(assets)
                    or not all(isinstance(asset, str) and asset for asset in assets)
                    or start != _month_end(start, 0)):
                raise ValueError("invalid synthetic fixture specification")
            if spec.get("generator_version") != "synthetic-monthly-v1":
                raise ValueError("unsupported generator version")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ResearchError(f"Cannot generate synthetic fixture: {exc}") from exc

        rng = random.Random(seed)

        def normal() -> float:
            # Box-Muller uses random() only, avoiding cached distribution state.
            u1 = max(rng.random(), 1e-15)
            u2 = rng.random()
            return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

        prices = {asset: 100.0 for asset in assets}
        rows: list[dict] = []
        for month in range(count):
            stamp = _month_end(start, month).isoformat()
            common_shock = normal() if month else 0.0
            for index, asset in enumerate(assets):
                if month:
                    common_loading = 0.009 + 0.0015 * index
                    idiosyncratic_scale = 0.008 + 0.004 * index
                    log_return = (0.005 + common_loading * common_shock
                                  + idiosyncratic_scale * normal())
                    prices[asset] = round(prices[asset] * math.exp(log_return), 8)
                rows.append({"asset": asset, "date": stamp, "available_at": stamp,
                             "price": prices[asset], "synthetic": True})
        return rows

    def validate(self, rows: list[dict], spec: dict) -> dict:
        """Return all discovered errors, including malformed inputs, without a crash.

        This harness admits a balanced, contiguous monthly panel with prices
        available on their observation date. Delayed availability is rejected:
        it cannot satisfy the locked same-close execution convention.
        """
        checks = {name: True for name in (
            "schema", "duplicates", "missing_values", "finite_prices", "positive_prices",
            "minimum_history", "equal_asset_histories", "expected_universe",
            "monthly_calendar", "expected_history", "availability_dates",
            "as_of_date_leakage", "synthetic_labels",
        )}
        errors: list[str] = []

        def fail(check: str, message: str) -> None:
            checks[check] = False
            entry = f"{check}: {message}"
            if entry not in errors:
                errors.append(entry)

        hashed = None
        try:
            hashed = content_hash(rows)
        except (TypeError, ValueError, OverflowError, RecursionError):
            fail("schema", "rows cannot be represented as finite canonical JSON")

        if not isinstance(rows, list):
            fail("schema", "panel must be a list of row dictionaries")
            rows = []
        if not rows:
            fail("missing_values", "panel is empty")

        expected_assets: list[str] = []
        expected_dates: list[date] = []
        as_of = None
        minimum_prices = 1
        try:
            expected_assets = spec["universe"]
            if (not isinstance(expected_assets, list) or not expected_assets
                    or not all(isinstance(asset, str) and asset for asset in expected_assets)
                    or len(set(expected_assets)) != len(expected_assets)):
                raise ValueError("universe must contain unique nonempty asset names")
            lookback = spec["lookback_months"]
            min_observations = spec["min_observations"]
            n_months = spec["n_months"]
            if (type(lookback) is not int or lookback < 2
                    or type(min_observations) is not int or min_observations < 2
                    or type(n_months) is not int or not 2 <= n_months <= 1200):
                raise ValueError("history parameters must be bounded positive integers")
            minimum_prices = lookback + min_observations + 1
            as_of = _date(spec["as_of_date"])
            start = _date(spec["start_date"])
            expected_dates = [_month_end(start, offset) for offset in range(n_months)]
            if start != expected_dates[0]:
                raise ValueError("start_date must be a month end")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            fail("schema", f"invalid validation specification: {exc}")
            expected_assets = []

        histories: dict[str, set[date]] = defaultdict(set)
        seen: Counter = Counter()
        all_dates: set[date] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                fail("schema", f"row {index} must be a dictionary")
                continue
            required = ("asset", "date", "available_at", "price", "synthetic")
            if any(field not in row or row[field] is None or row[field] == "" for field in required):
                fail("missing_values", f"row {index} lacks a required value")
            if row.get("synthetic") is not True:
                fail("synthetic_labels", f"row {index} must explicitly set synthetic=true")
            asset = row.get("asset")
            if not isinstance(asset, str) or not asset:
                fail("schema", f"row {index} has an invalid asset identifier")
                asset = None
            price = row.get("price")
            if isinstance(price, bool) or not isinstance(price, (int, float)):
                fail("finite_prices", f"row {index} price must be numeric and finite")
            else:
                try:
                    finite = math.isfinite(price)
                except OverflowError:
                    finite = False
                if not finite:
                    fail("finite_prices", f"row {index} price must be finite")
                elif price <= 0:
                    fail("positive_prices", f"row {index} price must be positive")
            stamp = None
            available = None
            try:
                stamp = _date(row.get("date"))
            except (TypeError, ValueError, OverflowError):
                fail("monthly_calendar", f"row {index} has an invalid observation date")
            try:
                available = _date(row.get("available_at"))
            except (TypeError, ValueError, OverflowError):
                fail("availability_dates", f"row {index} has an invalid availability date")
            if stamp is not None:
                all_dates.add(stamp)
                if asset is not None:
                    key = (asset, stamp)
                    seen[key] += 1
                    histories[asset].add(stamp)
                    if seen[key] > 1:
                        fail("duplicates", f"duplicate asset/date {asset}/{stamp}")
                if stamp != _month_end(stamp, 0):
                    fail("monthly_calendar", f"row {index} observation is not month end")
                if as_of is not None and stamp > as_of:
                    fail("as_of_date_leakage", f"row {index} observation occurs after as_of_date")
            if available is not None:
                if as_of is not None and available > as_of:
                    fail("as_of_date_leakage", f"row {index} becomes available after as_of_date")
                if stamp is not None and available != stamp:
                    fail("availability_dates", f"row {index} availability must equal observation date for same-close convention")

        if set(histories) != set(expected_assets):
            fail("expected_universe", "observed assets differ from the locked universe")
        for asset in expected_assets:
            dates = sorted(histories.get(asset, set()))
            if len(dates) < minimum_prices:
                fail("minimum_history", f"{asset} requires at least {minimum_prices} prices; received {len(dates)}")
            if dates and dates != [_month_end(dates[0], offset) for offset in range(len(dates))]:
                fail("monthly_calendar", f"{asset} has gaps or non-month-end dates")
            if expected_dates and dates != expected_dates:
                fail("expected_history", f"{asset} history differs from locked start_date/n_months")
        history_sets = list(histories.values())
        if history_sets and any(history != history_sets[0] for history in history_sets[1:]):
            fail("equal_asset_histories", "assets do not have identical observation dates")

        return {"passed": not errors, "errors": errors, "row_count": len(rows),
                "asset_count": len(histories), "month_count": len(all_dates),
                "data_hash": hashed, "checks": checks}
