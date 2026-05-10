import logging
from datetime import datetime

import pandas as pd
import pytest
import requests

from tests.utils.fixtures import yahoo_raw_response_data
import earningspy.generators.yahoo.time_series as time_series


class FakeResponse:

    def __init__(self, ok=True, status_code=200, payload=None, text=''):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _sample_ticker_frame():
    return pd.DataFrame(
        {
            'open': [100.0, 101.0],
            'high': [101.0, 102.0],
            'low': [99.0, 100.0],
            'close': [100.5, 101.5],
            'volume': [1000, 1100],
        },
        index=pd.to_datetime(['2024-01-02', '2024-01-03']),
    ).rename_axis('Date')


def test_get_one_ticker_logs_and_returns_none_on_request_exception(monkeypatch, caplog):
    def fake_get(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(time_series.requests, 'get', fake_get)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        result = time_series.get_one_ticker('AAPL', start_date='2024-01-01', end_date='2024-01-31')

    assert result is None
    assert "Yahoo request failed for AAPL" in caplog.text


def test_get_one_ticker_logs_non_ok_response(monkeypatch, caplog):
    def fake_get(*args, **kwargs):
        return FakeResponse(ok=False, status_code=503, text='service unavailable')

    monkeypatch.setattr(time_series.requests, 'get', fake_get)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        result = time_series.get_one_ticker('AAPL', start_date='2024-01-01', end_date='2024-01-31')

    assert result is None
    assert "Yahoo request returned non-OK response for AAPL" in caplog.text
    assert "status=503" in caplog.text


def test_get_one_ticker_logs_malformed_payload(monkeypatch, caplog):
    payload = {'chart': {'result': None}}

    def fake_get(*args, **kwargs):
        return FakeResponse(ok=True, payload=payload)

    monkeypatch.setattr(time_series.requests, 'get', fake_get)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        result = time_series.get_one_ticker('AAPL', start_date='2024-01-01', end_date='2024-01-31')

    assert result is None
    assert "Yahoo payload parsing failed for AAPL" in caplog.text


def test_get_portfolio_skips_failed_ticker_and_keeps_valid_data(monkeypatch, caplog):
    sample = _sample_ticker_frame()

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None, session=None, timeout=10):
        if asset == 'BAD':
            return None
        return sample.copy()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)

    with caplog.at_level(logging.INFO, logger=time_series.__name__):
        portfolio = time_series.get_portfolio(['GOOD', 'BAD'], start_date='2024-01-01', end_date=datetime(2024, 1, 31).date())

    assert 'GOOD' in portfolio.columns
    assert 'BAD' not in portfolio.columns
    assert "Skipping BAD: no data returned from Yahoo fetch" in caplog.text


def test_get_portfolio_logs_progress(monkeypatch, caplog):
    sample = _sample_ticker_frame()

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None, session=None, timeout=10):
        return sample.copy()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)

    with caplog.at_level(logging.INFO, logger=time_series.__name__):
        portfolio = time_series.get_portfolio(['AAA', 'BBB'], start_date='2024-01-01', end_date=datetime(2024, 1, 31).date())

    assert 'AAA' in portfolio.columns
    assert 'BBB' in portfolio.columns
    assert "Yahoo progress 1/2 (50%)" in caplog.text
    assert "Yahoo progress 2/2 (100%)" in caplog.text


def test_get_portfolio_logs_malformed_data_skip(monkeypatch, caplog):
    sample = _sample_ticker_frame()
    original_prepare_data = time_series.prepare_data

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None, session=None, timeout=10):
        return sample.copy()

    def fake_prepare_data(data, ticker):
        if ticker == 'BAD':
            return pd.DataFrame({'wrong': [1.0]}, index=pd.to_datetime(['2024-01-02'])).rename_axis('Date')
        return original_prepare_data(sample.copy(), ticker)

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'prepare_data', fake_prepare_data)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        portfolio = time_series.get_portfolio(['BAD', 'GOOD'], start_date='2024-01-01', end_date='2024-01-31')

    assert 'GOOD' in portfolio.columns
    assert 'BAD' not in portfolio.columns
    assert "Skipping BAD: malformed data after preparation" in caplog.text


