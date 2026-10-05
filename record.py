"""Append one snapshot of Winter Park's own snow report to data/resort/YYYY-MM.jsonl.

Nobody archives this feed, and its Summit zone is the only measured snowfall up high: the truth
the peak forecast can't yet be checked against. Last 48/72 h let a missed day be recovered.

Usage: python3 record.py [OUT_DIR]   (default: data/resort)
"""
import datetime
import json
import pathlib
import sys
import urllib.request

FEED = "https://mtnpowder.com/feed?resortId=5"
AREAS = ("BaseArea", "MidMountainArea", "SummitArea")
KEYS = ("Last24HoursIn", "Last48HoursIn", "Last72HoursIn")


def main(out_dir="data/resort"):
    req = urllib.request.Request(FEED, headers={"User-Agent": "pray4sno (github.com/trevthefoolish/pray4sno)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        report = json.load(r)["SnowReport"]
    fetched = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = {"fetched": fetched, "report_updated": report.get("LastUpdate"),
            **{a: {k: report[a].get(k) for k in KEYS} for a in AREAS if a in report}}
    path = pathlib.Path(out_dir) / f"{fetched[:7]}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(snap, separators=(",", ":")) + "\n")
    print(f"appended {path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
