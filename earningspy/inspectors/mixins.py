from __future__ import annotations

import logging
import math
from typing import Iterable, Optional, Union

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from earningspy.generators.yahoo.async_timeseries import get_portfolio as async_get_portfolio
from earningspy.generators.yahoo.time_series import get_portfolio
from earningspy.common.constants import (
    MARKET_DATA_TICKERS,
    TBILL_10_YEAR,
    EXP_RET_KEY,
    SP_500_TICKER,
    BETA_KEY,
    RF_KEY,
    TBILL_10_YEAR,
    VIX_TICKER,
    MARKET_CAP_KEY,
    SPLIT_GUARD_JUMP,
    SPLIT_GUARD_MAX_MARKET_CAP,
)


logger = logging.getLogger(__name__)


class WindowNotClosed(KeyError):
    """The event window ends after the last available price: its return is not known yet.

    A KeyError subclass so existing ``except KeyError`` paths still yield NaN.
    """


class CARMixin:

    def _coerce_price_timestamp(self, value: Union[pd.Timestamp, str]) -> pd.Timestamp:
        return pd.Timestamp(value).normalize()

    def _resolve_price_date(
        self,
        target: Union[pd.Timestamp, str],
        method: str = "nearest",
        fallback_method: Optional[str] = None,
    ) -> pd.Timestamp:
        target_ts = self._coerce_price_timestamp(target)

        if target_ts in self.price_history.index:
            return target_ts

        locator = self.price_history.index.get_indexer([target_ts], method=method)[0]
        if locator == -1 and fallback_method is not None:
            locator = self.price_history.index.get_indexer([target_ts], method=fallback_method)[0]
        if locator == -1:
            raise KeyError(f"Could not resolve trading date for {target_ts}")

        return self.price_history.index[locator]

    def _resolve_window_dates(self, earnings_date: pd.Timestamp, days: int) -> tuple[pd.Timestamp, pd.Timestamp]:
        earnings_ts = self._coerce_price_timestamp(earnings_date)
        initial_target = earnings_ts - BDay(1)
        end_target = earnings_ts + BDay(days)

        # Start should not jump forward when a prior trading day exists.
        initial_date = self._resolve_price_date(initial_target, method="pad", fallback_method="backfill")
        # A window that ends after the last available price has not closed: its return is
        # unknown. Never resolve the end backward — that would store a shorter window as if
        # it were the full one. The row stays empty and is computed once the window closes.
        last_price_date = self.price_history.index.max()
        if end_target > last_price_date:
            raise WindowNotClosed(
                f"window {initial_target.date()} -> {end_target.date()} ends after the last "
                f"price {last_price_date.date()}"
            )
        # End resolves forward to the next trading day (holidays).
        end_date = self._resolve_price_date(end_target, method="backfill")

        return initial_date, end_date

    def get_window_pct_change(self, row: pd.Series, days: int) -> float:
        earnings_date = row.name[0]
        ticker = row.name[1]

        initial_target = self._coerce_price_timestamp(earnings_date) - BDay(1)
        end_target = self._coerce_price_timestamp(earnings_date) + BDay(days)

        try:
            initial_date, end_date = self._resolve_window_dates(earnings_date, days)
            ts_slice = self.price_history.loc[:end_date, ticker].copy()
            ts_slice_ffill = ts_slice.ffill().loc[initial_date:end_date]
            ts_valid = ts_slice_ffill.dropna()

            if len(ts_valid) < 2:
                print(
                    "⚠️ Not enough data after ffill for "
                    f"{ticker}. target window {initial_target} -> {end_target}, "
                    f"resolved window {initial_date} -> {end_date}"
                )
                return np.nan

            start_price = ts_valid.iloc[0]
            end_price = ts_valid.iloc[-1]

            pct = (end_price - start_price) / start_price
            return np.round(pct, 4)

        except WindowNotClosed:
            return np.nan
        except KeyError as exc:
            print(f"❌ Could not compute window pct change for {ticker}: {exc}")
            return np.nan


    def _resolve_calendar_window(self, earnings_date: pd.Timestamp, days: int) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
        """(start, exit, last) sessions of the N-calendar-day window.

        start  the trading day before the report (the same start as the business-day window)
        exit   the first session after report + N calendar days: its open is the pessimistic exit
        last   the last session on or before report + N calendar days: its close is the fallback exit

        Raises WindowNotClosed while the exit session is not in the price history yet.
        """
        earnings_ts = self._coerce_price_timestamp(earnings_date)
        start = self._resolve_price_date(earnings_ts - BDay(1), method="pad", fallback_method="backfill")
        day_n = earnings_ts + pd.Timedelta(days=days)
        sessions = self._sessions()
        after = sessions[sessions > day_n]
        if after.empty:
            raise WindowNotClosed(
                f"calendar window {earnings_ts.date()} + {days}d: no session after {day_n.date()} "
                f"(last session {sessions.max().date() if len(sessions) else None})"
            )
        last = sessions[sessions <= day_n].max()
        return start, after[0], last

    def _sessions(self) -> pd.DatetimeIndex:
        """US trading sessions: the dates the S&P 500 has a close. Yahoo returns rows with no prices
        on market holidays, and ^VIX prints on some of them (Cboe extended hours), so neither the
        frame's index nor "any series has a price" is the cash market's calendar. Without the
        S&P 500 in the frame: the dates on which any series has a price."""
        frame = self.price_history
        cached = getattr(self, "_sessions_cache", None)
        if cached is not None and cached[0] is frame and cached[1] == frame.shape:
            return cached[2]
        if SP_500_TICKER in frame.columns and frame[SP_500_TICKER].notna().any():
            traded = frame[SP_500_TICKER].notna()
        else:
            traded = frame.notna().any(axis=1)
        sessions = frame.index[traded.to_numpy()]
        self._sessions_cache = (frame, frame.shape, sessions)
        return sessions

    def _open_at(self, ticker: str, session: pd.Timestamp) -> float:
        opens = getattr(self, "open_history", None)
        if opens is None or ticker not in opens.columns or session not in opens.index:
            return np.nan
        value = opens.at[session, ticker]
        return float(value) if pd.notna(value) and value > 0 else np.nan

    def _close_on_or_before(self, ticker: str, session: pd.Timestamp) -> float:
        closes = self.price_history.loc[:session, ticker].dropna()
        return float(closes.iloc[-1]) if len(closes) else np.nan

    def _close_at(self, ticker: str, session: pd.Timestamp) -> float:
        """The close on exactly ``session``; NaN when the ticker has no price that day. A delisted or
        stale ticker must not lend an older close to a window it did not trade through."""
        if ticker not in self.price_history.columns or session not in self.price_history.index:
            return np.nan
        value = self.price_history.at[session, ticker]
        return float(value) if pd.notna(value) and value > 0 else np.nan

    def get_calendar_window(self, row: pd.Series, days: int) -> tuple[float, float, Optional[str]]:
        """(stock return, S&P 500 return, exit basis) over the N-calendar-day window.

        Both legs start at the close of the last session before the report. They exit at the open of
        the first session after report + N calendar days when the stock and the S&P 500 both have
        that open, else both at the close of the last session on or before day N, so the two legs
        always cover the same dates. Every price is taken on its exact session: a ticker with no
        price that day (delisted, halted, stale) gets no window rather than an older price carried
        forward. NaN (and no basis) while the window is open or prices are missing.
        """
        earnings_date, ticker = row.name[0], row.name[1]
        try:
            start, exit_session, last = self._resolve_calendar_window(earnings_date, days)
        except WindowNotClosed:
            return np.nan, np.nan, None
        except KeyError as exc:
            print(f"❌ Could not resolve calendar window for {ticker}: {exc}")
            return np.nan, np.nan, None

        if ticker not in self.price_history.columns:
            return np.nan, np.nan, None

        legs = (ticker, SP_500_TICKER)
        sessions = self._sessions()
        before = sessions[sessions <= start]
        if before.empty:
            return np.nan, np.nan, None
        start = before.max()                      # a holiday row resolves to the session before it
        starts = [self._close_at(t, start) for t in legs]
        opens = [self._open_at(t, exit_session) for t in legs]
        if all(pd.notna(v) for v in opens):
            ends, basis = opens, "open"
        else:
            ends = [self._close_at(t, last) for t in legs]
            basis = "close"

        def _ret(a, b):
            return np.round((b - a) / a, 4) if pd.notna(a) and pd.notna(b) and a > 0 else np.nan

        stock_ret, spx_ret = _ret(starts[0], ends[0]), _ret(starts[1], ends[1])
        if pd.isna(stock_ret):
            return np.nan, np.nan, None          # the S&P 500 leg only means something beside the stock's
        exit_at = exit_session if basis == "open" else last
        jump = self._split_suspect(row, ticker, start, exit_at, ends[0])
        if jump is not None:
            self._warn_split_guard(row, ticker, days, start, exit_at, basis, starts[0], ends[0],
                                   stock_ret, jump)
            return np.nan, np.nan, None
        return stock_ret, spx_ret, basis

    def _warn_split_guard(self, row, ticker, days, start, exit_at, basis, start_price, exit_price,
                          stock_ret, jump) -> None:
        """One WARNING per guarded window, with everything needed to check it by hand."""
        if not hasattr(self, "split_guarded"):
            self.split_guarded = []
        self.split_guarded.append((ticker, pd.Timestamp(row.name[0]), days))
        cap = pd.to_numeric(row.get(MARKET_CAP_KEY, np.nan), errors="coerce")
        cap_text = f"${cap / 1e6:,.1f}M" if pd.notna(cap) else "unknown"
        prev_day, day, before, after, ratio = jump
        logger.warning(
            "SPLIT GUARD — %s %d-calendar-day window after the %s report left EMPTY "
            "(1+%d_CAL_RET, SPX_%d_CAL_RET, CAR_%d_CAL, BHAR_%d_CAL, %d_CAL_EXIT). "
            "Market cap %s is under the $%.0fM micro-cap limit and the price jumps %.2fx in one session: "
            "%s %s -> %s %s (%s). Yahoo often leaves a micro cap's reverse split unadjusted across such "
            "a day, so the window would read %+.1f%% (%s close %.4f -> %s %s %.4f) and that figure is "
            "not trusted. Check the ticker's split history; a genuine move needs the guard lifted by hand.",
            ticker, days, pd.Timestamp(row.name[0]).date(), days, days, days, days, days,
            cap_text, SPLIT_GUARD_MAX_MARKET_CAP / 1e6, ratio,
            prev_day.date(), f"{before:.4f}", day.date(), f"{after:.4f}",
            "the exit open" if (basis == "open" and day == exit_at) else "closes",
            stock_ret * 100, start.date(), start_price, exit_at.date(), basis, exit_price,
        )

    def _split_suspect(self, row: pd.Series, ticker: str, start: pd.Timestamp, end: pd.Timestamp,
                       exit_price: float) -> Optional[tuple]:
        """A micro cap (market cap under SPLIT_GUARD_MAX_MARKET_CAP at the report, or unknown) whose
        price rises SPLIT_GUARD_JUMP times or more from one session to the next inside the window,
        the exit price included. Yahoo often leaves a reverse split unadjusted across such a day,
        which would store a fake multi-fold return; the window is left empty instead.

        Returns the largest jump as (previous session, session, price before, price after, ratio),
        or None when the window is not suspect."""
        cap = pd.to_numeric(row.get(MARKET_CAP_KEY, np.nan), errors="coerce")
        if pd.notna(cap) and cap >= SPLIT_GUARD_MAX_MARKET_CAP:
            return None
        sessions = self._sessions()
        first = sessions[sessions <= start]
        first = first.max() if len(first) else start
        span = sessions[(sessions >= first) & (sessions <= end)]
        path = self.price_history[ticker].ffill().reindex(span)
        if pd.notna(exit_price) and span.size and span[-1] == end:
            path.iloc[-1] = exit_price           # an open exit: its gap counts too
        ratios = (path / path.shift(1)).dropna()
        if not (ratios >= SPLIT_GUARD_JUMP).any():
            return None
        day = ratios.idxmax()
        prev_day = path.index[path.index.get_loc(day) - 1]
        return prev_day, day, float(path[prev_day]), float(path[day]), float(ratios[day])


    def get_capm(self, row: pd.Series, days: int = 0) -> float:

        rf_label = RF_KEY.format(days).strip()
        R_label = EXP_RET_KEY.format(days).strip()

        rf = row[rf_label]
        R = row[R_label]
        b = row[BETA_KEY]

        capm = rf + b * (R - rf)
        return np.round(capm, 4)


    def _expected_return_for_series(self, series: pd.Series, days: int) -> float:
        """Historical mean N-day return of a price series, up to and including ``date``.

        The three canonical windows keep their exact original construction so the
        production 3/30/60 frame is unchanged:
            days == 3  -> mean of 3-business-day point returns (daily pct_change(3))
            days == 30 -> mean of month-over-month returns   (monthly resample)
            days == 60 -> mean of two-month returns          (bimonthly resample)

        Any OTHER window generalizes the days==3 construction: the mean of the
        N-business-day point return on the daily series. This mirrors how the raw
        window return itself is measured (earnings_date + N business days in
        ``get_window_pct_change``), so the expected-return baseline is on the same
        N-business-day footing as the realized return it is subtracted from.
        """
        if days == 30:
            return series.resample('1ME').ffill().pct_change(fill_method=None).mean()
        if days == 60:
            return series.resample('2ME').ffill().pct_change(fill_method=None).mean()
        # days == 3 and every other (arbitrary) window: N-business-day point return.
        return series.pct_change(days, fill_method=None).mean()

    def get_expected_return(self, row: pd.Series, days: int) -> float:

        date = row.name[0]
        ticker = row.name[1]

        try:
            exp_ret = self._expected_return_for_series(self.price_history[ticker].loc[:date], days)
        except KeyError:
            exp_ret = np.nan

        return np.round(exp_ret, 4)


    def get_market_expected_return(self, row: pd.Series, days: int) -> float:

        date = row.name[0]
        try:
            exp_ret = self._expected_return_for_series(self.price_history[SP_500_TICKER].loc[:date], days)
        except KeyError:
            exp_ret = np.nan

        return np.round(exp_ret, 4)


    def get_risk_free_rate(self, row: pd.Series, days: int) -> float:

        date = self._resolve_price_date(row.name[0], method="pad", fallback_method="backfill")
        rf = self.price_history.loc[date][TBILL_10_YEAR]

        if math.isnan(rf):
            rf = self.price_history[TBILL_10_YEAR].mean()
        rf = (rf / 100) * (days / 251)
        return np.round(rf, 4)


    def get_vix(self, row: pd.Series, days: int = 0) -> float:
        earnings_date = row.name[0]
        try:
            initial_date, end_date = self._resolve_window_dates(earnings_date, days)
        except WindowNotClosed:
            return np.nan

        ts_slice = self.price_history.loc[initial_date:end_date]
        try:
            value = ts_slice[VIX_TICKER].mean()
        except KeyError as e:
            print(f"VIX windows data is not in timeseries data")
            value = np.nan

        return np.round(value, 2)


    def get_vix_for_date(self, row: pd.Series) -> float:
        earnings_date = row.name[0]
        ticker = row.name[1]

        if not pd.isna(row['IS_AMC']) and row['IS_AMC'] == 1:
            earnings_date = self._coerce_price_timestamp(earnings_date) - BDay(1)

        earnings_date = self._resolve_price_date(earnings_date, method="pad", fallback_method="backfill")

        try:
            value = self.price_history.loc[earnings_date][VIX_TICKER]
        except KeyError as e:
            print(f"VIX value not present for {ticker} is not in timeseries data")
            value = np.nan

        return np.round(value, 2)


