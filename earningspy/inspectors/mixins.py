from __future__ import annotations

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
)

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
        # End should not jump backward when a later trading day exists.
        end_date = self._resolve_price_date(end_target, method="backfill", fallback_method="pad")

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

        except KeyError as exc:
            print(f"❌ Could not compute window pct change for {ticker}: {exc}")
            return np.nan


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
        initial_date, end_date = self._resolve_window_dates(earnings_date, days)

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

        market_assets = MARKET_DATA_TICKERS

        if async_:
            price_history = async_get_portfolio(list(assets) + market_assets, from_=from_)
        else:
            price_history = get_portfolio(list(assets) + market_assets, from_=from_)        
        price_history.index = pd.to_datetime(price_history.index, errors='coerce')
        price_history = price_history[~price_history.index.isna()]
        price_history = price_history[~price_history.index.duplicated(keep='first')]        
        price_history = price_history.sort_index()

        return price_history
