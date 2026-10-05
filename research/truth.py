"""R1/R2: what the ground truth says, over the full records.

- COOP observation time and completeness (base truth)
- Snow-to-liquid ratio at the base: by season, decade, month, and vs temperature
- How much more liquid the upper-mountain SNOTEL gauges get than the base
- SNOTEL depth gain per inch of liquid (a lower bound on the ratio up high: snow settles)

Usage: python3 research/truth.py
"""
import collections
import datetime as dt
import statistics as st

from common import COOP, SNOTEL, coop_daily, get_json, season, snotel_daily

DAY = dt.timedelta(days=1)


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def spread(v):
    return f"median {st.median(v):.2f}  p10 {q(v, .1):.2f}  p90 {q(v, .9):.2f}  (n={len(v)})"


def season_sums(daily, value):
    """{season: (days, total)} over Nov-Apr."""
    out = collections.defaultdict(lambda: [0, 0.0])
    for d, v in daily.items():
        s = season(d)
        if s is not None:
            out[s][0] += 1
            out[s][1] += value(v)
    return out


def increments(series):
    """Daily increase of a midnight-reading accumulator: {day: value(day+1) - value(day)}."""
    return {d: series[d + DAY] - series[d] for d in series if d + DAY in series}


def main():
    print("== Base truth: Winter Park COOP", COOP)
    raw = get_json("https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries"
                   f"&stations={COOP}&dataTypes=PRCP&startDate=2016-01-01&endDate=2026-09-30"
                   "&units=standard&format=json&includeAttributes=true")
    times = collections.Counter((r.get("PRCP_ATTRIBUTES") or "").split(",")[-1] for r in raw)
    print("observation time (2016-2026):", times.most_common(2))

    coop = coop_daily()
    snow = season_sums(coop, lambda v: v[0])
    liq = season_sums(coop, lambda v: v[1])
    full = sorted(s for s, (n, _) in snow.items() if n >= 0.9 * 181)
    print(f"days {min(coop)} .. {max(coop)}; complete Nov-Apr seasons: {len(full)} of {len(snow)}")

    print("\n== R2: season snow/liquid at the base (measured snowfall / gauge liquid)")
    ratio = {s: snow[s][1] / liq[s][1] for s in full}
    print("all seasons:", spread(list(ratio.values())))
    for dec in range(1940, 2030, 10):
        v = [r for s, r in ratio.items() if dec <= s < dec + 10]
        if v:
            print(f"  {dec}s: {spread(v)}")
    print("  last 6:", {s: round(ratio[s], 1) for s in full[-6:]})

    storm = {d: s / p for d, (s, p) in coop.items() if season(d) is not None and p >= 0.2 and s > 0}
    print("daily, days with >= 0.2 in liquid:", spread(list(storm.values())))
    by_month = collections.defaultdict(list)
    for d, r in storm.items():
        by_month[d.month].append(r)
    print("  by month:", {m: round(st.median(by_month[m]), 1) for m in (11, 12, 1, 2, 3, 4)})

    tavg = snotel_daily(SNOTEL["berthoud"], "TAVG")
    pairs = [(tavg[d - DAY], r) for d, r in storm.items() if d - DAY in tavg]
    bins = collections.defaultdict(list)
    for t, r in pairs:
        bins[int(t // 10) * 10].append(r)
    print("  vs Berthoud Summit mean temp of the day before (F):",
          {f"{b}s": round(st.median(v), 1) for b, v in sorted(bins.items()) if len(v) >= 20})
    print(f"  correlation(temp, ratio) = {st.correlation(*zip(*pairs)):.2f} (n={len(pairs)})")

    print("\n== R1: upper-mountain liquid vs base liquid, Nov-Apr seasons")
    prec = {k: snotel_daily(t, "PREC") for k, t in SNOTEL.items()}
    for k, p in prec.items():
        r = []
        for s in full:
            a, b = dt.date(s, 11, 1), dt.date(s + 1, 5, 1)
            if a in p and b in p:
                r.append((p[b] - p[a]) / liq[s][1])
        print(f"  {k} / base: {spread(r)}")
    r = []
    for s in range(2011, 2026):
        a, b = dt.date(s, 11, 1), dt.date(s + 1, 5, 1)
        if all(x in p for p in prec.values() for x in (a, b)):
            r.append((prec["berthoud"][b] - prec["berthoud"][a]) / (prec["foolcreek"][b] - prec["foolcreek"][a]))
    print(f"  berthoud / foolcreek: {spread(r)}  min {min(r):.2f}")

    print("\n== R1: SNOTEL depth gain per inch of liquid on storm days (lower bound: settlement)")
    for k, t in SNOTEL.items():
        dp, ds = increments(prec[k]), increments(snotel_daily(t, "SNWD", start="2002-07-01"))
        v = [ds[d] / dp[d] for d in dp if d in ds and season(d) is not None and 0.3 <= dp[d] < 3 and ds[d] > 0]
        print(f"  {k}: {spread(v)}")


if __name__ == "__main__":
    main()
