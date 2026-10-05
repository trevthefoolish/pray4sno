"""R4 (Open-Meteo path): how wrong is each model as-is, and how skill decays with lead day.

as-is:  Historical Forecast API (each run's first hours, stitched), winters 2021-26.
        Season totals of liquid and of Open-Meteo's `snowfall` vs the gauges.
leads:  Previous Runs API (`*_previous_dayN`, N=1..7), winters 2024-26.
        Daily 08:00-08:00 liquid vs the COOP gauge (base) and 00:00-00:00 vs SNOTEL (upper):
        bias ratio, MAE raw, MAE after a ratio fitted on the other winter.

The free API is rate-limited per IP; responses are cached in .cache/ so reruns cost nothing.
Usage: python3 research/openmeteo.py [asis|leads]
"""
import collections
import datetime as dt
import statistics as st
import sys

from common import SNOTEL, coop_daily, get_json, season, snotel_daily

GAUGES = {"base": (39.8877, -105.7613), "berthoud": (39.8036, -105.7779), "foolcreek": (39.8687, -105.8677)}
MODELS = ["ncep_nbm_conus", "ecmwf_ifs025", "ecmwf_aifs025_single", "gfs_seamless",
          "ncep_hrrr_conus", "icon_seamless", "gem_seamless"]
WINTERS = {"asis": (2021, 2025), "leads": (2024, 2025)}
DAY = dt.timedelta(days=1)


def hourly(api, model, gauge, variables, first, last):
    lat, lon = GAUGES[gauge]
    url = (f"https://{api}.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&hourly={','.join(variables)}&models={model}&timezone=America/Denver"
           f"&start_date={first}-11-01&end_date={last + 1}-04-30")
    h = get_json(url)["hourly"]
    times = [dt.datetime.fromisoformat(t) for t in h["time"]]
    return {v: dict(zip(times, h[v])) for v in variables}


def daily(series, end_hour):
    """Sum hourly mm into inches per 24 h window ending at end_hour; drop windows with gaps."""
    sums, counts = collections.defaultdict(float), collections.Counter()
    for t, v in series.items():
        d = (t - dt.timedelta(hours=end_hour, minutes=1)).date() + DAY  # value at t covers the hour ending t
        if v is not None:
            sums[d] += v / 25.4
            counts[d] += 1
    return {d: s for d, s in sums.items() if counts[d] == 24}


def truths():
    coop = coop_daily("2021-01-01", "2026-06-30")
    out = {"base": ({d: v[1] for d, v in coop.items()}, 8), "base_snow": ({d: v[0] for d, v in coop.items()}, 8)}
    for k, t in SNOTEL.items():
        p = snotel_daily(t, "PREC", "2021-10-01", "2026-06-30")
        out[k] = ({d + DAY: p[d + DAY] - p[d] for d in p if d + DAY in p}, 0)  # day D = 24 h ending 00:00 on D
    return out


def asis():
    obs = truths()
    print("model                gauge      season  fcst liq  obs liq  obs/fcst | fcst snow  obs snow  obs/fcst")
    for model in MODELS:
        for gauge in GAUGES:
            try:
                h = hourly("historical-forecast-api", model, gauge, ["precipitation", "snowfall"], *WINTERS["asis"])
            except Exception as e:
                print(model, gauge, "ERROR", e)
                continue
            truth, end = obs[gauge]
            liq = daily(h["precipitation"], end)
            snow = daily({t: (v or 0) * 10 if v is not None else None for t, v in h["snowfall"].items()}, end)
            for s in range(WINTERS["asis"][0], WINTERS["asis"][1] + 1):
                days = [d for d in liq if season(d) == s and d in truth]
                if len(days) < 0.9 * 181:
                    continue
                f, o = sum(liq[d] for d in days), sum(truth[d] for d in days)
                line = f"{model:20} {gauge:10} {s}-{(s + 1) % 100:02d}  {f:7.1f}  {o:7.1f}  {o / f:7.2f}x"
                if gauge == "base":
                    sd = [d for d in days if d in obs["base_snow"][0] and d in snow]
                    fs, os_ = sum(snow[d] for d in sd), sum(obs["base_snow"][0][d] for d in sd)
                    line += f" | {fs:8.0f}  {os_:8.0f}  {os_ / fs:7.2f}x"
                print(line)


def leads():
    obs = truths()
    var = [f"precipitation_previous_day{n}" for n in range(1, 8)]
    print("model                gauge      lead  bias(obs/fcst)  MAE raw  MAE calibrated(LOWO)  corr   [inches/day]")
    for model in MODELS:
        for gauge in GAUGES:
            try:
                h = hourly("previous-runs-api", model, gauge, var, *WINTERS["leads"])
            except Exception as e:
                print(model, gauge, "ERROR", e)
                continue
            truth, end = obs[gauge]
            for n, v in enumerate(var, 1):
                fc = daily(h[v], end)
                days = {s: [d for d in fc if season(d) == s and d in truth] for s in range(WINTERS["leads"][0], WINTERS["leads"][1] + 1)}
                if any(len(x) < 100 for x in days.values()):
                    continue
                all_days = [d for x in days.values() for d in x]
                f = [fc[d] for d in all_days]
                o = [truth[d] for d in all_days]
                ratio = {s: sum(truth[d] for d in x) / max(1e-9, sum(fc[d] for d in x)) for s, x in days.items()}
                cal = [abs(fc[d] * ratio[t] - truth[d]) for s, x in days.items() for d in x
                       for t in ratio if t != s]
                print(f"{model:20} {gauge:10} day{n}  {sum(o) / max(1e-9, sum(f)):10.2f}x  "
                      f"{st.mean(abs(a - b) for a, b in zip(f, o)):7.3f}  {st.mean(cal):12.3f}  "
                      f"{st.correlation(f, o) if len(set(f)) > 1 else float('nan'):10.2f}")


if __name__ == "__main__":
    {"asis": asis, "leads": leads}[sys.argv[1] if len(sys.argv) > 1 else "asis"]()
