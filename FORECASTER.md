# Forecaster

A Claude Code routine runs this twice a day (09:22 and 15:22 Denver). It writes the stats page and sets its own
odds, which are scored against the page's. If by May 1 its Brier score on days 1-3 isn't lower than the page's at
both points, delete this file, the routine, and "what i'm thinking" (see RESEARCH.md).

## Each run

1. Put the data branch next to the code:
   `git fetch origin data && git worktree add --detach store FETCH_HEAD`
2. Run `python3 score.py now` (the page's days 1-7) and `python3 score.py record store` (how the page and you have
   done so far; lower Brier is better).
3. Read the latest NWS Boulder forecast discussion: get `https://api.weather.gov/products/types/AFD/locations/BOU`,
   then the newest product's `@id`, then its `productText`.
4. Read the upper air over the peak, ECMWF against GFS:
   `https://customer-api.open-meteo.com/v1/forecast?latitude=39.8443&longitude=-105.7819&hourly=wind_direction_700hPa,wind_speed_700hPa,relative_humidity_700hPa,geopotential_height_500hPa,temperature_2m&models=ecmwf_ifs025,gfs_seamless&forecast_days=10&timezone=America%2FDenver&apikey=bSvD5raxPiFWRcz4`
   Moist northwest flow at 700 hPa with cold air aloft is what snows on Winter Park; southwest flow dries it out.
5. Set your odds of 1" or more of snow at the peak and at the village for days 1-3 (each the 24 hours ending 8 AM),
   in 10% steps. Start from the page's. Move only for a reason the page can't see (the storm track, the flow, the
   moisture, the cold air's timing, a model it doesn't use), and say why in "what i'm thinking".
6. Append one line to `store/log/YYYY-MM.jsonl` (this UTC month), with the page's `odds` from step 2 (leave out a
   point whose cell is `-`):
   `{"written": "<UTC ISO time>", "days": [{"end": "<YYYY-MM-DD>", "peak": {"page": 0.22, "forecaster": 0.3}, "base": {"page": 0.0, "forecaster": 0.0}}, ...]}`
7. Write `store/stats.json`: `{"written": "<UTC ISO time>", "doing": ["..."], "thinking": ["...", "..."]}`
   - **doing:** 1-2 sentences, only from step 2's `record`: how many forecasts have been scored, how many had snow,
     and the page's, your, and climatology's Brier scores. Before any are scored, say so.
   - **thinking:** 1-2 short paragraphs: what's coming and why, what would make it better or worse, and the day
     you'll know more.
   - **Voice:** lowercase, plain ASCII, first person, no hype. Days as `mon 10/12`; `night` is fine for timing.
     Every number must match step 2 or a source you read.
8. Check that both files parse as JSON and are ASCII, then:
   `cd store && git add log stats.json && git commit -m "Forecaster run" && git push origin HEAD:refs/heads/data`
   If the push is refused, write the same two files with the GitHub MCP tool `create_or_update_file` on branch `data`.

Touch nothing else: no other branch, no pull request, no comments.
