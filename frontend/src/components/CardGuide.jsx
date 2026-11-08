import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { ARCHETYPES, PERFORMANCE_ICON } from './CardFace'
import CardIcon from './CardIcon'

// The info button in the top bar and the card guide it opens: every card type with an outline of the card, what it
// is and how to unlock it. The rules mirror the backend (main.py, content.py, road_to_final.py, legends.json).

const IMPACT = '#b98bff' // CardFace IMPACT_PROFILE
const IMPACT_STADIUM = '#ff9a3c' // CardFace IMPACT_STADIUM

// Impact special awards by category, one short line each. Icons are the ones the card itself shows.
const AWARDS = [
  ['General', [
    ['Man of the Match', 'Most points on the winning team.', PERFORMANCE_ICON.motm],
    ['Game Winner', 'Scored the goal the opponent never came back from.', PERFORMANCE_ICON.gamewinner],
    ['Record Breaker', 'Hardest shot of the tournament so far.', PERFORMANCE_ICON.recordbreaker],
  ]],
  ['Scoring', [
    ['Sniper', 'Scores and shoots to put the puck in the net.'],
    ['Volume Shooter', 'Took the most shots.'],
    ['Chance Creator', 'Created the most dangerous chances (expected goals).'],
    ['Go-To Scorer', "The team's main scoring threat."],
  ]],
  ['Passing', [
    ['Playmaker', 'Assists and accurate passing.'],
    ['Pressure Breaker', 'Passes that free a teammate from pressure.'],
    ['Progression Master', 'Passes that skip past the most opponents.'],
    ['Chance Architect', 'Passes that set up the most dangerous shots.'],
  ]],
  ['Zone entries / exits', [
    ['Attack Launcher', 'Zone entries that lead to the most dangerous shots.'],
    ['Escape Artist', 'Most controlled exits out of the own zone.'],
  ]],
  ['Defending', [
    ['Shot Blocker', 'Throws the body in front of shots.'],
    ['Puck Hunter', 'Most puck battles won.'],
    ['Pass Thief', 'Most intercepted passes.'],
  ]],
  ['Work rate / Skating', [
    ['Workhorse', 'Most ice time and distance skated.'],
    ['Speedster', 'Fastest skater on the ice.'],
  ]],
  ['Goalkeeping', [
    ['Shot Stopper', 'Most saves.'],
    ['Brick Wall', 'Most saves on high-danger chances, even in a loss.', PERFORMANCE_ICON.wall],
  ]],
]

// Plain-language KPI explanations for people new to ice hockey. The technical definitions are in metrics.json.
const KPI = {
  goals: ['Goals', "Times the player put the puck in the opponent's net."],
  assists: ['Assists', "A pass or touch that set up a teammate's goal. Up to two players get an assist per goal."],
  points: ['Points', 'Goals plus assists: every goal the player scored or helped to score.'],
  shots: ['Shots', "Attempts on the opponent's net."],
  xg_sum: ['Expected goals (xG)', 'Every shot gets a chance of going in: close and central is high, far and wide is low. xG adds these up, so 0.6 xG means the shots were worth about 0.6 goals.'],
  shot_top_speed: ['Hardest shot', "Speed of the player's fastest shot, measured by tracking the puck."],
  skate_top_speed: ['Top skating speed', 'The fastest the player skated at any moment in the game.'],
  distance: ['Distance skated', 'How far the player skated in total during the game.'],
  toi: ['Time on ice', 'Minutes the player was actually on the ice. Players swap every minute or so, so 20 minutes or more is a lot.'],
  blocks: ['Blocked shots', 'Opponent shots the player stopped with their body or stick before they reached the goalie.'],
  puck_contest_wins: ['Puck battles won', 'One-on-one fights for a loose puck, often along the boards, that the player won.'],
  pass_pct: ['Pass success', 'Share of passes that reached a teammate.'],
  saves: ['Saves', 'Shots on goal the goalie stopped.'],
  save_pct: ['Save percentage', 'Share of shots on goal the goalie stopped. Above 92% is very good.'],
  shots_on_goal_against: ['Shots faced', 'Shots on goal the goalie had to deal with. More shots means a busier night.'],
  pbp_mean: ['Pressure relief', 'Opponents close to the passer (within 3 m) minus opponents close to the receiver. A positive number means the pass moved the puck away from pressure. Average per pass.'],
  packing_mean: ['Opponents skipped per pass', "How many opponents a pass moved the puck past, on the way to the opponent's goal. Average per pass."],
  packing_total: ['Opponents skipped in total', 'The same count, added up over all passes in the game.'],
  packing_positive_share: ['Forward passes', 'Share of passes that moved the puck past at least one opponent.'],
  xa_total: ['Expected assists (xA)', "The xG of the shots that came straight from the player's pass (within 4 seconds). It rewards setting up good chances, even if the shooter missed."],
  xa_assisted_shots: ['Shots set up', "Shots that came straight from the player's pass."],
  xa_mean: ['Quality of shots set up', 'How dangerous those shots were on average (xG per shot).'],
  blcxg_mean: ['Danger per zone entry', 'After the player brought the puck into the attacking zone, how much xG the team created before the puck left it. Average per entry.'],
  blcxg_total: ['Danger from all entries', 'The same, added up over all of the player’s entries.'],
  blcxg_entries: ['Zone entries', 'Times the player brought the puck into the attacking zone.'],
  controlled_exits: ['Controlled exits', 'Times the player got the puck out of the own zone while the team kept it, instead of just shooting it away.'],
  controlled_exit_share: ['Exit success', 'Share of exit attempts where the team kept the puck.'],
  zone_exit_attempts: ['Exit attempts', 'All attempts to move the puck out of the own zone.'],
  interceptions_total: ['Passes intercepted', 'Opponent passes the player cut off and stole.'],
}

