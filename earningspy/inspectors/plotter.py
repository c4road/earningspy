import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import gridspec
from tqdm import tqdm
from pandas.tseries.offsets import BDay

from earningspy.common.constants import (
    TICKER_KEY_CAPITAL,
    COMPANY_KEY_CAPITAL,
    ABS_RET_KEY,
)

class PEADPlotter:
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
            ax.set_title(f"{row[COMPANY_KEY_CAPITAL]} - {row[TICKER_KEY_CAPITAL]} {row[ABS_RET_KEY] * 100:.3g}% (3d Pct change)", fontsize=18)
            ax.set_ylabel("Price", fontsize=18)
            fig.tight_layout()
            ax.plot(price_range.index.to_numpy(), price_range.to_numpy())
            counter += 1                

    def _get_earnings_window(self, earnings_date):

        initial_date = str((earnings_date - BDay(10)).date())
        end_date = str((earnings_date + BDay(90)).date())

        if initial_date not in self.price_history.index:
            initial_date = self.price_history.index[
                self.price_history.index.get_indexer([initial_date], method="nearest")[0]]
        if end_date not in self.price_history.index:
            end_date = self.price_history.index[
                self.price_history.index.get_indexer([end_date], method="nearest")[0]]

        return initial_date, end_date
