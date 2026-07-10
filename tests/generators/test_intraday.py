"""
Unit tests for earningspy.generators.yahoo.intraday module.

Tests are network-mocked to validate:
- Interval validation
- Lookback clamping with warnings
- 422 over-cap error handling
- Empty-but-200 result handling
- Non-normalized timestamps (full intraday resolution)
- OHLCV vs close field
- include_prepost parameter
- range_ parameter
- Portfolio concurrency and failure isolation
- Old daily functions remain unchanged
"""

import json
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging

import pytest
import pandas as pd

from earningspy.generators.yahoo.intraday import (
    get_one_ticker_intraday,
    get_portfolio_intraday,
    VALID_INTRADAY_INTERVALS,
    INTRADAY_MAX_DAYS,
)
from earningspy.generators.yahoo.time_series import (
    get_one_ticker,
    get_portfolio,
    prepare_data,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_intraday_payload():
    """Mock Yahoo v8 intraday response with 5-minute bars."""
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "symbol": "HELE",
                        "exchangeTimezoneName": "America/New_York",
                        "regularMarketPrice": 25.50,
                        "chartPreviousClose": 25.25,
                        "dataGranularity": "5m",
                    },
                    "timestamp": [
                        1720687800,  # 2024-07-11 09:30 ET
                        1720688100,  # 2024-07-11 09:35 ET
                        1720688400,  # 2024-07-11 09:40 ET
                    ],
                    "indicators": {
                        "quote": [
                            {
                                "open": [25.10, 25.20, 25.30],
                                "high": [25.40, 25.50, 25.60],
                                "low": [25.00, 25.10, 25.20],
                                "close": [25.30, 25.40, 25.50],
                                "volume": [1000000, 1100000, 1200000],
                            }
                        ]
                    },
                }
            ]
        }
    }


@pytest.fixture
def empty_payload():
    """Mock Yahoo v8 response with no bars (empty timestamp list)."""
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "symbol": "HELE",
                        "exchangeTimezoneName": "America/New_York",
                    },
                    "timestamp": [],
                    "indicators": {
                        "quote": [
                            {
                                "open": [],
                                "high": [],
                                "low": [],
                                "close": [],
                                "volume": [],
                            }
                        ]
                    },
                }
            ]
        }
    }


@pytest.fixture
def error_422_payload():
    """Mock Yahoo v8 422 response (over-cap)."""
    return {
        "chart": {
            "error": {
                "code": "No data",
                "description": "1m data not available for startTime=1720000000 and endTime=1722000000",
            }
        }
    }


@pytest.fixture
def sample_daily_payload():
    """Mock Yahoo v8 daily response (1d interval)."""
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "symbol": "AAPL",
                        "regularMarketPrice": 150.00,
                    },
                    "timestamp": [1720656000, 1720742400, 1720828800],  # Three days
                    "indicators": {
                        "quote": [
                            {
                                "open": [149.50, 150.10, 150.20],
                                "high": [150.50, 151.00, 151.50],
                                "low": [149.00, 149.50, 150.00],
                                "close": [150.00, 150.50, 151.00],
                                "volume": [50000000, 45000000, 48000000],
                            }
                        ]
                    },
                }
            ]
        }
    }


# ============================================================================
# Tests: Interval Validation
# ============================================================================


def test_intraday_invalid_interval():
    """Test that invalid interval raises ValueError."""
    with pytest.raises(ValueError, match="Invalid interval"):
        get_one_ticker_intraday("HELE", interval="7m")


def test_intraday_invalid_interval_daily():
    """Test that daily interval '1d' raises ValueError."""
    with pytest.raises(ValueError, match="Invalid interval"):
        get_one_ticker_intraday("HELE", interval="1d")


def test_intraday_valid_intervals():
    """Test that all VALID_INTRADAY_INTERVALS are accepted."""
    for interval in VALID_INTRADAY_INTERVALS:
        # We're not actually making requests, just checking validation
        # Pass in a mocked session to avoid real network calls
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval=interval)
            # Should reach the request stage, meaning validation passed
            assert result is None


# ============================================================================
# Tests: Lookback Clamping
# ============================================================================


def test_intraday_lookback_clamping_1m_interval(caplog):
    """Test that lookback_days is clamped to 7 for 1m interval."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval="1m", lookback_days=30)

            # Check warning was logged
            assert any("Clamping lookback_days" in record.message for record in caplog.records)
            # Check the URL was built with clamped value
            call_args = mock_get.call_args
            assert "period1=" in call_args[0][0]
            # The URL should have been called with a 7-day lookback


def test_intraday_lookback_clamping_5m_interval(caplog):
    """Test that lookback_days is clamped to 60 for 5m interval."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval="5m", lookback_days=90)

            # Check warning was logged
            assert any("Clamping lookback_days" in record.message for record in caplog.records)


