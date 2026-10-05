"""Shared bits for the research scripts: sites, cached HTTP, observations."""
import datetime as dt
import hashlib
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"

# Base = the Winter Park COOP gauge (the base truth). Peak = top of Panoramic Express (Parsenn Bowl).
SITES = {"base": (39.8877, -105.7613), "peak": (39.8443, -105.7819),
         "berthoud": (39.8036, -105.7779), "foolcreek": (39.8687, -105.8677)}
COOP = "USC00059175"                      # Winter Park, 9,123 ft, read daily at 08:00
SNOTEL = {"berthoud": "335:CO:SNTL",      # Berthoud Summit, 11,300 ft, on the Divide
          "foolcreek": "1186:CO:SNTL"}    # Fool Creek, 11,130 ft


def get(url, headers=None, cache=True, tries=4):
    """GET with an on-disk cache keyed by URL + headers."""
    key = hashlib.sha1((url + json.dumps(headers or {}, sort_keys=True)).encode()).hexdigest()
    path = CACHE / "http" / key[:2] / key
    if cache and path.exists():
        return path.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "pray4sno-research", **(headers or {})})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body = r.read()
            break
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** (i + 1))
    if cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return body


def get_json(url):
    return json.loads(get(url))


def season(date):
    """Nov-Apr ski season a date belongs to, named by its starting year; None outside it."""
    y, m = date.year, date.month
    return y if m >= 11 else y - 1 if m <= 4 else None


def coop_daily(start="1942-01-01", end="2026-09-30"):
    """{date: (snow_in, liquid_in)} for days that passed QC. Day D = 24 h ending 08:00 on D."""
    out = {}
    y0, y1 = int(start[:4]), int(end[:4])
    for y in range(y0, y1 + 1, 10):
        a, b = max(start, f"{y}-01-01"), min(end, f"{y + 9}-12-31")
        url = ("https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries"
               f"&stations={COOP}&dataTypes=SNOW,PRCP&startDate={a}&endDate={b}"
               "&units=standard&format=json&includeAttributes=true")
        for r in get_json(url):
            vals = []
            for k in ("SNOW", "PRCP"):
                attrs = (r.get(k + "_ATTRIBUTES") or "").split(",")
                if r.get(k) in (None, "") or (len(attrs) > 1 and attrs[1].strip()):
                    break
                vals.append(float(r[k]))
            else:
                out[dt.date.fromisoformat(r["DATE"])] = tuple(vals)
    return out


def snotel_hourly(triplet, element, start, end):
    """{datetime: value} of a SNOTEL hourly element; timestamps are local standard time (UTC-7)."""
    url = ("https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?"
           f"stationTriplets={triplet}&elements={element}&duration=HOURLY"
           f"&beginDate={start}%2000:00&endDate={end}%2023:00")
    vals = get_json(url)[0]["data"][0]["values"]
    return {dt.datetime.fromisoformat(v["date"]): v["value"] for v in vals if v.get("value") is not None}
