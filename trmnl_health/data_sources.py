from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class DailyRecord:
    date: date
    weight_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    sleep_hours: Optional[float] = None
    body_fat_pct: Optional[float] = None
    recovery_score: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    resting_hr: Optional[float] = None
    strain: Optional[float] = None
    meal_type: Optional[str] = None
    calories_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    notes: str = ""


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:  # pragma: no cover - CSVs can contain stray strings
        return None


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def load_records(csv_path: Path) -> List[DailyRecord]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Tracker CSV not found at {csv_path}")

    records: List[DailyRecord] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_date = (row.get("date") or "").strip()
            if not raw_date:
                continue
            try:
                record_date = date.fromisoformat(raw_date)
            except ValueError:
                continue

            records.append(
                DailyRecord(
                    date=record_date,
                    weight_kg=_to_float(row.get("weight_kg")),
                    waist_cm=_to_float(row.get("waist_cm")),
                    sleep_hours=_to_float(row.get("sleep_hours")),
                    body_fat_pct=_to_float(row.get("body_fat_pct")),
                    recovery_score=_to_float(row.get("recovery_score")),
                    hrv_rmssd=_to_float(row.get("hrv_rmssd")),
                    resting_hr=_to_float(row.get("resting_hr")),
                    strain=_to_float(row.get("strain")),
                    meal_type=_clean_text(row.get("meal_type")),
                    calories_kcal=_to_float(row.get("calories_kcal")),
                    protein_g=_to_float(row.get("protein_g")),
                    carbs_g=_to_float(row.get("carbs_g")),
                    fat_g=_to_float(row.get("fat_g")),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    records.sort(key=lambda item: item.date)
    return records


def take_recent(records: Iterable[DailyRecord], days: int, latest_date: date) -> List[DailyRecord]:
    cutoff = latest_date.toordinal() - (days - 1)
    return [record for record in records if record.date.toordinal() >= cutoff]