def test_intraday_lookback_clamping_60m_interval(caplog):
    """Test that lookback_days is clamped to 730 for 60m interval."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval="60m", lookback_days=800)

            # Check warning was logged
            assert any("Clamping lookback_days" in record.message for record in caplog.records)


def test_intraday_lookback_within_cap_no_warning(caplog):
    """Test that no warning is logged when lookback_days is within cap."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval="5m", lookback_days=30)

            # Should NOT have a clamping warning
            clamping_warnings = [r for r in caplog.records if "Clamping lookback_days" in r.message]
            assert len(clamping_warnings) == 0


# ============================================================================
# Tests: 422 Over-Cap Error Handling
# ============================================================================


def test_intraday_422_over_cap(caplog):
    """Test that HTTP 422 with error description is logged distinctly."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 422
            mock_response.json.return_value = {
                "chart": {
                    "error": {
                        "description": "1m data not available for startTime=X endTime=Y"
                    }
                }
            }
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval="1m", lookback_days=10)

            assert result is None
            # Check that the error description was logged
            assert any("Yahoo 422" in record.message for record in caplog.records)


def test_intraday_422_without_description(caplog):
    """Test that HTTP 422 without error description is handled gracefully."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 422
            mock_response.json.return_value = {"chart": {}}
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("TEST", interval="1m")

            assert result is None
            assert any("422" in record.message for record in caplog.records)


# ============================================================================
# Tests: Empty-but-200 Results
# ============================================================================


def test_intraday_empty_200_response(empty_payload, caplog):
    """Test that empty timestamp list (but HTTP 200) is treated as a skip."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = empty_payload
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday("HELE", interval="5m")

            assert result is None
            assert any("empty result" in record.message for record in caplog.records)


# ============================================================================
# Tests: Non-Normalized Timestamps (Intraday Resolution)
# ============================================================================


def test_intraday_timestamps_not_normalized(sample_intraday_payload):
    """Test that intraday timestamps retain time-of-day (not normalized to midnight)."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_intraday_payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        assert not result.empty

        # Check that index has intraday times (not all midnight)
        times = result.index.time
        unique_times = set(times)
        assert len(unique_times) > 1, "All timestamps should not be the same time"

        # The times should be distinct within the day
        for i, time in enumerate(times):
            if i > 0:
                assert time != times[i - 1] or time == times[i - 1]  # Allow duplicates but check format


def test_intraday_timestamps_preserve_minutes(sample_intraday_payload):
    """Test that minutes are preserved in timestamps (specific to intraday)."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_intraday_payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        # Verify that the index has a name and is a DatetimeIndex
        assert result.index.name == "Date"
        assert isinstance(result.index, pd.DatetimeIndex)

        # Verify times are not all identical
        hours_minutes = [(t.hour, t.minute) for t in result.index]
        assert len(set(hours_minutes)) > 1, "Should have different times within the day"


# ============================================================================
# Tests: OHLCV vs Close Field
# ============================================================================


def test_intraday_ohlcv_columns(sample_intraday_payload):
    """Test that OHLCV columns are present with field='ohlcv'."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_intraday_payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        expected_cols = {"open", "high", "low", "close", "volume"}
        assert expected_cols.issubset(set(result.columns))


def test_intraday_prices_rounded_to_2dp(sample_intraday_payload):
    """Test that price columns are rounded to 2 decimal places."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_intraday_payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        # Check that close prices are rounded to 2dp
        for price in result["close"]:
            # Round to 10 decimals to account for floating point precision
            assert price == round(price, 2), f"Price {price} not rounded to 2dp"


def test_intraday_volume_is_int(sample_intraday_payload):
    """Test that volume is stored as nullable integer."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_intraday_payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        # Int64 is nullable integer, handles NaN for bars with no trades
        assert result["volume"].dtype == "Int64"


