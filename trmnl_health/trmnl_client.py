from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class TrmnlClient:
    def __init__(self, plugin_url: str, device_api_key: Optional[str] = None, timeout: int = 15) -> None:
        self.plugin_url = plugin_url
        self.device_api_key = device_api_key
        self.timeout = timeout

    def publish(self, merge_variables: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        payload = {"merge_variables": merge_variables}
        if dry_run:
            return {"dry_run": True, "payload": payload}

        response = requests.post(self.plugin_url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return {"status_code": response.status_code, "body": response.text}

    def current_screen(self) -> Dict[str, Any]:
        if not self.device_api_key:
            raise RuntimeError("TRMNL device API key missing. Set TRMNL_DEVICE_API_KEY to use this command.")

        response = requests.get(
            "https://usetrmnl.com/api/current_screen",
            headers={"access-token": self.device_api_key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
