"""
Validates the Finviz field specification (``field_spec.py``) against the actual
fetch configuration in ``constants.py``, and against the generated documentation
(``FINVIZ_FIELDS.md``). This is the guardrail that keeps the field dictionary
honest: if the fetched columns, their Finviz codes, or the ordering ever drift,
these tests fail loudly.
"""
import re
from pathlib import Path

import pytest

from earningspy.generators.finviz import field_spec
from earningspy.generators.finviz.field_spec import (
    FIELD_SPECS,
    BY_NAME,
    UNMAPPED_FINVIZ_CODES,
    comparable_to,
    to_markdown,
    Kind,
)
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS_NEW,
    CUSTOM_TABLE_FIELDS_ON_URL,
)
from tests.utils.fixtures import screener_mock_data

FINVIZ_DIR = Path(field_spec.__file__).parent
DOC_PATH = FINVIZ_DIR / "FINVIZ_FIELDS.md"

# Kinds whose raw Finviz string is expected to carry a trailing '%'.
PERCENT_KINDS = {
    Kind.SIMPLE_GROWTH, Kind.CAGR, Kind.YOY, Kind.SURPRISE,
    Kind.PCT, Kind.PCT_RETURN, Kind.PCT_FROM_LEVEL,
}
# Kinds whose raw Finviz string is a magnitude with an optional K/M/B/T suffix
# (a dollar or count level) and MUST NOT carry a '%'.
LEVEL_KINDS = {
    Kind.LEVEL_USD, Kind.LEVEL_USD_SHARE, Kind.LEVEL_COUNT,
}
_MONEY_SUFFIX = re.compile(r"^-?\d[\d,]*\.?\d*[KMBT]?$")

# The mock fixture is an older Finviz snapshot that predates a few columns we now
# request. These are legitimately absent (or all-null) in the fixture, so the
# format assertions skip them rather than fail. Kept explicit so a NEW gap (a
# field that should be present but isn't) still fails loudly.
FIELDS_ABSENT_IN_FIXTURE = {
    "Enterprise Value", "EV/EBITDA", "EV/Sales",  # added after fixture captured
    "Return% 1Y",                                 # present but all-null in fixture
    "Forward P/E",  # fixture predates the 2026-04-26 "Fwd P/E"->"Forward P/E" rename
}


def _non_null_raw_values(field_name):
    """All non-'-' raw string values for a field across the mock payload."""
    vals = []
    for row in screener_mock_data():
        v = row.get(field_name)
        if v not in (None, "", "-"):
            vals.append(v)
    return vals


def _url_codes():
    """The ordered list of integer column ids from CUSTOM_TABLE_FIELDS_ON_URL."""
    raw = CUSTOM_TABLE_FIELDS_ON_URL.replace("&c=", "").replace("\n", "").replace(" ", "")
    return [int(c) for c in raw.split(",") if c != ""]


# ---------------------------------------------------------------------------
# Spec <-> fetched field names
# ---------------------------------------------------------------------------
def test_spec_covers_exactly_the_fetched_fields():
    """Every fetched field is specced, and every specced field is fetched
    (no orphans in either direction), in the same order."""
    spec_names = [fs.name for fs in FIELD_SPECS]
    assert spec_names == CUSTOM_TABLE_ALL_FIELDS_NEW, (
        "field_spec.FIELD_SPECS must list exactly CUSTOM_TABLE_ALL_FIELDS_NEW, "
        "in the same order.\n"
        f"missing from spec: {set(CUSTOM_TABLE_ALL_FIELDS_NEW) - set(spec_names)}\n"
        f"extra in spec:     {set(spec_names) - set(CUSTOM_TABLE_ALL_FIELDS_NEW)}"
    )


def test_no_duplicate_field_names():
    names = [fs.name for fs in FIELD_SPECS]
    assert len(names) == len(set(names)), "duplicate field name in FIELD_SPECS"


def test_every_field_has_a_client_description():
    """The catalog is client-facing: every fetched field must carry a non-empty,
    plain-language description."""
    missing = [fs.name for fs in FIELD_SPECS if not fs.description.strip()]
    assert not missing, f"fields missing a client description: {missing}"


def test_descriptions_map_has_no_orphans():
    """Every entry in DESCRIPTIONS must correspond to a real fetched field, so the
    map cannot drift out of sync with the spec."""
    from earningspy.generators.finviz.field_spec import DESCRIPTIONS
    orphans = set(DESCRIPTIONS) - {fs.name for fs in FIELD_SPECS}
    assert not orphans, f"DESCRIPTIONS has entries for unknown fields: {orphans}"