class TimeSeriesMixin:

    def _load_price_history(
        self,
        price_history: Optional[pd.DataFrame],
        assets: Optional[Iterable[str]] = None,
    ) -> Optional[pd.DataFrame]:

        if price_history is None or price_history.empty:
            return None
        
        print("timeseries found")
        price_history.index = pd.to_datetime(price_history.index, errors='coerce')
        price_history = price_history[~price_history.index.isna()]
        price_history = price_history[~price_history.index.duplicated(keep='first')]        
        price_history = price_history.sort_index()
    
        return price_history

    def fetch_price_history(
        self,
        assets: Iterable[str],
        from_: str = "5y",
        async_: bool = False,
    ) -> pd.DataFrame:
        """Daily closes for ``assets`` plus the market series. The opens from the same responses
        are kept on ``self.open_history`` (the calendar windows exit at an open)."""

        market_assets = MARKET_DATA_TICKERS
        fetch = async_get_portfolio if async_ else get_portfolio
        price_history, open_history = fetch(list(assets) + market_assets, from_=from_, opens=True)

        price_history = self._clean_history(price_history)
        self.open_history = self._clean_history(open_history).reindex(price_history.index)

        return price_history

    @staticmethod
    def _clean_history(frame: pd.DataFrame) -> pd.DataFrame:
        frame.index = pd.to_datetime(frame.index, errors='coerce')
        frame = frame[~frame.index.isna()]
        frame = frame[~frame.index.duplicated(keep='first')]
        return frame.sort_index()
