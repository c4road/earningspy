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
)
from earningspy.calendars.utils import days_left
from earningspy.inspectors.mixins import CARMixin, TimeSeriesMixin


class PEADInspector(CARMixin, TimeSeriesMixin):
    """
    Calendar should be passed using this method
    pd.read_csv('<field-name>.csv', index_col=0, parse_dates=True)
    """

    def __init__(self, 
                 calendar=None,
                 price_history=None):

        self.calendar = self._load_calendar(calendar)
        self.backup = self.calendar.copy()
        self.price_history = self._load_price_history(price_history)

        self.remaining_data = self.calendar[~(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < -3)]
        self.merged_data = None


    def _load_calendar(self, calendar):

        calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] = calendar.apply(lambda row: days_left(row), axis=1)
        calendar = calendar.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)

        return calendar
    
    def _sort_calendar(self):
        self.calendar = self.calendar.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)


    def inspect(self, days=3, dry_run=False, reuse_timeseries=False, post_earnings=False, async_=False):

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

    def refresh(self, days=3, dry_run=False, reuse_timeseries=False, check_column=None, deep=False, async_=False):

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
        

    def _process_windows_columns(self, days=3, reuse_timeseries=False, async_=False):

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


    def _get_affected_rows(self, days, check_column=ABS_RET_KEY, deep=False, post_earnings=False):

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


    def join(self, storage, earnings_phase: str = "pre", keep="last"):
        """
        Join calendar with storage data.

        :param storage: DataFrame with historical data
        :param earnings_phase: 'pre' or 'post'
        :param keep: 'first' or 'last'
            first -> preserve data from new storage values
            last -> Preserves data from the canonical storage (default)
        """

        if storage is None or storage.empty:
            raise Exception("storage can't be empty")

        if self.calendar.empty:
            raise Exception("calendar is empty nothing to concat")

        if earnings_phase not in {"pre", "post"}:
            raise ValueError("earnings_phase must be either 'pre' or 'post'")

        if keep not in {"first", "last"}:
            raise ValueError("Keep must be either 'first' or 'last'")

        if earnings_phase == "pre":
            # Accounts for BMO row cases.
            storage = storage[storage[DAYS_TO_EARNINGS_KEY_CAPITAL] > 0]
        else: 
            # Account for AMC row cases.
            storage = storage[storage[DAYS_TO_EARNINGS_KEY_CAPITAL] <= -1]

        self.merged_data = (
            pd.concat([storage, self.calendar], join="outer")
            .sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)
            .reset_index()
            .drop_duplicates(subset=[FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL], keep=keep)
            .set_index(FINVIZ_EARNINGS_DATE_KEY)
        )

        self.merged_data[DAYS_TO_EARNINGS_KEY_CAPITAL] = (
            self.merged_data.apply(lambda row: days_left(row), axis=1)
        )
        self.merged_data = self.merged_data.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=False)

        return self.merged_data


    def _get_windows_abnormal_return(self, days):

        label = ABS_RET_KEY.format(days)
    
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_window_pct_change(row, days=days), axis=1)

    
    def _get_windows_market_expected_return(self, days):
        
        label = MARK_EXP_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_market_expected_return(row, days=days), axis=1)


    def _get_windows_capm(self, days):

        label = CAPM_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_capm(row, days=days), axis=1)


    def _get_windows_expected_return(self, days):

        label = EXP_RET_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_expected_return(row, days=days), axis=1)


    def _get_windows_risk_free_rate(self, days):
        label = RF_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_risk_free_rate(row, days=days), axis=1)


    def _get_windows_vix(self, days):

        label = VIX_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_vix(row, days=days), axis=1)


    def _get_earnings_vix(self):

        self.calendar.loc[self.affected_rows.index, EARNING_VIX_KEY] = self.calendar.loc[self.affected_rows.index].apply(
            lambda row: self.get_vix_for_date(row), axis=1)


    def _get_windows_car(self, days):
        label = CAR_KEY.format(days)
        ret_label = ABS_RET_KEY.format(days)
        capm_label = CAPM_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = (self.calendar[ret_label] - self.calendar[capm_label]).round(4)


    def _get_windows_bhar(self, days):
        label = BHAR_KEY.format(days)
        ret_label = ABS_RET_KEY.format(days)
        benchmark_label = MARK_EXP_KEY.format(days)
        self.calendar.loc[self.affected_rows.index, label] = (self.calendar[ret_label] - self.calendar[benchmark_label]).round(4)


    def _find_and_remove_duplicates(self):
        self.calendar = self.calendar.reset_index()
        self.calendar = self.calendar.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])
        self.calendar = self.calendar[~self.calendar.index.duplicated(keep='first')]

        self._remove_duplicate_ticker_quarters()

        self.calendar = self.calendar.reset_index()
        self.calendar = self.calendar.set_index(FINVIZ_EARNINGS_DATE_KEY)


    def _remove_duplicate_ticker_quarters(self):
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
