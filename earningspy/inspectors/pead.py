import math
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import gridspec
from tqdm import tqdm
from pandas.tseries.offsets import BDay

from earningspy.generators.yahoo.async_timeseries import get_portfolio

from earningspy.common.constants import (
    RANGES,
    DAYS_TO_EARNINGS_KEY_CAPITAL,
    DEFAULT_IF_ALPHA_WINDOW,
    TICKER_KEY_CAPITAL,
    COMPANY_KEY_CAPITAL,
    MARKET_DATA_TICKERS,
    TBILL_10_YEAR
)


class PEADInspector:

    def __init__(self, 
                 calendar=None,
                 training_data=None,
                 price_history=None):

        self._calendar = calendar
        self.price_history = self.load_price_history(price_history)
        self.new_training_data = training_data
        self.remaining_data = None
        self.old_training_data = None
        self.merged_training_data = None

        if self.new_training_data:
            raise Exception('Target data is already set')
    
        self.new_training_data = self._calendar[(self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < 0) &
                                                (self.calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < -DEFAULT_IF_ALPHA_WINDOW)]

    @property
    def calendar(self):
        self._calendar.sort_values(DAYS_TO_EARNINGS_KEY_CAPITAL, ascending=True)
        return self._calendar
    
    def load_price_history(self, price_history):

        if price_history is None:
            return None

        print("price_history found")
        price_history.index = pd.to_datetime(price_history.index, errors='coerce')
        price_history = price_history[~price_history.index.isna()]
        price_history = price_history[~price_history.index.duplicated(keep='first')]        
        price_history = price_history.sort_index()
    
        return price_history

    def get_price_history(self, from_='5y'):

        assets = set(self.new_training_data[TICKER_KEY_CAPITAL].to_list())
        market_assets = MARKET_DATA_TICKERS
        if not self.price_history or self.price_history.empty:
            self.price_history = get_portfolio(list(assets) + market_assets, from_=from_)

        self.price_history.index = pd.to_datetime(self.price_history.index, errors='coerce')
        self.price_history = self.price_history[~self.price_history.index.isna()]
        self.price_history = self.price_history[~self.price_history.index.duplicated(keep='first')]        
        self.price_history = self.price_history.sort_index()

        return self.price_history

    def get_window_pct_change(self, row, days):
        earnings_date = row.name
        initial_date = (earnings_date - BDay(1)).date()
        end_date = (earnings_date + BDay(days)).date()

        if initial_date not in self.price_history.index:
            initial_date = self.price_history.index[self.price_history.index.get_indexer([initial_date], method="nearest")[0]]
        if end_date not in self.price_history.index:
            end_date = self.price_history.index[self.price_history.index.get_indexer([end_date], method="nearest")[0]]

        ts_slice = self.price_history.loc[initial_date:end_date]
        try:
            value = ts_slice[row[TICKER_KEY_CAPITAL]].pct_change(len(ts_slice) - 1, fill_method=None).iloc[-1]
        except KeyError as e:
            print(f"Ticker {row[TICKER_KEY_CAPITAL]} is not in timeseries data")
            value = np.nan

        return np.round(value, 4)

    def get_risk_free_rate(self, row, days):

        date = str(row.name.date())
        if date not in self.price_history.index:
            date = self.price_history.index[
                self.price_history.index.get_indexer([date], method="nearest")[0]]
        rf = self.price_history.loc[date][TBILL_10_YEAR]
        
        if math.isnan(rf):
            rf = self.price_history[TBILL_10_YEAR].mean()
        rf = (rf / 100) * (days / 251)

        return np.round(rf, 4)

    def get_windows_abnormal_return(self):

        self.new_training_data.loc[:, '1+3_RET'] = self.new_training_data.apply(
            lambda row: self.get_window_pct_change(row, days=RANGES[0][1]), axis=1)
        self.new_training_data.loc[:, '1+30_RET'] = self.new_training_data.apply(
            lambda row: self.get_window_pct_change(row, days=RANGES[1][1]), axis=1)
        self.new_training_data.loc[:, '1+60_RET'] = self.new_training_data.apply(
            lambda row: self.get_window_pct_change(row, days=RANGES[2][1]), axis=1)

        return self.new_training_data

    def get_capm(self, row, days=0):
        if days == 3:
            rf = row['1+3_RF']
            R = row['EXP.RET_3']
            b = row['BETA']

        elif days == 30:
            rf = row['1+30_RF']
            R = row['EXP.RET_30']
            b = row['BETA']

        elif days == 60:
            rf = row['1+60_RF']
            R = row['EXP.RET_60']
            b = row['BETA']

        capm = rf + b * (R - rf)
        return np.round(capm, 4)

    def get_expected_return(self,row, days):

        try:
            if days == 3:
                exp_ret = self.price_history[row[TICKER_KEY_CAPITAL]].loc[:row.name].pct_change(days, fill_method=None).mean()
            elif days == 30:
                exp_ret = self.price_history[row[TICKER_KEY_CAPITAL]].loc[:row.name].resample('1M').ffill().pct_change().mean()
            elif days == 60:
                exp_ret = self.price_history[row[TICKER_KEY_CAPITAL]].loc[:row.name].resample('2M').ffill().pct_change().mean()
        except KeyError:
            exp_ret = np.nan

        return np.round(exp_ret, 4)
    
    def get_market_expected_return(self, row, days):
        try:
            if days == 3:
                exp_ret = self.price_history['^GSPC'].loc[:row.name].pct_change(days, fill_method=None).mean()
            elif days == 30:
                exp_ret = self.price_history['^GSPC'].loc[:row.name].resample('1M').ffill().pct_change().mean()
            elif days == 60:
                exp_ret = self.price_history['^GSPC'].loc[:row.name].resample('2M').ffill().pct_change().mean()
        except KeyError:
            exp_ret = np.nan

        return np.round(exp_ret, 4)
    
    def get_windows_market_expected_return(self):
        self.new_training_data.loc[:, 'MARK_EXP_3'] = self.new_training_data.apply(
            lambda row: self.get_market_expected_return(row, days=3), axis=1)
        self.new_training_data.loc[:, 'MARK_EXP_30'] = self.new_training_data.apply(
            lambda row: self.get_market_expected_return(row, days=30), axis=1)
        self.new_training_data.loc[:, 'MARK_EXP_60'] = self.new_training_data.apply(
            lambda row: self.get_market_expected_return(row, days=60), axis=1)
        
        return self.new_training_data
    
    def get_windows_capm(self):

        self.new_training_data.loc[:, 'CAPM_3'] = self.new_training_data.apply(
            lambda row: self.get_capm(row, days=3), axis=1)
        self.new_training_data.loc[:, 'CAPM_30'] = self.new_training_data.apply(
            lambda row: self.get_capm(row, days=30), axis=1)
        self.new_training_data.loc[:, 'CAPM_60'] = self.new_training_data.apply(
            lambda row: self.get_capm(row, days=60), axis=1)

        return self.new_training_data

    def get_windows_expected_return(self):

        self.new_training_data.loc[:, 'EXP.RET_3'] = self.new_training_data.apply(
            lambda row: self.get_expected_return(row, days=3), axis=1)
        self.new_training_data.loc[:, 'EXP.RET_30'] = self.new_training_data.apply(
            lambda row: self.get_expected_return(row, days=30), axis=1)
        self.new_training_data.loc[:, 'EXP.RET_60'] = self.new_training_data.apply(
            lambda row: self.get_expected_return(row, days=60), axis=1)

        return self.new_training_data

    def get_windows_risk_free_rate(self):

        self.new_training_data.loc[:, '1+3_RF'] = self.new_training_data.apply(
            lambda row: self.get_risk_free_rate(row, days=RANGES[0][1]), axis=1)
        self.new_training_data.loc[:, '1+30_RF'] = self.new_training_data.apply(
            lambda row: self.get_risk_free_rate(row, days=RANGES[1][1]), axis=1)
        self.new_training_data.loc[:, '1+60_RF'] = self.new_training_data.apply(
            lambda row: self.get_risk_free_rate(row, days=RANGES[2][1]), axis=1)
        
        return self.new_training_data
    
    def get_risk_free_rate(self, row, days):

        date = str(row.name.date())
        if date not in self.price_history.index:
            date = self.price_history.index[
                self.price_history.index.get_indexer([date], method="nearest")[0]]
        rf = self.price_history.loc[date]['^TNX']

        if math.isnan(rf):
            rf = self.price_history['^TNX'].mean()
        rf = (rf / 100) * (days / 251)

        return np.round(rf, 4)

    def get_earnings_window(self, earnings_date):

        initial_date = str((earnings_date - BDay(10)).date())
        end_date = str((earnings_date + BDay(90)).date())

        if initial_date not in self.price_history.index:
            initial_date = self.price_history.index[
                self.price_history.index.get_indexer([initial_date], method="nearest")[0]]
        if end_date not in self.price_history.index:
            end_date = self.price_history.index[
                self.price_history.index.get_indexer([end_date], method="nearest")[0]]

        return initial_date, end_date
    
    def get_vix(self, row, days=0):
        earnings_date = row.name
        initial_date = (earnings_date - BDay(1)).date()
        end_date = (earnings_date + BDay(days)).date()

        if initial_date not in self.price_history.index:
            initial_date = self.price_history.index[self.price_history.index.get_indexer([initial_date], method="nearest")[0]]
        if end_date not in self.price_history.index:
            end_date = self.price_history.index[self.price_history.index.get_indexer([end_date], method="nearest")[0]]

        ts_slice = self.price_history.loc[initial_date:end_date]
        try:
            value = ts_slice['^VIX'].mean()
        except KeyError as e:
            print(f"VIX windows data is not in timeseries data")
            value = np.nan

        return np.round(value, 2)
    
    def get_windows_vix(self):
        self.new_training_data.loc[:, '1+3_VIX'] = self.new_training_data.apply(
            lambda row: self.get_vix(row, days=RANGES[0][1]), axis=1)
        self.new_training_data.loc[:, '1+30_VIX'] = self.new_training_data.apply(
            lambda row: self.get_vix(row, days=RANGES[1][1]), axis=1)
        self.new_training_data.loc[:, '1+60_VIX'] = self.new_training_data.apply(
            lambda row: self.get_vix(row, days=RANGES[2][1]), axis=1)
        return self.new_training_data
    
    def get_vix_for_date(self, row):
        if row['IS_BMO'] == 1:
            earnings_date = row.name
        else:
            earnings_date = (row.name + BDay(1)).date()
    
        if earnings_date not in self.price_history.index:
            earnings_date = self.price_history.index[self.price_history.index.get_indexer([earnings_date], method="nearest")[0]]

        try:
            value = self.price_history.loc[earnings_date]['^VIX']
        except KeyError as e:
            print(f"VIX value not present for {row[TICKER_KEY_CAPITAL]} is not in timeseries data")
            value = np.nan

        return np.round(value, 2)

    def get_earning_vix(self):
        self.new_training_data.loc[:, 'EARNING_VIX'] = self.new_training_data.apply(
            lambda row: self.get_vix_for_date(row), axis=1)
        return self.new_training_data

    def get_windows_car(self):
        self.new_training_data['CAR_3'] = (self.new_training_data['1+3_RET'] - self.new_training_data['CAPM_3']).round(4)
        self.new_training_data['CAR_30'] = (self.new_training_data['1+30_RET'] - self.new_training_data['CAPM_30']).round(4)
        self.new_training_data['CAR_60'] = (self.new_training_data['1+60_RET'] - self.new_training_data['CAPM_60']).round(4)
        return self.new_training_data
    
    def get_windows_bhar(self):
        self.new_training_data['BHAR_3'] = (self.new_training_data['1+3_RET'] - self.new_training_data['MARK_EXP_3']).round(4)
        self.new_training_data['BHAR_30'] = (self.new_training_data['1+30_RET'] - self.new_training_data['MARK_EXP_30']).round(4)
        self.new_training_data['BHAR_60'] = (self.new_training_data['1+60_RET'] - self.new_training_data['MARK_EXP_60']).round(4)
        return self.new_training_data

    def _get_anomaly(self, value, anomaly_threshold=0.1):

        if value > anomaly_threshold:
            return 1
        if value < -anomaly_threshold:
            return -1
        else:
            return 0

    def prepare(self, dry_run=False):

        if dry_run:
            return self.new_training_data

        if self.price_history is None or self.price_history.empty:
            self.price_history = self.get_price_history()

        self.new_training_data = self.new_training_data.copy()
        self.get_windows_abnormal_return()
        self.get_windows_risk_free_rate()
        self.get_windows_expected_return()
        self.get_windows_market_expected_return()
        self.get_windows_capm()
        self.get_windows_car()
        self.get_windows_bhar()
        self.get_windows_vix()
        self.get_earnings_vix()
        self.find_and_remove_duplicates()

        return self.new_training_data
    
    def find_and_remove_duplicates(self):
        self.new_training_data = self.new_training_data.reset_index()
        self.new_training_data = self.new_training_data.set_index(['reportDate', TICKER_KEY_CAPITAL])
        self.new_training_data = self.new_training_data[~self.new_training_data.index.duplicated(keep='first')]

        self.find_and_remove_report_date_conflicts()

        self.new_training_data = self.new_training_data.reset_index()
        self.new_training_data = self.new_training_data.set_index('reportDate')
    
        return self.new_training_data

    def find_and_remove_report_date_conflicts(self):
        report_date_conflicts = self.find_report_date_conflicts()
        return self.new_training_data.drop(report_date_conflicts)

    def find_report_date_conflicts(self):
        items_to_remove = []
        for ticker in self.new_training_data.index.get_level_values(1).unique():
            for quarter in range(1, 5):
                item = self.new_training_data.loc[(self.new_training_data.index.get_level_values(1) == ticker) & 
                                                  (self.new_training_data.index.get_level_values(0).quarter == quarter)]  \
                                                  .sort_values(by='DATADATE', ascending=False)
                for i in range(1, len(item)):
                    items_to_remove.append(item.index[i])
                    print(f"Found duplicate for {item.index[0][1]} on {quarter} quarter")
        return items_to_remove

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
        self.remaining_data = self._calendar[~((self._calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < 0) & 
                                              (self._calendar[DAYS_TO_EARNINGS_KEY_CAPITAL] < -DEFAULT_IF_ALPHA_WINDOW))]
        if self.remaining_data.empty:
            print('Unprocesed data is empty')
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

    def plot_anomaly(self, direction, scope):
        
        if scope not in [3, 30, 60]:
            raise Exception("Invalid scope, must be 3, 30 or 60")

        if direction == 'bull':
            anomalies = self.new_training_data[self.new_training_data[f'1+{scope}_RET'] > 0]
            anomalies = anomalies.sort_values(f'1+{scope}_RET', ascending=False)
        elif direction == 'bear':
            anomalies = self.new_training_data[self.new_training_data[f'1+{scope}_RET'] > 0]
            anomalies = anomalies.sort_values(f'1+{scope}_RET')

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
            date_before, date_after = self.get_earnings_window(index)
            price_range = self.price_history[row[TICKER_KEY_CAPITAL]].loc[date_before: date_after]
            ax = fig.add_subplot(gs[counter])
            ax.tick_params(axis='x', rotation=45, labelsize=13)
            ax.axvline(pd.to_datetime(index), color='r', linestyle='--', lw=2)
            ax.set_title(f"{row[COMPANY_KEY_CAPITAL]} - {row[TICKER_KEY_CAPITAL]} {row['1+3_RET'] * 100:.3g}% (3d Pct change)", fontsize=18)
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
        self.merged_data = pd.concat([old_data, self.new_training_data], join='outer').drop_duplicates()
        try:
            self.merged_data.to_csv(store_path)
        except Exception as err:
            print(f"Unable to store data Error {str(err)}")
        else:
            print("Data stored successfully")
            return pd.read_csv(store_path, index_col=0, parse_dates=True)
