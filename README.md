# Spengler Cup Cards

An interactive hockey trading card app for the Sports Innovation Challenge. Fans explore a simulated 2025 Spengler Cup tournament, collect player cards, and discover the statistics and game moments behind standout performances.

Setup and launch instructions: [INSTALLATION.md](INSTALLATION.md).

## Features

- **Collection and packs:** Sign in with a username of your choice, open a starter pack, collect daily cards, browse a filterable gallery, and accumulate duplicate copies.
- **Player cards:** Base cards with player profiles, Impact Specials for standout performances, club legends, collector cards, stadium cards, and trophy cards. Card backs explain KPIs and rankings.
- **Tournament timeline:** Move through the matchdays from December 26 to 31, 2025. Cards and events unlock according to the selected tournament stage.
- **Predictions and trivia:** Earn cards and packs by predicting upcoming games and answering questions about completed matches.
- **Trades and rewards:** Trade three base cards for a new card. Your favorite team, collection progress, and Stadium edition influence cards and rewards. Club legends unlock at 50%, 75%, and 100% collection progress.
- **Ones to Watch:** Follow selected players on their road to the final; tournament performances influence their cards and earn additional packs.
- **Shootout duel:** Play against a bot with player-specific strengths and weaknesses.
- **Player profiles and videos:** Explore game statistics, traceable individual events, official YouTube highlights, and optional locally generated arena clips.

## Data and demo scope

The U.S. Collegiate Selects vs. HC Davos final uses separately supplied Wisehockey match statistics and events. These CSV exports are not included in the repository; place them under `data/` as described in the installation guide before starting the backend. The backend calculates metrics including Pass Packing, pressure on the passer, Expected Assists, Zone Entries/Exits, and Interceptions. Individual events make the calculations traceable on the cards. Decimal statistics display two decimal places; a third is retained when the value would otherwise round to zero.

Other tournament games use saved data from the official Spengler Cup game pages. Additional demo KPIs and ratings for these games are partly simulated and do not represent a complete Wisehockey event analysis. Sources and definitions are recorded in the content files and the app's KPI explanations.

Sign-in is a demo flow without passwords. Tournament progress, sessions, and cards are stored locally in SQLite. Stadium attendance and social actions are simulated, and rewards are illustrative. The app is designed for a local hackathon demo.

## Project structure

| Path | Contents |
|---|---|
| `backend/app/` | FastAPI, card assembly, KPI calculations, tournament, shootout, and SQLite |
| `backend/content/` | Card configuration, player profiles, image sources, and saved tournament data |
| `backend/scripts/` | Data updates, player statistics export, and optional video clipping |
| `backend/tests/` | Tests for calculations and app features |
| `data/` | Local CSV exports for the final and optional recording; excluded from Git |
| `frontend/src/` | React interface with Vite |
| `frontend/public/` | Images, logos, and player statistics export used by the app |
| `scripts/dev.py`, `Makefile` | Local installation and launch of both servers |

## Images and videos

Local images are included in the repository; some player portraits load from external sources. Sources and image credits are recorded primarily in `backend/content/player-images.json`, `card_images.json`, and `legends.json`. Reuse rights for several press, club, and agency images have not been established; public distribution requires appropriate permissions or replacement images.

YouTube videos are embedded and require internet access. Availability also depends on regional restrictions, embedding policies, and browser or network filters. The full arena recording and generated clips are not included in the repository. With the required CSVs supplied, the app works without the recording or clips; optional video clipping is covered in the installation guide.
