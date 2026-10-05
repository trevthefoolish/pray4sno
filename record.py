"""Append one snapshot of Winter Park's own snow report to data/resort/YYYY-MM.jsonl.

Nobody archives this feed. It is the only measured snowfall at the summit, the
on-mountain stations are the only temperatures on the slopes, and the resort's
5-day forecast is the local benchmark to beat. Every day not recorded is lost.

Usage: python3 record.py [OUT_DIR]   (default: data/resort)
"""
import datetime
import json
import pathlib
import sys
import urllib.request

FEED = "https://mtnpowder.com/feed?resortId=5"
AREAS = ("BaseArea", "MidMountainArea", "SummitArea")
AREA_KEYS = ("Name", "SinceLiftsClosedIn", "Last24HoursIn", "Last48HoursIn",
             "Last72HoursIn", "Last7DaysIn", "BaseIn")
STATION_KEYS = ("Name", "FeedSavedTime", "TemperatureF", "TemperatureHighF",
                "TemperatureLowF", "DewPointF", "Humidity", "WindDirection",
                "WindStrengthMph", "WindGustsMph", "Conditions")
DAYS = ("OneDay", "TwoDay", "ThreeDay", "FourDay", "FiveDay")
DAY_KEYS = ("date", "forecasted_snow_in", "forecasted_snow_day_in",
            "forecasted_snow_night_in", "temp_high_f", "temp_low_f")


def pick(d, keys):
    return {k: d.get(k) for k in keys}


def snapshot(feed, fetched):
    report, forecast = feed["SnowReport"], feed["Forecast"]
    return {
        "fetched": fetched,
        "report_updated": report.get("LastUpdate"),
        "storm_in": report.get("StormTotalIn"),
        "season_in": report.get("SeasonTotalIn"),
        "areas": {a: pick(report[a], AREA_KEYS) for a in AREAS if a in report},
        "stations": {k: pick(v, STATION_KEYS) for k, v in feed["CurrentConditions"].items()},
        "forecast_updated": forecast.get("FeedSavedTime"),
        "forecast": [pick(forecast[d], DAY_KEYS) for d in DAYS if d in forecast],
    }


def main(out_dir="data/resort"):
    req = urllib.request.Request(FEED, headers={"User-Agent": "pray4sno (github.com/trevthefoolish/pray4sno)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        feed = json.load(r)
    fetched = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = pathlib.Path(out_dir) / f"{fetched[:7]}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(snapshot(feed, fetched), separators=(",", ":")) + "\n")
    print(f"appended {path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