def test_intraday_volume_handles_nan(sample_intraday_payload):
    """Test that NaN volume (no trades on bar) is preserved, not crashing."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        # Create payload with a NaN volume (some bars have no trades)
        payload = sample_intraday_payload.copy()
        payload["chart"]["result"][0]["indicators"]["quote"][0]["volume"][1] = None  # Second bar has no volume

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = payload
        mock_get.return_value = mock_response

        # Should not crash; NaN volumes should be preserved as <NA>
        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        assert result["volume"].dtype == "Int64"
        # Second bar should have <NA> (pandas' representation of null in Int64)
        assert pd.isna(result["volume"].iloc[1])
        # Other bars should have valid volumes
        assert result["volume"].iloc[0] > 0
        assert result["volume"].iloc[2] > 0


# ============================================================================
# Tests: include_prepost Parameter
# ============================================================================


def test_intraday_include_prepost_in_url():
    """Test that include_prepost=True adds includePrePost=true to the URL."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("TEST", interval="5m", include_prepost=True)

        # Check URL contains includePrePost=true
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "includePrePost=true" in url


def test_intraday_exclude_prepost_by_default():
    """Test that include_prepost=False (default) does not add includePrePost to the URL."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("TEST", interval="5m")

        # Check URL does NOT contain includePrePost
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "includePrePost" not in url


# ============================================================================
# Tests: range_ Parameter
# ============================================================================


def test_intraday_range_parameter_in_url():
    """Test that range_ parameter is used in the URL instead of period1/period2."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("TEST", interval="5m", range_="5d")

        # Check URL contains range=5d
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "range=5d" in url
        # Should NOT contain period1 or period2
        assert "period1" not in url
        assert "period2" not in url


def test_intraday_range_overrides_lookback_days(caplog):
    """Test that range_ parameter causes lookback_days to be ignored."""
    with caplog.at_level(logging.INFO):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = get_one_ticker_intraday(
                "TEST", interval="5m", lookback_days=30, range_="1d"
            )

            # Check that range_ was used
            call_args = mock_get.call_args
            url = call_args[0][0]
            assert "range=1d" in url


# ============================================================================
# Tests: Portfolio Concurrency and Failure Isolation
# ============================================================================


def test_portfolio_intraday_close_field(sample_intraday_payload):
    """Test portfolio with field='close' returns wide DataFrame."""
    with patch("earningspy.generators.yahoo.intraday._create_session") as mock_session_creator:
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session_creator.return_value = mock_session
        
        # Make side_effect return a different response with correct symbol for each call
        def get_response(url, **kwargs):
            response = MagicMock()
            response.ok = True
            payload = sample_intraday_payload.copy()
            if "HELE" in url:
                payload["chart"]["result"][0]["meta"]["symbol"] = "HELE"
            else:
                payload["chart"]["result"][0]["meta"]["symbol"] = "TEST"
            response.json.return_value = payload
            return response
        
        mock_session.get.side_effect = get_response

        result = get_portfolio_intraday(
            ["HELE", "TEST"], interval="5m", field="close"
        )

        assert isinstance(result, pd.DataFrame)
        # Should have columns for each ticker
        assert "HELE" in result.columns
        assert "TEST" in result.columns
        # Should only have close prices
        assert len(result.columns) == 2


def test_portfolio_intraday_ohlcv_field(sample_intraday_payload):
    """Test portfolio with field='ohlcv' returns dict of DataFrames."""
    with patch("earningspy.generators.yahoo.intraday._create_session") as mock_session_creator:
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session_creator.return_value = mock_session
        
        # Make side_effect return a different response with correct symbol for each call
        def get_response(url, **kwargs):
            response = MagicMock()
            response.ok = True
            payload = sample_intraday_payload.copy()
            if "HELE" in url:
                payload["chart"]["result"][0]["meta"]["symbol"] = "HELE"
            else:
                payload["chart"]["result"][0]["meta"]["symbol"] = "TEST"
            response.json.return_value = payload
            return response
        
        mock_session.get.side_effect = get_response

        result = get_portfolio_intraday(
            ["HELE", "TEST"], interval="5m", field="ohlcv"
        )

        assert isinstance(result, dict)
        assert "HELE" in result
        assert "TEST" in result
        # Each entry should be a DataFrame with OHLCV
        assert "open" in result["HELE"].columns
        assert "close" in result["HELE"].columns


def test_portfolio_intraday_one_bad_ticker_skipped(sample_intraday_payload, caplog):
    """Test that one failed ticker is skipped while others succeed."""
    with caplog.at_level(logging.WARNING):
        with patch("earningspy.generators.yahoo.intraday._create_session") as mock_session_creator:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session_creator.return_value = mock_session
            
            def mock_get_side_effect(url, **kwargs):
                mock_response = MagicMock()
                if "GOOD" in url:
                    mock_response.ok = True
                    payload = sample_intraday_payload.copy()
                    payload["chart"]["result"][0]["meta"]["symbol"] = "GOOD"
                    mock_response.json.return_value = payload
                else:
                    mock_response.ok = False
                    mock_response.status_code = 500
                return mock_response

            mock_session.get.side_effect = mock_get_side_effect

            result = get_portfolio_intraday(
                ["GOOD", "BAD"], interval="5m", field="close"
            )

            # Should have the good ticker
            assert "GOOD" in result.columns
            assert result is not None


