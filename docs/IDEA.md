# Hockey Performance Cards — MVP Demo Plan

## Project Overview

Create an interactive, mobile-friendly web demo that turns ice hockey
performance statistics into collectible digital memorabilia.

Each card preserves a player's performance in a specific game through
three meaningful attributes, a short explanation, and an optional video
highlight. Special cards celebrate notable achievements.

The experience should help newcomers and experienced fans understand
why a performance mattered—not simply display numbers.

**Team:** 4 people  
**Timeline:** 1 month  
**Deliverable:** A polished interactive demo, not a live production platform

---

## 1. Core Concept

The experience follows one simple loop:

**Explore a match → answer a statistics question → earn a performance card
→ revisit its highlight → use it in a challenge → progress toward a reward.**

The cards should feel like memorabilia worth keeping, not just game tokens.

### Example Card

Illustrative example only:

> **Third-Period Wall**
>
> Goalkeeper — Championship Final
>
> **34 saves · 94.4% save percentage · 12 third-period saves**
>
> “His late saves helped preserve a one-goal lead.”
>
> **Watch the moment:** A crucial save in the closing minutes.

Every statistic and explanation used in the actual demo must be
supported by the selected dataset.

### Design Principles

- Make statistics understandable without requiring hockey knowledge.
- Let users explore information before answering questions.
- Explain why a performance mattered after each answer.
- Encourage learning through retries rather than punishing wrong answers.
- Present cards as collectibles tied to a specific game.
- Keep the underlying statistics visible alongside creative titles.
- Use video to illustrate the performance, not replace the data.
- Keep stadium editions cosmetic so home viewers are not disadvantaged.
- Clearly distinguish simulated features from real functionality.

---

## 2. Demo Scope

### Must-Haves

| Feature | Demo Implementation |
|---|---|
| Welcome and starter pack | Short introduction and three fixed starter cards; no account required |
| Performance cards | Approximately 3-5 cards from one completed match |
| Three attributes per card | Three verified, position-relevant statistics |
| Memorabilia details | Player, team, opponent, match date, and final score |
| Performance explanations | Brief, factual descriptions connecting statistics to the game |
| Achievement examples | Two or three examples with clearly stated qualification criteria |
| Video highlight experience | Two or three authorized clips, or clearly labeled placeholders |
| Quiz journey | Three questions based on a fixed, verified dataset |
| Card awards | Correct answers unlock cards; incorrect answers allow another attempt |
| Collection view | Owned cards, locked cards, and collection progress |
| Simple battle | One short statistical challenge against a simulated opponent |
| Reward progress | A simple collection milestone with illustrative prizes |
| Local persistence | Save progress in browser storage and provide a reset button |
| Responsive interface | Prioritize mobile while supporting desktop presentation |

The card interface should support a video attachment for every card.
For the demo, only two or three cards need playable clips. Other cards
can show a clearly labeled “Highlight unavailable in this demo” state.

### Nice-to-Haves

Only begin these after the complete core journey works:

- Simple card flip or foil effects.
- A filter for achievement cards.
- A second battle category.
- A short hockey glossary.
- A QR code opening the stadium demo route.
- A feedback question about whether the experience improved understanding.

### Great-to-Haves / Future Roadmap

These are explicitly outside the one-month build:

- Live match feeds.
- User accounts and authentication.
- Real multiplayer or matchmaking.
- Real prize draws and reward redemption.
- Secure stadium attendance verification.
- Card trading or a marketplace.
- Administration dashboard.
- Notifications.
- Automated video selection or editing.
- Automated performance-story generation.
- A library of approximately 100 validated KPIs.
- Automatic selection of three standout attributes per player.
- Complex ranking or rarity algorithms.
- Collections spanning multiple matches and tournaments.

---

## 3. Cards as Digital Memorabilia

### Card Identity

Each card represents:

**One player + one specific match + one recorded performance.**

Each card should include:

- Player name and image, where usage rights permit.
- Team and position.
- Opponent.
- Match date and competition stage.
- Final score.
- Three performance attributes.
- Short performance explanation.
- Achievement badge, where applicable.
- Video highlight or an explicit unavailable state.
- Standard or stadium visual edition.

Do not silently replace a collectible card's statistics with results
from a newer match.

### Card Layout

**Front**
- Player identity.
- Match or achievement title.
- Three highlighted attributes.
- Achievement badge.
- Visual edition.

**Detail view**
- Match context and final score.
- Plain-language performance explanation.
- Highlight video.
- Attribute definitions where needed.
- Achievement qualification criteria.
- Data source information.

The design should make users want to revisit the card after the quiz
or battle has finished.

### Achievement vs. Edition

Keep these concepts separate:

