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

## Pass Packing (frozen-opponent variant)

`pass_packing` reuses successful-pass eligibility and the first strictly later receiver snapshot within 2 seconds from PBP. Only opposing skaters count; goalkeepers are excluded. All opponent positions are frozen at pass release. The receiver's x coordinate comes from the later snapshot; later opponent movement is ignored.

Project into attacking x direction (+1 or −1). Count opponents strictly between passer and receiver x positions: positive for forward passes, negative for backward passes. A sideways pass or a backward pass crossing no opponents is zero. Opponents exactly level with either endpoint are not counted. This is longitudinal packing, not a geometric passing-lane model.

`infer_attack_directions` estimates direction independently per period from the median x position of the opposing goalkeeper. Both teams must have goalkeeper evidence on opposite sides and at least 10 m from center. Otherwise the direction is unavailable. The current export is normalized: Home attacks +x and Away attacks −x in all three periods. Do not blindly alternate direction each period. Another provider should supply verified `(period, side) -> +1/-1` mappings through the calculator argument.

Missing origin/player/opponent coordinates, reception snapshots, or direction produce unavailable results. Results store both source rows/timestamps, origin and reception x, attack direction, and IDs of bypassed/restored opponents. Aggregates include signed total and mean, positive share/count, coverage, and evaluated counts. Rankings retain the provisional minimum of 10 evaluated passes.

Registered as `Content.derived_kpis['pass_packing']`; authenticated endpoint: `/api/analysis/pass-packing`. `packing_mean` and `packing_total` are available as card metrics. They are displayed alongside average PBP on the Pressure Reliever card; Packing does not change that award's PBP-based winner. The selection of one passing award per category is not implemented by this KPI addition.

`pass_packing` moments link to the same pass timestamp and `pass` video window as PBP. Existing clips can be reused without recutting. The clip cutter ignores non-final/test-game events and cards without moments. Packing is currently computed only from the real final event export, not inferred for other games from aggregate statistics.


## Progression Master Award

`Content._add_progression_card` adds a separate `progression-master` collectible for the highest **positive mean Packing**, with the calculator's minimum evaluated-pass threshold (currently 10). Ties favor more evaluated passes, then the lexicographically greatest player ID, for deterministic selection. No card is created if nobody qualifies. The winner is calculated from the real final events; other games do not receive invented Packing awards.

The card shows average Packing, signed total Packing, and the share of evaluated passes with positive Packing. Supporting event links for the share include only positive passes; mean and total include all evaluated passes, including zero and negative values. When available, the highlight is the winner's highest positive-Packing pass clip (earliest timestamp breaks ties). Existing pass clips are reused. The normal collection, trivia, and final-game availability rules apply. Pressure Reliever remains independently awarded using PBP; selecting only one award per passing category remains future work.

## Expected Assists (xA) and Chance Architect

`expected_assists` evaluates each `Shot` row once, including `ShotResult=Goal`. Separate `Goal` rows never receive additional credit. A valid, finite `ShotXG` between 0 and 1 and an identified shooter/team are required; zero is valid, missing xG is not zero.

Search backward in precise timestamp order within the same period for the **last successful pass** from an identified teammate to the shooter, strictly before the shot and at most **4 seconds** earlier. Source-row order breaks equal-timestamp ordering; a pass with exactly the shot timestamp is not accepted. Opposing `PuckControlState=HomeControl/AwayControl` cancels attribution. A successful opponent pass also establishes intervening possession. Loose/contested puck states alone do not cancel attribution. No extra reception-coordinate requirement is introduced for this KPI: the successful outcome is the completion evidence.

The passer receives xA equal to shot xG. Each shot is credited to at most one passer; one pass can prepare multiple shots within the window unless opposing control intervenes. Rebounds without another successful pass can therefore retain the same passer under this definition. Exclusions record missing/invalid xG, unknown shooter, no qualifying pass, and intervening opponent control. This is project-defined chance attribution, not necessarily the provider's or official assist definition.

Results retain pass and shot source rows/timestamps, shooter, credited passer and value. Player statistics are total xA, attributed shot count, and average xG of attributed shots. Means use attributed shots only; a player with no credited shots has no mean. The current generic eligible/evaluated counts and coverage for these player aggregates describe credited shots, not the proportion of every pass successfully evaluated; match-wide attribution coverage must be read from the shot-level results and exclusions.

Registered as `derived_kpis['expected_assists']`; authenticated endpoint `/api/analysis/expected-assists`. Metrics: `xa_total`, `xa_assisted_shots`, `xa_mean`. The provisional **Chance Architect** award selects the highest positive total xA, without a minimum pass count. Ties favor more attributed shots, then player ID. No card is created if nobody has positive xA. Only the real final event export supplies these awards.

Supporting `expected_assist` moments belong to the passer and anchor video at the **shot timestamp**, while retaining the pass timestamp for traceability. The `expected_assist` recording window is **7 seconds before to 3 seconds after** the shot, covering a pass up to 4 seconds earlier. The card highlight selects the highest-xG attributed shot with a camera clip. No unrelated broadcast replay is attached to xA moments.

Existing shot clips may be too short for the new window. Run `python -m scripts.cut_clips --force` and restart the backend to regenerate clips with the union of all required event windows. Clip generation remains manual.
