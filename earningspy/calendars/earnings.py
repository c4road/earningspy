import pandas as pd
from earningspy.generators.finviz.data import (
    get_by_earnings_date, 
    get_by_tickers, 
    get_filters,
)

from earningspy.calendars.utils import calendar_pre_formatter, days_left
from earningspy.common.constants import (  
    FINVIZ_EARNINGS_DATE_KEY,
    DAYS_LEFT_KEY,
)

class EarningSpy:

    @classmethod
    def filters(cls, *args, **kwargs):
        return get_filters(*args, **kwargs)

    @classmethod
    def get_calendar(cls, sector=None, industry=None, index=None, future_only=True):
        
        finviz_data = cls.get_finviz(sector=sector, 
                                     industry=industry, 
                                     index=index)

        finviz_data = cls._arrange(finviz_data)
        if future_only:
            finviz_data = finviz_data[finviz_data[DAYS_LEFT_KEY] >= 0]
        return finviz_data


    @classmethod
    def get_this_week_earnings(cls):
        data = get_by_earnings_date(scope="this_week")
        return cls._arrange(data)

    @classmethod
    def get_previous_week_earnings(cls):
        data = get_by_earnings_date(scope="last_week")
        return cls._arrange(data)

    @classmethod
    def get_next_week_earnings(cls):
        data = get_by_earnings_date(scope="next_week")
        return cls._arrange(data)

    @classmethod
    def get_this_month_earnings(cls):
        data = get_by_earnings_date(scope="this_month")
        return cls._arrange(data)

    @classmethod
    def get_today_bmo(cls):
        data = get_by_earnings_date(scope="today_bmo")
        return cls._arrange(data)

    @classmethod
    def get_yesterday_amc(cls):
        data = get_by_earnings_date(scope="yesterday_amc")
        return cls._arrange(data)
    
    @classmethod
    def get_by_tickers(cls, tickers):
        """
        Get earnings data for a list of tickers.
        """
        if not isinstance(tickers, list):
            raise ValueError("tickers must be a list of strings")
        
        data = get_by_tickers(tickers)
        return cls._arrange(data)

    @classmethod
    def _check_missing_dates(cls, finviz_data):
        missing_count = finviz_data.index.to_series().apply(
            lambda row: isinstance(row, pd._libs.tslibs.nattype.NaTType) or pd.isna(row) or row is None
        ).sum()
        if missing_count > 0:
            print(f"[WARNING] Found {missing_count} missing earnings dates in the data.")

    @classmethod
    def _compute_days_left(cls, finviz_data):
        
        cls._check_missing_dates(finviz_data)
        finviz_data[DAYS_LEFT_KEY] = finviz_data.apply(lambda row: days_left(row), axis=1)
        return finviz_data

    @classmethod
    def _arrange(cls, data):
        data = data.set_index(FINVIZ_EARNINGS_DATE_KEY, drop=True)
        data = data.sort_index(ascending=True)
        data = cls._compute_days_left(data)
        return calendar_pre_formatter(data)
