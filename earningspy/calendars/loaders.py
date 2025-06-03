import pandas as pd
from earningspy.generators.alphavantage.calendar import EarningsCalendar
from earningspy.common.constants import (
    FINVIZ_EARNINGS_DATE_KEY,
    ALPHAVANTAGE_EARNINGS_DATE_KEY,
    TICKER_KEY_CAPITAL,
    DAYS_TO_EARNINGS_KEY_CAPITAL,
    DEFAULT_DAYS_PRE_EARNINGS,
)
from earningspy.config import Config

config = Config()


class CalendarLoader:

    def __init__(self, data=None, path=None):
        self.data = self._load_raw_data(data)
    
    @staticmethod
    def _update_days_left(data):
        data = data.reset_index(drop=True)
        data[FINVIZ_EARNINGS_DATE_KEY] = pd.to_datetime(data[FINVIZ_EARNINGS_DATE_KEY])
        data[DAYS_TO_EARNINGS_KEY_CAPITAL] = data[FINVIZ_EARNINGS_DATE_KEY].apply(EarningsCalendar._compute_days_left)
        return data

    @classmethod
    def load_stored_pre_earnings(cls):

        keep_first = pd.read_csv(config.PRE_EARNINGS_DATA_PATH)
        keep_first = cls._update_days_left(keep_first)
        keep_first = keep_first.set_index([FINVIZ_EARNINGS_DATE_KEY])
        keep_first = keep_first.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL)
        keep_first.drop(['index', 'level_0'], axis=1, inplace=True, errors='ignore')

        return keep_first

    def get_pre_earnings(self, days=DEFAULT_DAYS_PRE_EARNINGS):
        """Returns the upcoming earnings release"""
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY_CAPITAL] >= 0)
               & (self.data[DAYS_TO_EARNINGS_KEY_CAPITAL] <= days)]
    
    def store_pre_earnings(self, days=DEFAULT_DAYS_PRE_EARNINGS, path='upcoming.csv', keep='first'):
        """
        Use keep=last to preserve the data that is more recent
        this will store a new item until days left is equal to 0. Which means
        the report date less than 24 hours away.
        """
        old_data = pd.read_csv(path, index_col=0)
        pre_earnings = self.get_pre_earnings(days)
        if pre_earnings.empty:
            raise Exception('Nothing to update on old pre-earnings')
        return self._store(pre_earnings, old_data, path, keep)

    
    def _store(self, new_data, old_data, path,  keep):

        if new_data.empty:
            print("new data is empty nothing to concat")
            return
        merged_data = pd.concat([old_data, new_data], join='outer')
        merged_data.index = pd.to_datetime(merged_data.index)
        if len(merged_data.columns) != len(old_data.columns):
            raise Exception("Invalid concatenation, resulting data has diferent columns length")
        try:
            merged_data = merged_data.reset_index()
        except Exception:
            pass
        merged_data = merged_data.drop_duplicates([FINVIZ_EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL], keep=keep)
        merged_data = self._update_days_left(merged_data)
        merged_data = merged_data.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL)
        merged_data = merged_data.set_index([FINVIZ_EARNINGS_DATE_KEY])
        merged_data = merged_data.drop(['index', 'level_0'], axis=1, errors='ignore')
        merged_data.to_csv(path)
        return merged_data 

    def _load_raw_data(self, data):
        data = data.reset_index()
        data = self._update_days_left(data)
        data = data.set_index([FINVIZ_EARNINGS_DATE_KEY])
        return data

    def update_pre_earnings(self, days=DEFAULT_DAYS_PRE_EARNINGS):
        self.store_pre_earnings(days=days, path=config.PRE_EARNINGS_DATA_PATH, keep='first')
