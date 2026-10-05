"""Fit the calibration the forecast page applies, score it, and write calibration.json.

For each point (base, peak), forecast day 1-7 (24 h ending 08:00 MST) and model (NBM, ECMWF IFS,
ECMWF AIFS):  liquid = a * cold + b * cold liquid, where cold liquid is the model's precipitation in
hours at or below 1 C and cold is the fraction of such hours (light snow the models miss only happens
when it's cold; rain counts as nothing). The forecast is the mean of the three. The page shows what
actually fell on past days with a similar forecast: the odds of 1" or more of snow, and the 10th-90th
percentile of the snow on those days.
Truth: base = Winter Park COOP gauge (measured snowfall, read 08:00), Oct-May;
       peak = Berthoud Summit SNOTEL liquid x one snow-to-liquid ratio, Nov-Apr only: no snowfall is
       measured up there, and in Oct and May some of the liquid is rain.
The fit uses Nov-Apr. Scores are leave-one-winter-out: fit on the other winters, score the held-out one.

Usage: OPENMETEO_APIKEY=... python3 calibrate.py   (a few minutes; prints the scores)
"""
import collections
import datetime as dt
import json
import os
import pathlib
import statistics as st
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
POINTS = {"base": (39.8877, -105.7613), "peak": (39.8443, -105.7819)}  # COOP gauge; Panoramic Express top
MODELS = {"nbm": "ncep_nbm_conus", "ifs": "ecmwf_ifs025", "aifs": "ecmwf_aifs025_single"}
DAYS = range(1, 8)
SNOW_C = 1.0                            # at or below this 2 m temperature, precipitation counts as snow
WINTERS = (2023, 2024, 2025)            # Oct-May seasons; the archive starts Jan 2024
FIT_MONTHS = (11, 12, 1, 2, 3, 4)       # Oct and May are forecast and scored, not fitted
BINS = [0.01, 0.03, 0.06, 0.12, 0.25]   # forecast liquid (in) for the odds and range lookup
LEADS = {1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2}   # days 1-2, 3-4, 5-7 share a lookup table
DAY = dt.timedelta(days=1)


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pray4sno"}), timeout=300) as r:
        return json.load(r)


def season(d):
    return d.year if d.month >= 10 else d.year - 1 if d.month <= 5 else None


def fits(d, train):
    return season(d) in train and d.month in FIT_MONTHS


def forecasts():
    """{(model, point, n, date): (cold fraction, cold liquid inches)} forecast n days ahead for the
    24 h ending 08:00 MST on date."""
    out = {}
    hourly = ",".join(f"{v}_previous_day{n}" for v in ("precipitation", "temperature_2m") for n in DAYS)
    for model, om in MODELS.items():
        for w in WINTERS:
            url = ("https://customer-previous-runs-api.open-meteo.com/v1/forecast?"
                   f"latitude={','.join(str(p[0]) for p in POINTS.values())}"
                   f"&longitude={','.join(str(p[1]) for p in POINTS.values())}"
                   f"&hourly={hourly}&models={om}&start_date={w}-09-30&end_date={w + 1}-06-01"
                   f"&apikey={os.environ['OPENMETEO_APIKEY']}")
            for point, loc in zip(POINTS, get_json(url)):
                times = [dt.datetime.fromisoformat(t) for t in loc["hourly"]["time"]]
                for n in DAYS:
                    acc = collections.defaultdict(list)
                    for t, p, c in zip(times, loc["hourly"][f"precipitation_previous_day{n}"],
                                       loc["hourly"][f"temperature_2m_previous_day{n}"]):
                        if p is not None and c is not None:        # hour ending t; 15Z = 08:00 MST
                            acc[(t - dt.timedelta(hours=15, minutes=1)).date() + DAY].append((p, c <= SNOW_C))
                    out.update({(model, point, n, d): (sum(c for _, c in v) / 24, sum(p for p, c in v if c) / 25.4)
                                for d, v in acc.items() if len(v) == 24 and season(d) is not None})
    return out


