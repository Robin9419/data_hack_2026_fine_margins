# Installation and evaluation guide

This guide describes how to run the submission locally for evaluation. It assumes you have access to the original Wisehockey exports and arena recording supplied for the hackathon. Use those files in the locations below.

## Prerequisites

- Python 3.10 or newer with `venv` and `pip`.
- Node.js 20.19 or newer and npm (alternatively Node.js 22.12 or newer).
- To launch both servers with `make`: Linux, WSL, or macOS with Make.
- Internet access for the initial dependency installation, external player portraits, and YouTube videos.

Docker and cloud credentials are not required. Card configuration, saved public tournament data, and local images are included. The hackathon's Wisehockey CSV exports and full arena recording are supplied separately from the submission.

## Supply the match data before starting

From the hackathon dataset, use the final-game exports for U.S. Collegiate Selects vs. HC Davos on December 31, 2025. Create a `data/` directory at the repository root and copy these two files into it, preserving their exact filenames:

```text
data/
  U.S. Collegiate Selects_HC Davos_Wisehockey_Match_Statistics_31_12_2025 All.csv
  U.S. Collegiate Selects_HC Davos_Wisehockey_Match_Events_31_12_2025.csv
```

Use the original CSV contents and headers. Period-specific exports and sample spreadsheets are not needed. The backend requires both files to start; installing dependencies does not download or generate them. Their filenames are configured in `backend/content/match.json` (`stats_file` and `events_file`).

The local data directory and generated clips are covered by `.gitignore`. Images are included in the submission, so no separate image setup is needed.

## Quick start on Linux, WSL, or macOS

Clone the repository or download and extract a ZIP. Supply the two CSVs as described above, then run these commands from the project directory:

```bash
make install
make dev
```

`make install` creates `backend/.venv`, installs backend dependencies, and installs frontend dependencies using `package-lock.json`. `make dev` starts both servers; Ctrl+C stops them together.

- App: http://localhost:5173
- API documentation: http://localhost:8000/docs

In the browser, choose a username and optionally a favorite team, then open the starter pack. Use the tournament timeline to explore different matchdays. For evaluation, advance to December 31 or the post-tournament stage to inspect the final's Wisehockey-based cards and KPI explanations. Predictions can be tested before advancing a matchday; trivia and newly earned cards become available after the games have been played in the simulation.

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

The app runs without the full recording or generated clips once the required CSVs are supplied. To evaluate the arena replays linked to individual events, copy the original recording from the hackathon dataset to this exact path relative to the repository root:

```text
data/20251231_115035_SpenglerCup_Kam1 31.12.25 Game 11.mp4
```

After supplying both CSVs, placing the recording, and installing dependencies, run these commands from the project directory:

```bash
cd backend
source .venv/bin/activate
python -m scripts.cut_clips
```

On Windows, use the PowerShell activation command described above. `imageio-ffmpeg` is installed with the backend dependencies. The cutter generates `backend/media/clips/<event Timestamp>.mp4` and matching `.jpg` poster images, skipping existing pairs. These are served by the backend at `/api/media/clips/`. Clip generation is manual and does not run at server startup; allow several minutes, depending on your machine and the number of events. If clip windows or synchronization change, regenerate with `python -m scripts.cut_clips --force`; this overwrites existing clips. Restart the backend afterwards.

Clipping accounts for shared event timestamps and longer zone-entry sequences. The offset and clip windows are configured in `backend/content/videos.json`. The recording and generated media remain local and are excluded by `.gitignore`.

## Tests and frontend build

Supply the two CSVs before running backend tests. The arena recording is only needed for clip generation.

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
- If startup reports a missing CSV, check the `data/` directory, exact filenames (including spaces), and `backend/content/match.json`.
- If the cutter reports `Recording not found`, check the recording path in `backend/content/videos.json`.
- If packages are missing, rerun `make install` or install the requirements in the activated virtual environment.
- For API connection errors, check that the backend is running on port 8000 and the frontend on port 5173.
- For YouTube errors, check VPN or corporate filters and ad blockers, particularly for `youtube-nocookie.com`. Individual videos may have regional or embedding restrictions.
- Missing external portraits do not prevent startup; cards display a fallback.
