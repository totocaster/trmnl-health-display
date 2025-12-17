from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class MacroTargets:
    """Macro and calorie goals used for compliance calculations."""

    calories_min: float = 800.0
    calories_max: float = 1200.0
    protein_g: float = 100.0
    carbs_g: float = 60.0
    fat_g: float = 40.0


@dataclass(frozen=True)
class Settings:
    csv_path: Path
    plugin_url: str
    macro_targets: MacroTargets
    target_weight_kg: float
    starting_weight_override: Optional[float]
    device_api_key: Optional[str]
    timezone: str


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:  # pragma: no cover - defensive parsing
        raise ValueError(f"Unable to parse float from {value!r}") from exc


def load_settings() -> Settings:
    """Load configuration from environment variables."""

    csv_path = Path(
        os.getenv("TRACKER_CSV_PATH", "~/Notes/totocaster/Attachments/weight-loss-tracker.csv")
    ).expanduser()

    plugin_url = os.getenv("TRMNL_PLUGIN_URL")
    if not plugin_url:
        raise RuntimeError(
            "Missing TRMNL plugin webhook URL. Set TRMNL_PLUGIN_URL in your environment or .env file."
        )

    target_weight = _to_float(os.getenv("TARGET_WEIGHT_KG")) or 70.0
    starting_override = _to_float(os.getenv("STARTING_WEIGHT_KG"))

    macro_targets = MacroTargets(
        calories_min=float(os.getenv("CALORIES_MIN", 800)),
        calories_max=float(os.getenv("CALORIES_MAX", 1200)),
        protein_g=float(os.getenv("PROTEIN_TARGET_G", 100)),
        carbs_g=float(os.getenv("CARB_TARGET_G", 60)),
        fat_g=float(os.getenv("FAT_TARGET_G", 40)),
    )

    timezone = os.getenv("LOCAL_TIMEZONE", "Asia/Tokyo")

    return Settings(
        csv_path=csv_path,
        plugin_url=plugin_url,
        macro_targets=macro_targets,
        target_weight_kg=target_weight,
        starting_weight_override=starting_override,
        device_api_key=os.getenv("TRMNL_DEVICE_API_KEY"),
        timezone=timezone,
    )
