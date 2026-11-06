from unittest.mock import MagicMock, patch

import pytest
import numpy as np
import pandas as pd
import earningspy.generators.finviz.data as finviz_data_module
from earningspy.generators.finviz.data import (
    _get_screener_data,
    get_by_earnings_date,
    get_by_tickers,
)
from earningspy.generators.finviz.helper_functions.error_handling import FinvizColumnMismatch, NoResults
from earningspy.generators.finviz.helper_functions.scraper_functions import get_table
from earningspy.generators.finviz.screener import Screener
from tests.utils.fixtures import screener_mock_data

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


@pytest.fixture(autouse=True)
def mock_finviz_requests(monkeypatch):
    mock_data = screener_mock_data()

    def fake_init_from_url(*args, **kwargs):
        return list(mock_data)

    monkeypatch.setattr(Screener, 'init_from_url', fake_init_from_url)


@pytest.mark.parametrize("filters", [
    'ind_solar',
])
def test_get_screener_data(filters):
    print(f"Testing filter: {filters}")
    data = _get_screener_data(filter_string=filters, sort_column='marketcap')

    assert data.columns.tolist() == EXPECTED_COLUMNS, "DataFrame columns do not match expected columns"
    assert not data.empty, "DataFrame should not be empty"

    _assert_row_nan_threshold(data)


def test_screener_data_has_no_all_nan_columns():
    """A column that is NaN for every row means Finviz renamed or dropped its label."""
    data = _get_screener_data(filter_string='earningsdate_thismonth', sort_column='marketcap')

    all_nan = [column for column in data.columns if data[column].isna().all()]
    assert not all_nan, f"columns entirely NaN (Finviz label renamed or dropped?): {all_nan}"


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


def test_get_table_uses_last_text_fragment_per_cell():
    headers = ['Ticker', 'Price', 'Prev Close', 'P/E', 'Beta']
    page_html = """
    <html><body>
    <table>
        <tr>
            <th>Ticker</th><th>Price</th><th>Prev Close</th><th>P/E</th><th>Beta</th>
        </tr>
        <tr valign="top">
            <td><span>G</span>GOOGL</td>
            <td>346.77</td>
            <td>354.46</td>
            <td>26.45</td>
            <td>1.24</td>
        </tr>
    </table>
    </body></html>
    """

    rows = get_table(page_html, headers)

    assert len(rows) == 1
    row = rows[0]
    assert len(row) == len(headers)
    assert row['Ticker'] == 'GOOGL'
    assert row['Price'] == '346.77'
    assert row['Prev Close'] == '354.46'
    assert row['P/E'] == '26.45'
    assert row['Beta'] == '1.24'


def test_get_table_guardrail_raises_on_row_cell_mismatch():
    headers = ['Ticker', 'Price', 'Prev Close', 'P/E', 'Beta']
    page_html = """
    <html><body>
    <table>
        <tr>
            <th>Ticker</th><th>Price</th><th>Prev Close</th><th>P/E</th><th>Beta</th>
        </tr>
        <tr valign="top">
            <td><span>G</span>GOOGL</td>
            <td>346.77</td>
            <td>354.46</td>
            <td>26.45</td>
        </tr>
    </table>
    </body></html>
    """

    with pytest.raises(ValueError, match='Finviz column-count mismatch'):
        get_table(page_html, headers)



@pytest.mark.parametrize("raw, expected", [
    ("48.65%", 0.4865),
    ("1.01%", 0.0101),
    ("1.00%", 0.01),
    ("0.50%", 0.005),
    ("-0.80%", -0.008),
    ("0.00%", 0.0),
    ("3.5", 0.035),
    (50, 0.5),
])
def test_format_percent_scales_values(raw, expected):
    """A '%'-suffixed value is always divided by 100, so values within (-1%, 1%)
    are not mistaken for already-decimal fractions."""
    from earningspy.generators.finviz.utils import _format_percent
    assert _format_percent(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["-", "", "—", None, np.nan, "abc%"])
def test_format_percent_missing_is_nan(raw):
    from earningspy.generators.finviz.utils import _format_percent
    assert np.isnan(_format_percent(raw))


def test_no_percent_column_is_listed_twice():
    """The list is applied once per entry, so a repeated column is scaled twice."""
    from earningspy.generators.finviz.constants import PERCENTAJE_COLUMNS
    assert len(PERCENTAJE_COLUMNS) == len(set(PERCENTAJE_COLUMNS))


@pytest.mark.parametrize("column", ["Perf Quart", "Payout Ratio", "Profit M", "Oper M"])
@pytest.mark.parametrize("raw, expected", [("125.00%", 1.25), ("-340.50%", -3.405), ("0.83%", 0.0083), ("41.00%", 0.41)])
def test_percent_conversion_scales_once(column, raw, expected):
    from earningspy.generators.finviz.utils import _convert_percent_columns
    from earningspy.generators.finviz.constants import PERCENTAJE_COLUMNS
    data = pd.DataFrame({"AAA": {c: "1.00%" for c in PERCENTAJE_COLUMNS}})
    data.loc[column, "AAA"] = raw
    converted = _convert_percent_columns(data)
    assert float(converted.loc[column, "AAA"]) == pytest.approx(expected)