def test_get_portfolio_logs_and_raises_when_all_assets_fail(monkeypatch, caplog):
    monkeypatch.setattr(time_series, 'get_one_ticker', lambda *args, **kwargs: None)

    with caplog.at_level(logging.ERROR, logger=time_series.__name__):
        with pytest.raises(ValueError, match="No valid assets found"):
            time_series.get_portfolio(['BAD1', 'BAD2'], start_date='2024-01-01', end_date='2024-01-31')

    assert "No valid assets found for Yahoo portfolio request" in caplog.text


def test_get_portfolio_avoids_repeated_merge_and_preserves_date_union(monkeypatch):
    frames = {
        'AAA': pd.DataFrame(
            {
                'open': [10.0, 11.0],
                'high': [10.5, 11.5],
                'low': [9.5, 10.5],
                'close': [10.1, 11.1],
                'volume': [100, 110],
            },
            index=pd.to_datetime(['2024-01-02', '2024-01-03']),
        ).rename_axis('Date'),
        'BBB': pd.DataFrame(
            {
                'open': [20.0, 21.0],
                'high': [20.5, 21.5],
                'low': [19.5, 20.5],
                'close': [20.2, 21.2],
                'volume': [200, 210],
            },
            index=pd.to_datetime(['2024-01-03', '2024-01-04']),
        ).rename_axis('Date'),
    }

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None, session=None, timeout=10):
        return frames[asset].copy()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)
    monkeypatch.setattr(
        time_series.pd,
        'merge',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pd.merge should not be called")),
    )

    portfolio = time_series.get_portfolio(['AAA', 'BBB', 'AAA'], start_date='2024-01-01', end_date='2024-01-31')

    assert list(portfolio.columns) == ['AAA', 'BBB']
    assert portfolio.index.tolist() == list(pd.to_datetime(['2024-01-02', '2024-01-03', '2024-01-04']))
    assert portfolio.loc[pd.Timestamp('2024-01-02'), 'AAA'] == pytest.approx(10.1)
    assert pd.isna(portfolio.loc[pd.Timestamp('2024-01-02'), 'BBB'])
    assert portfolio.loc[pd.Timestamp('2024-01-04'), 'BBB'] == pytest.approx(21.2)


def test_get_range_rejects_invalid_value():
    with pytest.raises(Exception, match='Invalid from value'):
        time_series.get_range('2m', datetime(2024, 1, 1).date())


def test_get_range_returns_expected_string():
    start, end = time_series.get_range('1y', datetime(2024, 1, 1).date())
    assert start == '2023-01-01'
    assert end == '2024-01-01'


def test_get_range_timestamps_returns_unix_strings():
    start_ts, end_ts = time_series.get_range_timestamps('2024-01-01', '2024-01-02')
    assert start_ts.isdigit()
    assert end_ts.isdigit()
    assert int(end_ts) - int(start_ts) == 86400


def test_get_response_hint_handles_empty_and_long_text():
    assert time_series._get_response_hint(FakeResponse(text='')) == ''
    long_text = 'x' * 250
    hint = time_series._get_response_hint(FakeResponse(text=long_text))
    assert hint.endswith('...')
    assert len(hint) <= 203


def test_get_retry_strategy_falls_back_for_old_urllib3(monkeypatch):
    class FakeRetry:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    original_frozenset = frozenset
    call_state = {'count': 0}

    def broken_frozenset(*args, **kwargs):
        if call_state['count'] == 0:
            call_state['count'] += 1
            raise TypeError('unsupported')
        return original_frozenset(*args, **kwargs)

    monkeypatch.setattr(time_series, 'Retry', FakeRetry)
    monkeypatch.setitem(time_series.__dict__, 'frozenset', broken_frozenset)

    strategy = time_series._get_retry_strategy()

    assert isinstance(strategy, FakeRetry)
    assert 'method_whitelist' in strategy.kwargs


def test_fetch_ticker_data_handles_unexpected_session_failure(monkeypatch, caplog):
    class FakeSession:
        def get(self, *args, **kwargs):
            raise ValueError('boom')

    with caplog.at_level(logging.ERROR, logger=time_series.__name__):
        asset, data = time_series._fetch_ticker_data(FakeSession(), 'AAPL', start_date='2024-01-01', end_date='2024-01-02', timeout=1)

    assert asset == 'AAPL'
    assert data is None
    assert 'Unexpected Yahoo request failure for AAPL' in caplog.text


