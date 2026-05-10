import logging
import pandas as pd
import requests

from tests.utils.fixtures import (
    yahoo_raw_response_data,
    yahoo_raw_error_response_data,
    yahoo_raw_missing_fields_response_data,
)
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


def test_yahoo_raw_response_fixture_structure():
    payload = yahoo_raw_response_data()

    assert 'chart' in payload
    assert payload['chart']['error'] is None
    result = payload['chart']['result'][0]
    assert 'timestamp' in result
    assert isinstance(result['timestamp'], list)
    assert 'indicators' in result
    assert 'quote' in result['indicators']

    quote = result['indicators']['quote'][0]
    assert set(quote.keys()) >= {'open', 'high', 'low', 'close', 'volume'}
    assert all(isinstance(quote[key], list) for key in ['open', 'high', 'low', 'close', 'volume'])


def test_get_one_ticker_parses_yahoo_api_payload(monkeypatch, caplog):
    payload = yahoo_raw_response_data()

    def fake_get(*args, **kwargs):
        return FakeResponse(ok=True, payload=payload)

    monkeypatch.setattr(time_series.requests, 'get', fake_get)

    with caplog.at_level(logging.INFO, logger=time_series.__name__):
        data = time_series.get_one_ticker('SPY', start_date='2024-03-01', end_date='2024-03-02')

    assert data is not None
    assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']
    assert data.index.name == 'Date'
    assert data.shape == (2, 5)
    assert data['close'].tolist() == [509.9, 510.85]
    assert 'Fetching Yahoo ticker SPY' in caplog.text
    assert 'Successfully fetched Yahoo ticker SPY' in caplog.text


def test_get_one_ticker_parses_yahoo_api_payload_missing_fields(monkeypatch):
    payload = yahoo_raw_missing_fields_response_data()

    def fake_get(*args, **kwargs):
        return FakeResponse(ok=True, payload=payload)

    monkeypatch.setattr(time_series.requests, 'get', fake_get)

    data = time_series.get_one_ticker('SPY', start_date='2024-03-01', end_date='2024-03-02')

    assert data is not None
    assert 'high' not in data.columns
    assert 'low' not in data.columns
    assert list(data.columns) == ['open', 'close', 'volume']
    assert data['close'].tolist() == [509.9, 510.85]


def test_get_one_ticker_returns_none_for_yahoo_error_payload(monkeypatch, caplog):
    payload = yahoo_raw_error_response_data()

    def fake_get(*args, **kwargs):
        return FakeResponse(ok=True, payload=payload)

    monkeypatch.setattr(time_series.requests, 'get', fake_get)

    with caplog.at_level(logging.WARNING, logger=time_series.__name__):
        data = time_series.get_one_ticker('SPY', start_date='2024-03-01', end_date='2024-03-02')

    assert data is None
    assert 'Yahoo payload parsing failed for SPY' in caplog.text
