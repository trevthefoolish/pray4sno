"""Point values from archived NBM runs on AWS (noaa-nbm-grib2-pds), fetched by byte range.

For each run: 6-hourly liquid (APCP, mm), snowfall (ASNOW, m) and snow-to-liquid ratio
(SNOWLR) for leads 6..264 h at the base and peak points. Only the extracted point values
are cached (.cache/nbm/), never the CONUS grids.

Usage: python3 research/nbm.py 2025-01-15T12
"""
import concurrent.futures
import datetime as dt
import json
import sys
import time

import eccodes

from common import CACHE, POINTS, get

BUCKET = "https://noaa-nbm-grib2-pds.s3.amazonaws.com"
FIELDS = {"apcp": "APCP:surface:{a}-{b} hour acc fcst:",
          "asnow": "ASNOW:surface:{a}-{b} hour acc fcst:",
          "slr": "SNOWLR:surface:{b} hour fcst:"}
STEPS = range(6, 265, 6)


def ranges(run, step):
    """[(field, url, first_byte, last_byte)] for our fields in one forecast-hour file."""
    url = f"{BUCKET}/blend.{run:%Y%m%d}/{run:%H}/core/blend.t{run:%H}z.core.f{step:03d}.co.grib2"
    lines = get(url + ".idx", cache=False).decode().splitlines()
    offsets = [int(line.split(":")[1]) for line in lines]
    found = []
    for i, line in enumerate(lines):
        desc = line.split(":", 3)[3]
        for field, pattern in FIELDS.items():
            if desc == pattern.format(a=step - 6, b=step):
                found.append((field, url, offsets[i], offsets[i + 1] - 1 if i + 1 < len(lines) else ""))
    return found


def point_values(url, first, last):
    msg = eccodes.codes_new_from_message(get(url, {"Range": f"bytes={first}-{last}"}, cache=False))
    try:
        missing = eccodes.codes_get(msg, "missingValue")
        out = {}
        for name, (lat, lon) in POINTS.items():
            v = eccodes.codes_grib_find_nearest(msg, lat, lon)[0]["value"]
            out[name] = None if v == missing else v
        return out
    finally:
        eccodes.codes_release(msg)


def run_values(run):
    """{point: {field: {lead_h: value}}} for one run, cached."""
    path = CACHE / "nbm" / f"{run:%Y%m%dT%H}.json"
    if path.exists():
        return json.loads(path.read_text())
    out = {p: {f: {} for f in FIELDS} for p in POINTS}
    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        found = pool.map(lambda s: [(s,) + r for r in ranges(run, s)], STEPS)
        tasks = [(step, field, pool.submit(point_values, url, a, b))
                 for rs in found for step, field, url, a, b in rs]
        for step, field, fut in tasks:
            for p, v in fut.result().items():
                out[p][field][step] = v
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


if __name__ == "__main__":
    run = dt.datetime.fromisoformat(sys.argv[1])
    t = time.time()
    v = run_values(run)
    print(f"{run:%Y-%m-%d %HZ}: {time.time() - t:.0f}s")
    for p in POINTS:
        for field in FIELDS:
            print(p, field, [round(v[p][field][s], 2) if v[p][field].get(s) is not None else None
                             for s in list(STEPS)[:8]], "...")
