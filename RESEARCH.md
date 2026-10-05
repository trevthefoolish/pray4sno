# Research: forecasting snow at Winter Park

The evidence behind every choice in `calibrate.py`, `index.html` and `score.py`.

**Conventions:**
- "Liquid" means water equivalent.
- Seasons run Oct-May and are named by their starting year. The fit uses Nov-Apr.
- **Skill** = 1 − (squared error ÷ squared error of the monthly average), out of sample. 0 means no better than climatology; 1 means perfect. For odds (0-1 against snowed or not), the squared error is the Brier score, so this is the Brier skill score.

## Decisions

1. **Forecast from a calibrated, equal-weight blend of NBM, ECMWF IFS and ECMWF AIFS.** It beats every single model on days 1-2 and ties them on days 3-7. Other models added nothing.
2. **Calibrate per point × model × forecast day.**
   - Raw model liquid is about right at the base but 1.3-2x too low up high, by different amounts per model and lead.
   - Raw model `snowfall` fields are off by up to 11x.
3. **Only cold precipitation counts.** Precipitation in hours at or below 1 °C counts; rain counts as nothing.
4. **Show days 1-7.** Skill is near zero by day 10, and the week-2 total isn't robust.
5. **Show the odds of 1" or more, and the 10-90% range of the snow on those days, as pray4sno.ski does.** Every day 1-7 whose odds round to 10% or more gets a row. The odds are reliable at both points (day-1 Brier skill: base 0.64, peak 0.33). A 20% day that stays dry is an honest 1 in 5, not a false alarm.
6. **One data source: Open-Meteo's paid API**, for calibration and for the page.

## Ground truth

| Site | Elevation | Measures | Record |
|---|---|---|---|
| Winter Park COOP `USC00059175` (**base**) | 9,123 ft | snowfall + liquid, read at **08:00** | 1942-; 80 complete seasons |
| Berthoud Summit SNOTEL 335 (**peak** stand-in, on the Divide) | 11,300 ft | hourly liquid | 1978- |
| Fool Creek SNOTEL 1186 | 11,130 ft | hourly liquid | 2011- |
| Resort feed, Village / Mid / Summit | | reported snowfall, current only | archived by `record.py` |

- **Upper gauges vs base liquid:** Berthoud 1.72x (47 seasons, p10-p90 1.52-2.17); Fool Creek 1.36x. Berthoud beats Fool Creek every winter at almost the same height, so exposure matters as much as elevation.
- **Nothing measures snowfall at the peak**, about 12,000 ft at Panoramic Express. The resort's Summit reports, once recorded, are the only check.
- **Gauges undercatch snow in wind.** The COOP gauge misses up to about 70% (Yang 1998); SNOTEL about 30% at 2-4 m/s (Fassnacht 2004).
- **NRCS dates each daily SNOTEL reading by the day it closes (24:00).** Getting this wrong by a day dropped the day-1 correlation from 0.78 to 0.15.
- **Berthoud reports liquid in 0.1" steps.** At 15.2:1, the peak's "1 inch or more" means any measurable precipitation (1.5"), which falls on about half of winter days.
- **In October and May some of Berthoud's liquid is rain,** so the peak is fitted and scored Nov-Apr only. The base gauge measures snowfall itself, so it is scored Oct-May.
- **What's current:** RCC-ACIS (`data.rcc-acis.org`) has the COOP a day after; NCEI runs a week or more behind. SNOTEL `PREC` restarts each water year on Oct 1 (on 5 Oct 2026 nothing had posted since). The resort feed sleeps until opening (last update 28 Sep 2026).
- **What already exists:** NBM publishes snow-exceedance probabilities only out to about 54 h, in 6 h windows, so it can't give 24 h odds for days 1-7.

## Snow-to-liquid ratio (base)

- **Measured** over 80 winters: median 13.6:1 (p10-p90 11.6-16.3). The last six winters ran 14.1-15.2.
- **A single storm day** varies far more: 7.7-19:1. By month: Jan 13.9 down to Apr 10.2.
- **Temperature explains little** (r = -0.23).
- **Fitted against forecast cold liquid: 15.2:1.**
- **Open improvement:** random-forest ratio methods beat operational ones (MAE 2.9-3.7 vs 4-9; Veals 2025). ERA5 (from 1940) could supply training conditions for all 2,214 base storm days.

