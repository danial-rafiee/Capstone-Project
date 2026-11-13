"""Preview/append 60 days of SIMULATED demo readings; existing rows are preserved."""

import argparse
import json
import os
from pathlib import Path
import shlex
from datetime import datetime, timedelta, timezone

from smart_energy.analytics.database import Database
from smart_energy.analytics.demo_history import DemoHistoryGenerator, DemoHistorySeeder
from smart_energy.analytics.period_analytics import to_json_ready
from smart_energy.analytics.time_window import TimeWindow


def load_database_env(path):
    """Read simple KEY=value entries without executing shell code/interpolation.

    Only SMART_ENERGY_DB_* keys are loaded; MYSQL_ROOT_PASSWORD is never used.
    Explicit file values override process values. Quoted values are supported.
    """
    allowed = {"SMART_ENERGY_DB_" + key for key in
               ("HOST", "PORT", "USER", "PASSWORD", "NAME")}
    values = {}
    for number, raw in enumerate(Path(path).read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        if key not in allowed:
            continue
        if not separator:
            raise ValueError(f"Invalid database environment entry on line {number}.")
        try:
            parts = shlex.split(value.strip(), comments=True, posix=True)
        except ValueError:
            raise ValueError(f"Invalid quoting in environment entry on line {number}.") from None
        if len(parts) > 1:
            raise ValueError(f"Quote values containing spaces on line {number}.")
        values[key] = parts[0] if parts else ""
    # Defaults for this project's Docker host connection, not the in-container port.
    defaults = {"SMART_ENERGY_DB_HOST": "127.0.0.1", "SMART_ENERGY_DB_PORT": "3307",
                "SMART_ENERGY_DB_USER": "energy_app", "SMART_ENERGY_DB_NAME": "smart_energy_ha3"}
    for key, value in defaults.items():
        os.environ.setdefault(key, value)
    os.environ.update(values)


def resolve_end(now, explicit_end=None, resolution="hour"):
    """Keep storage in UTC; optionally simulate through the completed minute."""
    if now.utcoffset() is None:
        raise ValueError("Current time must include a timezone.")
    now = now.astimezone(timezone.utc)
    if resolution not in ("hour", "minute"):
        raise ValueError("End resolution must be hour or minute.")
    if explicit_end:
        end = datetime.fromisoformat(explicit_end)
        if end.utcoffset() is None:
            raise ValueError("--end must include a timezone.")
        end = end.astimezone(timezone.utc)
    else:
        end = now.replace(second=0, microsecond=0)
        if resolution == "hour":
            end = end.replace(minute=0)
    if end > now:
        raise ValueError("Future simulation endpoints are not supported.")
    return end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="Explicit .env file; contents/passwords are not printed.")
    parser.add_argument("--days", type=int, default=60, help="Elapsed UTC days; 60..366.")
    parser.add_argument("--end", help="ISO timestamp with timezone; default is latest completed UTC hour.")
    parser.add_argument("--end-resolution", choices=("hour", "minute"), default="hour",
                        help="Default endpoint precision; minute fills the elapsed partial hour. --end overrides it.")
    parser.add_argument("--building-id", type=int, default=1)
    parser.add_argument("--meter-id", type=int, default=101)
    parser.add_argument("--timezone", default="Europe/Berlin", help="Simulation's business calendar.")
    parser.add_argument("--seed", default="group18-demo-v1")
    parser.add_argument("--apply", action="store_true", help="Append missing simulated readings atomically.")
    args = parser.parse_args()
    if not 60 <= args.days <= 366:
        parser.error("--days must be between 60 and 366.")
    now = datetime.now(timezone.utc)
    try:
        end = resolve_end(now, args.end, args.end_resolution)
        if args.env_file:
            load_database_env(args.env_file)
        database = Database()
        report = DemoHistorySeeder(database, DemoHistoryGenerator(args.timezone, args.seed)).run(
            args.building_id, args.meter_id, TimeWindow(end-timedelta(days=args.days), end),
            apply=args.apply)
    except Exception as error:
        # Do not echo database exceptions/configuration, which may expose secrets.
        from smart_energy.analytics.errors import AnalyticsError, AnalyticsErrorHandler
        if isinstance(error, (ValueError, TypeError)):
            parser.error(str(error))
        safe = AnalyticsErrorHandler().handle(error)
        print(json.dumps(safe))
        if isinstance(error, AnalyticsError) and error.code == "database_unavailable":
            print("Check Docker, database environment and credentials locally.")
        return 1
    report["database_target"] = {
        "host": os.environ.get("SMART_ENERGY_DB_HOST", "127.0.0.1"),
        "port": os.environ.get("SMART_ENERGY_DB_PORT", "3306"),
        "database": os.environ.get("SMART_ENERGY_DB_NAME", "smart_energy_ha3"),
    }
    report["end_selection"] = "explicit" if args.end else "completed_" + args.end_resolution
    report["display_note"] = (
        "UTC storage is unchanged. Use *_local fields for display; latest interval start is not its end."
    )
    print(json.dumps(to_json_ready(report), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