def _exchange_screens(by_exchange, total_rows):
    """A screen over the row cap as a whole, served exchange by exchange."""
    from earningspy.generators.finviz.helper_functions.error_handling import RowCapExceeded

    def fake(url, *args, **kwargs):
        for exchange, rows in by_exchange.items():
            if exchange in url:
                if not rows:
                    raise NoResults("empty")
                return rows
        raise RowCapExceeded(total_rows, 1000)
    return fake


def test_a_screen_over_the_cap_is_read_by_exchange(monkeypatch):
    rows = [dict(r) for r in screener_mock_data()]
    nasd, nyse = rows[:1], rows[1:]
    fake = _exchange_screens({"exch_nasd": nasd, "exch_nyse": nyse + nasd, "exch_amex": []}, len(rows))
    monkeypatch.setattr(Screener, "init_from_url", fake)
    got = _get_screener_data(filter_string="earningsdate_thismonth")
    assert sorted(got.index) == sorted(r["Ticker"] for r in rows)


def test_a_partition_that_misses_too_many_rows_raises(monkeypatch):
    from earningspy.generators.finviz.helper_functions.error_handling import FinvizPartitionShortfall
    rows = [dict(r) for r in screener_mock_data()]
    monkeypatch.setattr(Screener, "init_from_url", _exchange_screens({"exch_nasd": rows, "exch_nyse": [], "exch_amex": []}, 2000))
    with pytest.raises(FinvizPartitionShortfall, match="2000"):
        _get_screener_data(filter_string="earningsdate_thismonth")


def test_a_full_url_over_the_cap_still_raises(monkeypatch):
    from earningspy.generators.finviz.helper_functions.error_handling import RowCapExceeded
    monkeypatch.setattr(Screener, "init_from_url", _exchange_screens({}, 2045))
    with pytest.raises(RowCapExceeded):
        _get_screener_data(full_query_url="https://finviz.com/screener.ashx?v=152&f=x")


def test_fetch_fails_when_header_labels_stop_matching(monkeypatch):
    """The 2026-10 short-label regression: values filed under "Market CapMkt Cap"
    left Market Cap missing on every row. The fetch must fail, not return NaNs."""
    def relabelled(*args, **kwargs):
        rows = []
        for row in screener_mock_data():
            row = dict(row)
            row["Market CapMkt Cap"] = row.pop("Market Cap")
            row["Short FloatShort Flt"] = row.pop("Short Float")
            rows.append(row)
        return rows

    monkeypatch.setattr(Screener, "init_from_url", relabelled)

    with pytest.raises(FinvizColumnMismatch, match="Market Cap") as excinfo:
        _get_screener_data(filter_string="earningsdate_thismonth")
    assert excinfo.value.columns == ["Market Cap", "Short Float"]


def test_dash_values_do_not_count_as_missing(monkeypatch):
    """A column Finviz renders as "-" for every row (e.g. no dividend payers) is
    present, so it must not trip the check."""
    def no_dividends(*args, **kwargs):
        return [dict(row, Dividend="-") for row in screener_mock_data()[:3]]

    monkeypatch.setattr(Screener, "init_from_url", no_dividends)

    data = _get_screener_data(full_query_url="https://finviz.com/screener.ashx?t=A,B,C")
    assert data["Dividend"].isna().all()


def test_known_absent_columns_are_exempt():
    from earningspy.generators.finviz.constants import FINVIZ_KNOWN_ABSENT_COLUMNS
    assert "Return% 1Y" in FINVIZ_KNOWN_ABSENT_COLUMNS
    assert "Return% 1Y" not in screener_mock_data()[0]  # absent, yet the fetch succeeds
    _get_screener_data(filter_string="earningsdate_thismonth")


@pytest.mark.parametrize("use_session", [True, False])
def test_finviz_requests_verify_the_tls_certificate(use_session):
    """Every value in the screen comes from this response, so the connection must be authenticated."""
    from earningspy.generators.finviz.helper_functions import request_functions as rf

    response = MagicMock(text="<html></html>", url="https://finviz.com", status_code=200)
    session = MagicMock()
    session.get.return_value = response
    with patch.object(rf, "_create_session", return_value=session):
        rf.http_request_get("https://finviz.com/screener.ashx", session=session if use_session else None)

    assert session.get.call_args.kwargs.get("verify", True) is True
    assert session.verify is not False


def test_certificate_failure_is_raised_not_ignored():
    import requests

    from earningspy.generators.finviz.helper_functions import request_functions as rf
    from earningspy.generators.finviz.helper_functions.error_handling import ConnectionTimeout

    session = MagicMock()
    session.get.side_effect = requests.exceptions.SSLError("certificate verify failed")
    with pytest.raises(ConnectionTimeout):
        rf.http_request_get("https://finviz.com/screener.ashx", session=session)
