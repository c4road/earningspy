import pandas as pd
from earningspy.generators.finviz.data import (
    get_filters,
    get_by_industry,
    get_by_sector,
    get_by_index,
    get_by_industry,
    get_micro_caps,
    get_small_caps,
    get_medium_caps,
    get_by_earnings_date,
)

from earningspy.config import Config
from earningspy.calendars.utils import calendar_pre_formatter, days_left
from earningspy.generators.alphavantage.calendar import EarningsCalendar
from earningspy.common.constants import (  
    FINVIZ_EARNINGS_DATE_KEY,
    DAYS_LEFT_KEY,
    ALLOWED_CAPITALIZATIONS,
    DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT,

)

config = Config()


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
        # if future_only:
        #     finviz_data = finviz_data[finviz_data[DAYS_LEFT_KEY] >= 0]
        return finviz_data

    @classmethod
    def get_finviz(cls,
                   sector=None,
                   industry=None,
                   index=None):
        
        if industry and not index and not sector:
            finviz_data = get_by_industry(industry)
        elif sector and not index and not industry:
            finviz_data = get_by_sector(sector)
        elif index and not sector and not industry:
            finviz_data = get_by_index(index)
        else:
            raise Exception('You can only pass sector, industry, or index not several of them')

        return finviz_data

    @classmethod
    def get_finviz_get_by_industry(cls, tickers):
        data = get_by_industry(tickers)
        return cls._arrange(data)

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

    def get_today_bmo(cls):
        data = get_by_earnings_date(scope="today_bmo")
        return cls._arrange(data)

    def get_yesterday_amc(cls):
        data = get_by_earnings_date(scope="yesterday_amc")
        return cls._arrange(data)

    @classmethod
    def get_by_capitalization(cls, cap='micro'):

        if cap not in ALLOWED_CAPITALIZATIONS:
            raise Exception(f"Invalid scope valid scopes {ALLOWED_CAPITALIZATIONS}")
        
        factory = {
            'micro': get_micro_caps,
            'small': get_small_caps,
            'medium': get_medium_caps, 
        }

        finviz_data = factory[cap]()

        return cls._arrange(finviz_data)
    
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
        finviz_data.loc[:, DAYS_LEFT_KEY] = finviz_data.apply(lambda row: days_left(row), axis=1)
        return finviz_data

    @classmethod
    def _arrange(cls, data):
        data = data.set_index(FINVIZ_EARNINGS_DATE_KEY, drop=True)
        data = data.sort_index(ascending=True)
        data = cls._compute_days_left(data)
        return calendar_pre_formatter(data)

    @classmethod
    def get_earning_date_for_missings(cls, 
                                 symbols,
                                 web=False):

        data = EarningsCalendar.get_or_create_earnings_calendar(update=True, web=web)
        results = data[data['symbol'].isin(symbols)]

        # only dates from this trimester, 15 days margin of error
        results = results[(results[DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT] < 90) & 
                          (results[DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT] > 0)]


        return results.sort_index()
