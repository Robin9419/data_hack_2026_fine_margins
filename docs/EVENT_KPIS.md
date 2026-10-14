# Adding Event KPIs and Video Links

## Architecture

`backend/app/event_kpis.py` owns reusable snapshot analysis and PBP. `EventAnalysis` indexes snapshots by period and precise millisecond timestamp, retains source row occurrences, parses coordinates, finds later snapshots, and counts nearby opponents. Pass and zone-entry/exit calculators can share this context while defining their own eligibility and sequence rules.

`Content` computes derived results once at startup, keeps them in `derived_kpis`, attaches evaluated pass moments to players, and exposes derived attributes through the existing cards API. Restart the backend after changing inputs or parameters. No database migration is needed: results are currently cached in memory.

## Pass Body Pressure

- Eligible: `EventType=Pass`, `PassResult=Successful`, identified passer and receiver on the same team.
- PBP_PG: opposing skaters within **≤3 m** of the passer in the pass row's snapshot.
- PBP_PE: opposing skaters within **≤3 m** of the receiver in the **first strictly later snapshot** containing receiver coordinates, within **≤2 seconds**, in the same period.
- All receiver-side coordinates come from that same snapshot. The successful outcome confirms completion; the snapshot does not prove the exact reception instant.
- PBP = PBP_PG − PBP_PE. Positive means pressure relief; zero means unchanged; negative means increased pressure.
- Goalkeepers are identified from Shot secondary-player IDs, not lineup slots. This follows this export's documented shot roles; other providers need an explicit roster/role mapping.
- Missing focal or listed opponent coordinates make the observation unavailable. Missing values never become zero and never enter means.
- Opponents absent from a snapshot cannot be reconstructed. Snapshot completeness and role identification must be validated for each new source.

Results retain source row number (1-based data row, excluding header), metric ID, passer/receiver IDs, both timestamps, reception row, both counts, value, eligibility and exclusion reason. Identical rows are separate occurrences: preserve Finley's two simultaneous penalties. Re-import protection must operate on source identity and row occurrence, not timestamp alone.

Player aggregates include mean PBP, positive count/share, eligible/evaluated counts, coverage and supporting event IDs. `/api/analysis/pass-body-pressure` returns all results to signed-in demo users.

A provisional **minimum of 10 evaluated passes** controls ranking eligibility. This is a product rule, not a statistically validated threshold. The “Pressure Reliever” card selects the highest positive mean, breaking ties by evaluated count then player ID. No card is added if nobody qualifies. It is a separate collectible and does not replace existing player cards. More than one card may therefore represent the same player. The current dataset's winner is Joey Muldowney; this is calculated, not hard-coded. PBP does not measure forward progression or overall passing quality.

## Adding Another KPI

1. Define the eligible event types, success outcomes, player roles, units, direction, window and missing-data policy. Inspect actual exported enum values.
2. Add a calculator accepting `EventAnalysis` and explicit parameters. Return event results, player aggregates, exclusions and parameters, following the PBP result shape.
3. Register the calculation in `Content.derived_kpis`. Keep computation out of React and JSON content files.
4. Add metric definitions to `backend/content/metrics.json` with `derived` naming the registered calculation and `aggregate` naming a player aggregate. Include label, format, unit, plain-language definition, source definition and direction.
5. Attach supporting events as moments and set attribute `moment_ids` to their IDs. Filter these IDs when an aggregate uses only a subset of events. Define an appropriate ranking pool and minimum sample count.
6. Add card attributes/types with explicit qualification rules. Inspect distributions and coverage before choosing thresholds.
7. Test spatial boundaries, timing, period boundaries, unsuccessful events, missing data, role exclusions, duplicate occurrences, and aggregation denominators.

For zone crossings, inspect `BluelineCrossingResult` and `BluelineCrossingDirection` first. Team-relative offensive/defensive direction must be established before labeling an entry or exit. Do not assume that every crossing has the same semantics as a successful pass.

## Video Integration

Each PBP moment retains the pass timestamp as its video anchor. `MatchEvents._moment` resolves the arena clip through `Content._camera_clip`; the frontend's existing “Behind this number” and timeline controls display it. PBP moments have no YouTube broadcast mapping: goal highlights are not evidence of a particular pass.

`backend/app/events.py` maps `pass_pressure` to the `pass` window in `backend/content/videos.json`. The current window is **3 seconds before to 5 seconds after** the pass, covering the accepted two-second reception snapshot window. To add another event type, map its moment kind to a window and add that window to the recording configuration.

Place the recording at the configured `recording.file` path and run:

```bash
cd backend
source .venv/bin/activate
python -m scripts.cut_clips
```

The existing cutter now discovers pass moments too, writes `backend/media/clips/<Timestamp>.mp4` and matching `.jpg`, and serves them through `/api/media/clips/`. Restart the backend afterward. Existing clips are skipped; use `--force` if window settings change. Encoding clips can take longer now because successful passes add many events.

Video time is `event Timestamp / 1000 - recording.timestamp_offset`. Confirm synchronization for each recording. Source rows identify KPI occurrences, while a shared timestamp can reuse the same physical video clip. If several moment kinds share a timestamp, the cutter uses the union of their windows so every linked event remains covered. Store both origin and later snapshot timestamps even when the clip is anchored at the origin.

Without generated clips, statistics and pass moments remain visible, with no pass video button. No clips are generated automatically at server startup.
