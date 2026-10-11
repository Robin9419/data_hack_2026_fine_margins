# Spengler Cup 2025

Research date: 2026-10-11. This document provides sporting context for the Hockey Performance Cards demo and the planned data import. It supplements the raw data and does not replace a statistics source.

## Overview

The Spengler Cup is an international invitational ice hockey tournament held in Davos since 1923. Its organizer describes it as the world's oldest club tournament. Both clubs and selection teams participate; it is neither a national-team world championship nor a regular league competition. [1, 2]

The **97th edition** took place from **26 to 31 December 2025** in Davos, Switzerland. Official game pages name the venue **zondacrypto-Arena**; other summaries use Eisstadion Davos. Six teams played eleven games. **HC Davos defeated the U.S. Collegiate Selects 6–3 in the final**, winning its 17th title and becoming the sole record holder. HC Fribourg-Gottéron, the 2024 winner, entered as defending champion. [1, 3, 5]

## Participants and Groups

| Group | Team | Context |
|---|---|---|
| Cattini | HC Davos | Swiss club and tournament host |
| Cattini | Team Canada | Canadian selection team; do not equate it with a club or automatically with the regular national team |
| Cattini | U.S. Collegiate Selects | Selection of American college/NCAA players; first appearance in 2025 |
| Torriani | HC Fribourg-Gottéron | Swiss club and defending champion |
| Torriani | HC Sparta Praha | Czech club; also called Sparta Prague |
| Torriani | IFK Helsinki | Finnish club; also called HIFK |

The U.S. selection made its tournament debut against established European professional teams and reached the final on its first appearance. The official retrospective describes its creative, dynamic style and confirms its tournament journey. It represents **neither a single university nor the U.S. national team**. [2, 5]

## Format and Results

Each three-team group played a round robin. Group winners advanced directly to the semifinals. The remaining teams played two cross-group quarterfinals, also called “pre-semifinals” by the organizer. Two semifinals and the final followed; there was no third-place game. [5]

The results below come from the tournament overview [5]. The final and U.S. semifinal were also checked against official game pages [3, 4]. The official history confirms Davos' title and route to the final [1]. Scores follow the order of the teams listed.

| Date | Stage | Game | Result |
|---|---|---|---|
| 2025-12-26 | Group Torriani | Fribourg-Gottéron – Sparta Praha | 5–2 |
| 2025-12-26 | Group Cattini | Team Canada – U.S. Collegiate Selects | 3–2 |
| 2025-12-27 | Group Torriani | IFK Helsinki – Sparta Praha | 1–4 |
| 2025-12-27 | Group Cattini | HC Davos – U.S. Collegiate Selects | 3–5 |
| 2025-12-28 | Group Torriani | Fribourg-Gottéron – IFK Helsinki | 4–3 |
| 2025-12-28 | Group Cattini | Team Canada – HC Davos | 1–4 |
| 2025-12-29 | Quarterfinal | Sparta Praha – Team Canada | 5–1 |
| 2025-12-29 | Quarterfinal | HC Davos – IFK Helsinki | 3–0 |
| 2025-12-30 | Semifinal | U.S. Collegiate Selects – Sparta Praha | 5–3 |
| 2025-12-30 | Semifinal | Fribourg-Gottéron – HC Davos | 1–3 |
| 2025-12-31 | Final | U.S. Collegiate Selects – HC Davos | 3–6 |

Fribourg won Group Torriani ahead of Sparta and Helsinki. All three teams in Group Cattini won one game; the U.S. selection finished first, followed by Davos and Canada. Davos therefore played five tournament games, while the U.S. selection played four. [5]

## The Final: the Game in This Repository

**The files under `data/` for the game on 2025-12-31 represent the final**, rather than the group game between the same teams on 2025-12-27.

| Field | Value |
|---|---|
| Competition | Spengler Cup |
| Edition | 2025, 97th edition |
| Stage | Final |
| Date and start time | 2025-12-31, 12:10 local time (Europe/Zurich, UTC+1) |
| Venue | zondacrypto-Arena, Davos |
| Home in the final dataset | U.S. Collegiate Selects |
| Away in the final dataset | HC Davos |
| Final score, Home:Away | 3:6 |
| Period scores, Home:Away | 1:2 / 2:1 / 0:3 |

Game details are supported by the official final page [3]. **Tournament host and a game's Home designation are separate properties.** Davos hosted the tournament but was designated Away in the final. Do not infer Home/Away from the venue during import.

### Game Progression

The score was tied 3–3 after two periods. Three Davos goals in the last five minutes decided the final, reversing its earlier 3–5 group-stage defeat against the U.S. selection. [1, 2, 3, 5]

The scoring sequence has been checked against the local Wisehockey event data. Times below are **elapsed minutes and seconds from the start of the game**; `MatchClock` in the CSV files contains seconds elapsed since the start of the respective period.

| Game time | Scorer | Team | Score US:Davos |
|---|---|---|---|
| 11:15 | Rasmus Asplund | HC Davos | 0:1 |
| 13:25 | Ryan Walsh | U.S. Collegiate Selects | 1:1 |
| 14:49 | Adam Tambellini | HC Davos | 1:2 |
| 23:56 | Aiden Fink | U.S. Collegiate Selects | 2:2 |
| 31:03 | Adam Tambellini | HC Davos | 2:3 |
| 33:42 | Jack Musa | U.S. Collegiate Selects | 3:3 |
| 55:21 | Filip Zadina | HC Davos | 3:4 |
| 56:48 | Enzo Corvi | HC Davos | 3:5 |
| 57:49 | Matej Stransky | HC Davos | 3:6 |

