import logging
from datetime import datetime

import pandas as pd
import pytest
import requests

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

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None):
        if asset == 'BAD':
            return None
        return sample.copy()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)
    monkeypatch.setattr(time_series, 'tqdm', lambda items: items)

    with caplog.at_level(logging.INFO, logger=time_series.__name__):
        portfolio = time_series.get_portfolio(['GOOD', 'BAD'], start_date='2024-01-01', end_date=datetime(2024, 1, 31).date())

    assert 'GOOD' in portfolio.columns
    assert 'BAD' not in portfolio.columns
    assert "Skipping BAD: no data returned from Yahoo fetch" in caplog.text


def test_get_portfolio_logs_malformed_data_skip(monkeypatch, caplog):
    sample = _sample_ticker_frame()
    original_prepare_data = time_series.prepare_data

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None):
        return sample.copy()

    def fake_prepare_data(data, ticker):
        if ticker == 'BAD':
            return pd.DataFrame({'wrong': [1.0]}, index=pd.to_datetime(['2024-01-02'])).rename_axis('Date')
        return original_prepare_data(sample.copy(), ticker)

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'prepare_data', fake_prepare_data)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)
    monkeypatch.setattr(time_series, 'tqdm', lambda items: items)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        portfolio = time_series.get_portfolio(['BAD', 'GOOD'], start_date='2024-01-01', end_date='2024-01-31')

    assert 'GOOD' in portfolio.columns
    assert 'BAD' not in portfolio.columns
    assert "Skipping BAD: malformed data after preparation" in caplog.text


def test_get_portfolio_logs_and_raises_when_all_assets_fail(monkeypatch, caplog):
    monkeypatch.setattr(time_series, 'get_one_ticker', lambda *args, **kwargs: None)
    monkeypatch.setattr(time_series, 'tqdm', lambda items: items)

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

    def fake_get_one_ticker(asset, from_='3m', start_date=None, end_date=None):
        return frames[asset].copy()

    monkeypatch.setattr(time_series, 'get_one_ticker', fake_get_one_ticker)
    monkeypatch.setattr(time_series, 'sleep', lambda _: None)
    monkeypatch.setattr(time_series, 'tqdm', lambda items: items)
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
