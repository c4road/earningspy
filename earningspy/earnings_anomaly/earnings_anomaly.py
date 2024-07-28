from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import pandas as pd

from earnings_calendar.constants import (
    DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
    DEFAULT_AFTER_EARNINGS_DATE_DAYS,
    RANGES,
)


class AnomalyDataGenerator:

    def __init__(self, 
                 calendar=None, 
                 price_history=None, 
                 price_history_from_file=False, 
                 price_history_file=None):

        self._calendar = calendar
        if price_history_from_file and price_history_file:
            self.price_history = self.read_price_history_from_file(price_history_file)
        elif price_history_from_file and not price_history_file:
            raise Exception("Need price_history_file if price_history_from_file is True")
        else:
            self.price_history = price_history

    def _get_price_history(self):
        pass
    
    @property
    def calendar(self):
        self._calendar.sort_values('days_left', ascending=True)
        return self._calendar
        
    def read_price_history_from_file(self, price_history_path):
        """
        Currently this is only compatible with price history coming from TDAmeritrade
        """
        
        df = pd.read_csv(price_history_path, index_col='Datetime')
        df.index = pd.to_datetime(df.index)
        return df

    def earnings_report_range_price_change(self,
                                           before=DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
                                           after=DEFAULT_AFTER_EARNINGS_DATE_DAYS,
                                           pct=False):

        self.calendar.reset_index(inplace=True)
        self.calendar.set_index('Ticker', inplace=True)
        for ticker in self.price_history.columns:

            try:
                report_date = self.calendar.loc[ticker, 'reportDate'].date()
            except (KeyError, AttributeError):
                print('Unable to get report date for ticker={}'.format(ticker))
                continue

            price_range = self.get_report_price_range_for_ticker(ticker=ticker,
                                                                 report_date=report_date,
                                                                 before=before,
                                                                 after=after)
            diff_column_name = 'diff'
            pct_column_name = 'pct'
            if price_range.empty:
                print(f"Price range is empty for {ticker}, report_date={report_date}")
                continue
            try:
                diff = (price_range.iloc[-1] - price_range.iloc[0])
            except IndexError:
                print('Unable to get price range diff for {}'.format(ticker))
                continue

            if pct:
                pct_value = diff / price_range.iloc[0]
                self.calendar.loc[ticker, f'{before}-{after} {pct_column_name}'] = pct_value
            else:
                self.calendar.loc[ticker, f'{before}-{after} {diff_column_name}'] = diff

        self.calendar.reset_index(inplace=True)
        self.calendar.set_index('reportDate', inplace=True)

        return self.calendar
    
    def process_ticker_with_several_dates(self): 
        pass

    def get_report_price_range_for_ticker(self,
                                          ticker,
                                          report_date,
                                          before=DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
                                          after=DEFAULT_AFTER_EARNINGS_DATE_DAYS,
                                          plot=False):

        date_before, date_after = self.get_report_date_range(report_date,
                                                             before,
                                                             after)
        price_range = self.price_history[ticker].loc[date_before: date_after]

        return price_range
    
    def plot_earnings_anomaly(self, 
                              sort_by=None,                                           
                              before=DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
                              after=DEFAULT_AFTER_EARNINGS_DATE_DAYS):
        
        row_amounts = len(self.calendar) // 3
        fig, ax = plt.subplots(len(self.calendar), 3, sharex=True, sharey=True)
        for index, row in self.calendar.iterrows():
            ticker = row['Ticker']
            date_before, date_after = self.get_report_date_range(index,
                                                                 before,
                                                                 after)
            price_range = self.price_history[ticker].loc[date_before: date_after]

            
            plt.xticks(rotation=50)
            ax.axvline(pd.to_datetime(index), color='r', linestyle='--', lw=2)
            ax.plot(price_range.index, price_range.values)
            plt.title(ticker)
            plt.xlabel("Date")
            plt.ylabel("Pricee")
            plt.show()

    def get_report_date_range(self,
                              reportDate,
                              before=DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
                              after=DEFAULT_AFTER_EARNINGS_DATE_DAYS):

        if isinstance(reportDate, str):
            reportDate = datetime.fromisoformat(reportDate)

        date_before = reportDate - relativedelta(days=before)
        date_after = reportDate + relativedelta(days=after)

        return str(date_before), str(date_after)

    def insert_report_pct_change_ranges(self,
                                        ranges=RANGES,
                                        pct=False):

        for before, after in ranges:
            self.earnings_report_range_price_change(before=before, after=after, pct=pct)

    def prepare(self, pct=False): 
        
        self.insert_report_pct_change_ranges(pct=pct)
        
        return self.calendar

    def update_price(self, price_history):

        current_prices = price_history.iloc[-1]
        for col in price_history.columns:
            self.calendar.loc[col]['Price'] = current_prices[col]