# ---------------------------------------------------------------------------
# Update cadence (which fields are live vs frozen)
# ---------------------------------------------------------------------------
def test_every_field_has_a_cadence():
    from earningspy.generators.finviz.field_spec import Cadence
    valid = {v for k, v in vars(Cadence).items() if not k.startswith("_")}
    missing = [fs.name for fs in FIELD_SPECS if fs.cadence is None]
    assert not missing, f"fields missing an update cadence: {missing}"
    bad = [(fs.name, fs.cadence) for fs in FIELD_SPECS if fs.cadence not in valid]
    assert not bad, f"fields with an invalid cadence value: {bad}"


def test_every_field_has_cadence_confidence():
    bad = [fs.name for fs in FIELD_SPECS
           if fs.cadence_confidence not in ("high", "med")]
    assert not bad, f"fields with missing/invalid cadence confidence: {bad}"


def test_cadence_map_has_no_orphans():
    from earningspy.generators.finviz.field_spec import CADENCE
    orphans = set(CADENCE) - {fs.name for fs in FIELD_SPECS}
    assert not orphans, f"CADENCE has entries for unknown fields: {orphans}"


def test_frozen_set_is_report_frozen_and_high_confidence():
    """The 'frozen at earnings' set the catalog owner wants to rely on must be
    classified REPORT_FROZEN with high confidence. Locks in the specific fields
    so a future edit can't silently reclassify a frozen fundamental as live."""
    from earningspy.generators.finviz.field_spec import Cadence
    expected_frozen = {
        "EPS", "EPS Past 5Y", "EPS Q/Q", "EPS YoY TTM", "EPS Surprise",
        "Sales", "Sales Past 5Y", "Sales Q/Q", "Sales YoY TTM", "Income",
        "Revenue Surprise", "ROA", "ROE", "ROIC", "Curr R", "Quick R",
        "LTDebt/Eq", "Debt/Eq", "Gross M", "Oper M", "Profit M",
        "Book/sh", "Cash/sh", "Payout Ratio",
    }
    for name in expected_frozen:
        fs = BY_NAME[name]
        assert fs.cadence == Cadence.REPORT_FROZEN, (
            f"{name} expected report_frozen, got {fs.cadence}"
        )
        assert fs.cadence_confidence == "high", (
            f"{name} is report_frozen but not high confidence"
        )
        assert fs.is_frozen


def test_price_bearing_ratios_are_not_report_frozen():
    """Guard the subtle trap: ratios that contain live price must NOT be labeled
    frozen, because they drift every day even though the fundamental is frozen."""
    from earningspy.generators.finviz.field_spec import Cadence
    for name in ("P/E", "P/S", "P/B", "P/FCF", "EV/EBITDA", "Dividend"):
        assert BY_NAME[name].cadence == Cadence.PRICE_OVER_FUNDAMENTAL, name
        assert not BY_NAME[name].is_frozen


def test_periodic_filing_fields_not_frozen_or_daily():
    """Ownership/short-interest fields follow their own regulatory cadence, so
    they are neither report_frozen nor market_daily."""
    from earningspy.generators.finviz.field_spec import Cadence
    for name in ("Inst Own", "Inst Trans", "Insider Own", "Insider Trans",
                 "Short Float", "Short Ratio", "Short Interest"):
        assert BY_NAME[name].cadence == Cadence.FILING_PERIODIC, name


# ---------------------------------------------------------------------------
# Serving decision (snapshot vs on-demand) for the pre-earnings model
# ---------------------------------------------------------------------------
def test_every_field_has_a_serving_decision():
    from earningspy.generators.finviz.field_spec import Serving
    valid = {v for k, v in vars(Serving).items() if not k.startswith("_")}
    bad = [(fs.name, fs.serving) for fs in FIELD_SPECS if fs.serving not in valid]
    assert not bad, f"fields with missing/invalid serving decision: {bad}"


def test_serving_is_consistent_with_cadence():
    """Serving is derived from cadence, so it must equal serving_for(cadence) for
    every field — the two axes can never contradict."""
    from earningspy.generators.finviz.field_spec import serving_for
    for fs in FIELD_SPECS:
        assert fs.serving == serving_for(fs.cadence), (
            f"{fs.name}: serving {fs.serving} inconsistent with cadence {fs.cadence}"
        )


