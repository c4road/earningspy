import os
from urllib.parse import parse_qsl, urlparse

import pytest
import requests
from lxml import html

import earningspy.generators.finviz.screener as screener_module
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS_NEW,
    CUSTOM_TABLE_FIELDS_ON_URL,
)
from earningspy.generators.finviz.helper_functions.error_handling import InvalidTableType, NoResults, RowCapExceeded
from earningspy.generators.finviz.helper_functions.scraper_functions import (
    get_page_urls,
    get_table,
    get_table_headers,
    get_total_rows,
)
from earningspy.generators.finviz.screener import MAX_REACHABLE_ROWS, Screener, _reversed_order

GRID_FIXTURES = os.path.join(os.path.dirname(__file__), '..', 'utils', 'finviz_grid')
URL_COLUMNS = [c for c in CUSTOM_TABLE_FIELDS_ON_URL.replace('&c=', '').replace('\n', '').split(',') if c]


def _grid_page(columns, rows, total=None):
    """Builds a grid-screener page: columns is [(id, label)], rows is [[cell, ...]]."""
    header_cells = "".join(
        f'<div role="columnheader" data-column-id="{cid}"><span class="fv-table_header-label">{label}</span></div>'
        for cid, label in columns
    )
    body = ""
    for row in rows:
        cells = ""
        for (cid, _), value in zip(columns, row):
            if cid == "ticker":
                cells += f'<div role="gridcell" data-column-id="ticker" data-ticker="{value}"><span>{value[0]}</span>{value}</div>'
            else:
                cells += f'<div role="gridcell" data-column-id="{cid}">{value}</div>'
        body += f'<div class="fv-table_row" role="row">{cells}</div>'
    count = f'<p class="fv-table_toolbar-count">#1 / {total} Total</p>' if total is not None else ""
    return f'<html><body>{count}<div role="grid"><div role="row">{header_cells}</div>{body}</div></body></html>'


def _serve(monkeypatch, respond):
    """Routes Screener's HTTP calls to respond(columns, offset, query) -> page html; returns the request log."""
    requests_log = []

    def fake_get(url, session=None, payload=None, parse=True, user_agent=None, timeout=10):
        query = dict(payload) if payload else dict(parse_qsl(urlparse(url).query))
        columns = query.get("c", "").split(",") if query.get("c") else []
        offset = query.get("r", "1")
        requests_log.append((offset, columns, query))
        page = respond(columns, offset, query)
        final_url = url if not payload else "https://finviz.com/screener/stocks?" + "&".join(
            f"{key}={value}" for key, value in payload.items() if value
        )
        return (html.fromstring(page) if parse else page), final_url

    monkeypatch.setattr(screener_module, "http_request_get", fake_get)
    return requests_log


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------
def test_get_table_parses_grid_rows_and_bare_ticker():
    columns = [("row", "No."), ("ticker", "Ticker"), ("price", "Price"), ("change", "Change %")]
    page = _grid_page(columns, [["1", "GOOGL", "346.77", "1.30%"]])

    headers = get_table_headers(html.fromstring(page))
    rows = get_table(page, headers, 1)

    assert headers == ["No.", "Ticker", "Price", "Change"]
    assert rows == [{"No.": "1", "Ticker": "GOOGL", "Price": "346.77", "Change": "1.30%"}]


def test_get_table_headers_reads_full_label_not_short_label():
    """Since 2026-10 each grid header carries a short label next to the full one;
    reading all its text gave "Market CapMkt Cap" and emptied the column."""
    page = _grid_page([("row", "No."), ("marketCap", "Market Cap"), ("volume", "Volume")], [["1", "3.2B", "100"]])
    page = page.replace(
        '<span class="fv-table_header-label">Market Cap</span>',
        '<span class="fv-table_header-label">Market Cap</span><span class="fv-table_header-label-short">Mkt Cap</span>',
    )

    headers = get_table_headers(html.fromstring(page))

    assert headers == ["No.", "Market Cap", "Volume"]
    assert get_table(page, headers, 1) == [{"No.": "1", "Market Cap": "3.2B", "Volume": "100"}]