def truth():
    """{"base": {date: (snow_in, liquid_in)}, "peak": {date: (None, liquid_in)}}, 24 h ending 08:00 MST."""
    base = {}
    for r in get_json("https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USC00059175"
                      "&dataTypes=SNOW,PRCP&startDate=2023-10-01&endDate=2026-05-31&units=standard&format=json"
                      "&includeAttributes=true"):
        flags = [(r.get(k + "_ATTRIBUTES") or ",,").split(",")[1] for k in ("SNOW", "PRCP")]
        if r.get("SNOW") not in (None, "") and r.get("PRCP") not in (None, "") and not any(flags) \
                and season(dt.date.fromisoformat(r["DATE"])) is not None:
            base[dt.date.fromisoformat(r["DATE"])] = (float(r["SNOW"]), float(r["PRCP"]))
    peak = {}
    for w in WINTERS:
        vals = get_json("https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=335:CO:SNTL"
                        f"&elements=PREC&duration=HOURLY&beginDate={w}-10-30%2000:00&endDate={w + 1}-05-01%2023:00")
        h = {dt.datetime.fromisoformat(v["date"]): v["value"] for v in vals[0]["data"][0]["values"]
             if v.get("value") is not None}                         # local standard time
        peak.update({t.date(): (None, max(0.0, h[t] - h[t - DAY])) for t in h
                     if t.hour == 8 and t - DAY in h and t.month in FIT_MONTHS})
    return {"base": base, "peak": peak}


def fit(fc, obs, point, train):
    """Fit everything on the winters in `train`. Returns (coef, blend): coef {(model, n): (a, b)};
    blend {(n, date): mean over models} of calibrated liquid, over all dates."""
    coef = {}
    for m in MODELS:
        for n in DAYS:
            pts = [(f, obs[point][d][1]) for (mm, p, nn, d), f in fc.items()
                   if (mm, p, nn) == (m, point, n) and fits(d, train) and d in obs[point]]
            if len(pts) >= 30:                              # a model can be missing from early winters
                s11 = sum(c * c for (c, _), _ in pts); s22 = sum(x * x for (_, x), _ in pts)
                s12 = sum(c * x for (c, x), _ in pts); det = s11 * s22 - s12 * s12
                s1y = sum(c * y for (c, _), y in pts); s2y = sum(x * y for (_, x), y in pts)
                coef[(m, n)] = ((s1y * s22 - s2y * s12) / det, (s2y * s11 - s1y * s12) / det)
    members = collections.defaultdict(list)
    for (m, p, n, d), (c, x) in fc.items():
        if p == point and (m, n) in coef:
            a, b = coef[(m, n)]
            members[(n, d)].append(max(0.0, a * c + b * x))
    return coef, {k: st.mean(v) for k, v in members.items()}


def bin_of(x):
    return sum(x >= e for e in BINS)


def snow_of(obs, point, ratio):
    """{date: snow inches}: measured at the base; liquid x ratio at the peak."""
    return {d: s if point == "base" else x * ratio for d, (s, x) in obs[point].items()}


def outcomes(blend, snow, train):
    """{(lead group, bin): (odds of 1"+, p10, p90 of snow on those days)} on training days with a similar
    forecast. A lead group with under 30 such days uses all lead groups; a bin with none (a warm day
    the past never saw) gets no chance of snow."""
    seen, pooled = collections.defaultdict(list), collections.defaultdict(list)
    for (n, d), f in blend.items():
        if fits(d, train) and d in snow:
            seen[(LEADS[n], bin_of(f))].append(snow[d])
            pooled[bin_of(f)].append(snow[d])
    out = {}
    for g in set(LEADS.values()):
        for k in range(len(BINS) + 1):
            v = seen[(g, k)] if len(seen[(g, k)]) >= 30 else pooled[k]
            wet = sorted(x for x in v if x >= 1)
            q = lambda p: wet[min(len(wet) - 1, int(p * len(wet)))]
            out[(g, k)] = (len(wet) / len(v), q(.1), q(.9)) if wet else (0.0, 0.0, 0.0)
    return out


