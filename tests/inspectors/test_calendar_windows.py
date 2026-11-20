"""
Calendar-day windows (30 and 60 days), computed beside the business-day ones.

Start: the close on the trading day before the report. Exit: the open of the first session after
report + N calendar days, or, without that open, the close of the last session on or before day N.
The S&P 500 is measured over the same dates and on the same basis.

All pure/in-memory: no network.
"""
import numpy as np
import pandas as pd
import pytest
from pandas.tseries.offsets import BDay

from earningspy.inspectors.mixins import CARMixin, WindowNotClosed
from earningspy.inspectors.pead import PEADInspector

REPORT = pd.Timestamp("2026-03-02")       # a Monday; +30 days = Wed 1 Apr, +60 days = Fri 1 May


def _closes(end: str, holidays=()) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-01", end)
    idx = idx[~idx.isin(pd.to_datetime(list(holidays)))]
    rng = np.random.RandomState(42)
    stock = 100 * np.cumprod(1 + rng.normal(0, 0.01, len(idx)))
    market = 5000 * np.cumprod(1 + rng.normal(0, 0.008, len(idx)))
    return pd.DataFrame({"AAA": stock, "^GSPC": market, "^TNX": 4.0, "^VIX": 15.0, "^RUT": 2000.0}, index=idx)


def _opens(closes: pd.DataFrame) -> pd.DataFrame:
    return closes.shift(1) * 1.002            # open a touch above the previous close


class _Insp(CARMixin):
    def __init__(self, closes, opens=None):
        self.price_history = closes
        self.open_history = opens


def _row(report=REPORT, ticker="AAA"):
    return pd.Series({"BETA": 1.2, "IS_AMC": 0}, name=(report, ticker))


def _ret(a, b):
    return round((b - a) / a, 4)


class TestWindowDates:
    def test_exit_is_the_session_after_day_n(self):
        px = _closes("2026-08-01")
        start, exit_session, last = _Insp(px)._resolve_calendar_window(REPORT, 30)
        assert start == pd.Timestamp("2026-02-27")                  # Friday before the Monday report
        assert last == pd.Timestamp("2026-04-01")                   # day 30, a Wednesday
        assert exit_session == pd.Timestamp("2026-04-02")           # next session's open

    def test_day_n_on_a_friday_exits_monday(self):
        px = _closes("2026-08-01")
        _, exit_session, last = _Insp(px)._resolve_calendar_window(REPORT, 60)
        assert last == pd.Timestamp("2026-05-01")                   # Friday
        assert exit_session == pd.Timestamp("2026-05-04")           # Monday

    def test_day_n_on_a_weekend(self):
        report = pd.Timestamp("2026-03-04")                         # Wed; +60 = Sun 3 May
        px = _closes("2026-08-01")
        _, exit_session, last = _Insp(px)._resolve_calendar_window(report, 60)
        assert last == pd.Timestamp("2026-05-01")
        assert exit_session == pd.Timestamp("2026-05-04")

    def test_holiday_after_day_n_moves_the_exit(self):
        px = _closes("2026-08-01", holidays=["2026-04-02"])
        _, exit_session, _ = _Insp(px)._resolve_calendar_window(REPORT, 30)
        assert exit_session == pd.Timestamp("2026-04-03")

    def test_holiday_row_with_no_prices_is_not_the_exit(self):
        # Yahoo returns a row on a market holiday with every price null; it is not a session.
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp("2026-04-02")] = np.nan                 # holiday right after day 30
        op = _opens(_closes("2026-08-01"))
        op.loc[pd.Timestamp("2026-04-02")] = np.nan
        insp = _Insp(px, op)
        _, exit_session, last = insp._resolve_calendar_window(REPORT, 30)
        assert exit_session == pd.Timestamp("2026-04-03") and last == pd.Timestamp("2026-04-01")
        stock, spx, basis = insp.get_calendar_window(_row(), 30)
        assert basis == "open"
        assert stock == _ret(px.at[pd.Timestamp("2026-02-27"), "AAA"], op.at[pd.Timestamp("2026-04-03"), "AAA"])

    def test_a_vix_print_on_a_holiday_is_not_a_session(self):
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp("2026-04-02")] = np.nan
        px.loc[pd.Timestamp("2026-04-02"), "^VIX"] = 16.0            # Cboe extended hours
        _, exit_session, _ = _Insp(px)._resolve_calendar_window(REPORT, 30)
        assert exit_session == pd.Timestamp("2026-04-03")

    def test_holiday_on_day_n_falls_back_to_the_session_before(self):
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp("2026-04-01")] = np.nan                 # day 30 itself a holiday
        _, exit_session, last = _Insp(px)._resolve_calendar_window(REPORT, 30)
        assert last == pd.Timestamp("2026-03-31") and exit_session == pd.Timestamp("2026-04-02")

    def test_trailing_empty_row_does_not_close_the_window(self):
        px = _closes("2026-04-02")
        px.loc[pd.Timestamp("2026-04-02")] = np.nan                 # only an empty row after day 30
        with pytest.raises(WindowNotClosed):
            _Insp(px)._resolve_calendar_window(REPORT, 30)

    def test_open_until_the_exit_session_exists(self):
        px = _closes("2026-04-01")                                  # day 30 itself is the last price
        with pytest.raises(WindowNotClosed):
            _Insp(px)._resolve_calendar_window(REPORT, 30)
        stock, spx, basis = _Insp(px).get_calendar_window(_row(), 30)
        assert np.isnan(stock) and np.isnan(spx) and basis is None

    def test_closes_weeks_before_the_business_day_window(self):
        px = _closes((REPORT + pd.Timedelta(days=64)).strftime("%Y-%m-%d"))      # to Mon 4 May
        insp = _Insp(px, _opens(px))
        assert not np.isnan(insp.get_calendar_window(_row(), 60)[0])
        assert np.isnan(insp.get_window_pct_change(_row(), 60))     # 60 business days not closed


