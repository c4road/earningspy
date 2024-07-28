import pandas as pd
from datetime import datetime
from earningspy.generators.finviz.utils import (
    get_filters,
    get_dataframe_by_industry,
    get_dataframe_by_sector,
    get_dataframe_by_index,
)
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS,
)
from dateutil.relativedelta import relativedelta
from earningspy.earnings_calendar.constants import (
    LOCAL_EARNINGS_CALENDAR_FOLDER,
    TRACKED_INDUSTRIES,
    DEFAULT_TABLE,
    EARNINGS_DATE_KEY,
    TICKER_KEY,
    DEFAULT_DATE_FORMAT,
    DAYS_TO_EARNINGS_KEY, 
    DEFAULT_LOCAL_CALENDAR_FILE,
)
from earningspy.config import Config

config = Config()

class MasterEarningsCalendar:

    @classmethod
    def get_whole_earnings_calendar(cls, 
                                    csv=False, 
                                    horizon='12month', 
                                    local_file=DEFAULT_LOCAL_CALENDAR_FILE):
        """
        doc: https://www.alphavantage.co/documentation/#earnings-calendar
        This functions makes a csv requests and transform the csv into a dataframe.
        to produce csv output mark csv as True 
        horizons = default 3months, choices=6month,12month

        """
        earnings_calendar_folder = LOCAL_EARNINGS_CALENDAR_FOLDER
        api_key = config.ALPHA_VANTAGE_API_KEY
        URL = 'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&apikey={}'.format(
            api_key)
        if csv:
            # file_path = f'./{earnings_calendar_folder}/{local_file}'
            file_path = f'~/Documents/Devs/earningspy/earningspy/local_data/{local_file}'
            data = pd.read_csv(file_path)
            data[EARNINGS_DATE_KEY] = pd.to_datetime(data[EARNINGS_DATE_KEY])
            data[DAYS_TO_EARNINGS_KEY] = data[EARNINGS_DATE_KEY].apply(cls._compute_days_left)
            data = data.set_index(EARNINGS_DATE_KEY, drop=True)
            return data

        else:
            if horizon:
                URL += '&horizon={}'.format(horizon)
            data = pd.read_csv(URL)
            data[EARNINGS_DATE_KEY] = pd.to_datetime(data[EARNINGS_DATE_KEY])
            data[DAYS_TO_EARNINGS_KEY] = data[EARNINGS_DATE_KEY].apply(
                cls._compute_days_left)
            data = data.set_index(EARNINGS_DATE_KEY, drop=True)

        return data.sort_index()

    @classmethod
    def update_local_earnings_calendar(cls, local_name='from-Feb2023EarningsCalendar.csv'):

        earnings_calendar_folder = LOCAL_EARNINGS_CALENDAR_FOLDER
        local = cls.get_whole_earnings_calendar(csv=True)
        web = cls.get_whole_earnings_calendar(csv=False)

        # Find the last date on the dataframe and add grab information
        # on the request from it 
        next_day = local.index[-1] + relativedelta(days=1)
        new = []
        for i in range(5):
            if not len(new):
                print(
                    f'Unable to find new data on {str(next_day)}, trying with the next day')
                next_day = next_day + relativedelta(days=1)
                new = web.loc[str(next_day):]
            else:
                break

        merged = pd.concat([local, new])
        print(local.info())
        print(merged.info())
        merged.to_csv(f'{earnings_calendar_folder}/{local_name}')
        print('File updated successfully')

        return merged

    @classmethod
    def _compute_days_left(cls, earnings_date):

        today = datetime.today()
        diff = earnings_date - today
        return int(diff.days)


class EarningSpy:

    @classmethod
    def filters(cls, *args, **kwargs):
        return get_filters(*args, **kwargs)
    
    @classmethod
    def get_calendar(cls, sector=None, industry=None, index=None, scope=(-90, 90)):
        
        finviz_data = cls.get_finviz(sector=sector, 
                                     industry=industry, 
                                     index=index)

        earnings_calendar = cls.get_earning_calendar_for(finviz_data.T.index, scope=scope)
        finviz_calendar = cls.merge_finviz_and_earnings_calendar(
                earnings_calendar=earnings_calendar, 
                finviz_data=finviz_data, 
                table=DEFAULT_TABLE, 
                industry=industry, 
                index=index)
 
        return finviz_calendar


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
    
    def get_time_series_portfolio(cls, tickers):
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
                                           table=DEFAULT_TABLE,
                                           sort_value=DAYS_TO_EARNINGS_KEY, 
                                           industry=False,
                                           index=False):

        columns = CUSTOM_TABLE_ALL_FIELDS
    
        if industry and 'Industry' not in columns:
            columns.append('Industry')
        elif index and 'Index' not in columns:
            columns.append('Index')

        filtered_data = finviz_data.T[columns]
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
                                 scope=(-90, 90)):
        """
        :symbols list of symbols 
        :scope 

        """
        data = MasterEarningsCalendar.get_whole_earnings_calendar(csv=True)
        results = data[data['symbol'].isin(symbols)]
        if not scope:
            return results.sort_index()
        
        # Earning calendar comes from de day 1 and we need just 90 days up and down
        results = results[(results[DAYS_TO_EARNINGS_KEY] < scope[1]) & 
                          (results[DAYS_TO_EARNINGS_KEY] > scope[0])]

        return results.sort_index()
    
    def update_local_earnings_calendar():
        pass 