- **Achievement:** Recognizes what the player accomplished.
- **Edition:** Recognizes how or where the fan collected the card.

For example, an overtime-winning performance can have both a standard
edition and a stadium edition.

A stadium edition must not imply that the player performed better.

---

## 4. Achievement Cards

Special cards should celebrate clear, verifiable accomplishments.

| Achievement | Example Qualification |
|---|---|
| Hat-Trick Hero | Three goals in one game |
| Clean Sheet | A goalkeeper completes the game without conceding |
| Overtime Decider | Scores the overtime-winning goal |
| Playmaker | Leads the match in assists, including ties |
| Tournament Record | Breaks a verified tournament record |

### Demo Approach

- Choose two or three achievements supported by the selected match data.
- If the match does not contain enough qualifying achievements, use
  fewer examples rather than inventing results.
- Show the qualification rule in the card detail view.
- Manually assign achievement badges from verified data.
- Do not build an automated achievement engine.

Creative card titles are welcome, but they should not imply an official
award unless one actually exists.

Avoid arbitrary rarity that suggests sporting excellence merely
because fewer copies exist.

---

## 5. Three Performance Attributes Per Card

### MVP Approach

Create a small library of approximately 25 supported metrics,
depending on data availability.

Each card displays three attributes selected manually from that library.

The attributes should be:

- Relevant to the player's position.
- Supported by reliable match data.
- Easy to explain.
- Useful together in telling the performance story.

### Example Attribute Sets

| Player Type | Possible Attributes |
|---|---|
| Forward | Goals, assists, shots on goal |
| Defender | Time on ice, blocked shots, assists |
| Goalkeeper | Saves, save percentage, goals against |

These are examples, not guaranteed available fields.

Use hardest-shot measurements, hits, or advanced passing metrics only
if a reliable source provides them.

Use hockey terminology such as “hits” or “checks,” rather than “tackles.”

### Attribute Display

For each attribute, define:

- Label.
- Value.
- Unit or format.
- Plain-language meaning.
- Whether a higher or lower value is preferable.
- Source.

Use actual match values rather than unexplained ratings such as
“Power: 92.”

### Future KPI Library

A future version could expand to approximately 100 validated KPIs.

Automatic attribute selection could:

1. Check availability and data quality.
2. Select metrics relevant to the player's position.
3. Identify standout results against an appropriate benchmark.
4. Avoid choosing three metrics that tell essentially the same story.
5. Select three complementary attributes.

This automation is outside the demo scope.

### Collection Attributes vs. Battle Attributes

Cards may highlight different statistics, but battles must compare
a shared, compatible metric.

A card's three displayed attributes are its performance story.
They are not automatically its complete battle rules.

---

## 6. Video Highlights

### Purpose

Video gives the collectible an emotional connection to the game.
Statistics explain the significance of the moment.

### Demo Implementation

- Use two or three authorized clips.
- Display a poster image and a clear play button.
- Open the video in the card detail view.
- Avoid autoplay.
- Provide a brief text description of the moment.
- Provide captions when the clip contains meaningful spoken content.

### Accurate Labeling

A single clip does not prove an aggregate statistic.

Examples:

- A goal clip demonstrates that goal.
- One save illustrates a 34-save performance.
- A compilation can illustrate multiple contributions.

Use labels such as:

> Highlight from this performance.

Do not suggest that one clip demonstrates an entire game total.

### Rights and Fallbacks

Confirm permission to use footage and player imagery.

Public availability does not automatically permit reuse.

If rights cannot be secured in time:

- Use an authorized substitute that is clearly identified, or
- Show a labeled video placeholder.

Do not present unrelated footage as the actual performance.

Full video coverage for every card belongs in a later phase.

---

## 7. Quiz, Battle, Stadium, and Reward Rules

### Quiz Rules

- Users can inspect relevant statistics before answering.
- Correct answers unlock the associated card.
- Incorrect answers provide helpful feedback and another attempt.
- Repeating a completed question does not award duplicate progress.
- Each answer includes a short performance explanation.

### Battle Rules

Use one transparent battle against a simulated opponent:

1. Display a category, such as shots on goal.
2. Let the user choose an eligible card.
3. Reveal the opponent's card.
4. Compare the values.
5. Explain the result.

Use compatible cards. Do not compare goalkeeper saves directly
with a forward's goals.

Define a simple tie rule before implementation.

Achievement badges and stadium editions do not add statistical power.

### Stadium Bonus

For the demo:

- Home users receive a standard edition.
- Stadium mode awards a visually enhanced edition.
- Both editions use identical performance statistics.
- A demo switch or special URL demonstrates the concept.

This does not verify actual attendance.

