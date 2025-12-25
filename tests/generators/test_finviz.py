import pytest
import numpy as np
from earningspy.generators.finviz.data import (
    _get_screener_data,
    get_by_earnings_date,
    get_by_tickers,
)

EXPECTED_COLUMNS = [
    'Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Market Cap',
    'P/E', 'Fwd P/E', 'PEG', 'P/S', 'P/B', 'P/C', 'P/FCF', 'Dividend',
    'Payout Ratio', 'EPS', 'EPS next Q', 'EPS This Y', 'EPS Next Y',
    'EPS Past 5Y', 'EPS Next 5Y', 'Sales Past 5Y', 'Sales Q/Q',
    'Sales YoY TTM', 'EPS Q/Q', 'Sales', 'Income', 'EPS Surprise',
    'Revenue Surprise', 'Outstanding', 'Float', 'Float %', 'Insider Own',
    'Insider Trans', 'Inst Own', 'Inst Trans', 'Short Float', 'Short Ratio',
    'Short Interest', 'ROA', 'ROE', 'ROIC', 'Curr R', 'Quick R',
    'LTDebt/Eq', 'Debt/Eq', 'Gross M', 'Oper M', 'Profit M', 'Perf Week',
    'Perf Month', 'Perf Quart', 'Perf Half', 'Perf Year', 'Perf YTD',
    'Beta', 'ATR', 'Volatility W', 'Volatility M', 'SMA20', 'SMA50',
    'SMA200', 'RSI', 'Target Price', 'Book/sh', 'Cash/sh', 'Employees',
    'Optionable', 'Prev Close', 'Shortable', 'Recom', 'Avg Volume',
    'Rel Volume', 'Volume', 'Price', 'Change', 'Dividend TTM',
    'Dividend Ex Date', 'EPS YoY TTM', 'Enterprise Value', 'EV/EBITDA', 'EV/Sales',
    '52W_NORM', 'IS_S&P500', 'IS_RUSSELL', 'IS_NASDAQ', 'IS_DOW_JONES', 'IS_AMC',
    'IS_BMO', 'IS_USA', 'EARNINGS_DATE', 'FCF', 'EBITDA', 'EBIT', 'DATADATE'
]

MAX_ROW_NAN_RATIO = 0.30  # 30% NaNs allowed per row


def _assert_row_nan_threshold(data, max_ratio=MAX_ROW_NAN_RATIO, top_k=10):
    # NaN ratio per row across ALL columns
    row_nan_ratio = data.isna().mean(axis=1)

    bad = row_nan_ratio[row_nan_ratio > max_ratio]
    if not bad.empty:
        worst = bad.sort_values(ascending=False).head(top_k)
        msg_lines = [
            f"{idx}: {ratio:.2%} NaNs | Ticker={data.loc[idx, 'Ticker'] if 'Ticker' in data.columns else 'N/A'}"
            for idx, ratio in worst.items()
        ]
        raise AssertionError(
            f"Found {len(bad)} rows with NaN ratio > {max_ratio:.0%}. "
            f"Showing worst {min(top_k, len(bad))} rows:\n" + "\n".join(msg_lines)
        )


@pytest.mark.parametrize("filters", [
    'ind_solar',
])
def test_get_screener_data(filters):
    print(f"Testing filter: {filters}")
    data = _get_screener_data(filters=filters, order='marketcap')

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"

    _assert_row_nan_threshold(data)


@pytest.mark.parametrize("scopes", [
    'next_week',
])
def test_get_by_earnings_date(scopes):
    print(f"Testing scope: {scopes}")
    data = get_by_earnings_date(scopes)

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"

    _assert_row_nan_threshold(data)


def test_get_by_tickers():
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    data = get_by_tickers(tickers)

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"

    _assert_row_nan_threshold(data)