# Installation and local demo

## Prerequisites

- Python 3.10 or newer with `venv` and `pip`.
- Node.js 20.19 or newer and npm (alternatively Node.js 22.12 or newer).
- To launch both servers with `make`: Linux, WSL, or macOS with Make.
- Internet access for the initial dependency installation, external player portraits, and YouTube videos.

Docker, cloud credentials, and the full game recording are not required. All necessary CSVs, content files, and local images are included.

## Quick start on Linux, WSL, or macOS

Clone the repository or download and extract a ZIP. From the project directory:

```bash
make install
make dev
```

`make install` creates `backend/.venv`, installs backend dependencies, and installs frontend dependencies using `package-lock.json`. `make dev` starts both servers; Ctrl+C stops them together.

- App: http://localhost:5173
- API documentation: http://localhost:8000/docs

In the browser, choose a username and optionally a favorite team, open the starter pack, and select a matchday using the tournament timeline.

## Manual launch

Start the backend in one terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows/PowerShell, use these commands instead:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Always open http://localhost:5173. Vite forwards `/api` requests to the backend. Ports 5173 and 8000 must be available. On Linux/WSL/macOS, `make backend` and `make frontend` also launch each server separately.

## Storage and reset

The first backend launch automatically creates `backend/hockey_cards.sqlite3`. It stores local users, sessions, cards, and tournament progress and is excluded from Git. A new username starts a new collection.

For a full reset, stop both servers, remove the local database and any associated `-wal`, `-shm`, or `-journal` files, then restart the servers. This deletes all local player progress. Afterwards, sign out in the browser or clear the site's local data.

## Generate optional arena videos

The demo launches without local videos. If you have the full recording and permission to use it, place it at this path:

```text
data/20251231_115035_SpenglerCup_Kam1 31.12.25 Game 11.mp4
```

Then, from the project directory:

```bash
cd backend
source .venv/bin/activate
python -m scripts.cut_clips
```

On Windows, use the PowerShell activation command described above. `imageio-ffmpeg` is installed with the backend dependencies. The cutter generates clips and poster images in `backend/media/clips/`, skipping existing pairs. If clip windows or synchronization change, regenerate with `python -m scripts.cut_clips --force`; this overwrites existing clips. Restart the backend afterwards.

Clipping accounts for shared event timestamps and longer zone-entry sequences. The offset and clip windows are configured in `backend/content/videos.json`. The recording and generated media remain local and are excluded by `.gitignore`.

## Tests and frontend build

From the project directory on Linux/WSL/macOS:

```bash
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
.venv/bin/python -m unittest discover -s tests
```

On Windows, activate the backend virtual environment and run `python -m pip install -r requirements-dev.txt` followed by `python -m unittest discover -s tests` from `backend/`.

Build the frontend from the project directory:

```bash
npm --prefix frontend run build
```

`frontend/dist/` is a generated artifact. The build alone does not start an API; the local demo uses the Vite development server with its API proxy. Test dependencies are not required for normal app startup.

## Data updates and troubleshooting

- Run `python -m scripts.fetch_testdata` from `backend/` to update saved official tournament games. Internet access is required, and the script overwrites `backend/content/testdata.json`.
- Afterwards, run `python -m scripts.player_games` from `backend/` to update the included player statistics export. Neither step is needed for installation.
- If packages are missing, rerun `make install` or install the requirements in the activated virtual environment.
- For API connection errors, check that the backend is running on port 8000 and the frontend on port 5173.
- For YouTube errors, check VPN or corporate filters and ad blockers, particularly for `youtube-nocookie.com`. Individual videos may have regional or embedding restrictions.
- Missing external portraits do not prevent startup; cards display a fallback.