def snow_ratio(blend, obs, train):
    """Least-squares snow inches per inch of forecast liquid at the base."""
    pts = [(f, obs["base"][d][0]) for (n, d), f in blend.items() if fits(d, train) and d in obs["base"]]
    return sum(x * y for x, y in pts) / sum(x * x for x, _ in pts)


def skill(rows):
    """rows: [(date, forecast, obs)] out of sample. 1 - SSE / SSE of the other winters' monthly mean.
    With odds and 0/1 outcomes, this is the Brier skill score against climatology."""
    sse = sse_clim = 0.0
    for d, f, o in rows:
        clim = [x for e, _, x in rows if e.month == d.month and season(e) != season(d)]
        sse += (f - o) ** 2
        sse_clim += (st.mean(clim) - o) ** 2
    return 1 - sse / sse_clim


def main():
    fc, obs = forecasts(), truth()
    for point in POINTS:                                    # out-of-sample scores, printed for RESEARCH.md
        brier, reliable, held = collections.defaultdict(list), collections.defaultdict(list), []
        for w in WINTERS:
            train = [x for x in WINTERS if x != w]
            blend = fit(fc, obs, point, train)[1]
            snow = snow_of(obs, point, snow_ratio(fit(fc, obs, "base", train)[1], obs, train))
            table = outcomes(blend, snow, train)
            for (n, d), f in blend.items():
                if season(d) == w and d in snow:
                    odds, lo, hi = table[(LEADS[n], bin_of(f))]
                    if d.month not in FIT_MONTHS:
                        brier["oct-may"].append((d, odds, snow[d] >= 1))
                        continue
                    brier[n].append((d, odds, snow[d] >= 1))
                    reliable[round(odds * 10) * 10].append(snow[d] >= 1)
                    if snow[d] >= 1:
                        held.append(round(lo) - .5 <= snow[d] <= round(hi) + .5)
        print(point, "Nov-Apr Brier skill", [round(skill(brier[n]), 2) for n in DAYS],
              "| odds -> observed", {k: round(100 * st.mean(v)) for k, v in sorted(reliable.items())},
              f"| range holds {st.mean(held):.0%} of {len(held)} snow days",
              *([f"| Oct and May, days 1-7: Brier skill {skill(brier['oct-may']):.2f}"] if brier["oct-may"] else []))

    calibration = {"points": POINTS, "models": MODELS, "snow_c": SNOW_C, "bins": BINS, "leads": LEADS}
    ratio = snow_ratio(fit(fc, obs, "base", WINTERS)[1], obs, WINTERS)
    for point in POINTS:                                    # final fit on every winter
        coef, blend = fit(fc, obs, point, WINTERS)
        calibration.setdefault("coef", {})[point] = {m: [[round(x, 4) for x in coef[(m, n)]] for n in DAYS]
                                                     for m in MODELS}
        snow = snow_of(obs, point, ratio)
        table = outcomes(blend, snow, WINTERS)
        groups = sorted(set(LEADS.values()))
        calibration.setdefault("odds", {})[point] = [[round(table[(g, k)][0], 2) for k in range(len(BINS) + 1)]
                                                     for g in groups]
        calibration.setdefault("range", {})[point] = [[[round(x, 1) for x in table[(g, k)][1:]]
                                                       for k in range(len(BINS) + 1)] for g in groups]
        by_month = collections.defaultdict(list)            # climatology: the reference for scoring live
        for d, s in snow.items():
            by_month[d.month].append(s >= 1)
        calibration.setdefault("clim", {})[point] = {m: round(st.mean(v), 2) for m, v in sorted(by_month.items())}
    calibration["snow_ratio"] = round(ratio, 2)
    (HERE / "calibration.json").write_text(json.dumps(calibration, indent=1))
    print(f"snow ratio {calibration['snow_ratio']:.1f}:1; wrote calibration.json")


if __name__ == "__main__":
    main()