class CalendarLoader:

    def __init__(self, data=None, path=None):
        self.data = self._load_raw_data(data)

    def get_pre_earnings(self, days=5):
        """Returns the upcoming earnings release"""
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY] >= 0)
               & (self.data[DAYS_TO_EARNINGS_KEY] <= days)]
    
    def get_post_earnings(self, days=5):
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY] < 0) & 
                         (self.data[DAYS_TO_EARNINGS_KEY] >= -days)]

    def get_pre_earnings_from_this_month(self):
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY] > -30) & 
                         (self.data[DAYS_TO_EARNINGS_KEY] < 0)]

    def get_pre_earnings_from_one_month(self, days=30):
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY] > -60) & 
                         (self.data[DAYS_TO_EARNINGS_KEY] < -days)]
    
    def get_pre_earnings_from_two_months(self, days=30):
        return self.data[(self.data[DAYS_TO_EARNINGS_KEY] > -90) & 
                         (self.data[DAYS_TO_EARNINGS_KEY] < -days)]

    def get_report_dates_by_ticker(self, ticker):
        "returns a Series"
        return self.data[self.data[TICKER_KEY] == ticker][TICKER_KEY]
    
    def store_pre_earnings(self, days=5, path='upcoming.csv', keep='first'):
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

    def store_post_earnings(self, days=5, path='reported.csv', keep='first'):
        old_data = pd.read_csv(path, index_col=0)
        post_earnings = self.get_post_earnings(days)
        return self._store(post_earnings, old_data, path, keep)
    
    def _store(self, new_data, old_data, path,  keep):

        merged_data = pd.concat([old_data, new_data], join='outer')
        merged_data.index = pd.to_datetime(merged_data.index)
        if len(merged_data.columns) != len(old_data.columns):
            raise Exception("Invalid concatenation, resulting data has diferent columns length")
        try:
            merged_data = merged_data.reset_index()
        except Exception:
            pass
        merged_data = merged_data.drop_duplicates([EARNINGS_DATE_KEY, TICKER_KEY], keep=keep)
        merged_data = self._update_days_left(merged_data)
        merged_data = merged_data.sort_values(DAYS_TO_EARNINGS_KEY)
        merged_data = merged_data.set_index([EARNINGS_DATE_KEY])
        merged_data['updatedAt'] = datetime.now().strftime(DEFAULT_DATE_FORMAT)
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
        data[DAYS_TO_EARNINGS_KEY] = data[EARNINGS_DATE_KEY].apply(MasterEarningsCalendar._compute_days_left)
        return data

    def update_pre_earnings(self, days=5):
        self.store_pre_earnings(days=days, path=config.PRE_EARNINGS_KEEP_LAST_NAME, keep='last')
        self.store_pre_earnings(days=days, path=config.PRE_EARNINGS_KEEP_FIRST_NAME, keep='first')

    def update_post_earnings(self, days=5):
        self.store_post_earnings(days=days, path=config.POST_EARNINGS_KEEP_FIRST_NAME, keep='first')

    @classmethod
    def load_stored_pre_earnings(cls):
        first = pd.read_csv(config.PRE_EARNINGS_KEEP_LAST_NAME)
        first = cls._update_days_left(first)
        first = first.set_index([EARNINGS_DATE_KEY])
        first = first.sort_values(DAYS_TO_EARNINGS_KEY)
        first.drop(['index', 'level_0'], axis=1, inplace=True, errors='ignore')

        last = pd.read_csv(config.PRE_EARNINGS_KEEP_FIRST_NAME)
        last = cls._update_days_left(last)
        last = last.set_index([EARNINGS_DATE_KEY])
        last = last.sort_values(DAYS_TO_EARNINGS_KEY)
        first.drop(['index', 'level_0'], axis=1, inplace=True, errors='ignore')

        return cls(first), cls(last)

    @classmethod
    def load_stored_post_earnings(cls):
        post = pd.read_csv(config.POST_EARNINGS_KEEP_FIRST_NAME)
        post = cls._update_days_left(post)
        post =  post.set_index([EARNINGS_DATE_KEY])
        post.drop(['index', 'level_0'], axis=1, inplace=True, errors='ignore')
        post = post.sort_values(DAYS_TO_EARNINGS_KEY)
        return cls(post)
