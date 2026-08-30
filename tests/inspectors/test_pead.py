"""
Tests for the generalized abnormal-return windows.

The PEAD math historically supported only the three canonical windows (3/30/60).
These tests lock two things:

  1. The window gate (``PEADInspector._validate_window``) accepts the canonical set
     AND any positive-integer business-day window, while still rejecting genuinely
     invalid input (0, negative, float, bool, None, str).
  2. The generalized expected-return math (``CARMixin._expected_return_for_series``)
     is BIT-IDENTICAL to the original hard-coded 3/30/60 branches, and produces a
     finite value for arbitrary windows.

All pure/in-memory — no network, no Finviz, no Yahoo.
"""
import numpy as np
import pandas as pd
import pytest

from earningspy.inspectors.pead import PEADInspector
from earningspy.inspectors.mixins import CARMixin
from earningspy.common.constants import ALLOWED_WINDOWS


@pytest.fixture
def price_series():
    """A deterministic ~2.5y daily (business-day) price path."""
    idx = pd.bdate_range("2024-01-01", "2026-08-01")
    rng = np.random.RandomState(42)
    returns = rng.normal(0, 0.01, len(idx))
    return pd.Series(100 * np.cumprod(1 + returns), index=idx)


class TestValidateWindow:
    @pytest.mark.parametrize("days", [*ALLOWED_WINDOWS, 1, 45, 90, 250])
    def test_accepts_positive_int_windows(self, days):
        # canonical windows and any positive-integer window are allowed
        PEADInspector._validate_window(days)  # must not raise

    @pytest.mark.parametrize("bad", [0, -5, -1])
    def test_rejects_non_positive(self, bad):
        with pytest.raises(Exception):
            PEADInspector._validate_window(bad)

    @pytest.mark.parametrize("bad", [3.0, 60.0, 45.5])
    def test_rejects_floats_even_when_equal_to_canonical(self, bad):
        # 3.0 == 3 is True, so `3.0 in ALLOWED_WINDOWS` would wrongly pass — the
        # gate must reject floats before they reach pct_change(days).
        with pytest.raises(Exception):
            PEADInspector._validate_window(bad)

    @pytest.mark.parametrize("bad", [True, False, None, "3", "45"])
    def test_rejects_bool_none_and_str(self, bad):
        with pytest.raises(Exception):
            PEADInspector._validate_window(bad)


class TestExpectedReturnGeneralization:
    def test_canonical_windows_are_bit_identical(self, price_series):
        # The generalized helper MUST reproduce the exact original branches so the
        # production 3/30/60 frame does not shift by a single digit.
        m = CARMixin()
        s = price_series

        assert m._expected_return_for_series(s, 3) == pytest.approx(
            s.pct_change(3, fill_method=None).mean(), abs=1e-12
        )
        assert m._expected_return_for_series(s, 30) == pytest.approx(
            s.resample("1ME").ffill().pct_change(fill_method=None).mean(), abs=1e-12
        )
        assert m._expected_return_for_series(s, 60) == pytest.approx(
            s.resample("2ME").ffill().pct_change(fill_method=None).mean(), abs=1e-12
        )

    @pytest.mark.parametrize("days", [1, 5, 45, 90, 120])
    def test_arbitrary_window_is_finite(self, price_series, days):
        # Any positive window yields a finite expected return, computed as the
        # N-business-day point return (the days==3 construction generalized).
        v = CARMixin()._expected_return_for_series(price_series, days)
        assert np.isfinite(v)

    @pytest.mark.parametrize("days", [1, 5, 45, 90])
    def test_arbitrary_window_matches_n_bday_pct_change(self, price_series, days):
        # Non-canonical windows are exactly the daily N-business-day pct_change mean.
        m = CARMixin()
        assert m._expected_return_for_series(price_series, days) == pytest.approx(
            price_series.pct_change(days, fill_method=None).mean(), abs=1e-12
        )
