# TRMNL Health Dashboard

Scripts that parse `~/Notes/totocaster/Attachments/weight-loss-tracker.csv`, build a morning snapshot of weight, nutrition, and Whoop metrics, and push the summary to your TRMNL private plugin via webhook.

## Setup

1. **Install dependencies**

   ```bash
   cd ~/Developer/trmnl_health
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** (copy `.env.example` once it exists or create manually):

   ```dotenv
   TRMNL_PLUGIN_URL=https://usetrmnl.com/api/custom_plugins/092b65ec-ffed-4b5f-a042-ee81ae838e8b
   TRMNL_DEVICE_API_KEY=replace-with-your-device-api-key
   TRACKER_CSV_PATH=~/Notes/totocaster/Attachments/weight-loss-tracker.csv
   TARGET_WEIGHT_KG=70
   LOCAL_TIMEZONE=Asia/Tokyo
   ```

   (Device API key is optional; it enables the `current-screen` helper.)

3. **Paste the Liquid markup** from `trmnl_health/templates/dashboard.liquid` into the Private Plugin’s Markup editor in the TRMNL UI.  
   The current template focuses on weight/body-fat trends plus projected goal date, matching the simplified layout shown in the repo.

## Commands

> All commands assume the virtual environment from step 1 is active.

- Publish the latest metrics (default 7-day averages):

  ```bash
  python -m trmnl_health publish
  ```

- Preview the payload without sending it:

  ```bash
  python -m trmnl_health publish --dry-run --show-payload
  ```

- Force a push even if nothing changed since the previous publish:

  ```bash
  python -m trmnl_health publish --force
  ```

- Inspect the most recent screen metadata returned by TRMNL (requires `TRMNL_DEVICE_API_KEY`):

  ```bash
  python -m trmnl_health current-screen
  ```

## How it works

1. `data_sources.py` parses the CSV into strongly typed `DailyRecord` objects.
2. `metrics.py` crunches weight deltas, lookback averages, macro compliance, and Whoop trends.
3. `payload_builder.py` converts the summary into a compact `cards` structure that the Liquid template can iterate over.
4. `trmnl_client.py` POSTs `{"merge_variables": payload}` to the webhook URL. Payload hashes are cached under `~/.cache/trmnl_health/state.json` to avoid redundant pushes (use `--force` to bypass).

The entire payload stays under 2 kB, so it fits the webhook limit. Rate limiting considerations: the CLI should run a handful of times per day (well below the 12/hr cap).

### Automating daily runs (launchd)

1. **Wrapper script** – `scripts/run_dashboard.sh` is already committed. It launches the CLI with a clean `PATH` and writes logs to `~/Library/Logs/trmnl_health.log`. Review the script if your Python path differs.
2. **Install the launch agent (runs at :30 past every hour)**
   ```bash
   cp launchd/com.toto.trmnlhealth.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.toto.trmnlhealth.plist
   ```
   This schedules a run once each hour at minute 30. If the Mac is asleep, launchd will execute the script soon after wake. Logs from launchd go to `~/Library/Logs/trmnl_health.launchd.log`.
3. **Manual control**
   ```bash
   launchctl start com.toto.trmnlhealth   # triggers immediately
   launchctl unload ~/Library/LaunchAgents/com.toto.trmnlhealth.plist
   ```
   Update the plist if paths change, then unload/load again.

## Next steps

- Expand the template or payload with streak counters, fasting windows, or TODO reminders as you gather more tracker data.