def test_recorded_page_with_short_labels_maps_to_field_names():
    """A real 2026-10-21 response whose headers carry short labels."""
    with open(os.path.join(GRID_FIXTURES, "page1_c1_short_labels.html")) as f:
        page = f.read()

    headers = get_table_headers(html.fromstring(page))
    rows = get_table(page, headers, 3)

    assert len(headers) == 36
    assert set(headers) - {"No."} <= set(CUSTOM_TABLE_ALL_FIELDS_NEW), set(headers) - set(CUSTOM_TABLE_ALL_FIELDS_NEW)
    assert {"Market Cap", "Forward P/E", "Short Float"} <= set(headers)
    assert all(row["Market Cap"] not in ("", None) for row in rows)


def test_get_table_raises_on_grid_column_misalignment():
    page = _grid_page([("row", "No."), ("price", "Price")], [["1", "346.77"]])
    page = page.replace('role="gridcell" data-column-id="price"', 'role="gridcell" data-column-id="change"')

    with pytest.raises(ValueError, match="Finviz column misalignment"):
        get_table(page, ["No.", "Price"], 1)


def test_get_table_headers_falls_back_to_table_layout():
    page = html.fromstring(
        '<html><body><table><tr valign="middle"><th>No.</th><th><a>Ticker</a></th><th>Change %</th></tr></table></body></html>'
    )
    assert get_table_headers(page) == ["No.", "Ticker", "Change"]


@pytest.mark.parametrize("markup, expected", [
    ('<p class="fv-table_toolbar-count">#1 / 1028 Total</p>', 1028),
    ('<div class="count-text whitespace-nowrap">#1 / 57 Total</div>', 57),
    ('<td class="count-text">#1 / 7 Total</td>', 7),
    ('<p class="fv-table_toolbar-count">#1 / n/a Total</p>', 0),
    ('<p>no results</p>', 0),
])
def test_get_total_rows(markup, expected):
    assert get_total_rows(html.fromstring(f"<html><body>{markup}</body></html>")) == expected


def test_get_page_urls_steps_by_page_size():
    url = "https://finviz.com/screener/stocks?v=152"
    assert get_page_urls(None, 41, url) == [url + "&r=1", url + "&r=21", url + "&r=41"]
    assert get_page_urls(None, 20, url) == [url + "&r=1"]


# ---------------------------------------------------------------------------
# Screener
# ---------------------------------------------------------------------------
def test_init_from_url_maps_query_params_to_request(monkeypatch):
    log = _serve(monkeypatch, lambda columns, offset, query: _grid_page(
        [("row", "No."), ("ticker", "Ticker"), ("price", "Price")], [["1", "AAPL", "250.00"]], total=1))

    data = Screener.init_from_url(
        "https://finviz.com/screener.ashx?v=152&t=AAPL,MSFT&f=exch_nasd,idx_sp500&o=-price&s=ta_topgainers&c=1,65"
    ).data

    first_query = log[0][2]
    assert first_query["v"] == "152"
    assert first_query["t"] == "AAPL,MSFT"
    assert first_query["f"] == "exch_nasd,idx_sp500"
    assert first_query["o"] == "-price"
    assert first_query["s"] == "ta_topgainers"
    assert first_query["c"] == "0,1,65"  # No. is always prepended as the row key
    assert data == [{"No.": "1", "Ticker": "AAPL", "Price": "250.00"}]


def test_init_from_url_rejects_unknown_table_type():
    with pytest.raises(InvalidTableType):
        Screener.init_from_url("https://finviz.com/screener.ashx?v=999")


def test_screener_raises_no_results_when_count_is_missing(monkeypatch):
    _serve(monkeypatch, lambda columns, offset, query: _grid_page([("row", "No.")], []))

    with pytest.raises(NoResults):
        Screener(filters=["earningsdate_thismonth"], custom_columns=["1"])


