# Card types and design

The decided card system for Hockey Performance Cards. Visual reference: [mockups/player-cards-photo.html](mockups/player-cards-photo.html). Concept and demo scope: [IDEA.md](IDEA.md).

A card is described by three independent things:

| Axis | Question | Values |
|---|---|---|
| **Kind** | What is the card about? | Base, Profile, Performance, Road to Final, Collector, Legend, Context |
| **Tier** | How strong was the match rating? (Profile only) | Bronze, Silver, Gold, Elite |
| **Edition** | How was the card collected or printed? | Standard, Stadium, Full Art, Cracked Ice, Gold |

Kind says what the card celebrates, tier says how well, edition says how it was obtained or printed. Edition never implies a better performance (see IDEA.md, "Achievement vs. Edition").

## Shared design rules

- One shape for every card: 5:7 with chamfered shoulders at the top and a pointed foot (SVG mask in `index.css`). A faint centre-ice graphic (faceoff circle, hash marks) and skate scratches sit in the middle of every player card.
- The photo fills the whole card. A dark gradient from the bottom keeps the text readable.
- **No KPIs on the front.** Numbers, explanations, clips and sources are on the back and on the card page. The front shows identity only.
- Top left: match rating, position and the nationality flag (base cards show a Base pill instead of a rating). Top right: team logo on a light chip.
- Bottom: jersey number plate and team, first name small, surname large, then the card's label (archetype or special title).
- Footer, centred in the point: context (match result or set count), the rarity symbol of the card, the trophy. Base cards show a lightly filled dot as rarity.
- Cards the user does not own yet are grey photo-only silhouettes with no name or label. Cards in a pack that is not yet revealed are mystery cards with nothing about the player.
- Team colours come from the team (`--c1` base, `--c2` accent). Special accent colours come from the kind or special type.

## Kinds

### 1. Base card

One for every player of every team, independent of any game. Photo as on the club homepage.

- Shows: photo, name, position, jersey, team. Label "Base".
- No rating, no tier, no match, no KPIs. The back has the profile (birth, nationality, height, weight, draft, club).
- Frame: team colour, thin line. Deliberately plain, so specials stand out.
- Rarity symbol: none.
- Obtained: starter pack, daily card.
- Data: `backend/content/base_cards.json`, photos from `docs/player-images.json`.
- Status: **in app**.

### 2. Profile special (game profile)

About 5 per team per game. One player who stood for one clear role in this game. The label is the archetype.

- Archetypes: Sniper, Playmaker, Volume Shooter, Chance Creator, Speedster, Shot Blocker, Workhorse, Go-To Scorer (team leader), Shot Stopper, Pressure Reliever. A new tracking metric can add an archetype.
- Shows: position, the tag (icon top left, its name above the player name), the game next to the jersey number. No rating or tier on the front.
- Frame: team colour. Rarity symbol: ◆.
- Back: the three KPIs that earned the archetype with value, rank and a plain-language definition, the story in one sentence and the video clips.
- Obtained: trivia ("Who was the Sniper in this game?").
- Status: **in app** (`cards.json`, MR and tier from `app/ratings.py`).

### 3. Performance special (outstanding performance)

Awarded by a fixed rule from the match data, for a performance that stands out. Darker than other cards, with fine glitter, the surname running along the right edge and the special label along the left edge. Each type has its own accent colour.

| Type | Rule | Accent |
|---|---|---|
| Man of the Match | Most points on the winning team, ties broken by goals | gold |
| Game Winner | Scorer of the game-winning goal (the goal after which the opponent never drew level) | red-orange |
| Brick Wall | Goalie with the most high-danger saves (xG from 0.15), even in a loss | blue |
| Record Breaker | New tournament best in top speed or shot speed (needs tournament history) | ice blue |

- Shows: MR, position, label on the side edge, no tier. Rarity symbol: ★★★.
- Obtained: trivia or live drop.
- Status: Player of the Match, Game Winner and Brick Wall **in app**; Record Breaker **in app with test data only** (needs earlier games). The other ten 2025 games (official results and statistics, see `backend/app/testdata.py`) add these specials marked TEST once they are played on the tournament timeline, with made-up match ratings; Brick Wall there counts all saves because there is no xG.
- "Team Leader" (highest xG on the losing team) is the Go-To Scorer profile card, so there is no separate type.

### 4. Road to Final (evolving)

One card per player that grows during the tournament. Starts as a normal profile card after the first game. Each stage is unlocked by a clear event and brings a visible upgrade (frame, glitter, final stage: Champion look).

