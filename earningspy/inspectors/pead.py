from __future__ import annotations

from typing import Literal, Optional, Union

import pandas as pd

from earningspy.common.constants import (
    FINVIZ_EARNINGS_DATE_KEY,
    DAYS_TO_EARNINGS_KEY_CAPITAL,
    TICKER_KEY_CAPITAL,
    ABS_RET_KEY,
    EXP_RET_KEY,
    RF_KEY,
    MARK_EXP_KEY,
    CAPM_KEY,
    VIX_KEY,
    EARNING_VIX_KEY,
    CAR_KEY,
    BHAR_KEY,
    ALLOWED_WINDOWS,
    AVAILABLE_CHECK_COLUMNS,
    DATADATE_KEY
)
from earningspy.calendars.utils import days_left
from earningspy.inspectors.mixins import CARMixin, TimeSeriesMixin


class PEADInspector(CARMixin, TimeSeriesMixin):
    """
    Calendar should be passed using this method
    pd.read_csv('<field-name>.csv', index_col=0, parse_dates=True)
    """

    def __init__(
        self,
        calendar: Optional[pd.DataFrame] = None,
        price_history: Optional[pd.DataFrame] = None,
    ):

        self.calendar: pd.DataFrame = self._load_calendar(calendar)
        self.backup = self.calendar.copy()
        self.price_history: Optional[pd.DataFrame] = self._load_price_history(price_history)

        self.remaining_data: pd.DataFrame = self.calendar[
            ~(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < -3)
        ]
        self.merged_data: Optional[pd.DataFrame] = None
        self.affected_rows: Optional[pd.DataFrame] = None


    def _load_calendar(self, calendar: Optional[pd.DataFrame]) -> pd.DataFrame:

        calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] = calendar.apply(lambda row: days_left(row), axis=1)
        calendar = calendar.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)

        return calendar
    
    def _sort_calendar(self) -> None:
        self.calendar = self.calendar.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)


    def inspect(
        self,
        days: int = 3,
        dry_run: bool = False,
        reuse_timeseries: bool = False,
        post_earnings: bool = False,
        async_: bool = False,
    ) -> Union["PEADInspector", pd.DataFrame]:

        if days not in ALLOWED_WINDOWS:
            raise Exception(f'Invalid day range. Select from {ALLOWED_WINDOWS}')

        self.affected_rows = self._get_affected_rows(days, post_earnings=post_earnings)
        if dry_run:
            self.affected_rows = self.affected_rows.reset_index()
            self.affected_rows = self.affected_rows.set_index([FINVIZ_EARNINGS_DATE_KEY])
            return self.affected_rows

        self._process_windows_columns(days=days, reuse_timeseries=reuse_timeseries, async_=async_)
        self._get_earnings_vix()
        self._find_and_remove_duplicates()
        self._sort_calendar()

        return self

    def refresh(
        self,
        days: int = 3,
        dry_run: bool = False,
        reuse_timeseries: bool = False,
        check_column: Optional[str] = None,
        deep: bool = False,
        async_: bool = False,
    ) -> Union["PEADInspector", pd.DataFrame]:

        if days not in ALLOWED_WINDOWS:
            raise Exception(f'Invalid day range. Select from {ALLOWED_WINDOWS}')

        if not check_column or check_column not in AVAILABLE_CHECK_COLUMNS:
            raise Exception(f"Provide a column to check for NaNs to do the refresh, must be from this list {AVAILABLE_CHECK_COLUMNS}")
        
        self.affected_rows = self._get_affected_rows(days, check_column=check_column, deep=deep)
        if dry_run:
            self.affected_rows = self.affected_rows.reset_index()
            self.affected_rows = self.affected_rows.set_index([FINVIZ_EARNINGS_DATE_KEY])
            return self.affected_rows
        
        self._process_windows_columns(days=days, reuse_timeseries=reuse_timeseries, async_=async_)
        self._get_earnings_vix()
        self._find_and_remove_duplicates()

        return self
        

    def _process_windows_columns(
        self,
        days: int = 3,
        reuse_timeseries: bool = False,
        async_: bool = False,
    ) -> None:

        if not reuse_timeseries:
            self.price_history = self.fetch_price_history(assets=set(self.affected_rows.index.get_level_values(1).to_list()), async_=async_)

        self.calendar = self.calendar.reset_index()
        self.calendar = self.calendar.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])

        self._get_windows_abnormal_return(days=days)
        self._get_windows_risk_free_rate(days=days)
        self._get_windows_expected_return(days=days)
        self._get_windows_market_expected_return(days=days)
        self._get_windows_capm(days=days)
        self._get_windows_car(days=days)
        self._get_windows_bhar(days=days)
        self._get_windows_vix(days=days)


    def _get_affected_rows(
        self,
        days: int,
        check_column: str = ABS_RET_KEY,
        deep: bool = False,
        post_earnings: bool = False,
    ) -> pd.DataFrame:

        start = days
        end = days + 30

        if deep:
            affected_rows = self.calendar[(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] <= -start)]
        else:
            affected_rows = self.calendar[(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] <= -start) &
                                          (self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] >= -end)]

        if not post_earnings:
            try:
                affected_rows = affected_rows[affected_rows[check_column.format(days)].isna()]
            except KeyError:
                raise Exception(f"Check column {check_column.format(days)} not found in the calendar. Is this post earnings data?"
                       " If so, set post_earnings=True.")
        affected_rows = affected_rows.reset_index()
        affected_rows = affected_rows.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])
        return affected_rows


    def join(
        self,
        storage: pd.DataFrame,
        earnings_phase: Literal["pre", "post"] = "pre",
        preserve: Literal["canonical", "incoming"] = "canonical",
        future_threshold_days: int = 5,
        past_threshold_days: int = 5,
    ) -> pd.DataFrame:
        """
        Join calendar with storage data.

        :param storage: DataFrame with historical data
        :param earnings_phase: 'pre' or 'post'
        :param preserve: 'canonical' or 'incoming'
            canonical -> preserve data from the canonical calendar (self.calendar)
            incoming -> preserve data from storage
        """

        if storage is None or storage.empty:
            raise Exception("storage can't be empty")

        if self.calendar.empty:
            raise Exception("calendar is empty nothing to concat")

        if earnings_phase not in {"pre", "post"}:
            raise ValueError("earnings_phase must be either 'pre' or 'post'")

        if preserve not in {"canonical", "incoming"}:
            raise ValueError("preserve must be either 'canonical' or 'incoming'")

        if earnings_phase == "pre":
            # Do not get data that with more than 5 days before earnings
            storage = storage[(storage[DAYS_TO_EARNINGS_KEY_CAPITAL] > 0) & 
                              (storage[DAYS_TO_EARNINGS_KEY_CAPITAL] <= future_threshold_days)].copy()
            
        else:
            storage = storage[(storage[DAYS_TO_EARNINGS_KEY_CAPITAL] < -1) & 
                              (storage[DAYS_TO_EARNINGS_KEY_CAPITAL] >= -past_threshold_days)].copy()

        if storage.empty:
            print("No data to merge after filtering by earnings_phase")
            return self.calendar

        cal = self.calendar.copy()

        # --- Critical fix: ensure dedupe keys exist as COLUMNS (not only in the index) ---
        needed_keys = {FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL}

        if not needed_keys.issubset(storage.columns):
            storage = storage.reset_index()

        if not needed_keys.issubset(cal.columns):
            cal = cal.reset_index()

        # Ensure DATADATE exists in both frames and is consistently datetime
        if DATADATE_KEY not in storage.columns:
            storage[DATADATE_KEY] = pd.NaT
        if DATADATE_KEY not in cal.columns:
            cal[DATADATE_KEY] = pd.NaT

        storage[DATADATE_KEY] = pd.to_datetime(storage[DATADATE_KEY], errors="raise", format="mixed")
        cal[DATADATE_KEY] = pd.to_datetime(cal[DATADATE_KEY], errors="raise", format="mixed")

        # Preserve rule: canonical => calendar wins; incoming => storage wins
        if preserve == "canonical":
            cal["_src_pri"] = 1
            storage["_src_pri"] = 0
        else:  # preserve == "incoming"
            cal["_src_pri"] = 0
            storage["_src_pri"] = 1

        merged = pd.concat([storage, cal], join="outer", ignore_index=True)

        self.merged_data = (
            merged
            .sort_values(["_src_pri", DATADATE_KEY], ascending=[False, False], kind="mergesort")
            .drop_duplicates(subset=[FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL], keep="first")
            .drop(columns=["_src_pri"])
            .sort_values(DATADATE_KEY, ascending=False)
            .set_index(FINVIZ_EARNINGS_DATE_KEY)
        )

        self.merged_data[DAYS_TO_EARNINGS_KEY_CAPITAL] = (
            self.merged_data.apply(lambda row: days_left(row), axis=1)
        )
        self.merged_data = self.merged_data.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)

        return self.merged_data


    def _get_windows_abnormal_return(self, days: int) -> None:

        label = ABS_RET_KEY.format(days)
    
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_window_pct_change(row, days=days), axis=1)

    
    def _get_windows_market_expected_return(self, days: int) -> None:
        
        label = MARK_EXP_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_market_expected_return(row, days=days), axis=1)


    def _get_windows_capm(self, days: int) -> None:

        label = CAPM_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_capm(row, days=days), axis=1)


    def _get_windows_expected_return(self, days: int) -> None:

        label = EXP_RET_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_expected_return(row, days=days), axis=1)


    def _get_windows_risk_free_rate(self, days: int) -> None:
        label = RF_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_risk_free_rate(row, days=days), axis=1)


    def _get_windows_vix(self, days: int) -> None:

        label = VIX_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_vix(row, days=days), axis=1)


    def _get_earnings_vix(self) -> None:

        self.calendar.loc[self.affected_rows.index, EARNING_VIX_KEY] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_vix_for_date(row), axis=1)


    def _get_windows_car(self, days: int) -> None:
        label = CAR_KEY.format(days)
        ret_label = ABS_RET_KEY.format(days)
        capm_label = CAPM_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = (self.calendar[ret_label] - self.calendar[capm_label]).round(4)


    def _get_windows_bhar(self, days: int) -> None:
        label = BHAR_KEY.format(days)
        ret_label = ABS_RET_KEY.format(days)
        benchmark_label = MARK_EXP_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = (self.calendar[ret_label] - self.calendar[benchmark_label]).round(4)


    def _find_and_remove_duplicates(self) -> None:
        self.calendar = self.calendar.reset_index()
        self.calendar = self.calendar.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])
        self.calendar = self.calendar[~self.calendar.index.duplicated(keep='first')]

        self._remove_duplicate_ticker_quarters()

        self.calendar = self.calendar.reset_index()
        self.calendar = self.calendar.set_index(FINVIZ_EARNINGS_DATE_KEY)


    def _remove_duplicate_ticker_quarters(self) -> None:
        self.calendar = self.calendar.reset_index()
        self.calendar['year'] = self.calendar[FINVIZ_EARNINGS_DATE_KEY].dt.year
        self.calendar['quarter'] = self.calendar[FINVIZ_EARNINGS_DATE_KEY].dt.quarter
        self.calendar = self.calendar.sort_values(FINVIZ_EARNINGS_DATE_KEY)
        original_len = len(self.calendar)
        self.calendar = self.calendar.drop_duplicates(subset=[TICKER_KEY_CAPITAL, 'year', 'quarter'], keep='last')
        num_duplicates = original_len - len(self.calendar)
        print(f"Found and removed {num_duplicates} duplicate ticker-quarter entries.")
        self.calendar = self.calendar.drop(columns=['year', 'quarter'])
        self.calendar = self.calendar.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])