def test_screener_caps_requested_rows_at_total(monkeypatch):
    log = _serve(monkeypatch, lambda columns, offset, query: _grid_page(
        [("row", "No."), ("ticker", "Ticker")], [["1", "AAPL"], ["2", "MSFT"]], total=2))

    data = Screener(custom_columns=["1"], rows=500).data

    assert [row["Ticker"] for row in data] == ["AAPL", "MSFT"]
    assert [offset for offset, _, _ in log[1:]] == ["1"]  # one page, not 25


def test_screener_merges_width_truncated_column_chunks(monkeypatch):
    """The grid renders a prefix of the requested columns; leftovers are refetched and merged on No."""
    labels = {"0": ("row", "No."), "1": ("ticker", "Ticker"), "65": ("price", "Price"), "66": ("change", "Change %")}
    values = {
        "1": {"0": "1", "1": "AAPL", "65": "250.00", "66": "1.00%"},
        "21": {"0": "21", "1": "MSFT", "65": "500.00", "66": "-2.00%"},
    }

    def respond(columns, offset, query):
        rendered = columns[:3]  # width cap: only three columns fit
        return _grid_page([labels[c] for c in rendered], [[values[offset][c] for c in rendered]], total=21)

    log = _serve(monkeypatch, respond)

    data = Screener(custom_columns=["0", "1", "65", "66"]).data

    assert data == [
        {"No.": "1", "Ticker": "AAPL", "Price": "250.00", "Change": "1.00%"},
        {"No.": "21", "Ticker": "MSFT", "Price": "500.00", "Change": "-2.00%"},
    ]
    assert ("1", ["0", "66"]) in [(offset, columns) for offset, columns, _ in log]
    assert ("21", ["0", "66"]) in [(offset, columns) for offset, columns, _ in log]


def test_screener_raises_when_grid_renders_no_columns(monkeypatch):
    def respond(columns, offset, query):
        if columns[1] == "1":
            return _grid_page([("row", "No."), ("ticker", "Ticker")], [["1", "AAPL"]], total=1)
        return _grid_page([("row", "No.")], [["1"]], total=1)

    _serve(monkeypatch, respond)

    with pytest.raises(ValueError, match="Finviz rendered no columns"):
        Screener(custom_columns=["1", "65"])


def test_screener_without_custom_columns_fetches_each_page_once(monkeypatch):
    log = _serve(monkeypatch, lambda columns, offset, query: _grid_page(
        [("row", "No."), ("ticker", "Ticker")], [[offset, f"T{offset}"]], total=21))

    data = Screener(filters=["idx_sp500"]).data

    assert [row["Ticker"] for row in data] == ["T1", "T21"]
    assert [offset for offset, _, _ in log[1:]] == ["1", "21"]


# ---------------------------------------------------------------------------
# Recorded Finviz responses
# ---------------------------------------------------------------------------
def test_screener_parses_recorded_grid_pages(monkeypatch):
    """Three real width-truncated responses for page 1 merge into every requested column."""
    def respond(columns, offset, query):
        first = [c for c in columns if c != "0"][0]
        with open(os.path.join(GRID_FIXTURES, f"page1_c{first}.html")) as f:
            return f.read()

    log = _serve(monkeypatch, respond)

    data = Screener(filters=["earningsdate_thismonth"], rows=3, custom_columns=URL_COLUMNS).data

    expected = (set(CUSTOM_TABLE_ALL_FIELDS_NEW) - {"Return% 1Y"}) | {"No."}
    assert len(data) == 3
    for row in data:
        assert set(row) == expected
    assert [row["Ticker"] for row in data] == ["BMRA", "RMCF", "EDUC"]
    assert data[0]["Market Cap"] == "8.51M"
    assert data[0]["ROIC"] == "-95.70%"
    assert data[0]["Change"] == "-1.33%"
    assert data[1]["EV/Sales"] == "0.60"
    assert data[1]["52W Range"] == "0.66 - 2.99"
    assert data[2]["Earnings"] == "Oct 14/a"
    assert len([1 for _, _, query in log if query.get("r") == "1"]) == 3  # three column chunks