- Front shows MR per game as small bars instead of any KPI.
- Rarity symbol: ★★★.
- Needs several games. Game 1 is real data, later games are a fictional example in the mockup.
- Stages in the app: 1 Debut (first game), 2 In Form (every further game, MR is the average, trend arrow), 3 Finalist (the team wins its semi-final: one tier up and glitter), 4 Champion (the team wins the final: dark gold look with the surname on the side). The mockup's "Hot Streak" (three games with MR 90 or more) is replaced by Finalist because the test ratings rarely reach it.
- Status: **in app with test data** (`backend/app/road_to_final.py`). The cards of the two best skaters of each team grow with every game played on the tournament timeline; the final uses the real data.

### 5. Collector card

A reward for owning cards. The card shows the collection, not a performance. It is never drawn or won in the trivia: the app derives it from the cards the user owns (`earned_cards` in `backend/app/content.py`, content in `backend/content/reward_cards.json`).

| Set | Rule | Reward card |
|---|---|---|
| Complete player | Own every card of one player (every player with at least 3 cards) | Collector card of that player |
| Duo / Rivals | Own both players' cards | Duo card (shared goals) or Rivals card (head to head) |
| All profile types | Own one card of every archetype | Coach card of the team |

- Shows: photo, name, "Collector" label, set progress ("3 / 3 cards"). Gold frame and glitter.
- Status: Complete player **in app**. Duo, Rivals and Coach are **mockup only**.

### 6. Legend

Players from earlier Spengler Cup years.

- Photo in black and white with a gold tint, year of the cup win or best season in the footer instead of a match result, label "Legend".
- No match rating. The back tells the story, with the tournament and years.
- Needs: list of legends, archive photos with cleared rights, short facts per player.
- Status: **mockup with placeholder**. No data in the repo yet.

### 7. Context card

Not a player. Gives context and collecting goals.

| Card | Content | Unlock | Status |
|---|---|---|---|
| Moment | The last goal of the game with score, scorer and assists | Own any card of the scorer | in app |
| Stadium | The arena | Win a card in the Stadium edition | in app |
| Trophy | The Spengler Cup | Own every special card of the match | in app |
| Mascot | Artwork from the club | Family tickets or kids' club | mockup only |

- Moment, Stadium and Trophy show a scene instead of a portrait. The Stadium and Trophy photos are Wikimedia Commons images (credit on the card page).

## Tiers (not shown on the cards)

Bronze, Silver, Gold and Elite are no longer shown on the card face: frames are in the team colour and on game level only the tags count. The match rating and its tier are still computed in the backend (`app/ratings.py`) and available on the card data.

The tier follows from the match rating, which is computed per match from the 40 skaters (or the 2 goalies).

| Tier | MR | Symbol | Frame |
|---|---|---|---|
| Bronze | below 80 | ● | copper |
| Silver | 80 to 89 | ◆ | silver |
| Gold | 90 to 96 | ★ | gold |
| Elite | 97 and above | ★★ | animated rainbow edge |

Match rating: for every KPI, the percentile among all skaters is `(pool - rank) / (pool - 1)`, ties share the best rank. Percentage KPIs (pass %, faceoff %, faceoff wins) only count for players with at least 10 passes or 5 faceoffs and rank among those players. The type score is the weighted sum, the best type wins, and `MR = 40 + 59 × score`.

| Type | KPIs and weights |
|---|---|
| Sniper | goals 35, xG 35, shots 30 |
| Playmaker | assists 40, passes 30, pass % 30 |
| Speedster | top speed 50, sprint distance 30, puck battles won 20 |
| Defender | blocks 50, puck battles won 25, time on ice 25 |
| Workhorse | time on ice 50, distance 50 |
| Faceoff Ace | faceoff wins 50, faceoff % 50 |
| Goalie | save % 45 (80 % to 95 %), high-danger save rate 35, goals saved above expected 20 (−2 to +2) |

The MR type is only used to compute the rating. The card's label is the archetype of the card.

## Editions

Independent of kind and tier. Cosmetic only.

| Edition | Look | How it is obtained | Status |
|---|---|---|---|
| Standard | The normal design | Default | in app |
| Stadium | Gold foil frame, holographic sheen, badge | Answering trivia at the arena | in app |
| Full Art | No frame, photo across the whole card, fine etched line | rare | CSS in app, assignment open |
| Cracked Ice | Foil with ice shards in cool blue | rare | CSS in app, assignment open |
| Gold | Whole card toned gold, secret number above the set size (e.g. 021/020, planned) | very rare | CSS in app, assignment open |

Rainbow and a reverse foil were left out on purpose: too colourful next to team colours, and the reverse foil is too close to the Stadium foil.

## Open items

- How Full Art, Cracked Ice and Gold are assigned (pack luck, milestone, event) and stored (`owned_cards.edition` currently knows `starter`, `standard`, `stadium`).
- Rights for photos. The base photos are hotlinked, see [PLAYER_IMAGES.md](PLAYER_IMAGES.md).
- Legends: which players, photos and facts.
- Sets and the Duo, Rivals and Coach cards need a set definition beyond "complete player".
- Road to Final needs data from more games.
