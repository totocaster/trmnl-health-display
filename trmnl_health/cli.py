from __future__ import annotations

import json
from typing import Optional

import typer

from .data_sources import load_records
from .metrics import summarize
from .payload_builder import build_payload, payload_hash
from .settings import load_settings
from .state import load_last_hash, save_last_hash
from .trmnl_client import TrmnlClient

app = typer.Typer(help="Publish health data to a TRMNL private plugin.")


@app.command()
def publish(
    lookback_days: int = typer.Option(7, help="Rolling window (days) for averages."),
    dry_run: bool = typer.Option(False, help="Print payload without hitting the TRMNL webhook."),
    force: bool = typer.Option(False, help="Bypass hash comparison and push regardless."),
    show_payload: bool = typer.Option(False, help="Print the payload JSON before publishing."),
) -> None:
    """Read tracker data, summarize it, and push to TRMNL."""

    settings = load_settings()
    records = load_records(settings.csv_path)
    summary = summarize(records, settings, lookback_days)
    history_length = min(len(records), 10)
    history = records[-history_length:] if history_length else []
    payload = build_payload(summary, settings, history)
    current_hash = payload_hash(payload)

    last_hash = load_last_hash()
    if not force and last_hash == current_hash:
        typer.secho("No changes detected; skipping publish.", fg=typer.colors.YELLOW)
        return

    if show_payload or dry_run:
        typer.echo(json.dumps(payload, indent=2))

    client = TrmnlClient(settings.plugin_url, settings.device_api_key)
    response = client.publish(payload, dry_run=dry_run)

    if dry_run:
        typer.secho("Dry run complete — payload not sent to TRMNL.", fg=typer.colors.CYAN)
        return

    save_last_hash(current_hash)
    typer.secho("Dashboard updated.", fg=typer.colors.GREEN)
    if response:
        typer.echo(json.dumps(response, indent=2))


@app.command("current-screen")
def current_screen() -> None:
    """Fetch metadata about the most recently rendered TRMNL screen."""

    settings = load_settings()
    client = TrmnlClient(settings.plugin_url, settings.device_api_key)
    try:
        data = client.current_screen()
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(data, indent=2))


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
