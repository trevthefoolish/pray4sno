"""What the forecast page shows now, and how the page and the forecaster routine have done so far.

  python3 score.py now          the page's days 1-7 as JSON: the same math and rounding as index.html
  python3 score.py record DIR   Brier scores so far of the page and the forecaster (FORECASTER.md), days 1-3,
                                from DIR/log/*.jsonl (the data branch), with climatology as the reference
Truth, as in calibrate.py: base (the village) = Winter Park COOP snowfall, via RCC-ACIS, which has it a day
after it falls; peak = Berthoud SNOTEL liquid x the snow ratio, Nov-Apr only.
"""
import datetime as dt
import json
import math
import pathlib
import statistics as st
import sys
import urllib.request
import zoneinfo

import calibrate as C

HERE = pathlib.Path(__file__).resolve().parent
CAL = json.loads((HERE / "calibration.json").read_text())
KEY = "bSvD5raxPiFWRcz4"                                   # the page's key (see index.html)
DENVER = zoneinfo.ZoneInfo("America/Denver")
UTC = dt.timezone.utc


def js_round(x):
    return math.floor(x + 0.5)


def window_end(t):
    """The hour ending t (UTC) belongs to the window ending at the first 15:00 UTC (08:00 MST) at or after t."""
    if t.hour * 60 + t.minute > 15 * 60:
        t += C.DAY
    return t.replace(hour=15, minute=0, second=0, microsecond=0)


def label(end):
    d = end.astimezone(DENVER)
    return f"{d:%a}".lower() + f" {d.month}/{d.day}"


def now():
    points = ("peak", "base")
    locs = C.get_json(
        "https://customer-api.open-meteo.com/v1/forecast?"
        f"latitude={','.join(str(CAL['points'][p][0]) for p in points)}"
        f"&longitude={','.join(str(CAL['points'][p][1]) for p in points)}"
        f"&hourly=precipitation,temperature_2m&models={','.join(CAL['models'].values())}"
        f"&past_days=1&forecast_days=9&timezone=GMT&apikey={KEY}")
    first = window_end(dt.datetime.now(UTC) + dt.timedelta(minutes=1))
    days = [{"day": label(first + k * C.DAY), "end": f"{first + k * C.DAY:%Y-%m-%d}"} for k in range(7)]
    for point, loc in zip(points, locs):
        hours = {}                                         # (model, window end) -> [(mm, cold?)]
        for model, om in CAL["models"].items():
            for t, p, c in zip(loc["hourly"]["time"], loc["hourly"][f"precipitation_{om}"],
                               loc["hourly"][f"temperature_2m_{om}"]):
                if p is not None and c is not None:
                    end = window_end(dt.datetime.fromisoformat(t).replace(tzinfo=UTC))
                    hours.setdefault((model, end), []).append((p, c <= CAL["snow_c"]))
        for k, day in enumerate(days):
            members = {}
            for m in CAL["models"]:
                h = hours.get((m, first + k * C.DAY), [])
                if len(h) == 24:
                    a, b = CAL["coef"][point][m][k]
                    cold = sum(c for _, c in h) / 24
                    members[m] = max(0.0, a * cold + b * sum(p for p, c in h if c) / 25.4)
            if not members:
                day[point] = {"cell": "-"}
                continue
            liq = st.mean(members.values())
            g, b = CAL["leads"][str(k + 1)], sum(liq >= e for e in CAL["bins"])
            odds, (lo, hi) = CAL["odds"][point][g][b], (js_round(x) for x in CAL["range"][point][g][b])
            pct = js_round(odds * 10) * 10
            cell = f'{lo if lo == hi else f"{lo}-{hi}"}" {pct}%' if pct else ""
            day[point] = {"cell": cell, "odds": odds, "liquid_in": round(liq, 3),
                          "models_liquid_in": {m: round(x, 3) for m, x in members.items()}}
    print(json.dumps(days, indent=1))


def truth(first, last):
    """{("base" | "peak", date): 1"+ of snow fell?} for the 24 h ending 08:00 on each date."""
    out = {}
    req = urllib.request.Request("https://data.rcc-acis.org/StnData", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"sid": "USC00059175", "sdate": f"{first}", "edate": f"{last}",
                                                  "elems": "snow"}).encode())
    with urllib.request.urlopen(req, timeout=60) as r:
        for d, snow in json.load(r)["data"]:
            if snow == "T" or snow.replace(".", "", 1).isdigit():     # T = trace; M, S, A... = not a clean day
                out[("base", dt.date.fromisoformat(d))] = snow != "T" and float(snow) >= 1
    vals = C.get_json("https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=335:CO:SNTL"
                      f"&elements=PREC&duration=HOURLY&beginDate={first - C.DAY}%2000:00&endDate={last}%2023:00")
    h = {dt.datetime.fromisoformat(v["date"]): v["value"] for station in vals for e in station["data"]
         for v in e["values"] if v.get("value") is not None}
    for t in h:
        if t.hour == 8 and t - C.DAY in h and t.month in C.FIT_MONTHS:   # Oct, May: some liquid is rain
            out[("peak", t.date())] = max(0.0, h[t] - h[t - C.DAY]) * CAL["snow_ratio"] >= 1
    return out


def record(store):
    runs = [json.loads(line) for f in sorted(pathlib.Path(store, "log").glob("*.jsonl"))
            for line in f.read_text().splitlines() if line.strip()]
    if not runs:
        print(json.dumps({"runs": 0}))
        return
    ends = [dt.date.fromisoformat(d["end"]) for r in runs for d in r["days"]]
    last = min(max(ends), dt.date.today())
    seen = truth(min(ends), last) if min(ends) <= last else {}
    out = {"first_run": runs[0]["written"], "runs": len(runs)}
    for point in ("peak", "base"):
        clim = CAL["clim"][point]                         # no climatology (summer): nothing to score against
        rows = [(d[point]["page"], d[point]["forecaster"], seen[(point, end)], clim[str(end.month)])
                for r in runs for d in r["days"] if point in d
                for end in [dt.date.fromisoformat(d["end"])] if (point, end) in seen and str(end.month) in clim]
        brier = lambda i: round(st.mean((x[i] - x[2]) ** 2 for x in rows), 4) if rows else None
        out[point] = {"forecasts_scored": len(rows), "snow_days_among_them": sum(x[2] for x in rows),
                      "brier_page": brier(0), "brier_forecaster": brier(1), "brier_climatology": brier(3)}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"now": now, "record": record}[sys.argv[1]](*sys.argv[2:])