class TestReturns:
    def test_exit_at_the_next_open_for_both_legs(self):
        px = _closes("2026-08-01")
        op = _opens(px)
        stock, spx, basis = _Insp(px, op).get_calendar_window(_row(), 30)
        start, exit_session = pd.Timestamp("2026-02-27"), pd.Timestamp("2026-04-02")
        assert basis == "open"
        assert stock == _ret(px.at[start, "AAA"], op.at[exit_session, "AAA"])
        assert spx == _ret(px.at[start, "^GSPC"], op.at[exit_session, "^GSPC"])

    def test_without_opens_exit_at_the_close_on_or_before_day_n(self):
        px = _closes("2026-08-01")
        stock, spx, basis = _Insp(px).get_calendar_window(_row(), 60)
        start, last = pd.Timestamp("2026-02-27"), pd.Timestamp("2026-05-01")
        assert basis == "close"
        assert stock == _ret(px.at[start, "AAA"], px.at[last, "AAA"])
        assert spx == _ret(px.at[start, "^GSPC"], px.at[last, "^GSPC"])

    @pytest.mark.parametrize("bad", [np.nan, 0.0])
    def test_a_missing_open_on_either_leg_moves_both_to_the_close(self, bad):
        px = _closes("2026-08-01")
        op = _opens(px)
        op.at[pd.Timestamp("2026-04-02"), "^GSPC"] = bad
        stock, spx, basis = _Insp(px, op).get_calendar_window(_row(), 30)
        start, last = pd.Timestamp("2026-02-27"), pd.Timestamp("2026-04-01")
        assert basis == "close"
        assert stock == _ret(px.at[start, "AAA"], px.at[last, "AAA"])
        assert spx == _ret(px.at[start, "^GSPC"], px.at[last, "^GSPC"])

    def test_prices_that_stop_before_the_exit_give_no_window(self):
        # delisted mid-window: the last close must not be carried to day N
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp("2026-03-20"):, "AAA"] = np.nan
        stock, spx, basis = _Insp(px, _opens(px)).get_calendar_window(_row(), 30)
        assert np.isnan(stock) and np.isnan(spx) and basis is None

    def test_no_price_on_the_start_session_gives_no_window(self):
        # a single stale quote before the report must not serve as the start
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp("2026-02-26"):pd.Timestamp("2026-02-27"), "AAA"] = np.nan
        stock, _, _ = _Insp(px).get_calendar_window(_row(), 30)
        assert np.isnan(stock)

    def test_start_on_a_holiday_row_uses_the_session_before(self):
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp("2026-02-27")] = np.nan                  # the day before the report is closed
        stock, _, basis = _Insp(px).get_calendar_window(_row(), 30)
        assert basis == "close"
        assert stock == _ret(px.at[pd.Timestamp("2026-02-26"), "AAA"], px.at[pd.Timestamp("2026-04-01"), "AAA"])

    def test_unknown_ticker_is_nan(self):
        px = _closes("2026-08-01")
        stock, spx, basis = _Insp(px).get_calendar_window(_row(ticker="ZZZ"), 30)
        assert np.isnan(stock) and np.isnan(spx) and basis is None

    def test_no_stock_price_blanks_the_market_leg(self):
        px = _closes("2026-08-01")
        px.loc[:pd.Timestamp("2026-05-01"), "AAA"] = np.nan          # delisted history: no start price
        stock, spx, basis = _Insp(px).get_calendar_window(_row(), 30)
        assert np.isnan(stock) and np.isnan(spx) and basis is None


