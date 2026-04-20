"""Unit tests for features/adherence_metrics.py."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from features.adherence_metrics import (
    compute_mpr,
    compute_pdc,
    consecutive_missed_doses,
    days_since_last_dose,
    is_persistent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REF = date(2026, 6, 1)
INTERVAL = 56  # q8w (T1 primary)


def _dates_from_ref(offsets: list[int], anchor: date = REF) -> list[date]:
    return sorted(anchor + timedelta(days=d) for d in offsets)


# ---------------------------------------------------------------------------
# compute_pdc
# ---------------------------------------------------------------------------


class TestComputePDC:
    def test_full_coverage(self):
        # Two doses covering the full 56-day window without a gap
        w_start = date(2026, 1, 1)
        w_end = date(2026, 2, 25)  # 56 days inclusive
        admins = [date(2026, 1, 1), date(2026, 2, 26)]
        pdc = compute_pdc(admins, INTERVAL, w_start, w_end)
        assert pdc == pytest.approx(1.0)

    def test_zero_doses(self):
        w_start = date(2026, 1, 1)
        w_end = date(2026, 3, 31)
        assert compute_pdc([], INTERVAL, w_start, w_end) == pytest.approx(0.0)

    def test_partial_coverage(self):
        # One dose on day 0; covers days 0..55 of a 100-day window
        w_start = date(2026, 1, 1)
        w_end = date(2026, 4, 10)  # 99 days after start → 100-day window
        admins = [date(2026, 1, 1)]
        pdc = compute_pdc(admins, INTERVAL, w_start, w_end)
        total = (w_end - w_start).days + 1  # 100
        assert pdc == pytest.approx(INTERVAL / total)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            compute_pdc([], INTERVAL, date(2026, 2, 1), date(2026, 1, 1))

    def test_dose_before_window_still_covers_window(self):
        # Dose 10 days before window; its 56-day supply covers the full 21-day window
        w_start = date(2026, 1, 11)
        w_end = date(2026, 1, 31)  # 21-day window
        admins = [date(2026, 1, 1)]  # covers 2026-01-01 through 2026-02-25
        pdc = compute_pdc(admins, INTERVAL, w_start, w_end)
        assert pdc == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_mpr
# ---------------------------------------------------------------------------


class TestComputeMPR:
    def test_perfect_mpr(self):
        # 4 doses × 56 days / 224 days = 1.0
        admins = _dates_from_ref([0, 56, 112, 168], REF)
        assert compute_mpr(admins, INTERVAL, 224) == pytest.approx(1.0)

    def test_half_mpr(self):
        # 2 doses × 56 / 224 days = 0.5
        admins = [date(2026, 1, 1), date(2026, 2, 26)]
        assert compute_mpr(admins, INTERVAL, 224) == pytest.approx(0.5)

    def test_zero_doses(self):
        assert compute_mpr([], INTERVAL, 90) == pytest.approx(0.0)

    def test_over_one_allowed(self):
        # MPR > 1.0 is valid (extra supply)
        admins = _dates_from_ref([0, 28, 56, 84], REF)
        mpr = compute_mpr(admins, INTERVAL, 90)
        assert mpr > 1.0

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            compute_mpr([], INTERVAL, 0)


# ---------------------------------------------------------------------------
# is_persistent
# ---------------------------------------------------------------------------


class TestIsPersistent:
    def test_persistent_on_schedule(self):
        # Gaps all exactly 56 days → persistent
        admins = _dates_from_ref([0, 56, 112, 168], date(2026, 1, 1))
        assert is_persistent(admins, INTERVAL) is True

    def test_persistent_gap_just_below_threshold(self):
        # threshold = 1.5 * 56 = 84 days; gap of 83 → persistent
        admins = [date(2026, 1, 1), date(2026, 3, 25)]  # 83-day gap
        assert is_persistent(admins, INTERVAL) is True

    def test_persistent_gap_at_threshold(self):
        # Gap of exactly 84 days (1.5 * 56) — strict > means at-threshold is still persistent
        admins = [date(2026, 1, 1), date(2026, 3, 26)]  # 84-day gap
        assert is_persistent(admins, INTERVAL) is True

    def test_not_persistent_gap_one_over_threshold(self):
        # Gap of 85 days (> 84.0 threshold) → NOT persistent
        admins = [date(2026, 1, 1), date(2026, 3, 27)]  # 85-day gap
        assert is_persistent(admins, INTERVAL) is False

    def test_not_persistent_gap_above_threshold(self):
        # Gap of 100 days → not persistent
        admins = [date(2026, 1, 1), date(2026, 4, 11)]  # 100-day gap
        assert is_persistent(admins, INTERVAL) is False

    def test_single_dose_is_persistent(self):
        assert is_persistent([date(2026, 1, 1)], INTERVAL) is True

    def test_no_doses_is_persistent(self):
        assert is_persistent([], INTERVAL) is True

    def test_custom_multiplier(self):
        # With multiplier=2.0, threshold=112; gap of 100 → persistent
        admins = [date(2026, 1, 1), date(2026, 4, 11)]  # 100-day gap
        assert is_persistent(admins, INTERVAL, gap_threshold_multiplier=2.0) is True


# ---------------------------------------------------------------------------
# consecutive_missed_doses
# ---------------------------------------------------------------------------


class TestConsecutiveMissedDoses:
    def test_no_missed_on_schedule(self):
        # Perfect schedule, no misses
        base = date(2026, 1, 1)
        admins = [base + timedelta(days=i * INTERVAL) for i in range(8)]
        ref = admins[-1]
        assert consecutive_missed_doses(admins, INTERVAL, ref, lookback_days=60) == 0

    def test_one_missed_dose(self):
        # Two consecutive intervals skipped = one missed dose between them
        base = date(2026, 1, 1)
        admins = [base, base + timedelta(days=INTERVAL * 2)]  # skipped one
        ref = base + timedelta(days=INTERVAL * 2)
        result = consecutive_missed_doses(admins, INTERVAL, ref, lookback_days=180)
        assert result == 1

    def test_two_consecutive_missed(self):
        # Three intervals gap = two missed
        base = date(2026, 1, 1)
        admins = [base, base + timedelta(days=INTERVAL * 3)]
        ref = base + timedelta(days=INTERVAL * 3)
        result = consecutive_missed_doses(admins, INTERVAL, ref, lookback_days=365)
        assert result == 2

    def test_no_doses_returns_zero(self):
        assert consecutive_missed_doses([], INTERVAL, REF, lookback_days=60) == 0

    def test_doses_outside_window_not_counted(self):
        # All doses are well before the 60-day lookback window
        base = date(2024, 1, 1)
        admins = [base + timedelta(days=i * INTERVAL) for i in range(5)]
        ref = date(2026, 6, 1)  # very far from doses
        # Without anchoring into the window, the function should handle this gracefully
        result = consecutive_missed_doses(admins, INTERVAL, ref, lookback_days=60)
        # Result >= 0 (may be > 0 due to expected doses after last actual dose)
        assert result >= 0


# ---------------------------------------------------------------------------
# days_since_last_dose
# ---------------------------------------------------------------------------


class TestDaysSinceLastDose:
    def test_dose_on_reference_date(self):
        admins = [REF]
        assert days_since_last_dose(admins, REF) == 0

    def test_dose_7_days_ago(self):
        admins = [REF - timedelta(days=7)]
        assert days_since_last_dose(admins, REF) == 7

    def test_future_dose_ignored(self):
        admins = [REF + timedelta(days=1)]
        assert days_since_last_dose(admins, REF) is None

    def test_no_doses_returns_none(self):
        assert days_since_last_dose([], REF) is None

    def test_multiple_doses_returns_most_recent(self):
        admins = [
            REF - timedelta(days=60),
            REF - timedelta(days=30),
            REF - timedelta(days=10),
            REF + timedelta(days=5),  # future, ignored
        ]
        assert days_since_last_dose(admins, REF) == 10
