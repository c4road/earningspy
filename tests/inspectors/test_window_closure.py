"""
Event windows that have not closed must stay empty.

A window runs from the trading day before the report to ``report + N`` business days. When
that end is after the last available price, the return is not known yet: the inspector must
return NaN (never the return to the latest price, which would store a shorter window as if it
were the full one), and the row must still be eligible on a later run so it is computed once
the window closes.

All pure/in-memory — no network, no Finviz, no Yahoo.
"""
import numpy as np
import pandas as pd
import pytest
from pandas.tseries.offsets import BDay

from earningspy.inspectors.mixins import CARMixin, WindowNotClosed
from earningspy.inspectors.pead import PEADInspector

REPORT = pd.Timestamp("2026-03-02")       # a Monday


def _prices(end: str, holidays=()) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-01", end)
    idx = idx[~idx.isin(pd.to_datetime(list(holidays)))]
    rng = np.random.RandomState(42)
    stock = 100 * np.cumprod(1 + rng.normal(0, 0.01, len(idx)))
    market = 5000 * np.cumprod(1 + rng.normal(0, 0.008, len(idx)))
    return pd.DataFrame({"AAA": stock, "^GSPC": market, "^TNX": 4.0, "^VIX": 15 + np.arange(len(idx)) % 5,
                         "^RUT": 2000.0}, index=idx)


class _Insp(CARMixin):
    def __init__(self, price_history):
        self.price_history = price_history


def _row(report=REPORT, ticker="AAA"):
    return pd.Series({"BETA": 1.2, "IS_AMC": 0}, name=(report, ticker))


def _full_return(px, report, days):
    start = px.index[px.index.get_indexer([report - BDay(1)], method="pad")[0]]
    end = px.index[px.index.get_indexer([report + BDay(days)], method="backfill")[0]]
    return round((px.loc[end, "AAA"] - px.loc[start, "AAA"]) / px.loc[start, "AAA"], 4)


class TestWindowEnd:
    def test_closed_window_is_the_full_return(self):
        px = _prices("2026-08-01")
        assert _Insp(px).get_window_pct_change(_row(), 60) == _full_return(px, REPORT, 60)

    def test_open_window_is_nan_not_the_partial_return(self):
        px = _prices((REPORT + BDay(40)).strftime("%Y-%m-%d"))      # only 40 of 60 days exist
        assert np.isnan(_Insp(px).get_window_pct_change(_row(), 60))

    def test_window_ending_on_the_last_price_is_closed(self):
        px = _prices((REPORT + BDay(30)).strftime("%Y-%m-%d"))
        assert _Insp(px).get_window_pct_change(_row(), 30) == _full_return(px, REPORT, 30)

    def test_holiday_at_the_end_resolves_forward(self):
        end_target = REPORT + BDay(30)
        px = _prices("2026-08-01", holidays=[end_target])
        insp = _Insp(px)
        _, end = insp._resolve_window_dates(REPORT, 30)
        assert end > end_target and end == px.index[px.index > end_target][0]
        assert insp.get_window_pct_change(_row(), 30) == _full_return(px, REPORT, 30)

    def test_resolve_raises_window_not_closed(self):
        px = _prices((REPORT + BDay(10)).strftime("%Y-%m-%d"))
        with pytest.raises(WindowNotClosed):
            _Insp(px)._resolve_window_dates(REPORT, 30)
        assert issubclass(WindowNotClosed, KeyError)

    def test_window_vix_is_nan_while_open_and_mean_once_closed(self):
        assert np.isnan(_Insp(_prices((REPORT + BDay(5)).strftime("%Y-%m-%d"))).get_vix(_row(), 30))
        px = _prices("2026-08-01")
        start = px.index[px.index.get_indexer([REPORT - BDay(1)], method="pad")[0]]
        end = px.index[px.index.get_indexer([REPORT + BDay(30)], method="backfill")[0]]
        assert _Insp(px).get_vix(_row(), 30) == round(px.loc[start:end, "^VIX"].mean(), 2)


def _calendar(days_ago: list[int]) -> pd.DataFrame:
    today = pd.Timestamp.today().normalize()
    rows = [{"EARNINGS_DATE": today - pd.Timedelta(days=d), "TICKER": f"T{d}", "1+60_RET": np.nan}
            for d in days_ago]
    return pd.DataFrame(rows).set_index("EARNINGS_DATE")


class TestEligibility:
    def test_rows_stay_eligible_until_their_window_can_have_closed(self):
        insp = PEADInspector(calendar=_calendar([59, 60, 85, 100, 114, 115]))
        affected = set(insp._get_affected_rows(60).index.get_level_values("TICKER"))
        # start unchanged (60 calendar days); end widened to ceil(60·7/5)+30 = 114
        assert affected == {"T60", "T85", "T100", "T114"}

    def test_filled_rows_are_not_recomputed(self):
        cal = _calendar([70, 100])
        cal.loc[cal["TICKER"] == "T100", "1+60_RET"] = 0.05
        insp = PEADInspector(calendar=cal)
        assert set(insp._get_affected_rows(60).index.get_level_values("TICKER")) == {"T70"}


class TestEndToEnd:
    def test_inspect_leaves_open_windows_empty_and_fills_them_once_closed(self):
        report = pd.Timestamp.today().normalize() - pd.Timedelta(days=70)
        cal = pd.DataFrame([{"EARNINGS_DATE": report, "TICKER": "AAA", "BETA": 1.2, "IS_AMC": 0,
                             "COMPANY": "A", "1+60_RET": np.nan}]).set_index("EARNINGS_DATE")
        open_px = _prices(pd.Timestamp.today().normalize().strftime("%Y-%m-%d"))
        out = PEADInspector(calendar=cal, price_history=open_px).inspect(60, reuse_timeseries=True).calendar
        out = out.reset_index()
        assert out["1+60_RET"].isna().all() and out["CAR_60"].isna().all() and out["1+60_VIX"].isna().all()

        later = (report + BDay(70)).strftime("%Y-%m-%d")
        closed_px = _prices(later)
        insp = PEADInspector(calendar=cal, price_history=closed_px)
        insp.affected_rows = insp.calendar.reset_index().set_index(["EARNINGS_DATE", "TICKER"])
        insp._process_windows_columns(days=60, reuse_timeseries=True)
        row = insp.calendar.iloc[0]
        assert row["1+60_RET"] == _full_return(closed_px, report, 60)
        assert row["CAR_60"] == round(row["1+60_RET"] - row["CAPM_60"], 4)
