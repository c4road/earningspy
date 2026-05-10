import os
import json
import pytest


def screener_mock_data():
    """Load screener_mock.json and return a list of dicts."""
    here = os.path.dirname(__file__)
    json_path = os.path.join(here, './screener_mock.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data


def yahoo_raw_response_data():
    """Load a sample Yahoo Finance raw chart API response."""
    here = os.path.dirname(__file__)
    json_path = os.path.join(here, '../generators/yahoo_raw_payload.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data


def yahoo_raw_error_response_data():
    """Load a sample Yahoo Finance raw chart API error response."""
    here = os.path.dirname(__file__)
    json_path = os.path.join(here, '../generators/yahoo_raw_payload_error.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data


def yahoo_raw_missing_fields_response_data():
    """Load a sample Yahoo Finance raw chart API response missing high/low."""
    here = os.path.dirname(__file__)
    json_path = os.path.join(here, '../generators/yahoo_raw_payload_missing_fields.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data
