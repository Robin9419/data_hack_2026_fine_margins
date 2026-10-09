# data-hack-2026

Repository for the Sports Innovation Challenge. Concept: [docs/IDEA.md](docs/IDEA.md).

## Hockey Performance Cards: skeleton app

- **backend/**: FastAPI + SQLite. Dummy username sign-in, starter pack, owned cards, card data.
- **frontend/**: React (Vite). Sign-in, card gallery, card detail page with KPI explanations and a video slot.

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
| Cards (player, title, which 3 KPIs, explanation, video) | `backend/content/cards.json` |
| Starter pack (3 free cards) | `starter_card_ids` in `backend/content/cards.json` |
| KPI library (CSV column, label, plain-language definition) | `backend/content/metrics.json` |
| Match metadata (teams, score, date) | `backend/content/match.json` |
| Achievements | `backend/content/achievements.json` |
| CSV loading, value formatting, match rank | `backend/app/content.py` |
| API routes | `backend/app/main.py` |
| Users / sessions / owned cards (SQLite) | `backend/app/db.py` → `backend/hockey_cards.sqlite3` |
| Styles (deliberately plain, ready for design) | `frontend/src/index.css` |

KPI values are not typed into `cards.json`. The backend reads them from the Wisehockey match statistics CSV in `data/` at startup, so card numbers always match the data.

### Open items

- **Positions and competition stage** are not in the dataset. They are `null` until confirmed.
- **Videos**: every card shows "Highlight unavailable in this demo". To add one, set `"video": {"url": "...", "poster": "...", "description": "..."}` on a card.
- Delete `backend/hockey_cards.sqlite3` to wipe all users.