const ZONES = 'The rink has three zones split by the blue lines: the own zone (in front of your goal), the neutral zone in the middle and the attacking zone.'

// Per award: what earns it and the three KPIs on the card back (same as archetype_metrics in the backend).
const AWARD_DETAIL = {
  'Man of the Match': { about: 'The player with the most points on the winning team. Ties go to the one with more goals.', kpis: ['goals', 'assists', 'points'] },
  'Game Winner': { about: 'Scored the goal that put the winning team ahead for good: the opponent never tied the game again.', kpis: ['goals', 'points', 'shots'] },
  'Record Breaker': { about: 'Fired the hardest shot of the tournament so far.', kpis: ['shot_top_speed', 'shots', 'toi'] },
  Sniper: { about: 'A pure goal scorer: shoots and finishes.', kpis: ['goals', 'shots', 'xg_sum'] },
  'Volume Shooter': { about: 'Keeps pulling the trigger: more shots than anyone else in the game.', kpis: ['shots', 'xg_sum', 'shot_top_speed'] },
  'Chance Creator': { about: 'Gets to the dangerous spots and creates the best scoring chances, even when they do not all go in.', kpis: ['xg_sum', 'shots', 'goals'] },
  'Go-To Scorer': { about: 'The main scoring threat of their own team: leads the team in shots and expected goals.', kpis: ['shots', 'xg_sum', 'goals'] },
  Playmaker: { about: 'Makes teammates better: sets up goals with accurate passes.', kpis: ['assists', 'points', 'pass_pct'] },
  'Pressure Breaker': { about: 'Gets the puck out of trouble: passes that take it from a crowded spot to a teammate with space.', kpis: ['pbp_mean', 'packing_mean', 'packing_total'] },
  'Progression Master': { about: 'Moves the game forward: passes that skip past the most opponents.', kpis: ['packing_mean', 'packing_total', 'packing_positive_share'] },
  'Chance Architect': { about: 'The pass before the shot: sets up the most dangerous chances for teammates.', kpis: ['xa_total', 'xa_assisted_shots', 'xa_mean'] },
  'Attack Launcher': { about: 'Brings the puck into the attacking zone in a way that leads to dangerous shots.', kpis: ['blcxg_mean', 'blcxg_total', 'blcxg_entries'], note: ZONES },
  'Escape Artist': { about: 'Gets the puck out of the own zone without giving it away.', kpis: ['controlled_exits', 'controlled_exit_share', 'zone_exit_attempts'], note: ZONES },
  'Shot Blocker': { about: 'Throws the body in front of shots to protect the goal.', kpis: ['blocks', 'puck_contest_wins', 'toi'] },
  'Puck Hunter': { about: 'Wins the puck back: the most one-on-one puck battles won.', kpis: ['puck_contest_wins', 'interceptions_total', 'blocks'] },
  'Pass Thief': { about: 'Reads the play and steals the most opponent passes.', kpis: ['interceptions_total', 'puck_contest_wins', 'blocks'] },
  Workhorse: { about: 'Never stops: the most minutes on the ice and the most distance skated.', kpis: ['toi', 'distance', 'puck_contest_wins'] },
  Speedster: { about: 'The fastest skater on the ice, who also wins the race to the puck.', kpis: ['skate_top_speed', 'puck_contest_wins', 'distance'] },
  'Shot Stopper': { about: 'The goalie who made the most saves.', kpis: ['saves', 'save_pct', 'shots_on_goal_against'] },
  'Brick Wall': { about: 'The goalie who stopped the most high-danger chances, even if the team lost.', kpis: ['saves', 'save_pct', 'shots_on_goal_against'], note: 'A high-danger chance is a shot with at least a 15% chance of going in (0.15 xG), usually from close to the net.' },
}

