import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from earningspy.common.constants import (
    EARNINGS_DATE_KEY,
    DAYS_TO_EARNINGS_KEY,
    SYMBOL_KEY
)
from earningspy.config import Config

config = Config()

class EarningsCalendar:

    @classmethod
    def get_or_create_earnings_calendar(cls,
                                        horizon='12month',
                                        update=False):
        """
        doc: https://www.alphavantage.co/documentation/#earnings-calendar
        This functions makes a csv requests and transform the csv into a dataframe.
        to produce csv output mark csv as True 
        horizons = default 3months, choices=6month,12month

        """
        not_found = False
        if update:
            cls.update_earnings_calendar()
        try:           
            data = cls._get_local_earnings_calendar()
        except Exception:
            print("Unable to find local earnings calendar fetching new one")
            not_found = True
            data = cls.get_alphavantage_earnings_calendar(horizon=horizon)
        else:
            print("Local earning calendar found")
            
        if not_found:
            try:
                cls._store_earnings_calendar(data)
            except Exception:
                print("Unable to store earnings calendar")
            else:
                print("New earnings calendar stored")
        return data.sort_index()
    
    @classmethod
    def get_alphavantage_earnings_calendar(cls, horizon='12month'):
        api_key = config.ALPHA_VANTAGE_API_KEY
        if not api_key:
            raise Exception('Unable to find ALPHAVANTAGE_API_KEY')
        URL = 'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&apikey={}'.format(api_key)
        if horizon:
            URL += '&horizon={}'.format(horizon)
        data = pd.read_csv(URL)
        data = cls._prepare_dataframe(data)
        return data
    
    @classmethod
    def update_earnings_calendar(cls):
        try:
            local = cls._get_local_earnings_calendar()
        except Exception:
            print("Unable to find local earnings calendar: Nothing to update")
            return

        web = cls.get_alphavantage_earnings_calendar()
        merged = pd.concat([local, web])
        try:
            merged = merged.reset_index()
        except Exception:
            pass
        merged = merged.drop_duplicates([EARNINGS_DATE_KEY, SYMBOL_KEY], keep='last')
        merged = cls._prepare_dataframe(merged)
        try:
            cls._store_earnings_calendar(merged)
        except Exception:
            print("Unable to store updated earnings calendar")
        print('File updated successfully')

    @classmethod
    def _compute_days_left(cls, earnings_date):

        today = datetime.today()
        diff = earnings_date - today
        return int(diff.days)

    @classmethod
    def _get_local_earnings_calendar(cls):
        """
        Loads a CSV file from the package and returns a DataFrame.

        :param file_name: Name of the CSV file (e.g., 'config.csv').
        :return: Pandas DataFrame with the contents of the CSV.
        """
        file_path = config.EARNINGS_CALENDAR_PATH
        if not file_path:
            raise Exception("No calendar provided")
        print(f"processing this file {file_path}")
        data = pd.read_csv(file_path)
        data = cls._prepare_dataframe(data)
        return data

    @classmethod
    def _store_earnings_calendar(cls, data):
        data.to_csv(config.EARNINGS_CALENDAR_PATH)

    @classmethod
    def _prepare_dataframe(cls, data):
        data[EARNINGS_DATE_KEY] = pd.to_datetime(data[EARNINGS_DATE_KEY])
        data[DAYS_TO_EARNINGS_KEY] = data[EARNINGS_DATE_KEY].apply(cls._compute_days_left)
        data = data.set_index(EARNINGS_DATE_KEY, drop=True)
        data = data.sort_index()
        return data