class TestSplitGuard:
    """Yahoo often leaves a micro cap's reverse split unadjusted: the window is left empty."""

    def _px(self, factor, day="2026-03-16"):
        px = _closes("2026-08-01")
        px.loc[pd.Timestamp(day):, "AAA"] *= factor
        return px

    def _row(self, cap):
        r = _row()
        r["MARKET_CAP"] = cap
        return r

    def test_micro_cap_with_a_twenty_fold_day_is_left_empty(self):
        stock, spx, basis = _Insp(self._px(20.0)).get_calendar_window(self._row(80e6), 30)
        assert np.isnan(stock) and np.isnan(spx) and basis is None

    def test_unknown_market_cap_is_guarded(self):
        stock, _, _ = _Insp(self._px(20.0)).get_calendar_window(_row(), 30)
        assert np.isnan(stock)

    def test_larger_company_keeps_its_move(self):
        stock, _, basis = _Insp(self._px(3.5)).get_calendar_window(self._row(800e6), 30)
        assert stock > 2.0 and basis == "close"

    def test_a_collapse_is_kept(self):
        stock, _, _ = _Insp(self._px(0.2)).get_calendar_window(self._row(80e6), 30)
        assert -0.9 < stock < -0.7

    def test_a_move_below_the_threshold_is_kept(self):
        stock, _, _ = _Insp(self._px(2.5)).get_calendar_window(self._row(80e6), 30)
        assert stock > 1.0

    def test_a_guarded_window_logs_an_informative_warning(self, caplog):
        with caplog.at_level("WARNING", logger="earningspy.inspectors.mixins"):
            _Insp(self._px(20.0)).get_calendar_window(self._row(80e6), 30)
        msg = " ".join(r.getMessage() for r in caplog.records if r.levelname == "WARNING")
        for part in ("SPLIT GUARD", "AAA", "30-calendar-day", "2026-03-02", "EMPTY", "$80.0M",
                     "$300M", "jumps 20.", "in one session", "2026-03-13", "2026-03-16", "reverse split", "%"):
            assert part in msg, part

    def test_no_warning_when_nothing_is_guarded(self, caplog):
        with caplog.at_level("WARNING", logger="earningspy.inspectors.mixins"):
            _Insp(self._px(20.0)).get_calendar_window(self._row(800e6), 30)
        assert not [r for r in caplog.records if "SPLIT GUARD" in r.getMessage()]

    def test_the_jump_into_the_exit_open_counts(self):
        px = _closes("2026-08-01")
        op = _opens(px)
        op.loc[pd.Timestamp("2026-04-02"), "AAA"] *= 20                # only the exit open jumps
        stock, _, _ = _Insp(px, op).get_calendar_window(self._row(80e6), 30)
        assert np.isnan(stock)


TODAY = pd.Timestamp.today().normalize()


def _calendar(days_ago, **cols):
    """One AAA row per report ``days_ago`` before today (the inspector recomputes DAYS_LEFT)."""
    rows = [{"EARNINGS_DATE": TODAY - pd.Timedelta(days=d), "TICKER": "AAA", "IS_AMC": 0, "BETA": 1.2,
             **{k: v[n] for k, v in cols.items()}} for n, d in enumerate(days_ago)]
    return pd.DataFrame(rows).set_index("EARNINGS_DATE")


