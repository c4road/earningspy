from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import pandas as pd

from earningspy.generators.yahoo.time_series import get_portfolio

from earningspy.earnings_calendar.constants import (
    DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
    DEFAULT_AFTER_EARNINGS_DATE_DAYS,
    RANGES,
    DAYS_TO_EARNINGS_KEY
)


class AnomalyInspector:

    def __init__(self, 
                 calendar=None):

        self._calendar = calendar
        self.price_history = None
        self.target = None

    def _get_price_history(self):
        assets = self.target['Ticker'].to_list()
        return get_portfolio(assets, from_='3m')
    
    @property
    def calendar(self):
        self._calendar.sort_values(DAYS_TO_EARNINGS_KEY, ascending=True)
        return self._calendar

    def earnings_report_range_price_change(self,
                                           before,
                                           after):

        self.target.reset_index(inplace=True)
        self.target.set_index('Ticker', inplace=True)
        for ticker in self.price_history.columns:

            try:
                report_date = self.target.loc[ticker, 'reportDate'].date()
            except (KeyError, AttributeError):
                print('Unable to get report date for ticker={}'.format(ticker))
                continue

            price_range = self.get_report_price_range_for_ticker(ticker=ticker,
                                                                 report_date=report_date,
                                                                 before=before,
                                                                 after=after)
            pct_column_name = 'pct'
            if price_range.empty:
                print(f"Price range is empty for {ticker}, report_date={report_date}")
                continue
            try:
                pct_value = (price_range.iloc[-1] - price_range.iloc[0]) / price_range.iloc[0]
                # self.target.loc[ticker, f'{before}-{after} {pct_column_name}'] = pct_value
                self.target.loc[ticker:, f'{before}-{after} {pct_column_name}'] = pct_value
            except IndexError:
                print('Unable to get price range diff for {}'.format(ticker))
                continue

        self.target.reset_index(inplace=True)
        self.target.set_index('reportDate', inplace=True)

        return self.target
    
    def process_ticker_with_several_dates(self): 
        pass

    def get_report_price_range_for_ticker(self,
                                          ticker,
                                          report_date,
                                          before=DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
                                          after=DEFAULT_AFTER_EARNINGS_DATE_DAYS):

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
                                        ranges=RANGES):

        for before, after in ranges:
            self.earnings_report_range_price_change(before=before, after=after)

    def _get_anomaly(self, value, anomaly_threshold=0.1):

        if value > anomaly_threshold:
            return 1
        if value < -anomaly_threshold:
            return -1
        else:
            return 0

    def prepare(self, days_target=21):

        self.target = self._calendar[(self.calendar[DAYS_TO_EARNINGS_KEY] < 0) &
                                     (self.calendar[DAYS_TO_EARNINGS_KEY] < -days_target)]
        self.price_history = self._get_price_history()
        self.insert_report_pct_change_ranges()
        self._calendar = self.calendar.drop(((self.calendar[DAYS_TO_EARNINGS_KEY] < 0) &
                                            (self.calendar[DAYS_TO_EARNINGS_KEY] < -days_target)).index, axis=0)
        self.target['is_anomaly'] = self.target['1-1 pct'].apply(self._get_anomaly)
        self.target['is_alpha'] = self.target['1-25 pct'].apply(self._get_anomaly)
        return self.target

    def update_price(self, price_history):
 
        current_prices = price_history.iloc[-1]
        for col in price_history.columns:
            self.calendar.loc[col]['Price'] = current_prices[col]
