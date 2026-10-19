# Awards and Categories — Discussion Summary

Updated: 2026-10-19. This document records the agreed product direction, implemented award rules, and outstanding decisions. Technical KPI and video integration instructions are in [EVENT_KPIS.md](EVENT_KPIS.md); tournament context is in [SPENGLER_CUP_2025.md](SPENGLER_CUP_2025.md).

## Product Direction

Group player awards into broader categories such as Passing, Scoring, Goalkeeping, Defending, and Work Rate / Skating. The intended experience is **one award from each category per game**, rather than issuing every award in every game. The specific award should vary between games while remaining supported by the performance data.

The user accepted this selection principle:

1. Sporting performance determines which awards qualify.
2. Among qualifying awards, prefer those awarded less frequently earlier in the tournament to encourage variety.
3. Award the selected title to its qualifying player for that specific game.

This is an agreed direction, not an implemented category-selection system. No final qualification thresholds, cross-award comparison method, frequency weighting, or category tie rules have been agreed. The current app still creates multiple independent awards per game.

## Proposed Category Mapping

This grouping was discussed as an example; it is not yet a finalized configuration.

| Category | Candidate awards |
|---|---|
| Passing | Playmaker, Pressure Reliever, Progression Master, Chance Architect |
| Scoring | Sniper, Volume Shooter, Chance Creator, Go-To Scorer |
| Goalkeeping | Shot Stopper, Brick Wall |
| Defending | Shot Blocker; further defensive awards to be defined |
| Work Rate / Skating | Workhorse, Speedster |

Man of the Match, Game Winner, and Record Breaker also exist. Their placement inside categories, or treatment as additional awards outside the category system, remains undecided. Reward, legend, and base cards are separate collection features, not automatically members of this player-performance category system.

## Existing Award Logic

The original nine archetypes are manually assigned to players in `backend/content/cards.json`: Sniper, Playmaker, Volume Shooter, Chance Creator, Speedster, Shot Blocker, Workhorse, Go-To Scorer, and Shot Stopper. Each displays supporting KPIs, but the three displayed attributes do not constitute an automatic scoring or selection formula.

Other awards are calculated in the backend:

| Award | Current rule |
|---|---|
| Pressure Reliever | Highest positive average PBP; at least 10 evaluated passes. Ties favor more evaluated passes, then player ID. |
| Progression Master | Highest positive average Packing; at least 10 evaluated passes. Ties favor more evaluated passes, then player ID. |
| Chance Architect | Highest positive total xA. Ties favor more attributed shots, then player ID. No minimum sample threshold currently applies. |
| Man of the Match | Most points on the winning team; goals break ties. |
| Game Winner | Scorer of the winning team's `(opponent final goals + 1)`-th goal, selected from goal events. |
| Brick Wall | Most saves against shots with xG ≥ 0.15; total saves break ties. |
| Record Breaker | New tournament hardest-shot best; currently available through the test-data tournament mode. |

For the three new passing awards, the final player-ID tie break selects the lexicographically greatest ID solely for deterministic behavior. The 10-pass minimum for PBP and Packing is provisional, not a statistically validated threshold.

These are project-defined awards. Do not present them as official Spengler Cup awards. Their calculation currently does not use a weighted multi-KPI category score.

## Passing: Three Complementary Dimensions

### Pressure Reliever — Pass Body Pressure

PBP measures pressure reduction around the puck carrier:

- `PBP_PG`: opposing skaters within **≤3 m** of the passer at pass release.
- `PBP_PE`: opposing skaters within **≤3 m** of the receiver in the first strictly later snapshot containing receiver coordinates within **≤2 seconds**, in the same period.
- `PBP = PBP_PG − PBP_PE`.

Only successful passes with identified teammates qualify. Goalkeepers do not count as pressure. Receiver and surrounding-player coordinates come from the same later snapshot. Missing required coordinates produce unavailable values, not zero.

Positive PBP indicates reduced pressure. The later snapshot is an estimate of the reception situation, not proof of the exact reception instant. This metric does not establish attacking progression or overall pass quality.

### Progression Master — Signed Packing

