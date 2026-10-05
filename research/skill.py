"""R4/R5 over six winters: each archived model's skill by lead day, and how far ahead is useful.

Forecast day N of a 12Z run is the 24 h ending 12Z (05:00 MST) N days later.
Truth: base = COOP day (24 h ending 08:00 MST, 3 h after the forecast day ends);
       upper gauges = SNOTEL hourly liquid over exactly the forecast day.

Scores per model x site x lead, leave-one-winter-out (fit on the other winters, score the held-out one):
  bias   sum(obs) / sum(forecast)                      (> 1: forecast too low)
  r      correlation
  skill  1 - SSE / SSE(climatology), forecast calibrated as a + b*f;
         climatology = the site's mean for that calendar month. > 0 beats climatology.
Also for multi-day totals, and for an equal-weight blend of the calibrated models.

Usage: python3 research/skill.py [SINCE_DATE]   (after gribstream.py has filled .cache/gs/)
"""
import collections
import csv
import datetime as dt
import statistics as st

from common import CACHE, SNOTEL, coop_daily, season, snotel_hourly

MODELS = ["nbm", "ifsoper", "aifsoper"]
BLENDS = {"blend": MODELS}                       # equal-weight mean of the calibrated models
SITES = ["base", "berthoud", "foolcreek"]
SPANS = {"1": (1, 1), "2": (2, 2), "3": (3, 3), "4": (4, 4), "5": (5, 5), "6": (6, 6), "7": (7, 7),
         "8": (8, 8), "10": (10, 10), "12": (12, 12), "14": (14, 14),
         "1-3": (1, 3), "4-7": (4, 7), "8-14": (8, 14)}
DAY = dt.timedelta(days=1)


def intervals(model, values):
    """[(end_hour, hours, mm)] from one run's raw values {lead_h: value} (see gribstream.py)."""
    out = []
    if model in ("ifsoper", "aifsoper"):              # running totals
        scale = 1000 if model == "ifsoper" else 1
        prev_t, prev_v = 0, 0.0
        for t in sorted(values):
            if t > 0:
                out.append((t, t - prev_t, max(0.0, values[t] - prev_v) * scale))
                prev_t, prev_v = t, values[t]
    for t, v in values.items():
        if model == "nbm" and 1 <= t <= 36:
            out.append((t, 1, v))
        elif model == "nbm" and t > 36 and t % 6 == 0:
            out.append((t, 6, v))
    return out


def load(model):
    """{(run_date, site): {lead_day: inches}} for complete 24 h windows."""
    out = {}
    for path in sorted((CACHE / "gs" / model).glob("*.csv")):
        run = dt.datetime.strptime(path.stem, "%Y%m%dT%H")
        raw = collections.defaultdict(dict)
        with path.open() as f:
            for row in csv.DictReader(f):
                if row["apcp"] not in ("", "NaN") and float(row["apcp"]) < 1000:   # NOAA missing = 9.999e20
                    t = round((dt.datetime.fromisoformat(row["forecasted_time"][:19]) - run).total_seconds() / 3600)
                    raw[row["name"]][t] = float(row["apcp"])
        for site, values in raw.items():
            days = collections.defaultdict(lambda: [0, 0.0])
            for t, hours, mm in intervals(model, values):
                n = (t - hours) // 24 + 1                  # keep intervals that don't straddle days
                if (t - 1) // 24 + 1 == n:
                    days[n][0] += hours
                    days[n][1] += mm
            out[(run.date(), site)] = {n: mm / 25.4 for n, (h, mm) in days.items() if h == 24}
    return out


def truth(first, last):
    """{site: {date: inches}} for the 24 h ending on that date (see module docstring)."""
    coop = coop_daily(f"{first}-10-01", f"{last + 1}-05-31")
    out = {"base": {d: v[1] for d, v in coop.items()}}
    for site in ("berthoud", "foolcreek"):
        h = {}
        for w in range(first, last + 1):
            h.update(snotel_hourly(SNOTEL[site], "PREC", f"{w}-10-25", f"{w + 1}-05-05"))
        out[site] = {t.date(): max(0.0, h[t] - h[t - DAY]) for t in h if t.hour == 5 and t - DAY in h}
    return out


