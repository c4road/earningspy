from earningspy.generators.yahoo.time_series import get_portfolio
from earningspy.generators.yahoo.async_timeseries import get_portfolio as async_get_portfolio

TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

def test_async_timeseries():
    """Test asynchronous time series data retrieval has low NaN ratio."""
    data = async_get_portfolio(assets=TICKERS, from_='3m')

    assert data is not None, "Data is None"
    missing_tickers = [t for t in TICKERS if t not in data.columns]
    assert not missing_tickers, f"Missing tickers: {missing_tickers}"

    for ticker in TICKERS:
        nan_ratio = data[ticker].isna().mean()
        assert nan_ratio <= 0.95, f"{ticker} has too many NaNs: {nan_ratio:.2%}"


def test_time_series():
    """Test synchronous timeseries data retrieval."""
    data = get_portfolio(assets=TICKERS, from_='3m')

    assert data is not None, "Data is None"
    missing_tickers = [t for t in TICKERS if t not in data.columns]
    assert not missing_tickers, f"Missing tickers: {missing_tickers}"

    for ticker in TICKERS:
        nan_ratio = data[ticker].isna().mean()
        assert nan_ratio <= 0.95, f"{ticker} has too many NaNs: {nan_ratio:.2%}"
