# Research: forecasting snow at Winter Park

Phase 1 is complete. Every number below comes from a script; see [Reproduce](#reproduce).

**Conventions:**
- "Liquid" means water equivalent.
- A forecast day is the 24 h ending 12Z (5 AM MST).
- Seasons run Nov-Apr and are named by their starting year.
- **Skill** = 1 − (squared error ÷ squared error of the monthly average), out of sample. 0 means no better than climatology; 1 means perfect.

## Answers

1. **Use a calibrated, equal-weight blend of NBM, ECMWF IFS and ECMWF AIFS.**
   - It beats every single model on days 1-2 at all three sites (skill 0.65-0.72 vs 0.62-0.67 for the best single model) and ties them on days 3-7.
   - GFS and IFS at 9 km add nothing to the blend. GEFS, HRRR and GEM tested weaker. ICON is the one untested blend candidate (R4).
2. **Calibration is not optional.**
   - Raw model liquid is about right at the base but **1.3-2x too low** at 11,200 ft. The bias differs by model and by lead day.
   - Open-Meteo's `snowfall` field adds another 1.5-11x error (a fixed 7:1 ratio; NBM is the exception).
3. **Forecast days 1-7.**
   - Day 8 is marginal.
   - Day 10 and beyond show no reliable skill. The days 8-14 total flips between "some skill" and none depending on which winters are scored.
   - Multi-day totals for days 1-3 and 4-7 hold up well (R5).
4. **Snow-to-liquid ratio is the next big lever.**
   - The base's median is 13.6:1 over 80 winters, but a single day varies from 7.7 to 19:1 (p10-p90).
   - Temperature alone explains little.
5. **One data provider, and Open-Meteo is enough.**
   - It serves the same three models live and archived, and its blend scores within 0.08 of GribStream's (R6).
   - It's callable from a browser with no key.
   - GribStream's extra history (NBM back to 2020, leads past day 7) didn't change any decision.

## R1. Ground truth

| Site | Elevation | Measures | Record |
|---|---|---|---|
| Winter Park COOP `USC00059175` (**base truth**) | 9,123 ft | snowfall + liquid, read daily at **08:00** | 1942-2026; 80 complete Nov-Apr seasons |
| Berthoud Summit SNOTEL 335 (upper truth, on the Divide) | 11,300 ft | liquid hourly, depth, temp | liquid since 1978 |
| Fool Creek SNOTEL 1186 (upper truth, drier) | 11,130 ft | liquid hourly, depth, temp | since 2011 |
| Resort feed `mtnpowder.com/feed?resortId=5` | Village / Mid / Summit | reported snowfall, 7 stations, the resort's forecast | current values only; `record.py` starts the archive |

- **Upper gauges vs base liquid:**
  - Berthoud **1.72x** (median of 47 seasons, p10-p90 1.52-2.17)
  - Fool Creek **1.36x** (15 seasons, 1.18-1.78)
  - Berthoud beats Fool Creek every winter (1.22-1.56x) at almost the same elevation, so exposure matters as much as height.
- **No gauge at the peak** (Panoramic Express, about 12,000 ft). Calibrate the peak to Berthoud, which sits on the Divide like Parsenn and the Cirque. Then check it against the resort's Summit reports once recorded.
- **Caveats:**
  - Both gauge types undercatch snow in wind: the COOP's unshielded 8" gauge by up to about 70% (Yang 1998), SNOTEL by about 30% at 2-4 m/s (Fassnacht 2004).
  - Resort reports are not independent measurements.

## R2. Snow-to-liquid ratio (base: measured snowfall ÷ gauge liquid)

- **All 80 winters:** median **13.6**, p10-p90 11.6-16.3. The last six winters were 14.1-15.2; decade medians range from 12.2 to 15.7, which looks like observer practice.
- **Single storm days** (≥ 0.2" liquid): median 12.5, p10-p90 7.7-19.0 (n = 2,214).
- **By month:** Nov 12.5, Dec 13.6, Jan 13.9, Feb 13.3, Mar 12.0, Apr 10.2.
- **Temperature explains little:** r = -0.23 against Berthoud's mean temperature the day before.
- **At elevation:** SNOTEL depth gain per inch of liquid is 8.3 (Berthoud) and 10.0 (Fool Creek). That's a floor, not the ratio, because new snow settles.
- **Literature:** random-forest ratio methods reach MAE 2.9-3.7 vs 4-9 for operational methods (Veals 2025; Pletcher 2024).
- **Next step:** ERA5 reanalysis (from 1940) can supply upper-air conditions for all 2,214 base storm days. That gives a long training set for a better ratio.

## R3. Archived forecasts

| Source | What it has | Used |
|---|---|---|
| GribStream `/runs` (paid) | NBM 2020-, GFS 2021-, IFS 0.25° 2024-, AIFS 2025- at every lead, point queries | **Model selection** (R4): 6 winters, 2,700 runs. Dropped after R6 |
| Open-Meteo Previous Runs (free) | 7 models from 2024, days 1-7 | **The source going forward** (R6) |
| AWS NBM GRIB2 | NBM 2020- | Cross-check only: matches GribStream; 145 s CPU per run |

**How each model's precipitation comes back** (all checked against the data):

| Model | Format |
|---|---|
| NBM | 1-h totals to 36 h, then 6-h totals (rounded to 0.01") |
| IFS | running total, in metres |
| AIFS | running total, in mm |
| GFS (dropped) | 6-h buckets through 2024; running total from 2025 |

## R4. Which models (same two winters for every model, 2024-03 to 2026-04)

Skill by forecast day; the blend is the equal-weight mean of the calibrated NBM, IFS and AIFS. Day 1 / 3 / 5 / 7:

| | Base | Berthoud | Fool Creek |
|---|---|---|---|
| NBM | 0.63 / 0.43 / 0.26 / 0.23 | 0.64 / 0.42 / 0.24 / 0.19 | 0.62 / 0.44 / 0.25 / 0.20 |
| ECMWF IFS 0.25° | 0.67 / 0.51 / 0.35 / 0.16 | 0.66 / 0.56 / 0.31 / 0.16 | 0.52 / 0.55 / 0.28 / 0.15 |
| ECMWF AIFS (since Feb 2025) | 0.57 / 0.52 / 0.27 / 0.30 | 0.66 / 0.48 / 0.32 / 0.27 | 0.60 / 0.47 / 0.30 / 0.31 |
| GFS (dropped) | 0.67 / 0.37 / 0.24 / 0.14 | 0.60 / 0.44 / 0.17 / 0.12 | 0.51 / 0.39 / 0.14 / 0.10 |
| ECMWF IFS 9 km (dropped) | 0.61 / 0.39 / 0.33 / 0.12 | 0.65 / 0.53 / 0.28 / 0.17 | 0.57 / 0.42 / 0.29 / 0.13 |
| **Blend** | **0.72 / 0.56 / 0.39 / 0.26** | **0.72 / 0.55 / 0.34 / 0.24** | **0.65 / 0.54 / 0.33 / 0.24** |

- **Adding GFS and IFS 9 km leaves the blend equal or worse.** Higher resolution (9 km vs 25 km) did not help once both are calibrated.
- **These two winters were easier than average.** Over all six winters NBM scored 0.53-0.59 on day 1 (vs 0.62-0.64 here), so expect real skill somewhat below the table.
- **Bias to correct** (measured ÷ forecast, day 1 / 3 / 7):

| Model | Berthoud | Base |
|---|---|---|
| NBM | 1.51 / 1.12 / 0.96 | 1.00 / 0.68 / 0.59 |
| IFS | 1.77 / 2.07 / 2.04 | 0.91 / 1.00 / 0.99 |
| AIFS | 1.99 / 1.91 / 1.87 | 1.03 / 0.97 / 0.94 |

  NBM's precipitation shrinks with lead; ECMWF's error doesn't. Calibration must be per site × model × lead.
- **Dropped earlier:**
  - **HRRR:** lost to NBM on day 1 at every gauge and only reaches day 2.
  - **GEFS mean:** among the weakest at every lead.
  - **GEM:** weaker than ECMWF everywhere in the two-winter Open-Meteo test.
  - **ICON:** weaker at the base and Fool Creek but about equal at Berthoud (day 3 correlation 0.68 vs 0.69). Its runs end at day 7.5 and GribStream doesn't archive it, so it was never tested in the blend. It's an open candidate.
- **Raw `snowfall` fields as-is** (Open-Meteo, base, measured ÷ forecast):

| Model | Ratio |
|---|---|
| NBM | 0.88-1.00x |
| ECMWF | 1.47x |
| AIFS | 2.24x |
| GEM | 2.1-2.4x |
| ICON | 2.8-6.3x |
| HRRR (which Open-Meteo stores as `gfs_seamless`) | 6.7-11.4x |

## R5. How far ahead

Blend skill, same winters as R4 (base / Berthoud / Fool Creek):

| Forecast | Skill |
|---|---|
| Day 1 | 0.72 / 0.72 / 0.65 |
| Day 3 | 0.56 / 0.55 / 0.54 |
| Day 5 | 0.39 / 0.34 / 0.33 |
| Day 7 | 0.26 / 0.24 / 0.24 |
| Day 8 | 0.20 / 0.19 / 0.17 |
| Day 10 | 0.08 / 0.07 / 0.07 |
| Days 1-3 total | 0.73 / 0.70 / 0.67 |
| Days 4-7 total | 0.50 / 0.48 / 0.48 |
| Days 8-14 total | 0.40 / 0.28 / 0.30, but **-0.05 / -0.04 / 0.05** over the last 1.5 winters: not robust |

**Show daily amounts for days 1-7, plus totals for days 1-3 and 4-7.** Nothing beyond day 8.

## R6. Data provider: Open-Meteo vs GribStream

The same blend scored on Open-Meteo's archive (same winters; day 1 / 3 / 5 / 7):

| Source | Base | Berthoud | Fool Creek |
|---|---|---|---|
| GribStream | 0.72 / 0.56 / 0.39 / 0.26 | 0.72 / 0.55 / 0.34 / 0.24 | 0.65 / 0.54 / 0.33 / 0.24 |
| Open-Meteo | 0.70 / 0.55 / 0.33 / 0.20 | 0.67 / 0.54 / 0.38 / 0.21 | 0.57 / 0.49 / 0.34 / 0.19 |

- **Open-Meteo scores 0-0.08 lower.** Part of that is its archive's definition of day N, about 12 h further ahead, so it's slightly conservative. Single models go both ways (its IFS beats GribStream's on some days).
- **What GribStream added beyond Open-Meteo:**
  - NBM back to 2020: four more winters for one of three blend members.
  - Lead times past 7 days, which turned out to have no reliable skill.
- **ICON** (Open-Meteo only) helps day 1 at the upper gauges (Fool Creek blend 0.57 → 0.65) but slightly hurts days 3-5, and its runs end at day 6.5. No consistent gain, so it stays out.

## R7. Live pipeline and cost

**GribStream** serves NBM, IFS and AIFS live, from the same API the calibration was fit on.

| | |
|---|---|
| Credits per refresh (both forecast points) | about 300 |
| Every 3 h | about 2.4k credits/day, within the free tier (about 6k/day observed) |
| Hourly | about 7.2k/day: Pro, $9.90/mo |
| Open-Meteo | not needed in the final design. ERA5, if the snow-ratio work uses it, is available without the paid plan for non-commercial use |

## Gotchas found (fixed in code)

- **NRCS dates each daily SNOTEL reading by the day it closes (24:00).** A one-day misalignment dropped the day-1 correlation from 0.78 to 0.15.
- **GribStream quirks:**
  - A quota cut truncates the response it lands in (HTTP 200), so batches are discarded on a quota stop.
  - The API throttles request rate (429), and a single request may span at most 92 days.
  - NOAA's missing value (9.999e20) can pass through.
  - GFS switched formats in 2025, and tiny rounding dips can look like resets.
- **Open-Meteo's `gfs_seamless` short-range archive is HRRR.**

## Reproduce

```sh
python3 research/openmeteo.py              # Open-Meteo archive (free API)
python3 research/skill.py 2024-03-01       # R5 and the Open-Meteo rows of R6
```

Scripts whose job is done live in git history:

| Commit | Script | What it produced |
|---|---|---|
| `f9be182` | `truth.py` | R1, R2 |
| `f9be182` | `openmeteo.py` (old) | as-is bias, early lead tests |
| `f9be182` | `nbm.py` | raw AWS cross-check |
| `ff7801a` | `gribstream.py`, `skill.py` (GribStream source) | the R4 table and the GribStream rows of R6 |
| `2d70f95` | `ifs9.py`, GFS decoding | dropped candidates |

Downloads are cached in `.cache/` (gitignored). No API keys needed.
