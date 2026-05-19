"""Adherence metrics for specialty-medication regimens.

All functions operate on sorted list[date] (not datetime). Used by:
  - questions/ground_truth/regimen_compliance.py (programmatic ground truth)
  - features/extractors/ (feature extraction arm)

Reference definitions:
  - PDC: Proportion of Days Covered (days supply / observation days)
  - MPR: Medication Possession Ratio (doses supplied × interval / window days)
  - Persistence: no gap > gap_threshold × prescribed interval
"""
from __future__ import annotations

from datetime import date, timedelta


def compute_pdc(
    administrations: list[date],
    prescribed_interval_days: int,
    window_start: date,
    window_end: date,
) -> float:
    """Proportion of Days Covered in [window_start, window_end].

    Each administration covers the patient for prescribed_interval_days days
    starting from the administration date. PDC = covered_days / total_days.
    """
    if window_end < window_start:
        raise ValueError("window_end must be >= window_start")
    if not administrations or prescribed_interval_days <= 0:
        return 0.0

    total_days = (window_end - window_start).days + 1
    covered = 0

    for offset in range(total_days):
        day = window_start + timedelta(days=offset)
        for admin in administrations:
            # Dose covers [admin, admin + interval - 1]
            if admin <= day < admin + timedelta(days=prescribed_interval_days):
                covered += 1
                break

    return covered / total_days


def compute_mpr(
    administrations: list[date],
    prescribed_interval_days: int,
    window_days: int,
) -> float:
    """Medication Possession Ratio: (doses × days_supply) / window_days.

    Returns the ratio of total days of medication supplied to the observation
    window length. May exceed 1.0 if the patient received extra doses.
    """
    if window_days <= 0:
        raise ValueError("window_days must be > 0")
    if not administrations or prescribed_interval_days <= 0:
        return 0.0
    return (len(administrations) * prescribed_interval_days) / window_days


def is_persistent(
    administrations: list[date],
    prescribed_interval_days: int,
    gap_threshold_multiplier: float = 1.5,
) -> bool:
    """True if no consecutive-dose gap exceeds gap_threshold_multiplier × prescribed_interval_days.

    Fewer than 2 administrations → always persistent (no gap to measure).
    """
    if len(administrations) < 2 or prescribed_interval_days <= 0:
        return True
    threshold = gap_threshold_multiplier * prescribed_interval_days
    for i in range(len(administrations) - 1):
        gap = (administrations[i + 1] - administrations[i]).days
        if gap > threshold:
            return False
    return True


def consecutive_missed_doses(
    administrations: list[date],
    prescribed_interval_days: int,
    reference_date: date,
    lookback_days: int = 60,
) -> int:
    """Max consecutive missed doses in (reference_date - lookback_days, reference_date].

    A "missed dose" is an expected dose slot (spaced prescribed_interval_days apart,
    anchored at the most recent administration before the lookback window) that had
    no actual administration within half an interval of the expected date.

    Returns 0 if there are no administrations or prescribed_interval_days <= 0.
    """
    if not administrations or prescribed_interval_days <= 0:
        return 0

    window_start = reference_date - timedelta(days=lookback_days)
    tolerance = max(1, prescribed_interval_days // 4)

    # All doses up to reference_date as context
    history = [d for d in administrations if d <= reference_date]
    if not history:
        return 0

    # Anchor: last dose at or before window_start; fall back to first dose if none
    anchor_candidates = [d for d in history if d <= window_start]
    anchor = anchor_candidates[-1] if anchor_candidates else history[0]

    # Walk expected dose slots from anchor+interval through reference_date
    expected = anchor + timedelta(days=prescribed_interval_days)
    admin_set = set(history)

    max_streak = 0
    current_streak = 0

    while expected <= reference_date:
        if expected >= window_start:
            # Check if any actual dose falls within ±tolerance of the expected date
            hit = any(abs((expected - d).days) <= tolerance for d in admin_set)
            if not hit:
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0
        expected += timedelta(days=prescribed_interval_days)

    return max_streak


def days_since_last_dose(
    administrations: list[date],
    reference_date: date,
) -> int | None:
    """Days between reference_date and the most recent administration on or before it.

    Returns None if there are no administrations on or before reference_date.
    """
    past = [d for d in administrations if d <= reference_date]
    if not past:
        return None
    return (reference_date - past[-1]).days
