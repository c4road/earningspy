from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import gridspec
from tqdm import tqdm

from earningspy.generators.yahoo.time_series import get_portfolio

from earningspy.earnings_calendar.constants import (
    DEFAULT_BEFORE_EARNINGS_DATE_DAYS,
    DEFAULT_AFTER_EARNINGS_DATE_DAYS,
    RANGES,
    DAYS_TO_EARNINGS_KEY,
    IS_ANOMALY_KEY,
    IS_ALPHA_KEY,
    DEFAULT_IF_ALPHA_WINDOW
)


class AnomalyInspector:

    def __init__(self, 
                 calendar=None,
                 training_data=None,
                 price_history=None):

        self._calendar = calendar
        self.price_history = price_history
        self.new_training_data = training_data

        self.remaining_data = None
        self.old_training_data = None
        self.merged_training_data = None

    def _get_price_history(self):
        assets = self.new_training_data['Ticker'].to_list()
        return get_portfolio(assets, from_='3m')
    
    @property
    def calendar(self):
        self._calendar.sort_values(DAYS_TO_EARNINGS_KEY, ascending=True)
        return self._calendar

    def earnings_report_range_price_change(self,
                                           before,
                                           after):

        self.new_training_data.reset_index(inplace=True)
        self.new_training_data.set_index('Ticker', inplace=True)
        for ticker in self.price_history.columns:

            try:
                report_date = self.new_training_data.loc[ticker, 'reportDate'].date()
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
                self.new_training_data.loc[ticker:, f'{before}-{after} {pct_column_name}'] = pct_value
            except IndexError:
                print('Unable to get price range diff for {}'.format(ticker))
                continue

        self.new_training_data.reset_index(inplace=True)
        self.new_training_data.set_index('reportDate', inplace=True)

        return self.new_training_data
    
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

    def prepare(self, alpha_window=DEFAULT_IF_ALPHA_WINDOW, dry_run=False):

        if self.new_training_data:
            raise Exception('Target is already set')
        
        data_to_process = self._calendar[(self.calendar[DAYS_TO_EARNINGS_KEY] < 0) &
                                     (self.calendar[DAYS_TO_EARNINGS_KEY] < -alpha_window)]
        if dry_run:
            return data_to_process

        self.new_training_data = data_to_process
        if not self.price_history:
            self.price_history = self._get_price_history()
        self.insert_report_pct_change_ranges()
        self.new_training_data['is_anomaly'] = self.new_training_data[IS_ANOMALY_KEY].apply(self._get_anomaly)
        self.new_training_data['is_alpha'] = self.new_training_data[IS_ALPHA_KEY].apply(self._get_anomaly)
        
        return self.new_training_data
    
    def save(
        self, 
        pre_earning_data_path, 
        old_training_data_path, 
        new_training_data_path,
        overwrite=False
    ):
        """
        Save unprocesed pre earnings data without the items that were processed
        Merge old training data with new training data and store it
        """
        # Delete trained records from the calendar
        self.remaining_data = self._calendar[~((self._calendar[DAYS_TO_EARNINGS_KEY] < 0) & 
                                            (self._calendar[DAYS_TO_EARNINGS_KEY] < -DEFAULT_IF_ALPHA_WINDOW))]
        if self.remaining_data.empty:
            raise Exception('Unprocesed data is empty')
        else:
            try:
                print("Storing remaining data")
                self.remaining_data.to_csv(pre_earning_data_path)
            except: 
                print("Unable to store remaining data") 
        
        if not overwrite and not new_training_data_path:
            raise Exception("store_path can't be empty if overwrite=False")
        
        data_saved = self.store_training_data(old_training_data_path, 
                                              new_training_data_path, 
                                              overwrite=overwrite)
        return data_saved
    
    def plot_anomaly(self, type, sort=True):

        if type == 'bear':
            anomalies = self.new_training_data[
                self.new_training_data['is_anomaly'] == -1]
        elif type == 'bull':
            anomalies = self.new_training_data[
                self.new_training_data['is_anomaly'] == 1]
        else:
            raise Exception("Invalid types, valid types:: ['bear', 'bull']")
        
        if anomalies.empty:
            raise Exception(f"No {type} anomalies in this data")
        
        if sort and type == 'bull':
            anomalies.sort_values('1-3 pct', ascending=False)
        elif sort and type == 'bear':
            anomalies.sort_values('1-3 pct')

        n_plots = len(anomalies)
        n_cols = 3
        n_rows = (n_plots + n_cols - 1) // n_cols

        plot_width = 8 
        plot_height = 5

        fig_width = plot_width * n_cols
        fig_height = plot_height * n_rows

        gs = gridspec.GridSpec(n_rows, n_cols)
        fig = plt.figure(figsize=(fig_width, fig_height))
        counter = 0
        for index, row in tqdm(anomalies.iterrows(), total = len(anomalies)):
            date_before, date_after = self.get_report_date_range(
                index, 10, 10)
            price_range = self.price_history[row.Ticker].loc[date_before: date_after]
            ax = fig.add_subplot(gs[counter])
            ax.tick_params(axis='x', rotation=45, labelsize=13)
            ax.axvline(pd.to_datetime(index), color='r', linestyle='--', lw=2)
            ax.set_title(f"{row['name']} - {row['Ticker']} {row['1-3 pct'] * 100:.3g}% (3d Pct change)", fontsize=18)
            ax.set_ylabel("Price", fontsize=18)
            fig.tight_layout()
            ax.plot(price_range.index.to_numpy(), price_range.to_numpy())
            counter += 1

    def store_training_data(self, old_data_path, store_path, overwrite=True):

        if overwrite:
            store_path = old_data_path
        else:
            if not store_path:
                raise Exception("store_path can't be empty if overwrite=False")

        if self.new_training_data.empty:
            print("new data is empty nothing to concat")
            return
        old_data = pd.read_csv(old_data_path, index_col=0)
        old_data.index = pd.to_datetime(old_data.index)
        assert len(old_data.columns) == len(self.new_training_data.columns), "Different length of columns"
        self.merged_data = pd.concat([old_data, self.new_training_data], join='outer')
        try:
            self.merged_data.to_csv(store_path)
        except Exception as err:
            print(f"Unable to store data Error {str(err)}")
        else:
            print("Data stored successfully")
            return pd.read_csv(store_path, index_col=0, parse_dates=True)
    
    def store_price_history(self):
        pass

    def get_post_earnings_for_training_data(self):
        pass
