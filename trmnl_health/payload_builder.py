from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from .data_sources import DailyRecord
from .metrics import Summary
from .settings import Settings


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


def _tz(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except Exception:  # pragma: no cover
        return ZoneInfo("UTC")


def _line_chart(history: Sequence[DailyRecord], attr: str, unit: str) -> Optional[Dict[str, Any]]:
    if not history:
        return None

    points: List[tuple[int, float]] = []
    for idx, record in enumerate(history):
        value = getattr(record, attr)
        if value is not None:
            points.append((idx, value))

    if len(points) < 2:
        return None

    values = [value for _, value in points]
    min_val = min(values)
    max_val = max(values)
    if abs(max_val - min_val) < 0.1:
        min_val -= 0.5
        max_val += 0.5

    width = max(len(history) - 1, 1)
    coord_pairs = []
    for idx, value in points:
        x = round((idx / width) * 280, 1)
        norm = (value - min_val) / (max_val - min_val)
        y = round(80 - (norm * 80), 1)
        coord_pairs.append(f"{x},{y}")

    return {
        "points": " ".join(coord_pairs),
        "min": f"{min_val:.1f}{unit}",
        "max": f"{max_val:.1f}{unit}",
    }


def _bar_chart(
    history: Sequence[DailyRecord],
    attr: str,
    *,
    unit: str,
    target: Optional[float] = None,
    calories_factor: Optional[float] = None,
    scale_override: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    values = [getattr(record, attr) for record in history if getattr(record, attr) is not None]
    if not values:
        return None

    scale = scale_override or target or max(values)
    if scale <= 0:
        scale = max(values)

    heights: List[float] = []
    values: List[str] = []
    percents: List[str] = []
    for record in history:
        value = getattr(record, attr)
        if value is None or value <= 0:
            height = 0.0
            display = "—"
        else:
            ratio = min(value / scale, 1.0)
            height = round(ratio * 80, 1)
            display = f"{value:.0f}{unit}"

        percent = None
        if calories_factor and value is not None and value > 0 and record.calories_kcal:
            fraction = min(1.0, (value * calories_factor) / record.calories_kcal)
            percent = f"{fraction * 100:.0f}%"

        heights.append(height)
        values.append(display)
        percents.append(percent or "")

    meta: Dict[str, Any] = {
        "heights": heights,
        "values": values,
        "percents": percents,
    }
    if target:
        meta["target_label"] = f"{target:.0f}{unit}"
    elif scale_override:
        meta["target_label"] = f"max {scale_override:.0f}{unit}"
    else:
        meta["target_label"] = f"max {scale:.0f}{unit}"
    return meta


def _projection(summary: Summary) -> Dict[str, Any]:
    latest_weight = summary.weight.latest_weight
    start_weight = summary.weight.start_weight
    start_date = summary.weight.start_date
    target_weight = summary.weight.target_weight
    days_since_start = summary.weight.days_since_start

    if (
        latest_weight is None
        or start_weight is None
        or start_date is None
        or days_since_start is None
        or days_since_start <= 0
    ):
        return {"message": "Not enough data to estimate trend yet."}

    delta = latest_weight - start_weight
    rate_per_day = delta / days_since_start
    if rate_per_day >= 0:
        return {"message": "Weight is flat or increasing; projection paused."}

    remaining = latest_weight - target_weight
    if remaining <= 0:
        return {"message": "Target already reached. Congrats!"}

    loss_per_day = abs(rate_per_day)
    days_to_goal = remaining / loss_per_day
    base_date = summary.generated_at.date()
    goal_date = base_date + timedelta(days=round(days_to_goal))

    fractions = [0.8, 0.6, 0.4, 0.2]
    milestones = []
    for fraction in fractions:
        weight_value = target_weight + (remaining * fraction)
        milestone_days = round(days_to_goal * fraction)
        milestone_date = base_date + timedelta(days=milestone_days)
        milestones.append(
            {
                "weight": f"{weight_value:.1f} kg",
                "date": milestone_date.strftime("%b %d"),
            }
        )

    return {
        "rate_per_day": f"{loss_per_day:.2f} kg/day",
        "rate_per_week": f"{loss_per_day * 7:.2f} kg/week",
        "goal_date": goal_date.strftime("%b %d, %Y"),
        "milestones": milestones,
    }


def build_payload(summary: Summary, settings: Settings, history: Sequence[DailyRecord]) -> Dict[str, Any]:
    tzinfo = _tz(settings.timezone)
    generated_local = summary.generated_at.astimezone(tzinfo)

    weight_delta_prev = summary.weight_delta_prev
    total_lost = None
    if summary.weight.start_weight is not None and summary.weight.latest_weight is not None:
        total_lost = summary.weight.start_weight - summary.weight.latest_weight

    to_goal = None
    if summary.target_delta is not None:
        to_goal = abs(summary.target_delta)

    summary_block = {
        "current_weight": _fmt_number(summary.weight.latest_weight, " kg"),
        "delta_daily": _fmt_delta(weight_delta_prev, " kg"),
        "total_lost": _fmt_number(total_lost, " kg"),
        "to_goal": _fmt_number(to_goal, " kg"),
    }

    sleep_values = [record.sleep_hours for record in history if record.sleep_hours is not None]
    sleep_scale = max([8.0] + sleep_values) if sleep_values else 8.0

    labels = [record.date.strftime("%m/%d") for record in history]

    charts = {
        "labels": labels,
        "window_days": len(history),
        "weight": _line_chart(history, "weight_kg", " kg"),
        "body_fat": _line_chart(history, "body_fat_pct", "%"),
        "protein": _bar_chart(history, "protein_g", unit="g", target=100, calories_factor=4),
        "carbs": _bar_chart(history, "carbs_g", unit="g", calories_factor=4),
        "fat": _bar_chart(history, "fat_g", unit="g", calories_factor=9),
        "sleep": _bar_chart(history, "sleep_hours", unit="h", scale_override=sleep_scale),
    }

    projection = _projection(summary)

    payload = {
        "generated_at": generated_local.strftime("%Y-%m-%d %H:%M"),
        "summary": summary_block,
        "charts": charts,
        "projection": projection,
    }
    return payload


def payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()
