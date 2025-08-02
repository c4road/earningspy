import pytest
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
    'Dividend Ex Date', 'EPS YoY TTM', '52W_NORM', 'IS_S&P500',
    'IS_RUSSELL', 'IS_NASDAQ', 'IS_DOW_JONES', 'IS_AMC', 'IS_BMO', 'IS_USA',
    'EARNINGS_DATE', 'DATADATE'
]

EXCLUDE_NAN_CHECK = [
    '52W_NORM', 'IS_S&P500', 'IS_RUSSELL', 'IS_NASDAQ', 'IS_DOW_JONES',
    'IS_AMC', 'IS_BMO', 'IS_USA', 'EARNINGS_DATE', 'DATADATE', 'Dividend Ex Date'
]


@pytest.mark.parametrize("filters", [
    # industries with few stocks to avoid running for too long time
    # 'ind_gambling',
    # 'ind_semiconductors',
    'ind_solar'
])
def test_get_screener_data(filters):
    print(f"Testing filter: {filters}")
    data = _get_screener_data(filters=filters, order='marketcap')
    nan_columns = [col for col in data.columns if col not in EXCLUDE_NAN_CHECK and data[col].isnull().any()]

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"
    assert not nan_columns, f"DataFrame contains NaNs in columns: {nan_columns}"


@pytest.mark.parametrize("scopes", [
    # 'last_week', 
    # 'this_week', 
    'next_week', 
])
def test_get_by_earnings_date(scopes):
    """Test the get_by_earnings_date function."""
    print(f"Testing scope: {scopes}")
    data = get_by_earnings_date(scopes)
    nan_columns = [col for col in data.columns if col not in EXCLUDE_NAN_CHECK and data[col].isnull().any()]

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"
    assert not nan_columns, f"DataFrame contains NaNs in columns: {nan_columns}"

def test_get_by_tickers():
    """Test the get_by_tickers function."""
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    data = get_by_tickers(tickers)
    nan_columns = [col for col in data.columns if col not in EXCLUDE_NAN_CHECK and data[col].isnull().any()]

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"
    assert not nan_columns, f"DataFrame contains NaNs in columns: {nan_columns}"
