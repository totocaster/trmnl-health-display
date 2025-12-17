from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional, Sequence

from .data_sources import DailyRecord, take_recent
from .settings import MacroTargets, Settings


def _mean(values: Sequence[Optional[float]]) -> Optional[float]:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def _delta(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None:
        return None
    return current - previous


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


@dataclass(frozen=True)
class MacroSnapshot:
    calories_kcal: Optional[float]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]


@dataclass(frozen=True)
class WhoopSnapshot:
    sleep_hours: Optional[float]
    recovery_score: Optional[float]
    hrv_rmssd: Optional[float]
    resting_hr: Optional[float]
    strain: Optional[float]


@dataclass(frozen=True)
class WeightSnapshot:
    latest_weight: Optional[float]
    previous_weight: Optional[float]
    start_weight: Optional[float]
    target_weight: float
    waist_cm: Optional[float]
    lookback_avg_weight: Optional[float]
    lookback_days: int
    latest_date: date


@dataclass(frozen=True)
class Summary:
    latest_record: DailyRecord
    weight: WeightSnapshot
    macro_latest: MacroSnapshot
    macro_average: MacroSnapshot
    whoop_latest: WhoopSnapshot
    whoop_average: WhoopSnapshot
    weight_delta_prev: Optional[float]
    weight_delta_start: Optional[float]
    target_delta: Optional[float]
    progress_percent: Optional[float]
    generated_at: datetime


def _find_previous(records: Sequence[DailyRecord], idx: int) -> Optional[DailyRecord]:
    for offset in range(idx - 1, -1, -1):
        candidate = records[offset]
        if candidate.weight_kg is not None:
            return candidate
    return None


def _first_weight(records: Sequence[DailyRecord]) -> Optional[float]:
    for record in records:
        if record.weight_kg is not None:
            return record.weight_kg
    return None


def summarize(records: List[DailyRecord], settings: Settings, lookback_days: int) -> Summary:
    if not records:
        raise ValueError("No tracker records found.")

    latest = records[-1]
    previous = _find_previous(records, len(records) - 1)

    start_weight = settings.starting_weight_override or _first_weight(records)
    lookback_days = max(lookback_days, 1)
    recent_records = take_recent(records, lookback_days, latest.date)

    weight_snapshot = WeightSnapshot(
        latest_weight=latest.weight_kg,
        previous_weight=previous.weight_kg if previous else None,
        start_weight=start_weight,
        target_weight=settings.target_weight_kg,
        waist_cm=latest.waist_cm,
        lookback_avg_weight=_mean([record.weight_kg for record in recent_records]),
        lookback_days=lookback_days,
        latest_date=latest.date,
    )

    macro_latest = MacroSnapshot(
        calories_kcal=latest.calories_kcal,
        protein_g=latest.protein_g,
        carbs_g=latest.carbs_g,
        fat_g=latest.fat_g,
    )

    macro_average = MacroSnapshot(
        calories_kcal=_mean([record.calories_kcal for record in recent_records]),
        protein_g=_mean([record.protein_g for record in recent_records]),
        carbs_g=_mean([record.carbs_g for record in recent_records]),
        fat_g=_mean([record.fat_g for record in recent_records]),
    )

    whoop_latest = WhoopSnapshot(
        sleep_hours=latest.sleep_hours,
        recovery_score=latest.recovery_score,
        hrv_rmssd=latest.hrv_rmssd,
        resting_hr=latest.resting_hr,
        strain=latest.strain,
    )

    whoop_average = WhoopSnapshot(
        sleep_hours=_mean([record.sleep_hours for record in recent_records]),
        recovery_score=_mean([record.recovery_score for record in recent_records]),
        hrv_rmssd=_mean([record.hrv_rmssd for record in recent_records]),
        resting_hr=_mean([record.resting_hr for record in recent_records]),
        strain=_mean([record.strain for record in recent_records]),
    )

    weight_delta_prev = _delta(weight_snapshot.latest_weight, weight_snapshot.previous_weight)
    weight_delta_start = _delta(weight_snapshot.latest_weight, weight_snapshot.start_weight)
    target_delta = _delta(weight_snapshot.latest_weight, weight_snapshot.target_weight)

    progress_percent: Optional[float] = None
    if (
        weight_snapshot.start_weight is not None
        and weight_snapshot.latest_weight is not None
        and weight_snapshot.start_weight != weight_snapshot.target_weight
    ):
        total_change = weight_snapshot.start_weight - weight_snapshot.target_weight
        achieved = weight_snapshot.start_weight - weight_snapshot.latest_weight
        if total_change != 0:
            progress_percent = _clamp((achieved / total_change) * 100, 0.0, 100.0)

    generated_at = datetime.now(timezone.utc)

    return Summary(
        latest_record=latest,
        weight=weight_snapshot,
        macro_latest=macro_latest,
        macro_average=macro_average,
        whoop_latest=whoop_latest,
        whoop_average=whoop_average,
        weight_delta_prev=weight_delta_prev,
        weight_delta_start=weight_delta_start,
        target_delta=target_delta,
        progress_percent=progress_percent,
        generated_at=generated_at,
    )