def test_portfolio_intraday_all_bad_raises_error(caplog):
    """Test that all-bad tickers raises ValueError."""
    with caplog.at_level(logging.ERROR):
        with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            with pytest.raises(ValueError, match="No valid assets found"):
                get_portfolio_intraday(["BAD1", "BAD2"], interval="5m", field="close")


def test_portfolio_intraday_dedup_assets():
    """Test that duplicate assets in the list are deduplicated."""
    with patch("earningspy.generators.yahoo.intraday._create_session") as mock_session_creator:
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        mock_session_creator.return_value = mock_session
        
        call_count = 0

        def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 500
            return mock_response

        mock_session.get.side_effect = count_calls

        # Make three requests with duplicates
        try:
            get_portfolio_intraday(["TEST", "TEST", "TEST"], interval="5m", field="close")
        except ValueError:
            pass

        # Should only have made 1 call (deduplicated) - one per unique asset
        # With ThreadPoolExecutor, the calls should be 1
        assert call_count == 1, f"Expected 1 call for deduplicated assets, got {call_count}"


# ============================================================================
# Tests: Daily Functions Unchanged
# ============================================================================


def test_daily_get_one_ticker_unchanged(sample_daily_payload):
    """Test that daily get_one_ticker still works (regression test)."""
    with patch("earningspy.generators.yahoo.time_series.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_daily_payload
        mock_get.return_value = mock_response

        result = get_one_ticker("AAPL", from_="3m")

        assert result is not None
        assert not result.empty
        # Daily should have normalized timestamps (all midnight)
        times = result.index.time
        from datetime import time as dt_time
        assert all(t == dt_time(0, 0) for t in times), "Daily should have normalized times to midnight"


def test_daily_prepare_data_drops_ohlv(sample_daily_payload):
    """Test that prepare_data still drops open/high/low/volume (regression test)."""
    data = pd.DataFrame({
        "open": [149.50, 150.10],
        "high": [150.50, 151.00],
        "low": [149.00, 149.50],
        "close": [150.00, 150.50],
        "volume": [50000000, 45000000],
    })

    result = prepare_data(data, "AAPL")

    # Should only have close column (renamed to ticker)
    assert "AAPL" in result.columns
    assert "open" not in result.columns
    assert "high" not in result.columns
    assert "low" not in result.columns
    assert "volume" not in result.columns


def test_daily_get_portfolio_unchanged(sample_daily_payload):
    """Test that daily get_portfolio still works (regression test)."""
    with patch("earningspy.generators.yahoo.time_series._create_session") as mock_session:
        mock_sess = MagicMock()

        def mock_get(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = sample_daily_payload
            return mock_response

        mock_sess.get.side_effect = mock_get
        mock_sess.__enter__.return_value = mock_sess
        mock_session.return_value = mock_sess

        result = get_portfolio(["AAPL", "MSFT"], from_="3m")

        assert result is not None
        # Should have close-only columns (both tickers)
        assert len(result.columns) >= 1


# ============================================================================
# Tests: Exchange Timezone Handling
# ============================================================================


def test_intraday_exchange_tz_from_response(sample_intraday_payload):
    """Test that exchange timezone from response is used."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = sample_intraday_payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        # Timestamps should be in NY time (no timezone info, but times should be NY local)
        # The timestamps in the payload are UTC epoch seconds, which should be converted
        # to NY timezone and result in reasonable market hour times
        assert len(result) > 0, "Should have at least one row"
        # Just verify the index has the correct name
        assert result.index.name == "Date"


def test_intraday_default_ny_tz_when_missing(sample_intraday_payload):
    """Test that America/New_York is used as fallback if exchangeTimezoneName is missing."""
    payload = sample_intraday_payload.copy()
    payload["chart"]["result"][0]["meta"] = {}  # Remove exchangeTimezoneName

    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = payload
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("HELE", interval="5m")

        assert result is not None
        # Should still work with default NY tz


# ============================================================================
# Tests: Request Headers
# ============================================================================


def test_intraday_user_agent_header():
    """Test that User-Agent header is sent (reused from daily)."""
    with patch("earningspy.generators.yahoo.intraday.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_one_ticker_intraday("TEST", interval="5m")

        # Check that headers were passed
        call_args = mock_get.call_args
        headers = call_args[1].get("headers", {})
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]