class TestInspector:
    def _closes(self):
        return _closes(TODAY.strftime("%Y-%m-%d"))

    def test_inspect_fills_both_families(self):
        px = self._closes()
        report = TODAY - pd.Timedelta(days=35)
        insp = PEADInspector(calendar=_calendar([35], **{"1+30_RET": [np.nan]}), price_history=px, open_history=_opens(px))
        insp = insp.inspect(days=30, reuse_timeseries=True)
        row = insp.calendar.reset_index().iloc[0]
        stock, spx, basis = _Insp(px, _opens(px)).get_calendar_window(_row(report=report), 30)
        assert basis == "open"
        assert row["1+30_CAL_RET"] == stock and row["SPX_30_CAL_RET"] == spx and row["30_CAL_EXIT"] == "open"
        assert row["CAR_30_CAL"] == round(stock - row["CAPM_30"], 4)
        assert row["BHAR_30_CAL"] == round(stock - row["MARK_EXP_30"], 4)
        assert np.isnan(row["1+30_RET"])        # 30 business days have not closed after 35 calendar days

    def test_three_day_window_has_no_calendar_columns(self):
        px = self._closes()
        insp = PEADInspector(calendar=_calendar([10], **{"1+3_RET": [np.nan]}), price_history=px, open_history=_opens(px))
        insp = insp.inspect(days=3, reuse_timeseries=True)
        assert "1+3_CAL_RET" not in insp.calendar.columns

    def test_calendar_rows_are_selected_apart_from_business_day_rows(self):
        cal = _calendar([40, 41, 75], **{"1+30_RET": [0.01, np.nan, 0.02], "1+30_CAL_RET": [np.nan, 0.03, np.nan]})
        insp = PEADInspector(calendar=cal)
        bd = list(insp._get_affected_rows(30).index.get_level_values(0))
        cal_rows = list(insp._get_calendar_rows(30).index.get_level_values(0))
        assert bd == [TODAY - pd.Timedelta(days=41)]                      # business-day empty only
        assert cal_rows == [TODAY - pd.Timedelta(days=40)]                # calendar empty, within 30+30 days

    def test_old_bronze_without_calendar_columns_gets_calendar_rows_only(self):
        cal = _calendar([40], **{"1+30_RET": [0.01]})
        insp = PEADInspector(calendar=cal)
        assert len(insp._get_affected_rows(30)) == 0 and len(insp._get_calendar_rows(30)) == 1

    def test_calendar_pass_never_touches_a_stored_business_day_window(self):
        # a delisted ticker: its stored business-day values must survive the calendar pass
        px = self._closes()
        cal = _calendar([40], **{"1+30_RET": [0.1234], "CAR_30": [0.1], "BHAR_30": [0.11], "CAPM_30": [0.0234],
                                 "MARK_EXP_30": [0.0134], "1+30_CAL_RET": [np.nan]})
        cal["TICKER"] = "GONE"
        insp = PEADInspector(calendar=cal, price_history=px, open_history=_opens(px)).inspect(
            days=30, reuse_timeseries=True)
        row = insp.calendar.reset_index().iloc[0]
        assert (row["1+30_RET"], row["CAR_30"], row["BHAR_30"]) == (0.1234, 0.1, 0.11)
        assert pd.isna(row["1+30_CAL_RET"])

    def test_business_day_pass_never_touches_a_stored_calendar_window(self):
        px = self._closes()
        cal = _calendar([35], **{"1+30_RET": [np.nan], "1+30_CAL_RET": [0.4321], "30_CAL_EXIT": ["open"]})
        insp = PEADInspector(calendar=cal, price_history=px, open_history=_opens(px)).inspect(
            days=30, reuse_timeseries=True)
        assert insp.calendar.reset_index().iloc[0]["1+30_CAL_RET"] == 0.4321

    def test_inspect_logs_a_summary_of_guarded_windows(self, caplog):
        px = self._closes()
        report = TODAY - pd.Timedelta(days=35)
        px.loc[report + pd.Timedelta(days=10):, "AAA"] *= 20
        cal = _calendar([35], **{"1+30_RET": [np.nan], "MARKET_CAP": [50e6]})
        with caplog.at_level("WARNING"):
            insp = PEADInspector(calendar=cal, price_history=px, open_history=_opens(px)).inspect(
                days=30, reuse_timeseries=True)
        summary = [r.getMessage() for r in caplog.records if r.name == "earningspy.inspectors.pead"]
        assert summary and "1 of 1 30-calendar-day windows left empty" in summary[0]
        assert f"AAA {report.date()}" in summary[0]
        assert pd.isna(insp.calendar.reset_index().iloc[0]["1+30_CAL_RET"])

    def test_columns_exist_when_no_row_is_affected(self):
        px = self._closes()
        cal = _calendar([5], **{"1+30_RET": [np.nan]})                # too recent for a 30-day window
        insp = PEADInspector(calendar=cal, price_history=px, open_history=_opens(px))
        insp = insp.inspect(days=30, reuse_timeseries=True)
        for col in ("1+30_CAL_RET", "SPX_30_CAL_RET", "CAR_30_CAL", "BHAR_30_CAL", "30_CAL_EXIT"):
            assert col in insp.calendar.columns
