import math
import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from earningspy.generators.yahoo.async_timeseries import get_portfolio as async_get_portfolio
from earningspy.generators.yahoo.time_series import get_portfolio
from earningspy.common.constants import (
    MARKET_DATA_TICKERS,
    TBILL_10_YEAR,
    EXP_RET_KEY,
    SP_500_TICKER,
    BETA_KEY,
    RF_KEY,
    TBILL_10_YEAR,
    VIX_TICKER,
)

class CARMixin:

    def get_window_pct_change(self, row, days):
        earnings_date = row.name[0]
        ticker = row.name[1]

        initial_date = (earnings_date - BDay(1)).date()
        end_date = (earnings_date + BDay(days)).date()

        if initial_date not in self.price_history.index:
            initial_date = self.price_history.index[self.price_history.index.get_indexer([initial_date], method="nearest")[0]]
        if end_date not in self.price_history.index:
            end_date = self.price_history.index[self.price_history.index.get_indexer([end_date], method="nearest")[0]]

        try:
            ts_slice = self.price_history.loc[initial_date:end_date, ticker].copy()
            ts_slice_ffill = ts_slice.ffill()
            ts_valid = ts_slice_ffill.dropna()

            if len(ts_valid) < 2:
                print(f"⚠️ Not enough data after ffill for {ticker} between {initial_date} and {end_date}")
                return np.nan

            start_price = ts_valid.iloc[0]
            end_price = ts_valid.iloc[-1]

            pct = (end_price - start_price) / start_price
            return np.round(pct, 4)

        except KeyError:
            print(f"❌ Ticker {ticker} not found in price history")
            return np.nan


    def get_risk_free_rate(self, row, days):

        date = str(row.name[0].date())

        if date not in self.price_history.index:
            date = self.price_history.index[
                self.price_history.index.get_indexer([date], method="nearest")[0]]
        rf = self.price_history.loc[date][TBILL_10_YEAR]
        
        if math.isnan(rf):
            rf = self.price_history[TBILL_10_YEAR].mean()
        rf = (rf / 100) * (days / 251)

        return np.round(rf, 4)


    def get_capm(self, row, days=0):

        rf_label = RF_KEY.format(days).strip()
        R_label = EXP_RET_KEY.format(days).strip()

        rf = row[rf_label]
        R = row[R_label]
        b = row[BETA_KEY]

        capm = rf + b * (R - rf)
        return np.round(capm, 4)


    def get_expected_return(self, row, days):

        date = row.name[0]
        ticker = row.name[1]

        try:
            if days == 3:
                exp_ret = self.price_history[ticker].loc[:date].pct_change(days, fill_method=None).mean()
            elif days == 30:
                exp_ret = self.price_history[ticker].loc[:date].resample('1ME').ffill().pct_change(fill_method=None).mean()
            elif days == 60:
                exp_ret = self.price_history[ticker].loc[:date].resample('2ME').ffill().pct_change(fill_method=None).mean()
        except KeyError:
            exp_ret = np.nan

        return np.round(exp_ret, 4)


    def get_market_expected_return(self, row, days):

        date = row.name[0]
        try:
            if days == 3:
                exp_ret = self.price_history[SP_500_TICKER].loc[:date].pct_change(days, fill_method=None).mean()
            elif days == 30:
                exp_ret = self.price_history[SP_500_TICKER].loc[:date].resample('1ME').ffill().pct_change(fill_method=None).mean()
            elif days == 60:
                exp_ret = self.price_history[SP_500_TICKER].loc[:date].resample('2ME').ffill().pct_change(fill_method=None).mean()
        except KeyError:
            exp_ret = np.nan

        return np.round(exp_ret, 4)


    def get_risk_free_rate(self, row, days):

        date = str(row.name[0].date())
        if date not in self.price_history.index:
            date = self.price_history.index[
                self.price_history.index.get_indexer([date], method="nearest")[0]]
        rf = self.price_history.loc[date][TBILL_10_YEAR]

        if math.isnan(rf):
            rf = self.price_history[TBILL_10_YEAR].mean()
        rf = (rf / 100) * (days / 251)
        return np.round(rf, 4)


    def get_vix(self, row, days=0):
        earnings_date = row.name[0]
        initial_date = (earnings_date - BDay(1)).date()
        end_date = (earnings_date + BDay(days)).date()

        if initial_date not in self.price_history.index:
            initial_date = self.price_history.index[self.price_history.index.get_indexer([initial_date], method="nearest")[0]]
        if end_date not in self.price_history.index:
            end_date = self.price_history.index[self.price_history.index.get_indexer([end_date], method="nearest")[0]]

        ts_slice = self.price_history.loc[initial_date:end_date]
        try:
            value = ts_slice[VIX_TICKER].mean()
        except KeyError as e:
            print(f"VIX windows data is not in timeseries data")
            value = np.nan

        return np.round(value, 2)


    def get_vix_for_date(self, row):
        earnings_date = row.name[0]
        ticker = row.name[1]

        if not pd.isna(row['IS_AMC']) and row['IS_AMC'] == 1:
            earnings_date = (earnings_date - BDay(1)).date()
        else:
            earnings_date = earnings_date
    
        if earnings_date not in self.price_history.index:
            earnings_date = self.price_history.index[self.price_history.index.get_indexer([earnings_date], method="nearest")[0]]

        try:
            value = self.price_history.loc[earnings_date][VIX_TICKER]
        except KeyError as e:
            print(f"VIX value not present for {ticker} is not in timeseries data")
            value = np.nan

        return np.round(value, 2)


class TimeSeriesMixin:

    def _load_price_history(self, price_history, assets=None):

        if price_history is None or price_history.empty:
            return None
        
        print("timeseries found")
        price_history.index = pd.to_datetime(price_history.index, errors='coerce')
        price_history = price_history[~price_history.index.isna()]
        price_history = price_history[~price_history.index.duplicated(keep='first')]        
        price_history = price_history.sort_index()
    
        return price_history

    def fetch_price_history(self, assets, from_='5y', async_=False):

        market_assets = MARKET_DATA_TICKERS

        if async_:
            price_history = async_get_portfolio(list(assets) + market_assets, from_=from_)
        else:
            price_history = get_portfolio(list(assets) + market_assets, from_=from_)        
        price_history.index = pd.to_datetime(price_history.index, errors='coerce')
        price_history = price_history[~price_history.index.isna()]
        price_history = price_history[~price_history.index.duplicated(keep='first')]        
        price_history = price_history.sort_index()

        return price_history