// The other card types: outline, what it is, how to unlock it.
const TYPES = [
  {
    id: 'base', name: 'Base', color: '#8ea3bb', icon: null, label: 'Base', rarity: '●',
    what: 'Every player of every team: photo, name, number and club.',
    unlock: ['Starter pack when you sign up.', 'Daily pack: 5 free cards every gameday.', 'Follow a social channel or buy match tickets for extra packs.', 'Trade 3 duplicates for 1 new card.'],
  },
  {
    id: 'road', name: 'Ones to Watch', color: '#ffd76a', icon: 'flag', label: 'Ones to Watch', rarity: '★★',
    what: 'The two star players of each team. The card grows with every game: Debut, In Form, Finalist, Champion.',
    unlock: ['Pulled by luck from packs and trade-ins, from day one.', 'Bonus: every goal or assist by your player earns a pack of 5 cards.'],
  },
  {
    id: 'legend', name: 'Legend', color: '#d9b45a', icon: 'star', label: 'Legend', rarity: '★★★', dark: true,
    what: 'Club greats from earlier Spengler Cups, in black and gold.',
    unlock: ["Collect 50%, 75% and 100% of a club's cards: one legend at each step.", 'Cannot be drawn or traded.'],
  },
  {
    id: 'collector', name: 'Collector', color: '#ffd76a', icon: 'gift', label: 'Collector', rarity: '★★',
    what: 'The club logo on a gold card, with the club history on its page.',
    unlock: ['Own every base card of that club.'],
  },
  {
    id: 'moment', name: 'Moment', color: '#7cc4ff', icon: 'star', label: 'Moment', rarity: '★★★',
    what: 'The last goal of the final, with score and scorer.',
    unlock: ['Own any card of the scorer.'],
  },
  {
    id: 'stadium', name: 'Stadium', color: '#c9d3df', icon: 'flag', label: 'Stadium', rarity: '◆◆',
    what: 'The VAT Arena in Davos.',
    unlock: ['Win any card in the trivia at the stadium.'],
  },
  {
    id: 'trophy', name: 'Trophy', color: '#ffd76a', icon: 'trophy', label: 'Trophy', rarity: '★★',
    what: 'The Spengler Cup itself.',
    unlock: ['Collect three special cards.'],
  },
]

// A small outline of a card in the real card shape: accent edge, icon top left, label at the bottom, rarity in the point.
function Outline({ color, icon, label, rarity, dark }) {
  return (
    <div className={`guide-outline ${dark ? 'dark' : ''}`} style={{ '--gc': color }} aria-hidden="true">
      <div className="guide-outline-in">
        {icon && <span className="guide-outline-icon"><CardIcon name={icon} /></span>}
        <span className="guide-outline-photo" />
        <span className="guide-outline-label">{label}</span>
        <span className="guide-outline-rarity">{rarity}</span>
      </div>
    </div>
  )
}

function Unlock({ items }) {
  return (
    <div className="guide-unlock">
      <strong>How to unlock</strong>
      <ul>{items.map((t) => <li key={t}>{t}</li>)}</ul>
    </div>
  )
}

const iconOf = (title, icon) => icon ?? ARCHETYPES[title]?.icon ?? 'star'