def test_frozen_fundamentals_are_served_from_snapshot():
    """The whole point: filing-reported fundamentals must be serve_from_snapshot
    (a 1-5 day pre-earnings lag is negligible for them)."""
    from earningspy.generators.finviz.field_spec import Serving
    for name in ("EPS", "Sales", "Income", "ROE", "ROIC", "Gross M", "Oper M",
                 "Profit M", "Debt/Eq", "Book/sh", "EPS Surprise"):
        assert BY_NAME[name].serving == Serving.FROM_SNAPSHOT, name


def test_price_bearing_ratios_are_stale_recompute():
    """Price-bearing ratios must be flagged stale_recompute, NOT plain snapshot:
    the fundamental is fine but the embedded price goes stale within days."""
    from earningspy.generators.finviz.field_spec import Serving
    for name in ("P/E", "P/S", "P/B", "P/FCF", "EV/EBITDA", "EV/Sales", "Dividend"):
        assert BY_NAME[name].serving == Serving.STALE_RECOMPUTE, name


def test_pure_market_fields_are_fetch_on_demand():
    """Pure price/technical fields are noise from a days-old snapshot -> on demand."""
    from earningspy.generators.finviz.field_spec import Serving
    for name in ("Price", "Change", "RSI", "SMA50", "52W High", "ATR",
                 "Perf Week", "Volume", "Market Cap"):
        assert BY_NAME[name].serving == Serving.ON_DEMAND, name


def test_ownership_and_short_are_served_from_snapshot():
    """Ownership/short update on multi-week regulatory cadences, so a 1-5 day-old
    snapshot is essentially always current -> serve from snapshot."""
    from earningspy.generators.finviz.field_spec import Serving
    for name in ("Inst Own", "Insider Own", "Short Float", "Short Interest"):
        assert BY_NAME[name].serving == Serving.FROM_SNAPSHOT, name


# ---------------------------------------------------------------------------
# Spec <-> Finviz URL codes  (the mapping the user cares about)
# ---------------------------------------------------------------------------
def test_finviz_codes_match_url_positionally():
    """Each field's finviz_code must equal the URL code at the same position.

    CUSTOM_TABLE_FIELDS_ON_URL drives which columns Finviz returns and in what
    order; CUSTOM_TABLE_ALL_FIELDS_NEW names them positionally. The spec records
    the code per field, so it must line up 1:1 with the URL codes.
    """
    codes = _url_codes()
    named = codes[: len(FIELD_SPECS)]
    for i, fs in enumerate(FIELD_SPECS):
        assert fs.finviz_code == named[i], (
            f"finviz_code mismatch at position {i} for '{fs.name}': "
            f"spec says {fs.finviz_code}, URL says {named[i]}"
        )


def test_trailing_unmapped_codes_are_declared():
    """Any URL code beyond the named fields must be listed in
    UNMAPPED_FINVIZ_CODES so the 'more codes than names' offset stays intentional
    and documented, never a silent drift."""
    codes = _url_codes()
    trailing = set(codes[len(FIELD_SPECS):])
    assert trailing == UNMAPPED_FINVIZ_CODES, (
        f"Trailing URL codes {trailing} do not match declared "
        f"UNMAPPED_FINVIZ_CODES {UNMAPPED_FINVIZ_CODES}. If Finviz codes changed, "
        f"update field_spec.py (and trim the URL if a code is truly unused)."
    )


def test_no_finviz_code_collisions():
    codes = [fs.finviz_code for fs in FIELD_SPECS if fs.finviz_code is not None]
    assert len(codes) == len(set(codes)), "two fields claim the same Finviz code"


# ---------------------------------------------------------------------------
# Comparability groups (equal-in-magnitude fields)
# ---------------------------------------------------------------------------
def test_comparable_groups_are_symmetric():
    """If A is comparable to B, then B must be comparable to A."""
    for fs in FIELD_SPECS:
        for other in comparable_to(fs.name):
            assert fs.name in comparable_to(other), (
                f"comparability not symmetric: {fs.name} -> {other} "
                f"but not {other} -> {fs.name}"
            )


