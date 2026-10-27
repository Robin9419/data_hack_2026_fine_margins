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

A provisional **minimum of 10 evaluated passes** controls ranking eligibility. This is a product rule, not a statistically validated threshold. The user-selected name **Pressure Breaker** replaces Pressure Reliever. Its stable card ID remains `pressure-reliever`, preserving ownership, artwork and links. The “Pressure Breaker” card selects the highest positive mean, breaking ties by evaluated count then player ID. No card is added if nobody qualifies. It is a separate collectible and does not replace existing player cards. More than one card may therefore represent the same player. The current dataset's winner is Joey Muldowney; this is calculated, not hard-coded. PBP does not measure forward progression or overall passing quality.

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

Registered as `Content.derived_kpis['pass_packing']`; authenticated endpoint: `/api/analysis/pass-packing`. `packing_mean` and `packing_total` are available as card metrics. They are displayed alongside average PBP on the Pressure Breaker card; Packing does not change that award's PBP-based winner. The selection of one passing award per category is not implemented by this KPI addition.

`pass_packing` moments link to the same pass timestamp and `pass` video window as PBP. Existing clips can be reused without recutting. The clip cutter ignores non-final/test-game events and cards without moments. Packing is currently computed only from the real final event export, not inferred for other games from aggregate statistics.


## Progression Master Award

`Content._add_progression_card` adds a separate `progression-master` collectible for the highest **positive mean Packing**, with the calculator's minimum evaluated-pass threshold (currently 10). Ties favor more evaluated passes, then the lexicographically greatest player ID, for deterministic selection. No card is created if nobody qualifies. The winner is calculated from the real final events; other games do not receive invented Packing awards.

The card shows average Packing, signed total Packing, and the share of evaluated passes with positive Packing. Supporting event links for the share include only positive passes; mean and total include all evaluated passes, including zero and negative values. When available, the highlight is the winner's highest positive-Packing pass clip (earliest timestamp breaks ties). Existing pass clips are reused. The normal collection, trivia, and final-game availability rules apply. Pressure Breaker remains independently awarded using PBP; selecting only one award per passing category remains future work.

## Expected Assists (xA) and Chance Architect

`expected_assists` evaluates each `Shot` row once, including `ShotResult=Goal`. Separate `Goal` rows never receive additional credit. A valid, finite `ShotXG` between 0 and 1 and an identified shooter/team are required; zero is valid, missing xG is not zero.

Search backward in precise timestamp order within the same period for the **last successful pass** from an identified teammate to the shooter, strictly before the shot and at most **4 seconds** earlier. Source-row order breaks equal-timestamp ordering; a pass with exactly the shot timestamp is not accepted. Opposing `PuckControlState=HomeControl/AwayControl` cancels attribution. A successful opponent pass also establishes intervening possession. Loose/contested puck states alone do not cancel attribution. No extra reception-coordinate requirement is introduced for this KPI: the successful outcome is the completion evidence.

The passer receives xA equal to shot xG. Each shot is credited to at most one passer; one pass can prepare multiple shots within the window unless opposing control intervenes. Rebounds without another successful pass can therefore retain the same passer under this definition. Exclusions record missing/invalid xG, unknown shooter, no qualifying pass, and intervening opponent control. This is project-defined chance attribution, not necessarily the provider's or official assist definition.

Results retain pass and shot source rows/timestamps, shooter, credited passer and value. Player statistics are total xA, attributed shot count, and average xG of attributed shots. Means use attributed shots only; a player with no credited shots has no mean. The current generic eligible/evaluated counts and coverage for these player aggregates describe credited shots, not the proportion of every pass successfully evaluated; match-wide attribution coverage must be read from the shot-level results and exclusions.