// Pop-up over the guide: what earns one award and the three KPIs behind it, explained in plain words.
function AwardDetail({ title, icon, onClose }) {
  const { about, kpis, note } = AWARD_DETAIL[title]
  return (
    <div className="results-overlay guide-detail-overlay" onClick={(e) => { e.stopPropagation(); onClose() }}>
      <div className="results-modal guide-detail" role="dialog" aria-modal="true" aria-labelledby="guide-detail-title" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="results-close" onClick={onClose} aria-label="Back to the card guide">✕</button>
        <p className="guide-detail-kicker">
          <span className="guide-award-icon"><CardIcon name={icon} /></span>
          Impact Special
        </p>
        <h2 id="guide-detail-title">{title}</h2>
        <p className="guide-detail-about">{about}</p>
        <h4 className="guide-detail-head">The 3 stats behind it</h4>
        <ol className="guide-kpis">
          {kpis.map((id) => (
            <li key={id}>
              <b>{KPI[id][0]}</b>
              <span>{KPI[id][1]}</span>
            </li>
          ))}
        </ol>
        {note && <p className="guide-detail-note">{note}</p>}
      </div>
    </div>
  )
}

function Guide({ onClose }) {
  const [award, setAward] = useState(null) // [title, icon] of the award whose pop-up is open
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && (award ? setAward(null) : onClose())
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [award, onClose])

  return createPortal(
    <div className="results-overlay guide-overlay" onClick={onClose}>
      <div className="results-modal guide-modal" role="dialog" aria-modal="true" aria-labelledby="guide-title" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="results-close" onClick={onClose} aria-label="Close">✕</button>
        <h2 id="guide-title">Card guide</h2>
        <p className="muted small">Every card type, what it means and how to get it.</p>

        <section className="guide-type">
          <div className="guide-outlines">
            <Outline color="#8ea3bb" label="Base" rarity="●" />
          </div>
          <div className="guide-text">
            <h3>{TYPES[0].name}</h3>
            <p>{TYPES[0].what}</p>
            <Unlock items={TYPES[0].unlock} />
          </div>
        </section>

        <section className="guide-type">
          <div className="guide-outlines">
            <Outline color={IMPACT} icon="target" label="Impact" rarity="◆◆" />
            <Outline color={IMPACT_STADIUM} icon="target" label="Stadium" rarity="★★" dark />
          </div>
          <div className="guide-text">
            <h3>Impact Specials</h3>
            <p>A player who stood out in one game. The purple tag names the award; the back shows the 3 stats and the clips that earned it. Tap an award below to see its stats explained.</p>
            <Unlock items={[
              'Trivia: 3 questions per gameday about the latest games. Right answer, card is yours.',
              'Luck: 10% chance in starter, daily, social and ticket packs; 25% per card in prediction packs and trade-ins.',
              'Answer the trivia at the stadium to win the dark orange Stadium edition (double points).',
            ]} />
          </div>
        </section>
        <div className="guide-awards">
          {AWARDS.map(([category, awards]) => (
            <div key={category} className="guide-award-group">
              <h4>{category}</h4>
              <ul>
                {awards.map(([title, line, icon]) => (
                  <li key={title}>
                    <button type="button" className="guide-award" onClick={() => setAward([title, iconOf(title, icon)])}>
                      <span className="guide-award-icon"><CardIcon name={iconOf(title, icon)} /></span>
                      <span><b>{title}</b> {line}</span>
                      <span className="guide-award-more" aria-hidden="true">›</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {TYPES.slice(1).map((t) => (
          <section key={t.id} className="guide-type">
            <div className="guide-outlines">
              <Outline color={t.color} icon={t.icon} label={t.label} rarity={t.rarity} dark={t.dark} />
            </div>
            <div className="guide-text">
              <h3>{t.name}</h3>
              <p>{t.what}</p>
              <Unlock items={t.unlock} />
            </div>
          </section>
        ))}

        <p className="guide-points muted small">
          Points per card: base 5, special 10, collector, moment, stadium and trophy 15, legend 25. Stadium editions count double.
        </p>
      </div>
      {award && <AwardDetail title={award[0]} icon={award[1]} onClose={() => setAward(null)} />}
    </div>,
    document.body,
  )
}

export default function CardGuide() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" className="info-button" onClick={() => setOpen(true)} aria-label="Card guide" title="Card guide">
        i
      </button>
      {open && <Guide onClose={() => setOpen(false)} />}
    </>
  )
}