def test_comparable_fields_share_unit_and_kind():
    """Fields declared comparable must share the same unit and kind — otherwise
    they are not actually 'equal in magnitude'."""
    for fs in FIELD_SPECS:
        for other_name in comparable_to(fs.name):
            other = BY_NAME[other_name]
            assert (fs.unit, fs.kind) == (other.unit, other.kind), (
                f"'{fs.name}' ({fs.kind}/{fs.unit}) declared comparable to "
                f"'{other_name}' ({other.kind}/{other.unit}) but units/kinds differ"
            )


def test_1y_growth_not_comparable_to_5y_cagr():
    """Guard the specific trap: single-year EPS growth must never share a
    comparability group with the 5-year CAGR fields."""
    assert "EPS Past 5Y" not in comparable_to("EPS This Y")
    assert "EPS Next 5Y" not in comparable_to("EPS Next Y")


# ---------------------------------------------------------------------------
# Known semantic assertions (lock in the researched facts)
# ---------------------------------------------------------------------------
def test_qq_fields_are_marked_yoy():
    """'Q/Q' fields are actually year-over-year per Finviz; the spec must reflect
    that, not sequential quarter-over-quarter."""
    assert BY_NAME["EPS Q/Q"].kind == Kind.YOY
    assert BY_NAME["Sales Q/Q"].kind == Kind.YOY


def test_dollar_eps_fields_are_levels_growth_fields_are_percent():
    assert BY_NAME["EPS"].kind == Kind.LEVEL_USD_SHARE
    assert BY_NAME["EPS next Q"].kind == Kind.LEVEL_USD_SHARE
    assert BY_NAME["EPS This Y"].kind == Kind.SIMPLE_GROWTH
    assert BY_NAME["EPS Next Y"].kind == Kind.SIMPLE_GROWTH


def test_five_year_growth_is_cagr():
    for name in ("EPS Past 5Y", "EPS Next 5Y", "Sales Past 5Y"):
        assert BY_NAME[name].kind == Kind.CAGR


def test_roic_note_flags_net_income_basis():
    assert "Net Income" in BY_NAME["ROIC"].note


def test_low_confidence_fields_are_not_marked_finviz_sourced():
    """Anything we could not confirm on Finviz's help page must not claim
    'finviz' as its source."""
    for fs in FIELD_SPECS:
        if fs.confidence == "verify":
            assert fs.source in ("cross-ref", "convention"), (
                f"'{fs.name}' is confidence=verify but claims source={fs.source}"
            )


def test_fixture_sourced_fields_are_high_confidence():
    """A field whose semantic type was confirmed against the live payload must be
    high confidence — and the corresponding fixture assertion below must exist to
    back that claim up."""
    fixture_backed = {"EPS next Q", "EPS Surprise", "Revenue Surprise",
                      "EPS YoY TTM", "Sales YoY TTM", "Income"}
    for fs in FIELD_SPECS:
        if fs.source == "fixture":
            assert fs.confidence == "high", (
                f"'{fs.name}' is source=fixture but not high confidence"
            )
            assert fs.name in fixture_backed, (
                f"'{fs.name}' claims source=fixture but has no dedicated fixture "
                f"assertion; add one or change its source"
            )


# ---------------------------------------------------------------------------
# Generated doc stays in sync
# ---------------------------------------------------------------------------
def test_generated_doc_exists():
    assert DOC_PATH.exists(), (
        f"{DOC_PATH.name} is missing. Generate it with: "
        f"python -m earningspy.generators.finviz.field_spec > {DOC_PATH}"
    )


def test_generated_doc_is_up_to_date():
    """FINVIZ_FIELDS.md must match what the spec generates right now, so the
    shipped doc never lies about the spec."""
    current = DOC_PATH.read_text()
    expected = to_markdown()
    assert current.strip() == expected.strip(), (
        "FINVIZ_FIELDS.md is stale. Regenerate with: "
        "python -m earningspy.generators.finviz.field_spec > "
        "earningspy/generators/finviz/FINVIZ_FIELDS.md"
    )


def test_doc_lists_every_field_and_its_code():
    doc = DOC_PATH.read_text()
    for fs in FIELD_SPECS:
        assert f"`{fs.name}`" in doc, f"{fs.name} missing from doc"
        if fs.finviz_code is not None:
            # code and name appear on the same table row
            row = next((ln for ln in doc.splitlines()
                        if f"`{fs.name}`" in ln), "")
            assert re.search(rf"\|\s*{fs.finviz_code}\s*\|", row), (
                f"Finviz code {fs.finviz_code} not shown for {fs.name}"
            )


