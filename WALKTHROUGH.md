# Spengler Cup Cards walkthrough

Collect hockey players, predict results, and explore the performances behind the cards as you move through the simulated 2025 Spengler Cup. For setup instructions, see [INSTALLATION.md](INSTALLATION.md).

## Start with the tour

Open http://localhost:5173, choose **Sign up**, enter a new username, and optionally select a favorite team. Open your free starter pack to begin your collection. Choosing a favorite team guarantees a player from that club in your starter pack.

After you finish opening the starter pack and return to Home, the first-use tour starts automatically. It introduces the activities, collection, rewards, and tournament timeline. You can skip it or replay it anytime from **Menu → Take the tour**. The card guide in the top bar also explains card types, awards, and statistics while you explore.

To return to your collection later, choose **Log in** and use the same username. This demo does not require a password; progress is saved on the computer running the app.

## A suggested first visit

1. **Open your starter pack and take the tour.** Visit Collection to see your first players and the cards still to collect.
2. **Make predictions before the tournament starts.** Open Predictions and choose your tournament picks, including the champion.
3. **Select December 26 in the bottom timeline.** Make predictions for that day's games and claim the daily pack from Home.
4. **Advance to December 27.** The previous day's games are now played. Review your prediction results, open earned packs, and try Quiz for cards from the completed games.
5. **Explore your players.** Open a player or card to discover profiles, statistics, and available highlights. Try a shootout using players from your collection.
6. **Explore the final's Impact Specials for the full functionality.** At the post-tournament stage, inspect the performances from U.S. Collegiate Selects vs. HC Davos. With both Wisehockey CSVs supplied and arena clips generated, these cards combine advanced KPI calculations with video of the supporting events.

## Follow the tournament timeline

The bar at the bottom lets you move from before the tournament through December 26–31 and then to after the tournament. You do not need to wait for real dates.

A selected gameday represents the time before that day's games have been played. Moving to the next stage plays the games you passed, resolves predictions, and makes their cards and trivia available. Make your picks before advancing. The available cards and activities change with the tournament stage, so an early collection deliberately shows less than the completed tournament.

## Grow your collection on Home

Home shows your current activities and highlights from your collection. Claim the daily pack, open packs earned through predictions or Ones to Watch players, and visit the activities you have not completed yet.

You can also claim bonus packs through the social-channel and match-ticket activities. These actions are simulated for the demo: you can try them without making a real purchase or verifying a social follow. New daily activities appear as you advance the tournament.

## Browse cards and player profiles

Open **Collection** to search by player name or jersey number and filter by team. Switch between **Players**, which groups cards by player, and **Cards**, which lets you filter by card type. Owned cards reveal their full details; unowned cards show what remains to collect.

Open a card to explore its front and back. Player profiles bring together the player's biography, tournament statistics, and related cards. Impact Specials explain the performance or award behind the card, with statistics, rankings, and supporting moments where available.

For example, **Progression Master** recognises passes that bypass opponents, **Chance Architect** recognises passes that create scoring chances, and **Brick Wall** celebrates a goalkeeper's saves. The in-app card guide explains these awards and their KPIs (key performance indicators) in plain language.

Official YouTube highlights are available for supported games. With the full datasets and generated arena clips, final-game cards can also link individual events to the statistic they support.

## The final: advanced KPIs connected to video

**The Impact Specials from the final on December 31 demonstrate the full analysis-and-video experience.** For U.S. Collegiate Selects vs. HC Davos, the app calculates advanced KPIs from the supplied Wisehockey events, uses them to recognise standout players, and connects the card's statistics to the underlying game moments. With arena clips generated, you can move from an aggregate value to an individual pass, shot, or zone entry and watch what happened. Earlier matches use saved public statistics and partly simulated demo KPIs and awards; the final is the match to explore this functionality in full.

