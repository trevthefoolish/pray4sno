# Research: forecasting snow at Winter Park

The evidence behind every choice in `calibrate.py` and `index.html`.

**Conventions:**
- "Liquid" means water equivalent.
- Seasons run Nov-Apr and are named by their starting year.
- **Skill** = 1 − (squared error ÷ squared error of the monthly average), out of sample. 0 means no better than climatology; 1 means perfect.

## Decisions

1. **Forecast from a calibrated, equal-weight blend of NBM, ECMWF IFS and ECMWF AIFS.** It beats every single model on days 1-2 and ties them on days 3-7. Other models added nothing.
2. **Calibrate per point × model × forecast day.**
   - Raw model liquid is about right at the base but 1.3-2x too low up high, by different amounts per model and lead.
   - Raw model `snowfall` fields are off by up to 11x.
3. **Only cold precipitation counts.** Precipitation in hours at or below 1 °C becomes snow at 15.2:1; rain counts as nothing.
4. **Show days 1-7.** Skill is near zero by day 10, and the week-2 total isn't robust.
5. **Show 0 under 1", plus "up to X".** That cuts the peak's false alarms from 88% to 16% without losing big days.
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
- **Snow:** the mean of the three models × 15.2.
- **"Up to":** the 90th percentile of past outcomes, by days 1-2 / 3-4 / 5-7 and dry / light / heavy forecast (< 0.05", 0.05-0.2", > 0.2" liquid), times the cold fraction.
- **Peak truth** is Berthoud's liquid. The peak uses the base's ratio, which is probably conservative.
- **Refit each spring.**

Out of sample, days 1-7:

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Base snow skill (vs measured snowfall) | 0.61 | 0.66 | 0.52 | 0.41 | 0.34 | 0.27 | 0.24 |
| Peak liquid skill (vs Berthoud) | 0.67 | 0.65 | 0.54 | 0.42 | 0.39 | 0.26 | 0.21 |
| Base: real amount ≤ "up to" | 88% | 88% | 88% | 87% | 89% | 87% | 88% |
| Peak: real amount ≤ "up to" | 90% | 91% | 89% | 89% | 91% | 91% | 92% |

**Variants that lost** (base snow skill, days 1 / 2 / 3 / 5 / 7):

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

**What number to show** (day 1; false alarm = ≥ 1" shown, nothing measured):

| Option | False alarms, peak / base | Big days (≥ 4" shown ≥ 2") | Light days (≥ 1") | Score, peak / base, days 1 / 5 |
|---|---|---|---|---|
| Average | 88% / 10% | 93% / 83% | 98% / 95% | 0.67, 0.39 / 0.61, 0.34 |
| **Average, 0 under 1"** | **16% / 5%** | **93% / 83%** | 70% / 80% | 0.65, 0.39 / 0.60, 0.30 |
| Median | 12% / 6% | 93% / 67% | 64% / 86% | 0.57, 0.26 / 0.48, 0.23 |
| Quantile-matched | 29% / 8% | 93% / 85% | 76% / 90% | 0.55, 0.11 / 0.56, -0.24 |

## Page (`index.html`)

- **How it works:** one request from the browser for three models, base and peak, hourly precipitation and temperature. It applies `calibration.json` with the same formula, which was checked against an independent Python recomputation.
- **What it shows:** the 3-day total (uncut averages), then 7 days of snow with "up to".
- **The API key is in the page source.** Accepted: there are no overage charges and the key can be rotated.
- **Storm replay,** using the run from 12Z on 12 April 2026 (base, 13-19 Apr): page 0 2 2 0 0 3 0; measured 0 2 6 0 0 3 0. Timing was right on all seven days. The 6" beat its "up to 4", the 1-in-10 case.

## Reproduce

```sh
OPENMETEO_APIKEY=... python3 calibrate.py   # prints the scores above, writes calibration.json
```

The research scripts are in git history: `f9be182` (ground truth, ratios), `ff7801a` (model selection), `2d194e7` (Open-Meteo skill).
