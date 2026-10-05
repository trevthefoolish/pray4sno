# Research: forecasting snow at Winter Park

**Phase 1 status:** ground truth and snow ratio are done. Skill by lead day is done for days 1-7 over two winters (Open-Meteo). Six-winter, day 1-16 skill is waiting on GribStream quota (see [Decisions](#decisions-needed)).

Every number here comes from a script in `research/`; see [Reproduce](#reproduce). "Liquid" means water equivalent. Windows are 24 h. Seasons run Nov-Apr and are named by their starting year.

## Bottom line so far

1. **There is good truth at the base and decent truth up high. The resort's own numbers have to be recorded from now on.**
   - The base gauge has 80 complete winters, read daily at 08:00.
   - Two SNOTEL gauges at about 11,200 ft have hourly liquid since 1978 and 2011.
   - No archive of the resort's Base / Mid / Summit report exists; `record.py` starts one.
2. **Raw model output is badly wrong here, and wrong differently per model, per elevation and per lead day.**
   - Every model's liquid is roughly right at the base but 1.3-2x too low at 11,300 ft. The models flatten the mountain.
   - Open-Meteo's `snowfall` field adds another 1.5-11x error on top of that.
   - Calibration has to be per point × model × lead.
3. **No single model wins.**
   - NBM is the best on day 1 (correlation 0.78-0.79).
   - ECMWF IFS keeps skill longest (0.69-0.75 at day 3 vs NBM's 0.55-0.61).
   - By day 7 every model is down to 0.2-0.35.
   - That favors a lead-dependent blend over any one model.
4. **Snow ratio is the second big lever.**
   - The base averages 13.6:1 over 80 winters.
   - A single day varies from 7.7 to 19:1 (p10-p90).
   - Temperature alone explains little (r = -0.23). Studies find machine-learning ratio methods roughly halve the error of operational ones.

## R1. Ground truth

| Site | Elevation | Measures | Record | Use |
|---|---|---|---|---|
| Winter Park COOP `USC00059175` | 9,123 ft | snowfall + liquid, daily, read **08:00** | 1942-2026; 80 of 85 Nov-Apr seasons ≥ 90% complete | **Base truth** |
| Berthoud Summit SNOTEL 335 | 11,300 ft | liquid hourly, depth, temp | liquid 1978-, depth 2002- | Upper truth (on the Divide) |
| Fool Creek SNOTEL 1186 | 11,130 ft | liquid hourly, depth, temp | 2011- | Upper truth (drier) |
| Resort feed (`mtnpowder.com/feed?resortId=5`) | Village / Mid-Mountain / Summit | reported snowfall, 7 stations, resort forecast | **current values only** | Recorded hourly from Oct 2026 by `record.py` |

- **Observation time:** 08:00 on 3,922 of 3,923 days since 2016 (GHCN attributes). So the base day ends at 8 AM.
- **The upper gauges get much more liquid than the base** (Nov-Apr):
  - Berthoud Summit: **1.72x** (median of 47 seasons, p10-p90 1.52-2.17)
  - Fool Creek: **1.36x** (15 seasons, 1.18-1.78)
  - Berthoud gets 1.22-1.56x Fool Creek **every** winter at nearly the same elevation, so exposure on the Divide matters as much as height.
  - For comparison, the resort's reported mid-mountain season totals ran 1.27-1.43x the COOP (2024-25, 2025-26).
- **No gauge exists at the peak** (Panoramic Express, about 12,000 ft). SNOTEL depth gain per inch of liquid is 8.3:1 at Berthoud and 10.0:1 at Fool Creek. That's a floor, not the ratio, because new snow settles while it falls.
- **Caveats:**
  - The COOP's unshielded 8" gauge undercatches snow, by up to about 70% at 6-7 m/s wind (Yang 1998). That inflates its measured ratio.
  - SNOTEL Alter-shielded gauges catch about 70% at 2-4 m/s (Fassnacht 2004).
  - Resort reports are not independent measurements, and published resort averages conflict (322-345").
- **Peak truth (recommendation):** calibrate the peak to Berthoud Summit liquid times the snow ratio. Berthoud is on the Divide, like Parsenn and the Cirque. Then check it, and replace it where better, against the resort's Summit-zone reports as `record.py` accumulates them.

## R2. Snow-to-liquid ratio (base, measured snowfall ÷ gauge liquid)

**Season ratio, all 80 winters:** median **13.6**, p10-p90 11.6-16.3.

| Decade | Median |
|---|---|
| 1940s | 14.8 |
| 1950s | 15.2 |
| 1960s | 14.1 |
| 1970s | 13.1 |
| 1980s | 15.7 |
| 1990s | 12.9 |
| 2000s | 12.2 |
| 2010s | 13.2 |
| 2020s | 14.6 |

- **The last 6 winters were 14.1-15.2.** The drift between decades looks like observer practice, so calibrate on recent winters.
- **A single storm day (≥ 0.2" liquid)** has median 12.5, p10-p90 7.7-19.0 (n = 2,214).
- **By month:** Nov 12.5, Dec 13.6, **Jan 13.9**, Feb 13.3, Mar 12.0, Apr 10.2.
- **Temperature explains little.** Against Berthoud's mean temperature the day before: 0s °F 12.5, 10s 13.1, 20s 11.3, 30s 10.3; r = -0.23.
- **Literature:**
  - Rockies modal ratio is about 15 (Baxter 2005).
  - Alta's median is 13.3 (Alcott & Steenburgh 2010).
  - Random-forest ratio methods reach MAE 2.9-3.7 vs 4-9 for operational methods (Veals 2025; Pletcher 2024).
  - NBM blends four methods (MaxTAloft, Cobb, Roebber, 850-700 mb thickness).

## R4a. Models as-is (Open-Meteo, stitched first hours of each run)

Ratios are measured ÷ forecast; above 1 means the model is too low.

| Model | Base liquid | Base `snowfall` field | Berthoud liquid | Fool Creek liquid | Winters |
|---|---|---|---|---|---|
| NBM | 0.88-1.13x | **0.88-1.00x** (NBM's own ratio, about 16:1) | 1.33-1.57x | 1.27-1.54x | 2024-26 |
| ECMWF IFS 0.25° | 0.71-0.97x | 1.47x | 1.76-1.84x | 1.42-1.48x | 2024-26 |
| ECMWF AIFS | 1.01x | 2.24x | 1.78x | 1.44x | 2025-26 |
| ICON | 0.89-1.01x | 2.8-6.3x | 1.38-1.49x | 0.94-1.47x | 2022-26 |
| GEM | 0.74-0.94x | 2.1-2.4x | 1.54-1.86x | 0.97-1.06x | 2023-26 |
| HRRR (= "GFS seamless", first hours) | **2.4-3.9x** | **6.7-11.4x** | 2.2-2.9x | 1.9-2.9x | 2021-26 |

- Open-Meteo's `snowfall` assumes **7:1** ("divide by 7"; NBM is the exception).
- In the US, Open-Meteo's `gfs_seamless` uses HRRR for the first hours. Its stitched archive is therefore HRRR, and it matches `ncep_hrrr_conus` exactly.
- **Correction to the planning notes:** the "GFS 6-11x too low" figure was really **HRRR**. The raw GFS archive (GribStream) will measure GFS separately.

## R4b. Skill by lead day (Open-Meteo Previous Runs, winters 2024-25 and 2025-26)

Daily liquid. Base windows end 08:00 (COOP); upper windows end 00:00 (SNOTEL).

**Correlation, base / Berthoud:**

| Model | Day 1 | Day 3 | Day 5 | Day 7 |
|---|---|---|---|---|
| NBM | **0.78** / **0.78** | 0.57 / 0.55 | 0.43 / 0.42 | 0.35 / **0.34** |
| ECMWF IFS | **0.78** / 0.73 | **0.71** / **0.69** | **0.55** / 0.48 | 0.30 / 0.32 |
| ICON | 0.70 / 0.75 | 0.57 / 0.68 | 0.40 / **0.51** | — |
| GEM | 0.74 / 0.59 | 0.62 / 0.44 | 0.31 / 0.28 | 0.22 / 0.18 |
| GFS seamless | 0.69 / 0.71 | 0.50 / 0.53 | 0.33 / 0.49 | 0.20 / 0.23 |

**Bias (measured ÷ forecast) at Berthoud:**

| Model | Day 1 | Day 3 | Day 7 |
|---|---|---|---|
| NBM | 1.41x | 0.97x | 0.89x |
| ECMWF | 1.96x | 2.01x | 1.68x |
| GEM | 1.75x | 2.04x | 1.92x |

- **NBM's precipitation shrinks with lead.** At the base its bias goes 0.95x at day 1 → 0.64x at day 3, so it puts down more precipitation at longer leads than actually falls. Bias depends on lead, so calibration must too.
- **GFS-seamless bias grows with lead** at the upper gauges (1.2x → 4.6x by day 7).
- **Method lesson:** a single ratio that fixes the season total often *raises* daily MAE, because MAE rewards forecasting too little on a skewed variable. Phase 2 must score bias and a proper probabilistic score (CRPS), not MAE alone.

## R3. Archives of past forecasts, and cost

| Source | Models | Back to | Lead | Cost | Verdict |
|---|---|---|---|---|---|
| Open-Meteo Previous Runs | NBM, IFS, AIFS, GFS, HRRR, ICON, GEM | about Jan 2024 | ≤ 7 days | your paid key | **Used above.** Paying doesn't extend the history. |
| GribStream `/runs` | NBM (Oct 2020), GEFS (Oct 2020), GFS (Mar 2021), HRRR (2014), IFS (Mar 2024), AIFS (Feb 2025), +ensembles | see left | 2-16 days | free about 10k credits/day; Pro $9.90-$244.70/mo | **Best route to 6 winters × 16 days** |
| AWS NBM GRIB2 (byte ranges) | NBM | Sep 2020 | 11 days | free | Works and matches GribStream, but **145 s CPU per run**: about 44 h for 6 winters |
| AWS ECMWF open data | IFS/AIFS + 51-member ensemble | Jan 2023 | 15 days | free | Heavy global GRIB; fallback only |
| GEFSv12 reforecast | GEFS, 5 members | 2000-2019 | 16 days (35 weekly) | free | About 23 MB per run-variable; use only if R5 needs 20 winters |

**GribStream checks**
- **NBM run 2025-01-01 12Z vs the raw AWS GRIB:** the snow ratio is identical at every lead. Precipitation and snow match exactly past 36 h.
- **Hours 1-36:** values are 1-h totals rounded to 0.01", so summing six of them reads about 0.25 mm low per 6 h.
- **Each model returns precipitation differently;** `research/gribstream.py` documents the format per model.
- **Credits:** about 150 per run for NBM, all four sites together. The full 6-model backfill is about 585k credits.
- **Free tier:** stopped after 45 NBM runs (about 10k credits a day), so the full backfill would take about 2 months.

## R5. Horizon (how far ahead is worth showing)

**So far, over 2 winters and days 1-7:**
- Daily correlation falls from about 0.78 on day 1 to about 0.5 on day 5 and about 0.2-0.35 on day 7, for every model.
- That's consistent with the literature: daily point precipitation has little useful skill past about day 5-7 (ECMWF headline scores; GEFS reforecast studies).

**Pending:** days 8-16 and multi-day totals or probabilities, using GribStream GEFS, GFS, IFS and NBM over 6 winters.

## R6. Live pipeline (must equal the calibration source)

- **Open-Meteo (paid key):** one call returns all models at both points; history about 2 winters; 7-day archive. Cheapest and simplest.
- **GribStream:** 6 winters of history, raw models and ensembles. Needs its own live calls (about 150-600 credits per refresh). The token has to stay server-side, in GitHub Actions.
- **Leading option:** a GitHub Actions job using whichever source the backtest favors, with Open-Meteo for any model whose calibration it alone supports.
- **Decision deferred until the 6-winter backtest shows whether the longer history actually improves calibration.**

## Methodology gotchas found (fixed in code)

- **NRCS dates each daily SNOTEL reading by the day it closes (24:00).** Misaligning by one day dropped the day-1 correlation from 0.78 to 0.15.
- **A GribStream quota cut truncates the response it lands in,** while still returning HTTP 200. Requests are now one run each, and the last run before a quota stop is discarded.
- **Open-Meteo's `gfs_seamless` short-range archive is HRRR.**
- **NBM hourly totals are rounded to 0.01".** That's fine for calibration, since its bias is lead-specific.

## Decisions needed

1. **Merge `record.py` and `.github/workflows/record.yml` to `main`.** Scheduled workflows only run from the default branch. Until it runs, no resort data is being saved.
2. **GribStream tier for the backfill** (about 585k credits):

| Plan | Credits/day | Time to finish | Price |
|---|---|---|---|
| Free | about 10k | about 2 months | $0 |
| Pro | 48k | about 12 days | $9.90/mo |
| Pro 2x | 96k | about 6 days | $18.80/mo |
| **Pro 8x** | 384k | **about 2 days** | **$67.80/mo** |

   **Recommended:** Pro 8x for one month, then drop to the tier the live pipeline needs. Ensemble members (GEFS 31, ECMWF 51) multiply credits per member, so they're excluded until the deterministic backtest shows where they'd help.

## Reproduce

```sh
python3 research/truth.py                       # R1, R2 (NCEI is slow: ~20 min first run)
OPENMETEO_APIKEY=... python3 research/openmeteo.py asis
OPENMETEO_APIKEY=... python3 research/openmeteo.py leads
GRIBSTREAM_TOKEN=... python3 research/gribstream.py nbm 2020 2025   # resumable
python3 research/nbm.py 2025-01-01T12           # raw AWS cross-check (needs `pip install eccodes`)
```

All downloads are cached in `.cache/` (gitignored). API keys come from the environment and never reach disk.