Registered as `derived_kpis['expected_assists']`; authenticated endpoint `/api/analysis/expected-assists`. Metrics: `xa_total`, `xa_assisted_shots`, `xa_mean`. The provisional **Chance Architect** award selects the highest positive total xA, without a minimum pass count. Ties favor more attributed shots, then player ID. No card is created if nobody has positive xA. Only the real final event export supplies these awards.

Supporting `expected_assist` moments belong to the passer and anchor video at the **shot timestamp**, while retaining the pass timestamp for traceability. The `expected_assist` recording window is **7 seconds before to 3 seconds after** the shot, covering a pass up to 4 seconds earlier. The card highlight selects the highest-xG attributed shot with a camera clip. No unrelated broadcast replay is attached to xA moments.

Existing shot clips may be too short for the new window. Run `python -m scripts.cut_clips --force` and restart the backend to regenerate clips with the union of all required event windows. Clip generation remains manual.

## Zone entries / exits: BLCxG and controlled exits

Implemented on 2026-10-27 in `event_kpis.py`, using the shared `EventAnalysis`. Registered as `derived_kpis['blc_xg']` and `derived_kpis['controlled_zone_exits']`. Authenticated endpoints: `/api/analysis/blc-xg` and `/api/analysis/controlled-zone-exits`.

### Crossing classification and eligibility

The export contains `BluelineCrossingDirection=TowardsOpponent/TowardsHome` and outcomes `PossessionMaintained`, `PossessionLost`, `PuckDumpedIn`, and `None`. Classify a crossing using `EventStartCoordinate.x` projected into the team's attacking direction, obtained from `infer_attack_directions` or an explicit `(period, side)` mapping:

- Opponent-side blue line + `TowardsOpponent`: offensive entry.
- Own-side blue line + `TowardsOpponent`: defensive exit.
- Opponent-side blue line + `TowardsHome`: offensive-zone departure.
- Own-side blue line + `TowardsHome`: defensive entry.

This uses provider-labelled blue-line events, not a hard-coded rink length. `EventPosition` alone is insufficient: it can label either side of a crossing. Missing crossing coordinates, team/direction, or an identified skater prevents attribution. Goalkeepers are excluded as award candidates. `None`/empty outcomes provide no confirmation of a puck crossing and do not start or terminate a sequence. Keep those source occurrences in the result list with an exclusion reason; do not deduplicate simultaneous rows. Validate these provider-specific semantics for each new export.

### BLCxG sequence rule

An identified offensive entry with any of the three known outcomes starts a sequence, including `PossessionLost` and `PuckDumpedIn`. Thus the metric covers puck entries rather than only controlled entries. The entrant receives the sum of **their team's** `ShotXG` values in the following offensive-zone sequence:

- **Opponent control, loose pucks, and contested possession inside the zone do not end it.** Shots after a recovery contribute to the same entry.
- End at a confirmed outward puck crossing, `PuckControlEndZone` outside the offensive zone, or a puck-action event (`Pass`, `Shot`, `Dump`, `Clear`) located outside it. A shot outside is not included.
- `StoppageOfPlay` ends it. `Goal` and `Faceoff` also provide explicit evidence of a stoppage. The goal's preceding Shot contributes once; the Goal row contributes no additional xG.
- Player crossings with `None` outcomes and penalty locations do not establish puck departure.
- Never carry a sequence across periods. Without observed departure/stoppage before a period change or end of the export, mark it `unclosed_sequence`; do not publish a partial total as complete.
- Order by precise timestamp and source-row occurrence. A second entry inside an already active sequence is retained as `overlapping_entry_without_departure` and excluded from evaluation. It does not restart attribution or double-credit shots.
- No time cap is imposed. A fully closed sequence without shots has BLCxG **zero**.

Each own-team shot must have finite xG in `[0, 1]`. If any is missing/invalid, the sequence value is unavailable. Retain `known_xg_total`, missing-shot source rows, and all shot source rows/timestamps for auditing, but exclude the incomplete sequence from means/totals. Opponent shots never add xG. This is entry-linked team chance production, not an isolated causal measure of the entrant's skill.

