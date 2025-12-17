from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .metrics import Summary
from .settings import MacroTargets, Settings


@dataclass
class CardRow:
    label: str
    value: str
    hint: Optional[str] = None
    trend: Optional[str] = None


@dataclass
class Card:
    title: str
    rows: List[CardRow]


def _fmt_number(value: Optional[float], unit: str, precision: int = 1) -> str:
    if value is None:
        return "—"
    if precision == 0:
        return f"{value:.0f}{unit}"
    return f"{value:.{precision}f}{unit}"


def _fmt_delta(value: Optional[float], unit: str = "", precision: int = 1) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{precision}f}{unit}"


def _macro_hint(label: str, target: float, unit: str = "g") -> str:
    return f"Goal {target:.0f}{unit}"


def _calorie_hint(targets: MacroTargets) -> str:
    return f"{int(targets.calories_min)}-{int(targets.calories_max)} kcal"


def _compliance_badge(value: Optional[float], low: float, high: float) -> str:
    if value is None:
        return "No data"
    if low <= value <= high:
        return "On target"
    if value < low:
        return "Low"
    return "High"


def _macro_badge(value: Optional[float], target: float, tolerance_percent: float = 0.1) -> str:
    if value is None:
        return "No data"
    delta = value - target
    tolerance = target * tolerance_percent
    if abs(delta) <= tolerance:
        return "On target"
    return "Low" if delta < 0 else "High"


def _tz(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except Exception:  # pragma: no cover - fallback for invalid tz names
        return ZoneInfo("UTC")


def build_payload(summary: Summary, settings: Settings) -> Dict[str, Any]:
    tzinfo = _tz(settings.timezone)
    generated_local = summary.generated_at.astimezone(tzinfo)
    latest_record = summary.latest_record

    header_value = _fmt_number(summary.weight.latest_weight, " kg")
    subtitle = f"{_fmt_delta(summary.target_delta, ' kg')} to target ({settings.target_weight_kg:.1f} kg)"

    progress = None
    if summary.progress_percent is not None:
        progress = {
            "percent": round(summary.progress_percent, 1),
            "label": subtitle,
        }

    weight_card = Card(
        title="Weight",
        rows=[
            CardRow(
                label="Today",
                value=f"{header_value} · {summary.weight.latest_date.strftime('%a %b %d')}",
                hint=f"Meal: {latest_record.meal_type or 'n/a'}",
            ),
            CardRow(
                label="Vs prev",
                value=_fmt_delta(summary.weight_delta_prev, " kg"),
                hint="Since last logged day",
            ),
            CardRow(
                label=f"{summary.weight.lookback_days}d avg",
                value=_fmt_number(summary.weight.lookback_avg_weight, " kg"),
                hint="Rolling average",
            ),
            CardRow(
                label="Waist",
                value=_fmt_number(summary.weight.waist_cm, " cm"),
            ),
        ],
    )

    macro_targets = settings.macro_targets
    macros_card = Card(
        title="Nutrition",
        rows=[
            CardRow(
                label="Calories",
                value=_fmt_number(summary.macro_latest.calories_kcal, " kcal", precision=0),
                hint=_calorie_hint(macro_targets) + f" · {_compliance_badge(summary.macro_latest.calories_kcal, macro_targets.calories_min, macro_targets.calories_max)}",
            ),
            CardRow(
                label="Protein",
                value=_fmt_number(summary.macro_latest.protein_g, " g", precision=0),
                hint=_macro_hint("Protein", macro_targets.protein_g) + f" · {_macro_badge(summary.macro_latest.protein_g, macro_targets.protein_g)}",
            ),
            CardRow(
                label="Carbs",
                value=_fmt_number(summary.macro_latest.carbs_g, " g", precision=0),
                hint=_macro_hint("Carbs", macro_targets.carbs_g) + f" · {_macro_badge(summary.macro_latest.carbs_g, macro_targets.carbs_g)}",
            ),
            CardRow(
                label="Fat",
                value=_fmt_number(summary.macro_latest.fat_g, " g", precision=0),
                hint=_macro_hint("Fat", macro_targets.fat_g) + f" · {_macro_badge(summary.macro_latest.fat_g, macro_targets.fat_g)}",
            ),
            CardRow(
                label="Avg intake",
                value=f"{_fmt_number(summary.macro_average.calories_kcal, ' kcal', precision=0)} · {summary.weight.lookback_days}d",
                hint="Rolling calorie average",
            ),
        ],
    )

    def _trend(latest: Optional[float], avg: Optional[float], unit: str, precision: int = 1) -> str:
        if latest is None or avg is None:
            return "—"
        delta = latest - avg
        if abs(delta) < 0.05:
            return "flat"
        direction = "up" if delta > 0 else "down"
        return f"{direction} {abs(delta):.{precision}f}{unit}"

    whoop_card = Card(
        title="Recovery",
        rows=[
            CardRow(
                label="Sleep",
                value=_fmt_number(summary.whoop_latest.sleep_hours, " h"),
                hint=f"{_trend(summary.whoop_latest.sleep_hours, summary.whoop_average.sleep_hours, ' h')}",
            ),
            CardRow(
                label="Recovery",
                value=_fmt_number(summary.whoop_latest.recovery_score, "%", precision=0),
                hint="Whoop readiness",
            ),
            CardRow(
                label="HRV",
                value=_fmt_number(summary.whoop_latest.hrv_rmssd, " ms", precision=0),
                hint=_trend(summary.whoop_latest.hrv_rmssd, summary.whoop_average.hrv_rmssd, ' ms', precision=0),
            ),
            CardRow(
                label="Resting HR",
                value=_fmt_number(summary.whoop_latest.resting_hr, " bpm", precision=0),
                hint=_trend(summary.whoop_average.resting_hr, summary.whoop_latest.resting_hr, ' bpm', precision=0),
            ),
            CardRow(
                label="Strain",
                value=_fmt_number(summary.whoop_latest.strain, "", precision=1),
                hint=_trend(summary.whoop_latest.strain, summary.whoop_average.strain, '', precision=1),
            ),
        ],
    )

    notes_text = latest_record.notes.strip() or "No notes logged yet."
    lifestyle_card = Card(
        title="Notes & Reminders",
        rows=[
            CardRow(label="Notes", value=notes_text[:200]),
            CardRow(
                label="Goal progress",
                value=f"{summary.progress_percent:.1f}% complete" if summary.progress_percent is not None else "—",
                hint=_fmt_delta(summary.weight_delta_start, " kg") + " since start",
            ),
        ],
    )

    cards = [weight_card, macros_card, whoop_card, lifestyle_card]
    payload_cards = [
        {
            "title": card.title,
            "rows": [
                {key: value for key, value in asdict(row).items() if value}
                for row in card.rows
                if row.value
            ],
        }
        for card in cards
    ]

    payload = {
        "header": header_value,
        "subtitle": subtitle,
        "generated_at": generated_local.strftime("%Y-%m-%d %H:%M"),
        "cards": payload_cards,
        "progress": progress,
    }
    return payload


def payload_hash(payload: Dict[str, Any]) -> str:
    """Deterministic hash of the payload for change detection."""
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()
