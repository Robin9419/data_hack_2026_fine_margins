# Installation and evaluation guide

Follow the numbered steps below to run the app on your computer. For the full experience, we recommend supplying the two Wisehockey datasets and generating the arena video clips. The app can also start using the included public tournament data as a fallback.

Docker, cloud credentials, and a separate frontend build are not needed. Internet access is needed to install dependencies and view external player portraits and YouTube videos.

## 1. Install the tools

Install these tools once:

- **Python 3.10 or newer:** download it from [python.org](https://www.python.org/downloads/). On Windows, include the Python launcher and select “Add Python to PATH” if the installer offers these options.
- **Node.js:** install the Node.js 22 LTS release or a newer LTS release from [nodejs.org](https://nodejs.org/en/download). npm is included. Node.js 20.19 or newer also works.
- **Make, for Linux/macOS/WSL only:** on Ubuntu or Debian, run `sudo apt install make python3-venv python3-pip`. On macOS, `xcode-select --install` installs Apple's command-line tools, including Make.

On Windows, use the PowerShell instructions below; Make is not needed. `make dev` supports Linux/macOS/WSL, but not native Windows. For WSL, install the tools inside WSL and follow the Linux instructions.

After installation, reopen your terminal and verify the versions:

**Windows — PowerShell:**

```powershell
py -3 --version
node --version
npm.cmd --version
```

**Linux/macOS/WSL — Terminal:**

```bash
python3 --version
node --version
npm --version
make --version
```

## 2. Download the project

Extract the submission ZIP or clone the repository.

Run the commands below from the **project folder** containing `Makefile`, `backend`, and `frontend`, unless stated otherwise.

## 3. Recommended: add the match datasets and recording

The restricted hackathon files are supplied separately from the submission.

In the project folder, create a folder named `data`. From the hackathon dataset, copy the final-game exports for U.S. Collegiate Selects vs. HC Davos on December 31, 2025 into it. Keep their exact filenames:

```text
data/
  U.S. Collegiate Selects_HC Davos_Wisehockey_Match_Statistics_31_12_2025 All.csv
  U.S. Collegiate Selects_HC Davos_Wisehockey_Match_Events_31_12_2025.csv
```

Use the original files without changing their contents or headers. Period-specific exports and sample spreadsheets are not needed.

For the recommended arena video clips, also copy the full recording into the same folder:

```text
data/20251231_115035_SpenglerCup_Kam1 31.12.25 Game 11.mp4
```

If either CSV is missing, the app starts in a public-data demo mode and displays a notice. Cards, packs, predictions, trivia, and the shootout remain available. Final-game specials use public statistics and simulated demo awards; Wisehockey tracking KPIs, event evidence, and the last-goal reward are unavailable. You can add both CSVs later and restart the app to enable the full analysis.

The recording is needed for clip generation. Images and saved public tournament data are already included. Keep the restricted files local; the `data` folder and generated clips are excluded from Git.

## 4. Install the app dependencies

Install the dependencies using the commands for your operating system:

**Windows — PowerShell:**

```powershell
py -3 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

No Python environment activation is needed.

**Linux/macOS/WSL — Terminal:**

```bash
make install
```

## 5. Recommended: generate the arena video clips

Generate clips to watch the events behind the final-game KPIs in the app. First complete steps 3 and 4, including supplying the recording.

**Windows — PowerShell:**

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.cut_clips
cd ..
```

**Linux/macOS/WSL — Terminal:**

```bash
cd backend
.venv/bin/python -m scripts.cut_clips
cd ..
```

Allow several minutes. The command reports clips cut or already present and saves clips and posters in `backend/media/clips`. FFmpeg is included in the dependencies. Existing clips are reused; generation normally runs only once. Restart the app afterwards if it was already running.

## 6. Start the app

**Windows — PowerShell:**

Use two terminal windows in the project folder.

In the **first window**, start the backend:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In the **second window**, start the frontend:

```powershell
npm.cmd --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Keep both windows open while using the app.

**Linux/macOS/WSL — Terminal:**

```bash
make dev
```

This starts both services.

Successful startup shows `Application startup complete` for the backend and a local address with port `5173` for the frontend.

## 7. Open the app and explore

Open **http://localhost:5173** in your browser.

Sign up with a new username, optionally choose a favorite team, and open your starter pack. The first-use tour starts after you return to Home. You can replay it from **Menu → Take the tour**.

See [WALKTHROUGH.md](WALKTHROUGH.md) for suggested activities, card types, and how to explore the full experience.

## 8. Stop the app and launch it again later

Press **Ctrl+C** to stop the app—in both windows on Windows, or once with `make dev`. If Windows asks to terminate the batch job, enter `Y`.

To launch it again, repeat **step 6**. Dependencies and clips do not need to be installed or generated again.

Your collection and tournament progress are saved locally. Use a new username to start a fresh collection, including when comparing the fallback and full-data experiences.

## Troubleshooting

- **A command is not recognized:** check the tool installation in step 1 and reopen the terminal. On Windows, use `py -3` and `npm.cmd` as shown.
- **A file or folder cannot be found:** check that your terminal is in the project folder containing `backend` and `frontend`.
- **Dependencies are missing:** repeat step 4 for your operating system.
- **The clip generator reports missing CSVs or `Recording not found`:** check all three filenames and their location in the `data` folder in step 3.
- **The browser cannot connect:** wait for both startup messages in step 6, and check that both services are still running. Open http://localhost:5173.
- **Port 5173 or 8000 is already in use:** stop any earlier instance of this app with Ctrl+C and try again.
- **A video does not play:** external YouTube videos require internet access and may be affected by regional restrictions, browser filters, ad blockers, or embedding policies. For local arena clips, complete step 5 and restart the app.
- **A player portrait is missing:** external portraits require internet access. The app displays a fallback and remains usable.

For a complete reset of all local users and progress, stop the app, delete `backend/hockey_cards.sqlite3` and any files beside it whose names begin with `hockey_cards.sqlite3-`, then restart. This deletes all local player progress. Afterwards, sign out in the browser or clear the site's local data.
