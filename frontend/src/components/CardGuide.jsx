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

function Guide({ onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return createPortal(
    <div className="results-overlay" onClick={onClose}>
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
            <p>A player who stood out in one game. The purple tag names the award; the back shows the 3 stats and the clips that earned it.</p>
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
                    <span className="guide-award-icon"><CardIcon name={icon ?? ARCHETYPES[title]?.icon ?? 'star'} /></span>
                    <span><b>{title}</b> {line}</span>
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