def test_get_portfolio_skips_asset_when_ticker_fetch_raises(monkeypatch, caplog):
    sample = _sample_ticker_frame()

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None, session=None, timeout=10):
        if asset == 'BAD':
            raise RuntimeError('boom')
        return sample.copy()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        portfolio = time_series.get_portfolio(['GOOD', 'BAD'], start_date='2024-01-01', end_date=datetime(2024, 1, 31).date())

    assert 'GOOD' in portfolio.columns
    assert 'BAD' not in portfolio.columns
    assert 'Skipping BAD: Yahoo fetch failed (boom)' in caplog.text


def test_get_portfolio_skips_empty_ticker_dataset(monkeypatch, caplog):
    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None, session=None, timeout=10):
        return pd.DataFrame()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        with pytest.raises(ValueError, match='No valid assets found'):
            time_series.get_portfolio(['BAD'], start_date='2024-01-01', end_date=datetime(2024, 1, 31).date())

    assert 'Yahoo returned an empty dataset' in caplog.text


def test_normalize_close_frame_sets_date_index_and_removes_duplicates():
    frame = pd.DataFrame({'SPY': [1.0, 2.0]}, index=['2024-01-01', '2024-01-01'])
    frame.index.name = 'NotDate'

    normalized = time_series._normalize_close_frame(frame, 'SPY')

    assert normalized.index.name == 'Date'
    assert len(normalized) == 1
    assert normalized.iloc[0, 0] == pytest.approx(2.0)


def test_normalize_close_frame_raises_when_asset_column_missing():
    frame = pd.DataFrame({'OTHER': [1.0]}, index=['2024-01-01'])

    with pytest.raises(KeyError):
        time_series._normalize_close_frame(frame, 'SPY')


def test_get_range_uses_all_accepted_periods():
    end_date = datetime(2024, 1, 1).date()

    assert time_series.get_range('9m', end_date) == ('2023-04-01', '2024-01-01')
    assert time_series.get_range('5y', end_date) == ('2019-01-01', '2024-01-01')
    assert time_series.get_range('10y', end_date) == ('2014-01-01', '2024-01-01')
    assert time_series.get_range('20y', end_date) == ('2004-01-01', '2024-01-01')
    assert time_series.get_range('30y', end_date) == ('1994-01-01', '2024-01-01')


def test_create_session_mounts_adapters():
    session = time_series._create_session()

    assert 'https://' in session.adapters
    assert 'http://' in session.adapters
    assert session.adapters['https://'].__class__.__name__ == 'HTTPAdapter'
    assert session.adapters['http://'].__class__.__name__ == 'HTTPAdapter'


def test_get_one_ticker_uses_session_get(monkeypatch):
    payload = yahoo_raw_response_data()

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse(ok=True, payload=payload)

    data = time_series.get_one_ticker('SPY', start_date='2024-03-01', end_date='2024-03-02', session=FakeSession(), timeout=1)

    assert data is not None
    assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']


def test_prepare_data_returns_close_only():
    frame = pd.DataFrame(
        {
            'open': [1.0],
            'high': [2.0],
            'low': [0.5],
            'close': [1.5],
            'volume': [100],
        },
        index=pd.to_datetime(['2024-01-01']),
    ).rename_axis('Date')

    result = time_series.prepare_data(frame, 'SPY')

    assert list(result.columns) == ['SPY']
    assert result.iloc[0, 0] == pytest.approx(1.5)


def test_prepare_data_raises_missing_column():
    frame = pd.DataFrame({'close': [1.5]}, index=pd.to_datetime(['2024-01-01'])).rename_axis('Date')

    with pytest.raises(KeyError):
        time_series.prepare_data(frame, 'SPY')


def test_get_portfolio_handles_unexpected_normalize_exception(monkeypatch, caplog):
    sample = _sample_ticker_frame()

    def fake_prepare_data(data, ticker):
        return sample.copy()

    def fake_normalize_close_frame(data, ticker):
        raise RuntimeError('unexpected normalize failure')

    monkeypatch.setattr(time_series, 'get_one_ticker', lambda *args, **kwargs: sample.copy())
    monkeypatch.setattr(time_series, 'prepare_data', fake_prepare_data)
    monkeypatch.setattr(time_series, '_normalize_close_frame', fake_normalize_close_frame)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)

    with caplog.at_level(logging.ERROR, logger=time_series.__name__):
        with pytest.raises(ValueError, match='No valid assets found'):
            time_series.get_portfolio(['BAD'], start_date='2024-01-01', end_date=datetime(2024, 1, 31).date())

    assert 'Skipping BAD: could not normalize prepared data' in caplog.text