# ---------------------------------------------------------------------------
# Live-payload validation (against tests/utils/screener_mock.json, a real
# 100-row Finviz screener response). This is what confirms the semantic KIND of
# each field empirically: a percentage field's raw value ends in '%', a money
# level ends in an optional K/M/B/T, a dollar/ratio level is a bare number.
# ---------------------------------------------------------------------------
def test_mock_payload_has_all_specced_fields():
    """Sanity: the fixture carries every specced field except the ones we know
    were added after the fixture was captured (so the format assertions below
    are exercised, not silently skipped)."""
    sample = screener_mock_data()[0]
    missing = [fs.name for fs in FIELD_SPECS
               if fs.name not in sample and fs.name not in FIELDS_ABSENT_IN_FIXTURE]
    assert not missing, f"mock payload missing specced fields: {missing}"


@pytest.mark.parametrize(
    "field_name",
    [fs.name for fs in FIELD_SPECS if fs.kind in PERCENT_KINDS],
)
def test_percent_fields_are_formatted_as_percent(field_name):
    """Every value of a percent-kind field must end in '%' in the raw payload."""
    values = _non_null_raw_values(field_name)
    if not values:
        pytest.skip(f"{field_name} has no values in fixture "
                    f"(expected: {field_name in FIELDS_ABSENT_IN_FIXTURE})")
    bad = [v for v in values if not str(v).endswith("%")]
    assert not bad, (
        f"{field_name} is kind={BY_NAME[field_name].kind} (percent) but has "
        f"non-'%' raw values, e.g. {bad[:3]}"
    )


@pytest.mark.parametrize(
    "field_name",
    [fs.name for fs in FIELD_SPECS
     if fs.kind in LEVEL_KINDS and fs.finviz_code is not None],
)
def test_level_fields_are_not_percent(field_name):
    """A dollar/count level must be a magnitude (optional K/M/B/T suffix) and
    never a percentage."""
    values = _non_null_raw_values(field_name)
    if not values:
        pytest.skip(f"{field_name} has no values in fixture "
                    f"(expected: {field_name in FIELDS_ABSENT_IN_FIXTURE})")
    pct = [v for v in values if str(v).endswith("%")]
    assert not pct, (
        f"{field_name} is kind={BY_NAME[field_name].kind} (level) but has "
        f"'%'-formatted raw values, e.g. {pct[:3]}"
    )
    malformed = [v for v in values if not _MONEY_SUFFIX.match(str(v))]
    assert not malformed, (
        f"{field_name} level has values not matching a magnitude pattern, "
        f"e.g. {malformed[:3]}"
    )


def test_eps_next_q_is_a_dollar_level_not_a_percent():
    """Locks in the researched fact that 'EPS next Q' is a $ estimate, not a
    growth %. (This was previously only cross-referenced; the fixture confirms
    it directly.)"""
    values = _non_null_raw_values("EPS next Q")
    assert values, "fixture has no EPS next Q values"
    assert all(not str(v).endswith("%") for v in values), (
        f"EPS next Q looks like a percentage in the payload: "
        f"{[v for v in values if str(v).endswith('%')][:3]}"
    )
    # bare decimal / integer dollar figure
    assert all(_MONEY_SUFFIX.match(str(v)) for v in values)


def test_surprise_and_yoy_ttm_fields_are_percent_in_payload():
    """The fields that were only 'convention'/'cross-ref' confidence for their
    percent nature are confirmed as '%'-formatted by the live fixture."""
    for name in ("EPS Surprise", "Revenue Surprise", "EPS YoY TTM", "Sales YoY TTM"):
        values = _non_null_raw_values(name)
        assert values, f"fixture has no {name} values"
        assert all(str(v).endswith("%") for v in values), (
            f"{name} expected all '%'-formatted; offenders: "
            f"{[v for v in values if not str(v).endswith('%')][:3]}"
        )


def test_income_is_money_level_in_payload():
    """'Income' aggregation was assumed; confirm it is at least a money-level
    magnitude (K/M/B/T), not a percentage or ratio."""
    values = _non_null_raw_values("Income")
    assert values, "fixture has no Income values"
    assert all(not str(v).endswith("%") for v in values)
    assert all(_MONEY_SUFFIX.match(str(v)) for v in values), (
        f"Income has non-magnitude values: "
        f"{[v for v in values if not _MONEY_SUFFIX.match(str(v))][:3]}"
    )