## Models

Same two winters for every model (2024-03 to 2026-04). Skill day 1 / 3 / 5 / 7:

| | Base | Berthoud | Fool Creek |
|---|---|---|---|
| NBM | 0.63 / 0.43 / 0.26 / 0.23 | 0.64 / 0.42 / 0.24 / 0.19 | 0.62 / 0.44 / 0.25 / 0.20 |
| ECMWF IFS 0.25° | 0.67 / 0.51 / 0.35 / 0.16 | 0.66 / 0.56 / 0.31 / 0.16 | 0.52 / 0.55 / 0.28 / 0.15 |
| ECMWF AIFS (from Feb 2025) | 0.57 / 0.52 / 0.27 / 0.30 | 0.66 / 0.48 / 0.32 / 0.27 | 0.60 / 0.47 / 0.30 / 0.31 |
| GFS (dropped) | 0.67 / 0.37 / 0.24 / 0.14 | 0.60 / 0.44 / 0.17 / 0.12 | 0.51 / 0.39 / 0.14 / 0.10 |
| IFS 9 km (dropped) | 0.61 / 0.39 / 0.33 / 0.12 | 0.65 / 0.53 / 0.28 / 0.17 | 0.57 / 0.42 / 0.29 / 0.13 |
| **Blend** | **0.72 / 0.56 / 0.39 / 0.26** | **0.72 / 0.55 / 0.34 / 0.24** | **0.65 / 0.54 / 0.33 / 0.24** |

- **Source and caveats:**
  - Scored on GribStream's archive, which runs 12Z to 12Z.
  - These two winters were easier than average: NBM's day 1 over six winters was 0.53-0.59.
  - The Open-Meteo archive gives the same blend 0-0.08 lower. Part of that is its day N running about 12 h further ahead.
- **Adding GFS or IFS 9 km leaves the blend equal or worse.**
- **Dropped earlier:**
  - HRRR (worse than NBM on day 1, ends at day 2)
  - GEFS mean (weakest at every lead)
  - GEM (weaker everywhere)
  - ICON (helps day 1 up high, hurts days 3-5, ends at day 6.5)
- **Bias, measured ÷ forecast, day 1 / 3 / 7:**

| Model | Berthoud | Base |
|---|---|---|
| NBM | 1.51 / 1.12 / 0.96 | 1.00 / 0.68 / 0.59 |
| IFS | 1.77 / 2.07 / 2.04 | 0.91 / 1.00 / 0.99 |

- **Raw `snowfall` at the base,** measured ÷ forecast: NBM 0.88-1.00x, ECMWF 1.47x, AIFS 2.24x, GEM 2.1-2.4x, ICON 2.8-6.3x, HRRR 6.7-11.4x. Open-Meteo uses a fixed 7:1 ratio except for NBM.

**How far ahead** (blend; base / Berthoud / Fool Creek):

| Forecast | Skill |
|---|---|
| Day 8 | 0.20 / 0.19 / 0.17 |
| Day 10 | 0.08 / 0.07 / 0.07 |
| Days 1-3 total | 0.73 / 0.70 / 0.67 |
| Days 4-7 total | 0.50 / 0.48 / 0.48 |
| Days 8-14 total | 0.40 / 0.28 / 0.30 over two winters, but -0.05 / -0.04 / 0.05 over the last 1.5 |

## Calibration (`calibrate.py` → `calibration.json`)

**How the forecast is built:**
- **Days:** 24 h ending 08:00 MST, matching the base gauge.
- **Per point × day × model:** liquid = a × cold + b × cold liquid.
  - *Cold liquid* is precipitation in hours ≤ 1 °C.
  - *Cold* is the fraction of such hours, so a warm day forecasts zero.
- **Odds and range:** the mean of the three models falls in one of six bins (< 0.01", 0.01-0.03", 0.03-0.06", 0.06-0.12", 0.12-0.25", ≥ 0.25" liquid). That bin's past days, for days 1-2 / 3-4 / 5-7, give the odds of 1"+ and the 10th-90th percentile of the snow on the days it came.
  - Under 30 past days: the lead groups are pooled.
  - No past days (warm days at the peak, which the winter fit never saw): 0%.
