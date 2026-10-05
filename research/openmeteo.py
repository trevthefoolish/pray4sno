"""Open-Meteo Previous Runs (archive from Jan 2024): daily liquid by forecast day, per model, at the
four sites, in the shape skill.py scores.

Day N of the 12Z run on date R = the 24 h ending 12Z on R+N, summed from `precipitation_previous_dayN`
(each hour as forecast N x 24 h before it). Leads run about 12 h longer than a single run's day N,
so these scores are slightly conservative next to run-based archives.

Usage: OPENMETEO_APIKEY=... python3 research/openmeteo.py
"""
import collections
import datetime as dt
import json
import os

from common import CACHE, SITES, get_json

MODELS = {"nbm": "ncep_nbm_conus", "ifs": "ecmwf_ifs025", "aifs": "ecmwf_aifs025_single"}
DAYS = range(1, 8)


def fetch(model, winter):
    lats = ",".join(str(a) for a, _ in SITES.values())
    lons = ",".join(str(b) for _, b in SITES.values())
    hourly = ",".join(f"precipitation_previous_day{n}" for n in DAYS)
    url = (f"https://customer-previous-runs-api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}"
           f"&hourly={hourly}&models={model}&start_date={winter}-10-31&end_date={winter + 1}-05-01"
           f"&apikey={os.environ['OPENMETEO_APIKEY']}")
    return get_json(url)


def days(model):
    """{(run_date, site): {day: inches}} for complete 24 h windows ending 12Z."""
    out = collections.defaultdict(dict)
    for winter in (2023, 2024, 2025):
        for site, loc in zip(SITES, fetch(model, winter)):
            h = loc["hourly"]
            times = [dt.datetime.fromisoformat(t) for t in h["time"]]
            for n in DAYS:
                sums, counts = collections.defaultdict(float), collections.Counter()
                for t, v in zip(times, h[f"precipitation_previous_day{n}"]):
                    if v is not None:
                        end = (t - dt.timedelta(hours=12, minutes=1)).date() + dt.timedelta(days=1)
                        sums[end] += v
                        counts[end] += 1
                for end, mm in sums.items():
                    if counts[end] == 24:
                        out[(end - dt.timedelta(days=n), site)][n] = mm / 25.4
    return out


if __name__ == "__main__":
    (CACHE / "om").mkdir(parents=True, exist_ok=True)
    for name, model in MODELS.items():
        d = days(model)
        (CACHE / "om" / f"{name}.json").write_text(json.dumps({f"{r}|{s}": v for (r, s), v in d.items()}))
        print(name, len(d), "run-site pairs")