Player aggregates: eligible/evaluated entry counts, total/mean BLCxG, entries with a shot, coverage, ranking eligibility, and evaluated event IDs. Means include evaluated zero-shot entries. Metrics: `blcxg_mean`, `blcxg_total`, `blcxg_entries`.

### Controlled defensive exits

An identified skater's defensive exit counts as controlled only when `BluelineCrossingResult=PossessionMaintained`. `PossessionLost` and `PuckDumpedIn` count as zero. Unknown outcomes remain unavailable, not zero. No later retention window or reception snapshot is imposed: the provider's result supplies the possession evidence at the crossing.

The calculator evaluates **BlueLineCrossing rows only**. It does not additionally infer exits from passes, Clears or Dumps, which could duplicate crossing events. It therefore measures the player attribution provided by those crossing rows, not every possible breakout assist.

Player aggregates: eligible exits (including unknown outcomes), evaluated/attempted exits with known outcomes, controlled-exit count, controlled share (`controlled / evaluated`), coverage (`evaluated / eligible`), and supporting IDs. If no exits can be evaluated, the count/share is unavailable and the player cannot rank. Metrics: `controlled_exits`, `controlled_exit_share`, `zone_exit_attempts`. The controlled count links only successful exits; the share and attempt count link all evaluated exits.

### Category and provisional awards

`backend/content/award_categories.json` registers **Zone entries / exits**, exposed by `/api/award-categories`. Both new cards retain `category_id` and `category` and show category context on the detail page. Attack Launcher is the user-selected replacement for Entry Catalyst; the stable card ID remains `entry-catalyst`, preserving ownership and links. The sample threshold remains provisional. Escape Artist is the user-selected replacement for Exit Specialist; the stable card ID remains `exit-specialist` so existing ownership and links are preserved:

- **Attack Launcher** (`entry-catalyst`): highest positive mean BLCxG with at least **3 evaluated entries**. Ties favor evaluated entry count, then the lexicographically greatest player ID. The sample minimum is provisional; the observed dataset has relatively few entries per player.
- **Escape Artist** (`exit-specialist`): most controlled defensive exits, requiring a positive count. Ties favor controlled share, then player ID.

The real final currently yields Aiden Fink for Attack Launcher (mean 0.09375 xG over 4 evaluated entries; total 0.375) and Lukas Frick for Escape Artist (7 controlled exits out of 12 evaluated). Winners are calculated, not hard-coded. Only this final has the required event data; do not invent these KPIs for other tournament games.

Both awards currently remain independent collectibles. Registration of a category does **not** implement history-dependent selection of exactly one award per category/game. `/api/award-categories` explicitly reports `selection_policy=independent_awards`.

### Sequence videos

`zone_entry` moments anchor at the entry timestamp and retain the sequence end and all contributing shots in `kpi`. Their explicit `clip_window` is **3 seconds before entry through 2 seconds after the observed sequence end**. `zone_exit` uses a fixed `[-3, +5]` second window. Neither attaches unrelated YouTube goals.

`cut_clips.event_windows` merges these event-specific windows with fixed recording windows for timestamps shared by multiple moments. This permits future sequence KPIs to request different clip lengths without adding computation to React. Existing entry clips may be too short, so regenerate with:

```bash
cd backend
source .venv/bin/activate
python -m scripts.cut_clips --force
```

Then restart the backend so clip availability is refreshed. Sequence clips can be longer than pass/shot clips; generation remains manual. The frontend already supports playing linked moments in the card detail timeline and spotlight. Award highlights choose a positive supporting event, when its arena clip exists. No video encoding is performed as part of KPI calculation.

## Defending: Puck Hunter and Pass Thief

Pass Thief is the user-selected replacement for Passing Lane Guardian. The stable card ID remains `passing-lane-guardian`, preserving ownership and links.

