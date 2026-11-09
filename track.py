#!/usr/bin/env python3
"""Append one row of the Cal Poly Pomona BRIC 3rd-floor headcount to data.csv.

Standard library only. The ASI "Live Facility Counts" widget is an empty page
that loads its numbers from a JSON API in the browser; this script reads that
API directly. The 3rd floor is reported as four zones (South, Northeast,
North, West) - we log their total plus each zone's count.
"""

import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

ACCOUNT_KEY = "79e7d1a1-a9f2-400c-afea-27bd152a15da"
API_URL = ("https://goboardapi.azurewebsites.net/api/FacilityCount/"
           "GetCountsByAccount?AccountAPIKey=" + ACCOUNT_KEY)
FLOOR_PREFIX = "3rd floor"                    # matched case-insensitively
ZONES = ["south", "northeast", "north", "west"]

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = os.path.join(HERE, "data.csv")
DEBUG_FILE = os.path.join(HERE, "latest.html")  # raw response, kept only after a failed run

FIELDS = ["time", "weekday", "hour", "count", "capacity", "percent", "status",
          "source_last_updated"] + ZONES + ["note"]


def la_now():
    """Current time in America/Los_Angeles."""
    utc = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return utc.astimezone(ZoneInfo("America/Los_Angeles"))
    except Exception:
        # Windows without the tzdata package: apply US DST rules by hand.
        def nth_sunday(month, n):
            d = datetime(utc.year, month, 1, tzinfo=timezone.utc)
            return d + timedelta(days=(6 - d.weekday()) % 7, weeks=n - 1)
        dst_start = nth_sunday(3, 2).replace(hour=10)  # 2:00 PST
        dst_end = nth_sunday(11, 1).replace(hour=9)    # 2:00 PDT
        offset = -7 if dst_start <= utc < dst_end else -8
        return utc.astimezone(timezone(timedelta(hours=offset)))


def fetch(attempts=3):
    """Return the raw API response body as text."""
    req = urllib.request.Request(API_URL, headers={
        "User-Agent": "bric-tracker/1.0 (personal gym-crowd logger)",
        "Accept": "application/json",
    })
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(5 * (i + 1))


def zone_key(name):
    """'3rd Floor - Northeast Area' -> 'northeast'."""
    tail = name.split("-", 1)[-1].strip().lower()
    return tail[:-5].strip() if tail.endswith(" area") else tail


def parse(raw):
    """Pull the 3rd-floor totals out of the API response. Raises ValueError if absent."""
    data = json.loads(raw)
    zones = [loc for loc in data
             if str(loc.get("LocationName", "")).strip().lower().startswith(FLOOR_PREFIX)]
    if not zones:
        raise ValueError("no location named '3rd Floor ...' in response")

    count = sum(int(z.get("LastCount") or 0) for z in zones)
    capacity = sum(int(z.get("TotalCapacity") or 0) for z in zones)
    all_closed = all(z.get("IsClosed") for z in zones)
    # Timestamps are local Pacific time without an offset, e.g. 2026-11-08T22:12:52.797
    updated = max(str(z.get("LastUpdatedDateAndTime") or "") for z in zones)

    row = {
        "count": count,
        "capacity": capacity,
        "percent": round(count / capacity * 100, 1) if capacity else "",
        "status": "closed" if all_closed else "open",
        "source_last_updated": updated[:16].replace("T", " "),
        "note": "",
    }
    extra = []
    for z in zones:
        key = zone_key(z["LocationName"])
        if key in ZONES:
            row[key] = z.get("LastCount")
        else:
            extra.append(z["LocationName"].strip())
    if extra:
        row["note"] = "unlisted 3rd-floor zone(s) included in total: " + "; ".join(extra)
    return row, zones


def append_row(row):
    new_file = not os.path.exists(DATA_CSV) or os.path.getsize(DATA_CSV) == 0
    with open(DATA_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        if new_file:
            w.writeheader()
        w.writerow(row)


def main():
    now = la_now()
    row = {"time": now.strftime("%Y-%m-%d %H:%M"),
           "weekday": now.strftime("%A"),
           "hour": now.hour}
    raw = None
    try:
        raw = fetch()
        parsed, zones = parse(raw)
        row.update(parsed)
        if os.path.exists(DEBUG_FILE):
            os.remove(DEBUG_FILE)  # last run worked, so drop the old debug dump
    except Exception as e:
        row["note"] = f"error: {type(e).__name__}: {e}"[:300]
        if raw is not None:
            with open(DEBUG_FILE, "w", encoding="utf-8") as f:
                f.write(raw)
        append_row(row)
        print(f"{row['time']}  could not read 3rd floor - {row['note']}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning::{row['note']}")
        return 0  # still commit the error row

    append_row(row)
    print(f"Logged {row['time']} ({row['weekday']})")
    for z in zones:
        cap = z.get("TotalCapacity") or 0
        lc = z.get("LastCount") or 0
        pct = f"{lc / cap * 100:.0f}%" if cap else "n/a"
        state = "Closed" if z.get("IsClosed") else "Open"
        print(f"  {z['LocationName'].strip():28} {state:6}  count {lc:>3} / {cap:<3} "
              f"{pct:>4}   updated {str(z['LastUpdatedDateAndTime'])[:16].replace('T', ' ')}")
    print(f"  {'3rd floor total':28} {row['status'].title():6}  count {row['count']:>3} / "
          f"{row['capacity']:<3} {row['percent']:>3}%   updated {row['source_last_updated']}")
    if row["note"]:
        print("  note:", row["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
