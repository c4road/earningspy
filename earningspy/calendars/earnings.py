import pandas as pd
from datetime import datetime
from earningspy.generators.finviz.data import (
    get_filters,
    get_by_industry,
    get_by_sector,
    get_by_index,
    get_by_industry,
    get_micro_caps,
    get_small_caps,
    get_medium_caps,
)
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS_NEW,
    POST_GENERATED_FIELDS
)
from earningspy.generators.alphavantage.calendar import EarningsCalendar
from earningspy.common.constants import (
    TRACKED_INDUSTRIES,
    EARNINGS_DATE_KEY,
    TICKER_KEY,
    DEFAULT_DATE_FORMAT,
    DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT,
)
from earningspy.config import Config
from earningspy.calendars.utils import calendar_pre_formatter

config = Config()


class EarningSpy:

    @classmethod
    def filters(cls, *args, **kwargs):
        return get_filters(*args, **kwargs)

    @classmethod
    def get_calendar(cls, sector=None, industry=None, index=None, scope=(-90, 90)):
        
        finviz_data = cls.get_finviz(sector=sector, 
                                     industry=industry, 
                                     index=index)

        earnings_calendar = cls.get_earning_calendar_for(finviz_data.T.index, 
                                                         scope=scope,
                                                         web=True)
        finviz_calendar = cls.merge_finviz_and_earnings_calendar(
                earnings_calendar=earnings_calendar, 
                finviz_data=finviz_data)
 
        return calendar_pre_formatter(finviz_calendar)

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
        """
        :param tickers: list of tickers
        :return: DataFrame with the finviz data for the tickers
        """
        finviz_data = get_by_industry(tickers)
        return finviz_data
    
    @classmethod
    def get_custom_calendar(cls, tickers):
        finviz_data = cls.get_finviz_get_by_industry(tickers)

        earnings_calendar = cls.get_earning_calendar_for(finviz_data.T.index, web=True)
        finviz_calendar = cls.merge_finviz_and_earnings_calendar(
                earnings_calendar=earnings_calendar, 
                finviz_data=finviz_data)
        
        return finviz_calendar
    
    def get_this_week_earnings():
        pass

    def get_previous_week_earnings():
        pass

    def next_week_earnings():
        pass


    @classmethod
    def gel_all_tracked_industries(cls, 
                                   table='Custom', 
                                   raw=False, 
                                   scope='all',
                                   industries=TRACKED_INDUSTRIES):
        if scope == 'all':
            all_tracked_industries = []
            for industry in industries:
                print('Updating {}'.format(industry))
                industry_data = cls.get_finviz(industry=industry)
                industry_data.reset_index(inplace=True)
                all_tracked_industries.append(industry_data)
            result = pd.concat(all_tracked_industries)
        else:
            Exception("Not implemented use scope='all'")
        return result

    @classmethod
    def merge_finviz_and_earnings_calendar(cls, 
                                           earnings_calendar, 
                                           finviz_data,
                                           sort_value=DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT):

        filtered_data = finviz_data.T[CUSTOM_TABLE_ALL_FIELDS + POST_GENERATED_FIELDS]
        earnings_calendar = earnings_calendar.rename(columns={'symbol': TICKER_KEY})
        earnings_calendar = earnings_calendar.reset_index()
        earnings_calendar = earnings_calendar.merge(
            filtered_data, 
            on=TICKER_KEY, 
            validate='many_to_one'
        )
        earnings_calendar = earnings_calendar.set_index(EARNINGS_DATE_KEY)
        earnings_calendar = earnings_calendar.sort_values(sort_value)
        earnings_calendar['dataDate'] = datetime.now().strftime(DEFAULT_DATE_FORMAT)
        return earnings_calendar

    @classmethod
    def get_earning_calendar_for(cls, 
                                 symbols,
                                 scope=(-45, 45),
                                 web=False):
        """
        :symbols list of symbols 
        :scope 

        """
        data = EarningsCalendar.get_or_create_earnings_calendar(update=True, web=web)
        results = data[data['symbol'].isin(symbols)]
        if not scope:
            return results.sort_index()
        
        # Earning calendar comes from de day 1 and we need just 90 days up and down
        results = results[(results[DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT] < scope[1]) & 
                          (results[DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT] > scope[0])]

        return results.sort_index()
    
    @classmethod
    def get_calendar_by_cap(cls, cap='micro', scope=(-15, 5)):

        if cap not in ['micro', 'small', 'medium', 'all']:
            raise Exception("Invalid scope valid scopes ['micro', 'small', 'medium', 'all']")
        
        factory = {
            'micro': get_micro_caps,
            'small': get_small_caps,
            'medium': get_medium_caps, 
        }

        finviz_data = factory[cap]()
        calendar = cls.get_earning_calendar_for(finviz_data.T.index, 
                                                scope=scope,
                                                web=True)

        finviz_calendar = cls.merge_finviz_and_earnings_calendar(
            earnings_calendar=calendar, 
            finviz_data=finviz_data, 
        )

        return calendar_pre_formatter(finviz_calendar)
