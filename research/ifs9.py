"""ECMWF IFS HRES at 9 km: archived 12Z runs from Open-Meteo's Single Runs API (hindcasts from
March 2024, about 11 days ahead), written in the same layout as gribstream.py so skill.py scores
it alongside the other models. Hourly precipitation = 1-h totals (mm).

Usage: OPENMETEO_APIKEY=... python3 research/ifs9.py
"""
import concurrent.futures
import json
import os
import urllib.error

from common import CACHE, SITES, get
from gribstream import runs

OUT = CACHE / "gs" / "ifs9"


def fetch(run):
    path = OUT / f"{run:%Y%m%dT%H}.csv"
    if path.exists():
        return
    lats = ",".join(str(a) for a, _ in SITES.values())
    lons = ",".join(str(b) for _, b in SITES.values())
    url = (f"https://customer-single-runs-api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}"
           f"&hourly=precipitation&models=ecmwf_ifs&run={run:%Y-%m-%dT%H}:00&forecast_days=11"
           f"&apikey={os.environ['OPENMETEO_APIKEY']}")
    try:
        data = json.loads(get(url, cache=False))
    except urllib.error.HTTPError:                 # run not in the archive
        return
    lines = ["forecasted_at,forecasted_time,lat,lon,name,member,apcp"]
    for name, loc in zip(SITES, data):
        h = loc["hourly"]
        for t, v in zip(h["time"], h["precipitation"]):
            if v is not None:
                lines.append(f"{run:%Y-%m-%dT%H}:00:00Z,{t}:00Z,{loc['latitude']},{loc['longitude']},{name},0,{v}")
    if len(lines) > 1:
        path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [r for r in runs("ifsoper", 2023, 2025)]      # same span as the GribStream IFS archive
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        list(pool.map(fetch, todo))
    print(f"ifs9: {len(list(OUT.glob('*.csv')))} runs cached")