- **Peak truth** is Berthoud's liquid × 15.2, the base's ratio, which is probably conservative.
- **`clim`:** each month's share of days with 1"+, the reference for scoring live.
- **Refit each spring.**

Out of sample, days 1-7:

| Brier skill, Nov-Apr | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Base (vs measured snowfall) | 0.64 | 0.58 | 0.50 | 0.46 | 0.35 | 0.26 | 0.25 |
| Peak (vs Berthoud) | 0.33 | 0.29 | 0.27 | 0.19 | 0.20 | 0.15 | 0.13 |

- **October and May at the base,** days 1-7 together: 0.36.
- **Reliability,** odds shown → share of those days with 1"+:
  - Base: 10 → 6, 20 → 24, 30 → 24, 40 → 38, 50 → 50, 60 → 43, 70 → 71, 80 → 82, 90 → 87.
  - Peak: 20 → 34, 30 → 31, 40 → 43, 50 → 44, 60 → 54, 70 → 74, 80 → 82, 90 → 90.
- **The 10-90% range holds** 86% of snow days at the base and 91% at the peak. That's wider than 80% because snow comes in whole inches, and in 1.5" steps up high.
- **Bins,** Brier skill over days 1-7, base / peak: 4 bins 0.40 / 0.17; **6 bins 0.425 / 0.219**; 8 bins 0.425 / 0.222. The tie goes to fewer.
- **Fitting Oct-May instead** tied at the base. At the peak, Oct-May truth is partly rain, so it can't be judged.
- **A separate bin for warm days** changed nothing: they already land in the driest bin.

**Variants that lost,** scored on the average when the page showed it (base snow skill, days 1 / 2 / 3 / 5 / 7):

| Variant | Skill |
|---|---|
| a + b × all liquid | 0.64 / 0.61 / 0.53 / 0.28 / 0.20, and it turned an October rain week into daily "snow" |
| No intercept | 0.64 / 0.60 / 0.53 / 0.26 / 0.18 (peak day 7 fell to 0.11) |
| 0 or 2 °C cutoff | within 0.02 of 1 °C |
| Temperature-varying ratio | 0.55 / 0.60 / 0.46 |
| NBM's own snowfall | 0.57 / 0.46 / 0.28 |

- **Other things that lost:**
  - Separate ratios per day scored the same as one.
  - As a range, the spread between the models held the outcome only 9-60% of the time.
- **The cutoff's cost:** it misses 5 of 251 light snow days at the peak and 1 of 82 big ones. At the base it catches more snow days (95% vs 94% on day 1).

## Page (`index.html`)

- **How it works:** one request from the browser for three models, base and peak, hourly precipitation and temperature. It applies `calibration.json` with the same formula as `score.py now`, which matched the page cell for cell.
- **What it shows:** every day 1-7 whose odds round to 10% or more at either point, as `lo-hi" NN%`. A blank cell means under 5%. With no such day: `no sno in sight through <day 7>.`
- **The API key is in the page source.** Accepted: there are no overage charges and the key can be rotated.

## Stats and the forecaster (`stats.html`, `FORECASTER.md`, `score.py`)

- **A Claude Code routine runs `FORECASTER.md` twice a day** (09:22 and 15:22 Denver). It reads the NWS Boulder discussion and the upper air, and writes `stats.json` to the `data` branch, which `stats.html` shows.
- **It also sets its own odds for days 1-3,** logged next to the page's in the `data` branch's `log/YYYY-MM.jsonl`. `score.py record` scores both against the gauges with `clim` as the reference.
- **It has to earn its place:** a sample written on 5 Oct 2026 caught what the table can't see (a trough on 12 Oct, Hurricane Rachel's moisture in ECMWF but not GFS). If by 1 May 2027 its Brier score on days 1-3 isn't lower than the page's at both points, delete the routine, `FORECASTER.md` and "what i'm thinking".

## Reproduce

```sh
OPENMETEO_APIKEY=... python3 calibrate.py   # prints the scores above, writes calibration.json
python3 score.py now                        # the page's days 1-7
python3 score.py record STORE               # page vs forecaster so far, from a checkout of the data branch
```

The research scripts are in git history: `f9be182` (ground truth, ratios), `ff7801a` (model selection), `2d194e7` (Open-Meteo skill).