Additional attendance-based reward points are optional and illustrative.
They are not necessary for the core demo.

### Rewards

Use a simple collection milestone rather than a complex points economy.

Example:

> Collect three match cards to unlock a demo prize entry.

Show sample tickets or merchandise with a clear notice:

> Demo only — no actual prize draw or reward redemption.

Real eligibility rules, legal review, winner selection, and fulfillment
belong in a future production phase.

---

## 8. Technical Approach

A frontend-only implementation should be sufficient.

### Recommended Structure

- Mobile-friendly web frontend.
- Static data files for cards, statistics, questions, and achievements.
- Browser storage for collection and progress.
- Authorized video files or permitted embeds.
- Static hosting.
- Reset function for testing and presentations.

### Not Required

- Backend server.
- Database.
- Authentication.
- Live data integration.
- Multiplayer infrastructure.
- Automated KPI selection.
- Video processing pipeline.

### Shared Data Definitions

Agree on these during the first working day.

**Performance Card**
- Card ID.
- Player ID and name.
- Team and position.
- Match ID.
- Opponent, date, stage, and final score.
- Three highlighted attribute IDs and values.
- Performance explanation.
- Optional achievement ID.
- Optional video reference.
- Visual edition.

**Metric Definition**
- Metric ID.
- Label.
- Unit and display format.
- Plain-language definition.
- Higher-is-better or lower-is-better rule, where applicable.

**Match Statistics**
- Player ID.
- Match ID.
- Available verified metric values.
- Data source.

**Achievement**
- Achievement ID.
- Title.
- Qualification criteria.
- Badge or visual treatment.

**Video Highlight**
- Video ID.
- File or permitted embed reference.
- Poster image.
- Description.
- Related card or metric.
- Attribution and permission status.

**Question**
- Question ID.
- Prompt.
- Answer choices.
- Correct answer.
- Explanation.
- Awarded card ID.

**User Progress**
- Owned card IDs and editions.
- Completed question IDs.
- Collection milestone progress.

**Battle**
- Statistical category.
- Eligible cards.
- Opponent card.
- Comparison and tie rules.

Keep data and game rules separate from interface components so work
can proceed in parallel.

---

## 9. Presentation Journey

Target a three-to-five-minute walkthrough.

### Step 1 — Arrive From a Results Page

Introduce the hook:

> The match is over—but who made the difference?

### Step 2 — Open a Starter Pack

Show attractive cards with understandable performance attributes.

### Step 3 — Explore a Performance Question

Let the user inspect information, answer, and learn why the result mattered.

### Step 4 — Earn a Memorable Card

Show the match identity, three attributes, and achievement badge.

### Step 5 — Watch the Highlight

Connect the numbers to a visible moment from the game.

### Step 6 — Demonstrate Stadium Mode

Show the enhanced visual edition with unchanged battle statistics.

### Step 7 — Play a Battle

Compare one statistical category against a simulated opponent.

### Step 8 — View Reward Progress

Show the incentive to collect more cards and return for another match.

---

## 10. Definition of Done

The demo is ready when:

- The complete journey works without developer intervention.
- Users can earn and inspect cards.
- Every card represents a specific player and match.
- Every card displays three verified attributes.
- Achievement cards show clear qualification criteria.
- Video clips have confirmed usage permission, or placeholders are labeled.
- Video labels accurately describe what the clip illustrates.
- Refreshing preserves collection progress.
- Resetting restores the starting state.
- Quiz answers and battle outcomes match the dataset.
- Repeating a question does not award duplicate progress.
- Stadium editions and achievement badges do not create battle advantages.
- Rewards and simulated opponents are clearly labeled.
- Core screens work on mobile and desktop.
- Text is readable and controls are usable.
- A newcomer can understand the basic experience without assistance.
- The presentation can be repeated reliably.

---

## 11. Validation Questions

During testing, ask:

1. Did you understand how to earn a card?
2. Did the three attributes make sense?
3. Did the explanation help you understand the player's performance?
4. Did the video make the card more meaningful?
5. Did you understand why the achievement card was special?
6. Did the card feel like something you would want to keep?
7. Did you understand the battle result?
8. Would you return to collect cards from another match?
9. Which part felt confusing or unnecessary?

The central question is:

> Does turning a performance into a collectible—with statistics,
> context, and video—make fans want to explore the game more deeply?

---

## Final Recommendation

Build one excellent loop rather than several partially working systems.

The central value is turning a performance into something a fan can:

**Understand → earn → keep → revisit → use.**

### Revised Pitch

> Collect the performances that defined the game.
>
> Every card preserves a player's standout contribution through three
> meaningful statistics, a memorable achievement where earned, and a
> highlight you can revisit.