`award_categories.json` registers **Defending**, with the existing **Shot Blocker** title in `existing_awards` and two additional independently calculated awards. `_add_category_cards` now handles both derived KPI selections and selections using existing aggregate metrics. Existing Shot Blocker cards receive category metadata without changing their manual assignment. Other games do not receive invented Interception or Puck Hunter awards.

### Interceptions

`interceptions(analysis)` is registered as `derived_kpis['interceptions']`, exposed through authenticated `/api/analysis/interceptions`. Metric: `interceptions_total`.

- Evaluate `EventType=Pass` rows; only `PassResult=Intercepted` qualifies.
- Primary player is the passer. **Secondary player is the intercepting opponent**, not an intended teammate receiver.
- Require identified, distinct players and opposite Home/Away teams. Exclude goalkeeper interceptors. Successful, Failed and unknown pass outcomes do not count.
- Include all zones and periods. No coordinates, possession search or timing window is needed: the provider explicitly supplies the outcome and interceptor.
- Each eligible source occurrence contributes 1 to the interceptor. Preserve source row and timestamp, including distinct occurrences sharing a timestamp. Never collapse rows by timestamp.
- Invalid eligible rows retain `value=None` and an exclusion reason. They are not credited as zero-valued events. Match-level eligible/evaluated counts and coverage expose attribution completeness.
- Player totals count validated interceptions; identified skaters with none have zero and an empty event list. If some eligible rows cannot be attributed, totals are validated counts, not guaranteed complete totals. Use match-level coverage to assess this limitation. Per-player completeness is not inferred from unassigned events.

All 79 intercepted passes in the current final export identify a valid opposing skater, so attribution coverage is 100%. Subsequent control-event spot checks corroborate the secondary-player role. This is the provider's interception definition, not a reconstruction of forced turnovers or all defensive recoveries.

`interception` moments belong to the interceptor and anchor at the **intercepted pass timestamp**, retaining the passer and source row in `kpi`. They use the existing `pass` video window (`[-3, +5]` seconds). No unrelated broadcast goal replay is attached. The existing cutter discovers these moments and merges their windows with other moments at the same timestamp. Generate missing clips with `python -m scripts.cut_clips`; use `--force` to regenerate existing ones, then restart the backend.

### Award rules

- **Puck Hunter** (`puck-hunter`): highest positive **PCW / puck battles won** from the aggregate statistics, across **all zones**, as explicitly requested. Ties favor validated interceptions, then the lexicographically greatest player ID.
- **Pass Thief** (`passing-lane-guardian`): highest positive **interception count**, across all zones. Ties favor aggregate PCW, then the lexicographically greatest player ID.

Both show PCW, interceptions and blocked shots, ordered with the deciding KPI first. Supporting attributes do not form a weighted score. Omit an award if nobody has a positive valid primary value. The final currently awards Puck Hunter to **Valentin Nussbaumer (11 PCW)** and Pass Thief to **Eric Pohlkamp (5 interceptions, 7 PCW)**. Four players share the highest interception count; the PCW tie-break selects Pohlkamp. Winners are computed, not fixed in JSON.

PCW remains the existing aggregate metric `puck_contest_wins`; no guessed contest-winner calculator is introduced. Contested control rows identify participants, but do not explicitly identify the winner, and later possession can belong to another player. Consequently PCW has `moment_ids=None` and no dedicated evidence highlight. The card's interception attribute still links its validated interception events. Pass Thief's highlight uses a supporting interception clip when available. Workhorse's definition and attributes have not been changed by this addition.

For category configuration, derived awards specify `derived` and `aggregate`; aggregate-stat awards specify `primary_metric` and `aggregate`. `tie_break_metric` optionally supplies a supporting metric used only to resolve equal primary values. Candidate enrichment copies aggregates to preserve cached calculator results. The new category is available through `/api/award-categories`; the selection policy remains `independent_awards`, not one award per category/game.
