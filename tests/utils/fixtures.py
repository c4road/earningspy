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