def pairs(model_days, obs, site, a, b):
    """[(date the span ends, forecast, observed)] for forecast days a..b of every run."""
    out = []
    for (run, s), days in model_days.items():
        o = [obs.get(run + n * DAY) for n in range(a, b + 1)]
        if s == site and season(run + b * DAY) is not None and None not in o and all(n in days for n in range(a, b + 1)):
            out.append((run + b * DAY, sum(days[n] for n in range(a, b + 1)), sum(o)))
    return out


def calibrate(ps):
    """Leave-one-winter-out a + b*f: {date: (calibrated forecast, obs)}; None if < 2 winters."""
    by_w = collections.defaultdict(list)
    for p in ps:
        by_w[season(p[0])].append(p)
    if len(by_w) < 2 or len(ps) < 60:
        return None
    out = {}
    for w, test in by_w.items():
        fs = [f for v, q in by_w.items() if v != w for _, f, _ in q]
        os_ = [o for v, q in by_w.items() if v != w for _, _, o in q]
        b = st.covariance(fs, os_) / st.variance(fs) if st.variance(fs) > 0 else 0.0
        a = st.mean(os_) - b * st.mean(fs)
        out.update({d: (a + b * f, o) for d, f, o in test})
    return out


def skill(cal):
    """1 - SSE / SSE(monthly climatology from the other winters)."""
    by_wm = collections.defaultdict(list)
    for d, (_, o) in cal.items():
        by_wm[(season(d), d.month)].append(o)
    sse = sse_clim = 0.0
    for d, (f, o) in cal.items():
        clim = ([x for (w, m), v in by_wm.items() if m == d.month and w != season(d) for x in v] or
                [x for (w, m), v in by_wm.items() if w != season(d) for x in v])
        sse += (f - o) ** 2
        sse_clim += (st.mean(clim) - o) ** 2
    return 1 - sse / sse_clim


def main(since="2020-01-01"):
    """since: score only runs from this date, so models with different archives compare fairly."""
    since = dt.date.fromisoformat(since)
    data = {m: {k: v for k, v in load(m).items() if k[0] >= since} for m in MODELS}
    obs = truth(2020, 2025)
    for site in SITES:
        print(f"\n== {site}: skill vs climatology [correlation] by forecast day; > 0 beats climatology")
        print(f"{'':14}" + "".join(f"{k:>12}" for k in SPANS))
        cals = {}
        for m in MODELS:
            cells = []
            for k, (a, b) in SPANS.items():
                ps = pairs(data[m], obs[site], site, a, b)
                cal = cals[(m, k)] = calibrate(ps)
                r = st.correlation([p[1] for p in ps], [p[2] for p in ps]) if cal else 0
                cells.append(f"{skill(cal):+.2f} [{r:.2f}]" if cal else "")
            print(f"{m:14}" + "".join(f"{c:>12}" for c in cells))
        for name, models in BLENDS.items():
            cells = []
            for k in SPANS:
                members = [cals[(m, k)] for m in models if cals[(m, k)]]
                dates = set().union(*members) if members else set()
                blend = {d: (st.mean(c[d][0] for c in members if d in c), next(c[d][1] for c in members if d in c))
                         for d in dates}
                cells.append(f"{skill(blend):+.2f}" if blend else "")
            print(f"{name:14}" + "".join(f"{c:>12}" for c in cells))
        bias = {m: [sum(p[2] for p in pairs(data[m], obs[site], site, n, n)) /
                    max(1e-9, sum(p[1] for p in pairs(data[m], obs[site], site, n, n))) for n in (1, 3, 7)]
                for m in MODELS}
        print("bias obs/fcst, days 1/3/7: " + "  ".join(f"{m} {'/'.join(f'{x:.2f}' for x in v)}" for m, v in bias.items()))


if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])