The final's goaltenders were **Adam Gajan** for the U.S. selection and **Sandro Aeschlimann** for Davos. [5; also local event lineups]

Another relevant tournament moment: **Aiden Fink scored three goals in the semifinal against Sparta** (07:38, 38:42, 41:02). That hat trick belongs to 2025-12-30 and must not be attributed to a final performance card. Fink scored one goal in the final. [4, local final data]

### Confirmed Simultaneous Penalties for Quinn Finley

In period 2, Quinn Finley received **two separate penalties at the same time**: `MatchClock=1186`, equivalent to 39:46 elapsed game time. The two penalty rows are identical in the exported fields, and the official final ticker also shows two entries. The repository owner confirmed on 2026-10-11 that these represent two distinct penalties. [3, 6, 7]

**Preserve both penalty events during import and analysis.** Identical field values or timestamps do not prove that an event is a duplicate. Event identity and repeat-import handling must preserve distinct occurrences within an export, for example by retaining source row numbers.

## Implications for Cards, the Data Model, and Analysis

- A performance card must remain tied to **one player and one specific game**. Keep final, group-stage, and tournament-wide performances distinct.
- Research establishes this game's competition stage as **Final**. `backend/content/match.json` currently still has `stage: null`; this document does not change application configuration.
- `usc-hcd-2025-12-31` is the project's internal game ID, not a verified official tournament ID.
- The local CSV files cover **one game**. They cannot support tournament-wide rankings, records, or trends. Other results in this document provide context from external sources.
- The 40 rows in the full-game statistics represent skaters. The event data also identifies the two goaltenders. Missing goaltender statistics must not be replaced with zero goals against or zero saves.
- “Shots” in the local KPI library means shots; do not relabel it as “Shots on goal” without verification. Different sources may use different shot definitions.
- “Playmaker” is a project-defined achievement with its own criterion, rather than a verified official Spengler Cup award. Player imagery and highlights require appropriate usage rights independently of this sporting research.
- Team and player names have variants, such as Sparta Praha/Prague, IFK/HIFK, and Stransky/Stránský. Preserve raw spellings and manage mappings explicitly; do not use names as permanent identifiers.

### Known Characteristics of the Local Files

These observations come from repository inspection and the owner's clarification, rather than solely from web sources:

1. The full-game event file is exactly the concatenation of the three period files, totaling 4,458 rows. Do not import these overlapping exports as additional events.
2. Both Quinn Finley penalty rows at period 2, `MatchClock=1186`, are valid separate events. Preserve both, even though their exported fields are identical. See the confirmed clarification above.
3. Goals, assists, and points in the period statistics apparently contain full-game values. Use events for goals per period rather than summing these columns.
4. Events contain Wisehockey tag/entity IDs, while statistics contain team, jersey number, and names. Stability of entity IDs across multiple games has not been established.
5. Coordinates in event rows are snapshots, rather than a complete continuous tracking dataset.

## Sources and Reliability

All web sources below were accessed on **2026-10-11**. Official sources take precedence. The tournament overview is a supplementary source for the complete results list; it carries a citation warning and has inconsistent dates in its All-Star references. Consequently, no official MVP, All-Star, or top-scorer awards are adopted from it here.

1. **Spengler Cup, official history:** the 2025 section confirms the 97th edition, final progression, Davos' 17th title, and its route through Helsinki and Fribourg; the 2024 section confirms Fribourg as the previous winner. <https://www.spenglercup.ch/en/tournament/history>
2. **Spengler Cup, “U.S. Collegiate Selects to return to the Spengler Cup”, 2026-04-02:** official retrospective on the team's debut and 2025 tournament journey. Do not use its 2026/2027 information as the 2025 participant list. <https://www.spenglercup.ch/en/news/us-collegiate-selects-return-spengler-cup>
3. **Spengler Cup, “HC Davos crowned record Spengler Cup champion”:** when accessed, this news URL redirects to the official final game page with its result, time, period scores, and ticker. <https://www.spenglercup.ch/en/news/hc-davos-crowned-record-spengler-cup-champion>
4. **Spengler Cup, “Sensational college selection reaches final”:** this news URL leads to the official U.S. semifinal game page with its result and scoring sequence. <https://www.spenglercup.ch/en/news/sensational-college-selection-reaches-final>
5. **Wikipedia, “2025 Spengler Cup”:** supplementary overview of participants, groups, format, and all eleven results. <https://en.wikipedia.org/wiki/2025_Spengler_Cup>
6. **Local primary data:** CSV exports under `data/`, particularly `U.S. Collegiate Selects_HC Davos_Wisehockey_Match_Events_31_12_2025.csv` and `U.S. Collegiate Selects_HC Davos_Wisehockey_Match_Statistics_31_12_2025 All.csv`; field descriptions in the Excel samples' glossary sheets.
7. **Repository owner clarification, 2026-10-11:** the two Quinn Finley penalties in period 2 were separate penalties assessed at the same time. This resolves the earlier uncertainty about the identical exported rows.

The current homepage already shows 2026 content. Use historical sections and dated game pages for claims about 2025. This document summarizes sources in its own words.
