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

    return {
        "rate_per_day": f"{loss_per_day:.2f} kg/day",
        "rate_per_week": f"{loss_per_day * 7:.2f} kg/week",
        "goal_date": goal_date.strftime("%b %d, %Y"),
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

    charts = {
        "window_days": len(history),
        "weight": _line_chart(history, "weight_kg", " kg"),
        "body_fat": _line_chart(history, "body_fat_pct", "%"),
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
