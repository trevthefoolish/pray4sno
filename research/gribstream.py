"""Archived forecast runs from GribStream at the forecast points and the truth gauges.

Daily 12Z runs (issued about 5 AM MST), Nov-Apr, every lead time, raw as GribStream returns
them; cached per run in .cache/gs/<model>/<run>.csv. Credits = valid times x variables, and
all four sites count as one. On quota exhaustion (429 with a long Retry-After) it stops;
rerun after the daily reset to resume. A quota cut can truncate the response it lands in, so
requests are one run each and the last run saved before a quota stop is discarded. Empty
runs (not in the archive) cost nothing and are never cached.

Precipitation comes back differently per model (checked on the 2025-03-15 12Z run):
  nbm            1-h totals to 36 h, then 6-h totals at 42, 48, ...; 3-hourly leads are NaN
  gfs            6-h buckets (total since the last 00/06/12/18 h of lead) through 2024; running
                 total from the start of the run in 2025-26. Tell them apart by whether values drop.
  aifsoper       running total from the start of the run (mm)
  ifsoper        running total from the start of the run (m)
  gefsatmosmean  3-h total at 3, 9, 15, ... h; 6-h total at 6, 12, 18, ... h
  hrrr           1-h totals

Usage: GRIBSTREAM_TOKEN=... python3 research/gribstream.py MODEL [FIRST_WINTER LAST_WINTER]
"""
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

from common import CACHE, SITES

MODELS = {  # dataset: (max lead, archive start, [(name, level, info, alias)])
    "nbm": ("264h", "2020-10-01", [("APCP", "surface", "", "apcp"), ("ASNOW", "surface", "", "asnow")]),
    "gfs": ("384h", "2021-03-22", [("APCP", "surface", "", "apcp")]),
    "gefsatmosmean": ("240h", "2020-10-01", [("APCP", "surface", "ens mean", "apcp")]),
    "hrrr": ("48h", "2014-07-30", [("APCP", "surface", "", "apcp")]),
    "ifsoper": ("360h", "2024-03-01", [("tp", "sfc", "", "apcp")]),
    "aifsoper": ("360h", "2025-02-25", [("tp", "sfc", "", "apcp")]),
}


class QuotaExhausted(Exception):
    pass


def runs(model, first, last):
    start = dt.datetime.fromisoformat(MODELS[model][1])
    out = []
    for w in range(first, last + 1):
        d = dt.datetime(w, 11, 1, 12)
        while d < dt.datetime(w + 1, 5, 1):
            if d >= start:
                out.append(d)
            d += dt.timedelta(days=1)
    return out


def path(model, run):
    return CACHE / "gs" / model / f"{run:%Y%m%dT%H}.csv"


def fetch(model, run):
    lead, _, variables = MODELS[model]
    body = {"timesList": [f"{run:%Y-%m-%dT%H}:00:00Z"], "minLeadTime": "0h", "maxLeadTime": lead,
            "coordinates": [{"lat": a, "lon": b, "name": n} for n, (a, b) in SITES.items()],
            "variables": [{"name": n, "level": lv, "info": i, "alias": a} for n, lv, i, a in variables]}
    req = urllib.request.Request(
        f"https://gribstream.com/api/v2/{model}/runs", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['GRIBSTREAM_TOKEN']}", "Content-Type": "application/json",
                 "Accept": "text/csv", "Accept-Encoding": "gzip"})
    for attempt in range(10):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                data = r.read()
                return (gzip.decompress(data) if r.headers.get("Content-Encoding") == "gzip" else data).decode()
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After") or 0)
            if e.code != 429 and e.code < 500:
                raise
            if e.code == 429 and wait > 600:
                raise QuotaExhausted(wait)
            error = f"HTTP {e.code}"
            time.sleep(max(wait, min(300, 2 ** (attempt + 2))))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            error = repr(e)
            time.sleep(min(300, 2 ** (attempt + 2)))
        print(f"  retry {attempt + 1} for {run:%Y-%m-%d}: {error}", flush=True)
    raise RuntimeError(f"GribStream request kept failing: {error}")


def main(model, first="2020", last="2025"):
    todo = [r for r in runs(model, int(first), int(last)) if not path(model, r).exists()]
    print(f"{model}: {len(todo)} runs to fetch", flush=True)
    last_saved = None
    for i, run in enumerate(todo):
        try:
            text = fetch(model, run)
        except QuotaExhausted as e:
            if last_saved:
                last_saved.unlink()
            sys.exit(f"{model}: quota exhausted after {i} runs; resume in {e.args[0] / 3600:.1f} h")
        if text.count("\n") > 1:
            last_saved = path(model, run)
            last_saved.parent.mkdir(parents=True, exist_ok=True)
            last_saved.write_text(text)
        if i % 30 == 0:
            print(f"  {run:%Y-%m-%d}: {text.count(chr(10)) - 1} rows", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
