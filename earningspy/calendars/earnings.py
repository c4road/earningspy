import pandas as pd
from datetime import datetime
from earningspy.generators.finviz.utils import (
    get_filters,
    get_dataframe_by_industry,
    get_dataframe_by_sector,
    get_dataframe_by_index,
    get_dataframe_by_tickers,
    get_micro_caps_data,
    get_small_caps_data,
    get_medium_caps_data,
)
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS,
    POST_GENERATED_FIELDS
)
from earningspy.generators.alphavantage.calendar import EarningsCalendar
from earningspy.common.constants import (
    TRACKED_INDUSTRIES,
    EARNINGS_DATE_KEY,
    TICKER_KEY,
    TICKER_KEY_CAPITAL,
    DEFAULT_DATE_FORMAT,
    DAYS_TO_EARNINGS_KEY_CAPITAL,
    DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT,
    DEFAULT_DAYS_PRE_EARNINGS,
)
from earningspy.config import Config

config = Config()

def calendar_formatter(data):
    data = data.drop(['LTDebt/Eq', 'Dividend Ex-Date'], axis=1)
    data.columns = data.columns.str.replace(' ', '_')
    data.columns = data.columns.str.upper()
    data.columns = data.columns.str.strip()
    data = data.rename(columns={'VOLATILITY_W': 'VOLATILITY_HIGH', 'VOLATILITY_M': 'VOLATILITY_LOW'})

    data['LTDEBT/EQ'] = pd.to_numeric(data['LTDEBT/EQ'], errors='coerce')
    data['IS_AMC'] = data['IS_AMC'].fillna(0).astype('int64')
    data['IS_BMO'] = data['IS_BMO'].fillna(0).astype('int64')

    # drop columns that are not useful or preprocessed
    data = data.drop([
        'FISCALDATEENDING',
        'COUNTRY',
        'INDEX', 
        'ESTIMATE',
        'EARNINGS', 
        'CURRENCY', 
        'RETURN%_1Y', 
        'DIVIDEND_EST.', 
        'DIVIDEND_TTM', 
        'OPTION/SHORT', 
        'VOLATILITY', 
        '52W_HIGH', 
        '52W_LOW', 
        '52W_RANGE'
    ], axis=1)

    # round to four decimal places
    data = data.round(4)
    return data
    

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
 
        return calendar_formatter(finviz_calendar)


    @classmethod
    def get_finviz(cls,
                   sector=None,
                   industry=None,
                   index=None,
                   table='Custom', 
                   details=True):
        
        if industry and not index and not sector:
            finviz_data = get_dataframe_by_industry(
                industry, 
                details=details, 
                table=table)
        elif sector and not index and not industry:
            finviz_data = get_dataframe_by_sector(
                sector, 
                details=details, 
                table=table)
        elif index and not sector and not industry:
            finviz_data = get_dataframe_by_index(
                index, 
                details=details, 
                table=table)
        else:
            raise Exception('You can only pass sector, industry, or index not several of them')

        return finviz_data
    
    @classmethod
    def get_finviz_by_tickers(cls, tickers):
        """
        :param tickers: list of tickers
        :return: DataFrame with the finviz data for the tickers
        """
        finviz_data = get_dataframe_by_tickers(tickers)
        return finviz_data
    
    @classmethod
    def get_custom_calendar(cls, tickers):
        finviz_data = cls.get_finviz_by_tickers(tickers)

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
                industry_data = cls.get_finviz(industry=industry, 
                                               table=table, 
                                               raw=raw, 
                                               save=True)
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
            'micro': get_micro_caps_data,
            'small': get_small_caps_data,
            'medium': get_medium_caps_data, 
        }

        finviz_data = factory[cap](order='marketcap')
        calendar = cls.get_earning_calendar_for(finviz_data.T.index, 
                                                scope=scope,
                                                web=True)

        finviz_calendar = cls.merge_finviz_and_earnings_calendar(
            earnings_calendar=calendar, 
            finviz_data=finviz_data, 
        )

        return calendar_formatter(finviz_calendar)



class CalendarLoader:

    def __init__(self, data=None, path=None):
        self.data = self._load_raw_data(data)

    def get_pre_earnings(self, days=DEFAULT_DAYS_PRE_EARNINGS):
        """Returns the upcoming earnings release"""
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY_CAPITAL] >= 0)
               & (self.data[DAYS_TO_EARNINGS_KEY_CAPITAL] <= days)]

    def get_report_dates_by_ticker(self, ticker):
        "returns a Series"
        return self.data[self.data[TICKER_KEY_CAPITAL] == ticker][TICKER_KEY_CAPITAL]
    
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
        merged_data = merged_data.drop_duplicates([EARNINGS_DATE_KEY, TICKER_KEY_CAPITAL], keep=keep)
        merged_data = self._update_days_left(merged_data)
        merged_data = merged_data.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL)
        merged_data = merged_data.set_index([EARNINGS_DATE_KEY])
        merged_data = merged_data.drop(['index', 'level_0'], axis=1, errors='ignore')
        merged_data.to_csv(path)
        return merged_data 

    def _load_raw_data(self, data):
        data = data.reset_index()
        data = self._update_days_left(data)
        data = data.set_index([EARNINGS_DATE_KEY])
        return data

    @staticmethod
    def _update_days_left(data):
        data = data.reset_index(drop=True)
        data[EARNINGS_DATE_KEY] = pd.to_datetime(data[EARNINGS_DATE_KEY])
        data[DAYS_TO_EARNINGS_KEY_CAPITAL] = data[EARNINGS_DATE_KEY].apply(EarningsCalendar._compute_days_left)
        return data

    def update_pre_earnings(self, days=DEFAULT_DAYS_PRE_EARNINGS):
        self.store_pre_earnings(days=days, path=config.PRE_EARNINGS_DATA_PATH, keep='first')

    @classmethod
    def load_stored_pre_earnings(cls):

        keep_first = pd.read_csv(config.PRE_EARNINGS_DATA_PATH)
        keep_first = cls._update_days_left(keep_first)
        keep_first = keep_first.set_index([EARNINGS_DATE_KEY])
        keep_first = keep_first.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL)
        keep_first.drop(['index', 'level_0'], axis=1, inplace=True, errors='ignore')

        return keep_first
