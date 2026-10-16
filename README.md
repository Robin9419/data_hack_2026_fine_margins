# data-hack-2026

Repository for the Sports Innovation Challenge. Concept: [docs/IDEA.md](docs/IDEA.md).

## Hockey Performance Cards: skeleton app

- **backend/**: FastAPI + SQLite. Dummy username sign-in, a starter pack for new accounts only, owned cards (standard or stadium edition), trivia quiz, reward points, card data.
- **frontend/**: React (Vite). Sign-in, pack opening (tap a mystery card to reveal it), reward bar, trivia quiz with a card-unlock animation, card gallery, card detail page with KPI explanations and a video slot.

### Run it

On Linux, WSL, or macOS, start both servers from the repository root:

```bash
make install   # First setup, or after dependencies change
make dev
```

Open http://localhost:5173. Ctrl+C stops both servers. Use `make backend` or
`make frontend` to start either server separately. `make help` lists the commands.
Requires Python, Node.js/npm, and Make. The frontend uses port 5173 strictly so
it cannot silently switch to a port that the backend's CORS configuration rejects.

Alternatively, start the servers manually:

Backend (terminal 1):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` to the backend on port 8000. API docs: http://localhost:8000/docs.

### Where things live

| What | File |
|---|---|
| Cards (player, position, archetype title, which 3 KPIs, explanation, video) | `backend/content/cards.json` |
| Card kinds, tiers, editions and their design rules | `docs/CARD_TYPES.md`, mockup `docs/mockups/player-cards-photo.html` |
| Match rating (MR) and tier per player | `backend/app/ratings.py` |
| Performance specials (Player of the Match, Game Winner, Brick Wall) | `performance_specials` in `backend/content/cards.json`, rules in `backend/app/content.py` |
| Card front (all kinds, tier frames, finishes) | `frontend/src/components/CardFace.jsx`, `.card-*` in `frontend/src/index.css` |
| Team logos and colours | `frontend/src/teams.js` |
| Pack size (starter cards for a new account) | `pack_size` in `backend/content/cards.json` |
| Player photos (matched to cards by team + jersey) | `docs/player-images.json` |
| Pack opening page and animation | `frontend/src/pages/PackOpening.jsx`, `.pack-*` in `frontend/src/index.css` |
| KPI library (CSV column, label, plain-language definition) | `backend/content/metrics.json` |
| Match metadata (teams, score, date) | `backend/content/match.json` |
| Quiz clue per archetype (`archetypes`) | `backend/content/cards.json` |
| Reward milestones and points per card edition | `backend/content/rewards.json` |
| Quiz page and unlock animation | `frontend/src/pages/Quiz.jsx`, `frontend/src/components/CardUnlock.jsx`, `.unlock-*` in `index.css` |
| Achievements | `backend/content/achievements.json` |
| Video sources: full-game recording (sync offset, clip windows) and YouTube clip times per goal | `backend/content/videos.json` |
| Cutting the event clips out of the recording | `backend/scripts/cut_clips.py` → `backend/media/clips/` |
| Game events per player (goals, assists, shots, saves, faceoff wins) and their clips | `backend/app/events.py` |
| Which events sit behind each KPI (`events`) | `backend/content/metrics.json` |
| CSV loading, value formatting, match rank | `backend/app/content.py` |
| API routes | `backend/app/main.py` |
| Users / sessions / owned cards (SQLite) | `backend/app/db.py` → `backend/hockey_cards.sqlite3` |
| Styles (deliberately plain, ready for design) | `frontend/src/index.css` |

KPI values are not typed into `cards.json`. The backend reads them from the Wisehockey match statistics CSV in `data/` at startup, so card numbers always match the data. That CSV only covers skaters, so goalkeeper numbers (saves, shots faced) are counted from the match events CSV instead.

The card face shows only the photo, the archetype (`title`, e.g. Sniper, Workhorse, Shot Stopper), name, position and team. The three KPIs and the explanation are on the card detail page. Cards you don't own yet, and pack cards before you reveal them, are mystery cards: no photo, name or archetype, and the API sends nothing about them either.

### Trivia and rewards

A new account gets a starter pack of 3 random cards. After that cards are only won through trivia: a round is 3 questions, each "Who was the *Sniper* in this game?" (the card's archetype) with four player options and a clue. A wrong answer can be retried; a right one unlocks the card with an animation. The player says where they watch (self-reported in the demo; a real product would verify a ticket or location): **at home** gives the standard card (10 pts), **at the stadium** gives the foil Stadium edition (25 pts, purely cosmetic otherwise) and upgrades a card already owned as standard. The reward bar at the top shows the points and the milestones in `rewards.json` (illustrative rewards only).

### Open items

- **Positions** are not in the dataset. The values in `cards.json` (Forward / Defender / Goalkeeper) were entered by hand from the public team rosters.
- **Competition stage** is not in the dataset. It is `null` until confirmed.
- **Videos**: every game event on the card detail page has its own clip, cut from the full-game arena camera recording (`data/20251231_115035_SpenglerCup_Kam1 31.12.25 Game 11.mp4`, 13.7 GB). Neither the recording nor the clips are in git: put the recording in `data/` and run `python -m scripts.cut_clips` from `backend/` (a few minutes; it only decodes the seconds around each event), then restart the backend. Event time to video time is `Timestamp / 1000 - timestamp_offset` (`videos.json` → `recording`). The offset was measured by lining up the crowd noise with the 9 goals, and each period gave the same value, so the recording has no cuts. Without clips the page falls back to the official highlights of the final on the Spengler Cup Davos YouTube channel (`O3rLScC5SKw`), embedded with the YouTube player; those only cover the 9 goals and stay available as the "TV" replay. A card's highlight is the player's best moment on camera: first goal, else assist, else the most dangerous save or shot by xG. To use a self-hosted file instead, set `"video": {"url": "...", "poster": "...", "description": "..."}` on a card.
- **Event links**: each KPI lists the match events behind its number where that is possible (goals, assists, shots, xG, hardest shot, faceoff wins, goalkeeper saves and shots against). Every count matches the statistics CSV. Blocked shots, time on ice, distance, speed, passing and puck battles can't be traced to single events: the events CSV does not name the blocker, and the others are tracking totals.
- **Player photos** are hotlinked from the URLs in `docs/player-images.json` and need an internet connection. Rights are not cleared for most of them (see `docs/PLAYER_IMAGES.md`). Cards without a photo show the jersey number.
- Delete `backend/hockey_cards.sqlite3` to wipe all users.
