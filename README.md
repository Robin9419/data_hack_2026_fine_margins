# data-hack-2026

Repository for the Sports Innovation Challenge. Concept: [docs/IDEA.md](docs/IDEA.md).

## Hockey Performance Cards: skeleton app

- **backend/**: FastAPI + SQLite. Dummy username sign-in, a starter pack for new accounts only, owned cards (standard or stadium edition), trivia quiz, reward points, card data.
- **frontend/**: React (Vite). Sign-in, pack opening (tap a mystery card to reveal it), reward bar, trivia quiz with a card-unlock animation, card gallery, card detail page with KPI explanations and a video slot.

### Run it

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
| Pack size (starter cards for a new account) | `pack_size` in `backend/content/cards.json` |
| Player photos (matched to cards by team + jersey) | `docs/player-images.json` |
| Pack opening page and animation | `frontend/src/pages/PackOpening.jsx`, `.pack-*` in `frontend/src/index.css` |
| KPI library (CSV column, label, plain-language definition) | `backend/content/metrics.json` |
| Match metadata (teams, score, date) | `backend/content/match.json` |
| Quiz clue per archetype (`archetypes`) | `backend/content/cards.json` |
| Reward milestones and points per card edition | `backend/content/rewards.json` |
| Quiz page and unlock animation | `frontend/src/pages/Quiz.jsx`, `frontend/src/components/CardUnlock.jsx`, `.unlock-*` in `index.css` |
| Achievements | `backend/content/achievements.json` |
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
- **Videos**: every card shows "Highlight unavailable in this demo". To add one, set `"video": {"url": "...", "poster": "...", "description": "..."}` on a card.
- **Player photos** are hotlinked from the URLs in `docs/player-images.json` and need an internet connection. Rights are not cleared for most of them (see `docs/PLAYER_IMAGES.md`). Cards without a photo show the jersey number.
- Delete `backend/hockey_cards.sqlite3` to wipe all users.
