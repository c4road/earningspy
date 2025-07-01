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
    DATADATE_KEY,
    ALLOWED_WINDOWS,
)
from earningspy.calendars.utils import days_left
from earningspy.inspectors.mixins import CARMixin, TimeSeriesMixin

class PEADInspector(CARMixin, TimeSeriesMixin):

    def __init__(self, 
                 calendar=None,
                 price_history=None):

        self.calendar = self._load_calendar(calendar)
        self.new_training_data = self.calendar[(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < -3)]

        self.price_history = self._load_price_history(price_history=price_history, 
                                                      assets=set(self.new_training_data[TICKER_KEY_CAPITAL].to_list()))
        self.remaining_data = self.calendar[~(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < -3)]
        self.merged_data = None


    def _load_calendar(self, calendar):

        calendar.loc[:, DAYS_TO_EARNINGS_KEY_CAPITAL] = calendar.apply(lambda row: days_left(row), axis=1)
        calendar.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=True)
        return calendar


    def inspect(self, days=3, dry_run=False):

        if days not in ALLOWED_WINDOWS:
            raise Exception(f'Invalid day range. Select from {ALLOWED_WINDOWS}')
    
        self.new_training_data = self.new_training_data.reset_index()
        self.new_training_data = self.new_training_data.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])
        affected_rows = self.new_training_data[self.new_training_data[DAYS_TO_EARNINGS_KEY_CAPITAL] < -days]

        if dry_run:
            return affected_rows
        
        self.new_training_data = self.new_training_data.copy()

        self._get_windows_abnormal_return(days=days, affected_rows=affected_rows)
        self._get_windows_risk_free_rate(days=days, affected_rows=affected_rows)
        self._get_windows_expected_return(days=days, affected_rows=affected_rows)
        self._get_windows_market_expected_return(days=days, affected_rows=affected_rows)
        self._get_windows_capm(days=days, affected_rows=affected_rows)
        self._get_windows_car(days=days, affected_rows=affected_rows)
        self._get_windows_bhar(days=days, affected_rows=affected_rows)
        self._get_windows_vix(days=days, affected_rows=affected_rows)
        self._get_earnings_vix(affected_rows)
        self._find_and_remove_duplicates()

        return self.new_training_data


    def join(self, old_training_data):

        if old_training_data is None or old_training_data.empty:
            raise Exception("old_training_data can't be empty")

        if self.new_training_data.empty:
            print("new data is empty nothing to concat")
            return


        self.merged_data = pd.concat([old_training_data, self.new_training_data], join='outer')
        self.merged_data = self.merged_data.reset_index()
        self.merged_data = self.merged_data.drop_duplicates(subset=[FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL], keep='first')
        self.merged_data = self.merged_data.set_index([FINVIZ_EARNINGS_DATE_KEY])
        return self.merged_data


    def _get_windows_abnormal_return(self, days, affected_rows):

        label = ABS_RET_KEY.format(days)

        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = affected_rows.apply(
            lambda row: self.get_window_pct_change(row, days=days), axis=1)

        return self.new_training_data

    
    def _get_windows_market_expected_return(self, days, affected_rows):
        
        label = MARK_EXP_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = self.new_training_data.apply(
            lambda row: self.get_market_expected_return(row, days=days), axis=1)

        return self.new_training_data


    def _get_windows_capm(self, days, affected_rows):

        label = CAPM_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = self.new_training_data.apply(
            lambda row: self.get_capm(row, days=days), axis=1)

        return self.new_training_data


    def _get_windows_expected_return(self, days, affected_rows):

        label = EXP_RET_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = affected_rows.apply(
            lambda row: self.get_expected_return(row, days=days), axis=1)

        return self.new_training_data


    def _get_windows_risk_free_rate(self, days, affected_rows):
        label = RF_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = affected_rows.apply(
            lambda row: self.get_risk_free_rate(row, days=days), axis=1)
        
        return self.new_training_data

    
    def _get_windows_vix(self, days, affected_rows):

        label = VIX_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = self.new_training_data.apply(
            lambda row: self.get_vix(row, days=days), axis=1)

        return self.new_training_data


    def _get_earnings_vix(self, affected_rows):

        self.new_training_data[EARNING_VIX_KEY] = 0.0
        self.new_training_data.loc[affected_rows.index, EARNING_VIX_KEY] = self.new_training_data.apply(
            lambda row: self.get_vix_for_date(row), axis=1)
        return self.new_training_data


    def _get_windows_car(self, days, affected_rows):
        label = CAR_KEY.format(days)
        ret_label = ABS_RET_KEY.format(days)
        capm_label = CAPM_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = (self.new_training_data[ret_label] - self.new_training_data[capm_label]).round(4)
        return self.new_training_data


    def _get_windows_bhar(self, days, affected_rows):
        label = BHAR_KEY.format(days)
        ret_label = ABS_RET_KEY.format(days)
        benchmark_label = MARK_EXP_KEY.format(days)
        self.new_training_data[label] = 0.0
        self.new_training_data.loc[affected_rows.index, label] = (self.new_training_data[ret_label] - self.new_training_data[benchmark_label]).round(4)
        return self.new_training_data


    def _find_and_remove_duplicates(self):
        self.new_training_data = self.new_training_data.reset_index()
        self.new_training_data = self.new_training_data.set_index([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL])
        self.new_training_data = self.new_training_data[~self.new_training_data.index.duplicated(keep='first')]

        self._find_and_remove_report_date_conflicts()

        self.new_training_data = self.new_training_data.reset_index()
        self.new_training_data = self.new_training_data.set_index(FINVIZ_EARNINGS_DATE_KEY)
    
        return self.new_training_data


    def _find_and_remove_report_date_conflicts(self):
        report_date_conflicts = self._find_report_date_conflicts()
        self.new_training_data = self.new_training_data.drop(report_date_conflicts)


    def _find_report_date_conflicts(self):
        items_to_remove = []
        for ticker in self.new_training_data.index.get_level_values(1).unique():
            for quarter in range(1, 5):
                item = self.new_training_data.loc[(self.new_training_data.index.get_level_values(1) == ticker) & 
                                                  (self.new_training_data.index.get_level_values(0).quarter == quarter)]  \
                                                  .sort_values(by=DATADATE_KEY, ascending=False)
                for i in range(1, len(item)):
                    items_to_remove.append(item.index[i])
                    print(f"Found duplicate for {item.index[0][1]} on {quarter} quarter")
        return items_to_remove