# ---------------------------------------------------------------------------
# Finviz's 1000-row cap for anonymous users
# ---------------------------------------------------------------------------
def _capped_screen(tickers, page_size=20):
    """Serves `tickers` (in ascending order) like Finviz: pages of `page_size`
    in either sort direction, and a 403 for any page past row 1000."""
    def respond(columns, offset, query):
        start = int(offset)
        if start > MAX_REACHABLE_ROWS:
            response = requests.Response()
            response.status_code = 403
            raise requests.HTTPError("403 Client Error: Forbidden", response=response)
        ordered = tickers[::-1] if query.get("o", "").startswith("-") else tickers
        page = ordered[start - 1:start - 1 + page_size]
        rows = [[str(start + i), ticker] for i, ticker in enumerate(page)]
        return _grid_page([("row", "No."), ("ticker", "Ticker")], rows, total=len(tickers))
    return respond


def test_screener_reads_rows_past_cap_in_reverse_order(monkeypatch):
    tickers = [f"T{n:04d}" for n in range(1, 1031)]
    log = _serve(monkeypatch, _capped_screen(tickers))

    data = Screener(filters=["earningsdate_thismonth"], sort_order="marketcap").data

    assert [row["Ticker"] for row in data] == tickers
    assert [row["No."] for row in data] == [str(n) for n in range(1, 1031)]
    pages = [(query.get("o"), int(offset)) for offset, _, query in log[1:]]
    assert max(r for o, r in pages if o == "marketcap") == 981
    assert [r for o, r in pages if o == "-marketcap"] == [1, 21]


def test_screener_respects_requested_rows_past_cap(monkeypatch):
    tickers = [f"T{n:04d}" for n in range(1, 1501)]
    _serve(monkeypatch, _capped_screen(tickers))

    data = Screener(sort_order="-price", rows=1200).data

    assert [row["Ticker"] for row in data] == tickers[::-1][:1200]


def test_screener_under_cap_never_reads_reverse_order(monkeypatch):
    tickers = [f"T{n:04d}" for n in range(1, 1001)]
    log = _serve(monkeypatch, _capped_screen(tickers))

    data = Screener(sort_order="marketcap").data

    assert len(data) == 1000
    assert {query.get("o") for _, _, query in log} == {"marketcap"}


def test_screener_warns_when_blank_sort_value_is_unreachable(monkeypatch, caplog):
    """Finviz sorts a blank sort value last in both directions (seen live: ASBH,
    no market cap, row 1030 either way), so it falls outside both windows. The
    shortfall is logged, not silently dropped."""
    ranked = [f"T{n:04d}" for n in range(1, 1030)]
    forward = _capped_screen(ranked + ["BLANK"])
    reverse = _capped_screen(["BLANK"] + ranked)  # reversed by the server: BLANK last again

    def respond(columns, offset, query):
        return (reverse if query.get("o", "").startswith("-") else forward)(columns, offset, query)

    _serve(monkeypatch, respond)

    data = Screener(sort_order="marketcap").data

    assert len(data) == 1029
    assert "BLANK" not in [row["Ticker"] for row in data]
    assert "Fetched 1029 of 1030 rows" in caplog.text
    assert "blank 'marketcap'" in caplog.text


def test_screener_raises_when_screen_exceeds_both_directions(monkeypatch):
    log = _serve(monkeypatch, _capped_screen([f"T{n}" for n in range(2001)]))

    with pytest.raises(RowCapExceeded, match="2001 rows"):
        Screener(sort_order="marketcap")
    assert len(log) == 1  # fails before scraping any page


@pytest.mark.parametrize("order, expected", [
    ("marketcap", "-marketcap"), ("-marketcap", "marketcap"), ("", "-ticker"),
])
def test_reversed_order(order, expected):
    assert _reversed_order(order) == expected