We added several KPIs that are **calculated by the app from Wisehockey events and tracking information**, rather than read as ready-made values from the supplied exports: **BLCxG** (blue-line crossing expected goals) sums the team's shot xG following an attacking-zone entry until the sequence ends; **Packing** measures opponents bypassed by a pass towards the attacking goal; **PBP** (Pass Body Pressure) compares nearby opponents around the passer before release and the receiver after reception to measure pressure relieved by a completed pass; and **xA** (expected assists) credits a qualifying pass before a shot with that shot's xG. These calculations build on the supplied event data and shot xG, with coverage checks where tracking information is incomplete.

## Card types at a glance

| Card type | What it represents | How to collect it |
|---|---|---|
| **Base** | A player's identity and profile; the foundation of a club collection. | Starter and bonus packs, daily packs, and trade-ins. |
| **Impact Special** | A standout game performance, such as a scoring, passing, defensive, or goalkeeper award. Includes player-focused KPI cards and performance awards such as Player of the Match. | Trivia, packs, trade-ins, and shootout rewards, once the relevant game has been played. |
| **Ones to Watch** | Selected stars whose cards develop through stages such as Debut, In Form, Finalist, and Champion. | Packs and trade-ins as their teams enter the tournament. Owning these players can earn bonus packs for their goals and assists. |
| **Legend** | A club great, with career stories and achievements. | Automatically earn a legend at 50%, 75%, and 100% of a club's available base and special cards. Legends are not drawn from packs or trade-ins. |
| **Collector** | A club-logo card celebrating a completed base collection. | Own every base card of that club. |
| **Moment** | The final's last goal, including its scorer and score. | Own a card of its scorer after the final has been played. Requires the Wisehockey datasets. |
| **Stadium** | A card celebrating the arena in Davos. | Win a card through stadium trivia. |
| **Trophy** | The Spengler Cup itself. | Collect three special cards. |

**Standard and Stadium are editions, rather than separate player card types.** In Quiz, choosing the stadium venue can award a Stadium edition or upgrade a card you already own. Stadium editions also contribute more reward points. The Stadium arena card is a separate reward card.

## Predict results and play trivia

In **Predictions**, choose answers for upcoming games, such as the winner, a goal question, and a game statistic. Before the tournament begins, you can also make tournament-wide predictions. Correct answers earn packs when the corresponding results are resolved by advancing the timeline.

In **Quiz**, answer questions about completed games to win their special cards. Use the hint if you need help. Choose **At home** for standard cards or **At the stadium** for Stadium editions. Stadium attendance is simulated; no ticket is required to try it. A gameday's trivia opportunity is used when you start its round, so explore the relevant performances beforehand if you want to improve your chances.

## Trade cards and unlock rewards

In **Trade**, select three base-card copies and exchange them for a random card you do not yet own. Duplicates are useful here, and **Fill with duplicates** helps choose spares. You can also trade single copies, which removes those copies from your collection.

As your collection grows, you earn points shown in the reward bar at the top. Inspect its markers to see the reward milestones. These rewards are illustrative for the hackathon demo. Completing club collections also unlocks Collector and Legend cards automatically.

## Play a shootout duel

Open **Shootout** and choose **1 vs 1** (a shooter against a goalkeeper) or **2 vs 2** (two attackers against a defender and goalkeeper). Pick players from your collection by comparing their strengths and weaknesses, then watch the attack play out and review the result. Attack and defence alternate during the duel.

The opponent is played by a bot in this demo, even where the interface calls it a friend. Player strengths use game data where available and simulated attributes otherwise. Without the Wisehockey datasets, rink situations are also clearly labelled as simulated. Completing a duel earns a pack; winning can also award a special card while eligible specials remain to collect.

## Evaluate the full experience

For the most complete evaluation, supply both CSVs and generate arena clips following the recommended steps in [INSTALLATION.md](INSTALLATION.md). Advance past the final and focus on its **Impact Specials** to see the advanced KPI calculations alongside video of the events behind them.

If the **Public-data demo** notice is visible, you can still explore collection, predictions, trivia, trades, and shootout. Final-game awards use public statistics and simulated demo awards; Wisehockey tracking analysis and the last-goal Moment card require the supplied datasets. Use a new username for a fresh collection when comparing the two experiences.