Packing measures opponents bypassed in the attacking direction. The user chose the **frozen-opponent variant**:

- Freeze opposing skater positions at pass release.
- Compare passer x at release with receiver x in the accepted later snapshot.
- Count frozen opponent x positions strictly between those endpoints.
- Forward progression is positive; backward progression restoring opponents ahead of the puck is negative.
- Sideways passes and backward passes crossing no opponents score zero.

Goalkeepers are excluded. Opponent movement after release does not affect the value. The implementation uses the rink's longitudinal x axis, not geometric passing lanes. Team/period attacking direction must be known; the current export preserves the same orientation across periods.

The name **Progression Master** was explicitly selected by the user after discussing Line Breaker and names involving Stretch. Packing does not require a minimum pass length, so the award is not defined as a stretch-pass award.

### Chance Architect — Expected Assists

xA measures shot chances prepared by passing:

- For each shot with valid xG, find the **last successful teammate pass to the shooter within four seconds before the shot**, in the same period.
- The passer receives **xA = shot xG**.
- Intervening opponent possession cancels attribution. The user explicitly confirmed this rule.
- Each shot credits at most one passer. Separate Goal rows do not add credit again.
- Missing xG is unavailable, not zero. Shots need not result in a goal.

The implementation detects opponent control states and successful opponent passes. A loose or contested puck alone is not treated as confirmed opponent possession. Multiple shots can credit the same prior pass if each meets the rule; rebound handling beyond this rule remains a possible refinement.

**Chance Architect** is the provisional name introduced during implementation; the user has not explicitly selected this title. The agreed ranking basis is total xA, with average xG per attributed shot shown as supporting context.

### Interpreting the Dimensions Together

| Packing | PBP | Interpretation |
|---|---|---|
| Positive | Positive | Bypasses opponents and reduces local pressure |
| Positive | Negative | Gains progression but puts the receiver under more pressure |
| Negative | Positive | Moves backward to relieve pressure |

xA adds whether a pass prepares a subsequent shot and how dangerous that shot was. None of these metrics alone identifies the best passer in every respect. Their units and distributions differ; raw PBP, Packing, and xA values should not be compared directly to choose a category winner.

## Implemented Final-Game Examples

At the time of this discussion, the real final dataset produces:

| Award | Player | Evidence |
|---|---|---|
| Pressure Reliever | Joey Muldowney | Mean PBP approximately 0.82 from 11 evaluated passes |
| Progression Master | Eric Pohlkamp | Mean Packing approximately 1.64; signed total 23 |
| Chance Architect | Tino Kessler | Total xA 0.551 from five attributed shots |

These are calculated examples, not fixed winners to hard-code. The real event export covers the final only. Other games' aggregate statistics do not justify invented PBP, Packing, or xA results.

## Cards and Video Evidence

The passing awards are currently separate special cards. A player can receive multiple cards for one game. KPI attributes link to supporting moments, with source rows and timestamps retained for auditing.

- PBP and Packing videos anchor at pass release and reuse the pass clip.
- xA videos anchor at the shot, retaining the preceding pass timestamp in the calculation result.
- The xA clip window includes enough lead-in to show a qualifying pass up to four seconds earlier.
- Missing clips do not prevent calculation; they leave the event without a camera playback button.
- Clips are generated manually; widening a window requires regeneration with `--force`.

## Decisions Needed Before Category Selection

1. Finalize category membership, including treatment of Man of the Match, Game Winner, and Record Breaker.
2. Define qualification for each award and automate the currently manual archetypes.
3. Choose comparable measures of standout performance across different KPIs, rather than comparing raw units.
4. Define how earlier award frequency influences selection and how ties are resolved.
5. Decide what happens if nobody qualifies: omit that category or use an explicitly defined fallback. Do not fabricate a qualifying performance.
6. Decide whether the same player can win multiple categories in one game.
7. Confirm the Chance Architect name and whether xA needs a sample threshold or further rebound/sequence rules.
8. Make history-dependent selection reproducible in chronological game order and specify whether revisiting a game preserves its original award.

Until these decisions are made, retain independently calculated awards and their transparent KPI evidence. The one-award-per-category policy remains the next product step.
