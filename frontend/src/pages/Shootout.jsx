import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import BackLink from '../components/BackLink'
import CardFace from '../components/CardFace'
import HalfRink from '../components/HalfRink'
import PlayerPhoto from '../components/PlayerPhoto'

// Shootout duel against a friend (backend/app/shootout.py; in this demo the friend is played by a bot). Each turn one
// side attacks from a real zone entry of the final: the user only picks players for the slots, the backend simulates the
// play from the players' strengths and weaknesses, and the page replays it on the rink and explains it. The page stays
// simple for newcomers: a player shows what they are good at in a few words, and the numbers behind it are one tap away
// (the stats sheet, "Show the numbers"). Every player card can play; the ones without tracking data wait under
// "Other players".

const SLOT_LABEL = { carrier: 'Puck carrier', support: 'Support', goalie: 'Goalie', defender: 'Defender' }
const SLOT_ROLE = { carrier: 'skater', support: 'skater', defender: 'skater', goalie: 'goalie' }
const GOALIE_SPOT = [25.1, 0]
// The traits that matter in each slot: a forward's shot blocking means nothing when they attack.
const ATTACK_TRAITS = ['close', 'long', 'power', 'speed', 'passing', 'battles']
const SLOT_TRAITS = {
  carrier: ATTACK_TRAITS,
  support: ATTACK_TRAITS,
  defender: ['blocking', 'reading', 'battles', 'speed'],
  goalie: ['close', 'long', 'lateral'],
}
const pct = (v) => `${Math.round(v * 100)}%`
const fullName = (card) => `${card.player.first_name} ${card.player.last_name}`
// One player can have several cards (a base card and a special): they are the same player on the ice.
const playerOf = (card) => `${fullName(card)}|${card.player.team}`
const OTHERS_PAGE = 24

export default function Shootout() {
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const [info, setInfo] = useState(null)
  const [players, setPlayers] = useState(null) // every pickable player card, the real-data ones first
  const [duel, setDuel] = useState(null)
  const [picks, setPicks] = useState({})
  const [slot, setSlot] = useState(null)
  const [play, setPlay] = useState(null) // { result, turn, next, reward } while a turn is replayed and explained
  const [frame, setFrame] = useState(0)
  const [phase, setPhase] = useState('pick') // pick, playing, result
  const [stats, setStats] = useState(null) // the entry whose stats sheet is open
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.duelInfo().then(setInfo).catch((err) => setError(err.message))
    api.duelPlayers().then((d) => setPlayers(d.players)).catch((err) => setError(err.message))
  }, [])

  // Replay the frames one after the other, then explain the play.
  useEffect(() => {
    if (phase !== 'playing') return
    const frames = play.result.frames
    if (frame >= frames.length) {
      setPhase('result')
      return
    }
    const t = setTimeout(() => setFrame(frame + 1), frames[frame].ms)
    return () => clearTimeout(t)
  }, [phase, frame, play])

  const begin = (view) => {
    setDuel(view)
    setPicks({})
    setSlot(view.turn?.slots[0] ?? null)
    setPlay(null)
    setPhase('pick')
    setError(null)
  }

  const start = async (mode) => {
    setBusy(true)
    try {
      begin(await api.duelStart(mode))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.duelPlay(duel.id, picks)
      if (data.progress) setProgress(data.progress)
      setPlay({ result: data.result, turn: duel.turn, next: data.duel, reward: data.pack ? data : null })
      setFrame(0)
      setPhase('playing')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !info) return <p className="error">{error}</p>
  if (!info || !players) return <p className="muted">Loading…</p>

  if (!duel)
    return (
      <section className="duel">
        <BackLink to="/" label="Back home" />
        <Lobby active={info.active} busy={busy} onStart={start} onContinue={() => begin(info.active)} />
        {error && <p className="error">{error}</p>}
      </section>
    )

  const shownTurn = play ? play.turn : duel.turn
  const finishedNow = phase === 'result' && play.next.finished

  return (
    <section className="duel">
      <BackLink to="/" label="Back home" />
      <Scoreboard duel={phase === 'playing' ? duel : play?.next ?? duel} />
      {phase === 'pick' && duel.turn && (
        <p className="duel-prompt">
          <strong>{duel.turn.attacking ? 'Your attack' : 'Your defence'}</strong>
          {duel.turn.attacking
            ? duel.mode === '2v2'
              ? 'Pick who carries the puck in and who supports.'
              : 'Pick who carries the puck in and shoots.'
            : duel.mode === '2v2'
            ? 'Pick your goalie and defender. Your friend picks attackers after you.'
            : 'Pick your goalie. Your friend picks a shooter after you.'}
        </p>
      )}
      {shownTurn && (
        <Board players={players} turn={shownTurn} picks={picks} slot={slot} setSlot={setSlot} play={play} frame={frame} phase={phase} />
      )}

      {phase === 'pick' && duel.turn && (
        <Picker duel={duel} players={players} picks={picks} slot={slot} setSlot={setSlot} setPicks={setPicks} busy={busy} onSubmit={submit} onStats={setStats} />
      )}
      {phase === 'playing' && (
        <div className="pack-actions">
          <button type="button" className="pack-button secondary" onClick={() => setFrame(play.result.frames.length)}>
            Skip to the result
          </button>
        </div>
      )}
      {phase === 'result' && <Why play={play} onStats={setStats} />}
      {phase === 'result' && !finishedNow && (
        <div className="pack-actions">
          <button type="button" className="pack-button" onClick={() => begin(play.next)}>
            Next: {play.next.turn.attacking ? 'your attack' : 'your defence'} →
          </button>
        </div>
      )}
      {finishedNow && (
        <Finish
          duel={play.next}
          reward={play.reward}
          onOpen={() => navigate('/pack', { state: { pack: play.reward.pack, title: play.reward.title } })}
          onAgain={() => {
            setDuel(null)
            api.duelInfo().then(setInfo).catch(() => {})
          }}
        />
      )}
      {error && <p className="error">{error}</p>}
      {stats && <StatsSheet entry={stats} onClose={() => setStats(null)} />}
    </section>
  )
}

function Lobby({ active, busy, onStart, onContinue }) {
  return (
    <div className="duel-lobby">
      <h1>Shootout duel</h1>
      <p className="duel-lede">
        Challenge a friend to a shootout. Pick your players, then watch the attack play out. Every player is good at
        different things, taken from how they really played. Pick the right player for the moment and beat your friend.
      </p>
      <p className="duel-rewards">Every duel earns a free pack. Win it for an extra pack with a special card.</p>
      <div className="duel-modes">
        <button type="button" className="duel-mode" disabled={busy} onClick={() => onStart('1v1')}>
          <strong>1 vs 1</strong>
          <span>Your shooter against your friend's goalie.</span>
        </button>
        <button type="button" className="duel-mode" disabled={busy} onClick={() => onStart('2v2')}>
          <strong>2 vs 2</strong>
          <span>Two attackers against your friend's goalie and defender.</span>
        </button>
      </div>
      {active && (
        <div className="pack-actions">
          <button type="button" className="pack-button secondary" onClick={onContinue}>
            Continue your {active.mode === '2v2' ? '2 vs 2' : '1 vs 1'} duel ({active.score.you}–{active.score.bot})
          </button>
        </div>
      )}
      <details className="duel-how">
        <summary>How it works</summary>
        <ul className="small">
          <li>This is a demo, so you play alone: your friend is played by the computer.</li>
          <li>Three rounds: you attack, then your friend attacks. Level after three rounds: sudden death.</li>
          <li>Every attack starts at the blue line, from a real zone entry of the final.</li>
          <li>The defence picks first. When you attack you see who defends, but not what they are good at until they have played.</li>
          <li>Pick any player for any turn, as often as you like. A player just can't play for both sides in the same turn.</li>
          <li>Players from the final use the real tracking data. You can pick any other card too, but without tracking data their stats are random and weaker.</li>
        </ul>
      </details>
    </div>
  )
}

function Scoreboard({ duel }) {
  const marks = (side) =>
    duel.history.filter((h) => h.attacker === side).map((h, i) => <i key={i} className={h.goal ? 'goal' : 'miss'} />)
  const sudden = duel.round > duel.regulation
  return (
    <div className="duel-score">
      <div className="duel-side you">
        <span>You</span>
        <b>{duel.score.you}</b>
        <span className="duel-marks">{marks('you')}</span>
      </div>
      <small className="duel-round">{duel.finished ? 'Final' : sudden ? 'Sudden death' : `Round ${duel.round} of ${duel.regulation}`}</small>
      <div className="duel-side bot">
        <span>Friend</span>
        <b>{duel.score.bot}</b>
        <span className="duel-marks">{marks('bot')}</span>
      </div>
    </div>
  )
}

// The rink: the zone entry with the slots before the play, then the replay frame by frame.
function Board({ players, turn, picks, slot, setSlot, play, frame, phase }) {
  const attacker = turn.attacking ? 'you' : 'bot'
  const defender = turn.attacking ? 'bot' : 'you'
  const s = turn.scenario
  const names = {}
  if (play) {
    const { attack, defense, cards } = play.result
    const name = (cid) => cards[cid]?.card.player.last_name
    Object.assign(names, { A1: name(attack.carrier), A2: name(attack.support), G: name(defense.goalie), D: name(defense.defender) })
  } else {
    const own = Object.fromEntries(players.map((e) => [e.card.id, e]))
    const label = (key) => (picks[key] ? own[picks[key]]?.card.player.last_name : SLOT_LABEL[key])
    const opp = (key) => turn.opponent[key]?.card.player.last_name
    if (turn.attacking) Object.assign(names, { A1: label('carrier'), A2: label('support'), G: opp('goalie'), D: opp('defender') })
    else Object.assign(names, { A1: 'Attacker', A2: 'Attacker', G: label('goalie'), D: label('defender') })
  }

  const frames = play?.result.frames
  const current = frames ? frames[Math.min(frame, frames.length - 1)] : null
  const at = current?.positions ?? { A1: s.carrier, A2: s.support, D: s.defender, G: GOALIE_SPOT, puck: s.carrier }
  const pickable = phase === 'pick'
  const slotOf = { A1: 'carrier', A2: 'support', D: 'defender', G: 'goalie' }
  const dots = [
    { id: 'A1', kind: 'skater', side: attacker },
    at.A2 && { id: 'A2', kind: 'skater', side: attacker },
    at.D && { id: 'D', kind: 'skater', side: defender },
    { id: 'G', kind: 'goalie', side: defender },
  ]
    .filter(Boolean)
    .map((d) => {
      const own = turn.slots.includes(slotOf[d.id])
      return {
        ...d,
        at: at[d.id],
        label: names[d.id],
        active: pickable && own && slot === slotOf[d.id],
        onClick: pickable && own ? () => setSlot(slotOf[d.id]) : undefined,
      }
    })
  dots.push({ id: 'puck', kind: 'puck', at: at.puck })
  const caption = current?.caption ?? null
  return (
    <HalfRink
      dots={dots}
      duration={current ? Math.min(current.ms * 0.85, 1000) : 0}
      caption={caption}
      outcome={phase !== 'pick' && current?.outcome}
    />
  )
}

function Picker({ duel, players, picks, slot, setSlot, setPicks, busy, onSubmit, onStats }) {
  const { turn } = duel
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(OTHERS_PAGE)
  const byId = Object.fromEntries(players.map((e) => [e.card.id, e]))
  const full = turn.slots.every((k) => picks[k])
  // A player can't play twice in one turn: not for both sides, not in two of your slots.
  const friends = new Set(Object.values(turn.opponent).map((e) => playerOf(e.card)))
  const yours = new Set(Object.entries(picks).filter(([k]) => k !== slot).map(([, cid]) => playerOf(byId[cid].card)))

  const choose = (cid) => {
    const next = { ...picks, [slot]: cid }
    setPicks(next)
    setSlot(turn.slots.find((k) => !next[k]) ?? slot)
  }

  const fitting = players.filter((e) => e.role === SLOT_ROLE[slot])
  const real = fitting.filter((e) => e.real)
  const q = query.trim().toLowerCase()
  const others = fitting.filter(
    (e) => !e.real && (!q || [fullName(e.card), e.card.player.team, e.card.title].some((t) => t && t.toLowerCase().includes(q))),
  )
  const tile = (e) => (
    <Tile
      key={e.card.id}
      entry={e}
      picked={Object.entries(picks).find(([, cid]) => cid === e.card.id)?.[0]}
      blocked={friends.has(playerOf(e.card)) ? 'Plays for your friend' : yours.has(playerOf(e.card)) ? 'Already in your line-up' : null}
      slot={slot}
      onPick={() => choose(e.card.id)}
      onStats={() => onStats(e)}
    />
  )
  return (
    <div className="duel-picker">
      <Opponent turn={turn} onStats={onStats} />
      <div className="duel-slots">
        {turn.slots.map((k) => {
          const e = byId[picks[k]]
          return (
            <button key={k} type="button" className={`duel-slot ${slot === k ? 'active' : ''} ${e ? 'filled' : ''}`} onClick={() => setSlot(k)}>
              <small>{SLOT_LABEL[k]}</small>
              <strong>{e ? e.card.player.last_name : 'Pick'}</strong>
            </button>
          )
        })}
        <button type="button" className="pack-button duel-go" disabled={!full || busy} onClick={onSubmit}>
          {busy ? 'Playing…' : turn.attacking ? 'Attack!' : 'Defend!'}
        </button>
      </div>
      <p className="duel-hand-title">
        Choose your <strong>{SLOT_LABEL[slot]?.toLowerCase()}</strong>
      </p>
      <div className="duel-hand">{real.map(tile)}</div>
      <details className="duel-bench">
        <summary>
          Other players ({fitting.length - real.length}) <span className="muted">· no tracking data, so their stats are random and weaker</span>
        </summary>
        <label className="search duel-search">
          <input
            type="search"
            value={query}
            placeholder="Search a player, team or card"
            aria-label="Search the other players"
            onChange={(e) => {
              setQuery(e.target.value)
              setLimit(OTHERS_PAGE)
            }}
          />
        </label>
        <div className="duel-hand">{others.slice(0, limit).map(tile)}</div>
        {others.length > limit && (
          <button type="button" className="link-button duel-more" onClick={() => setLimit(limit + OTHERS_PAGE)}>
            Show more ({others.length - limit} left)
          </button>
        )}
        {!others.length && <p className="muted small">No players match.</p>}
      </details>
    </div>
  )
}

function Opponent({ turn, onStats }) {
  const entries = Object.entries(turn.opponent)
  if (!entries.length) return null
  return (
    <div className="duel-opponent">
      <small className="muted">Defending:</small>
      {entries.map(([k, e]) => (
        <button key={k} type="button" className="duel-opp" disabled={!e.profile} onClick={() => onStats(e)}>
          <PlayerPhoto player={e.card.player} className="duel-photo tiny" />
          <span>
            <strong>{e.card.player.last_name}</strong>
            <small className="muted">{e.profile ? <Good profile={e.profile} slot={k} /> : `${e.card.title} · strengths unknown`}</small>
          </span>
        </button>
      ))}
    </div>
  )
}

// What a player is good (and bad) at in this slot, in a few words.
function Good({ profile, slot }) {
  const ranked = SLOT_TRAITS[slot].map((t) => profile.traits[t]).sort((a, b) => b.value - a.value)
  const good = ranked.filter((t) => t.value >= 65).slice(0, 2).map((t) => t.short)
  const bad = ranked.filter((t) => t.value <= 35).slice(-1).map((t) => t.short)
  return (
    <span className="duel-good">
      {good.length > 0 && <span className="up">▲ {good.join(', ')}</span>}
      {bad.length > 0 && <span className="down">▼ {bad.join(', ')}</span>}
      {!good.length && !bad.length && <span>All-rounder</span>}
    </span>
  )
}

function Tile({ entry, picked, blocked, slot, onPick, onStats }) {
  const { card, profile } = entry
  return (
    <div className={`duel-tile ${picked ? 'picked' : ''} ${blocked ? 'used' : ''}`}>
      <button type="button" className="duel-tile-main" disabled={!!blocked} onClick={onPick}>
        <PlayerPhoto player={card.player} className="duel-photo" />
        <span className="duel-tile-body">
          <strong>{card.player.last_name}</strong>
          <small className="muted">{card.title ?? `${card.player.position} · ${card.player.team}`}</small>
          {blocked ? <small className="muted">{blocked}</small> : <Good profile={profile} slot={slot} />}
          {picked && <small className="duel-picked">{SLOT_LABEL[picked]}</small>}
        </span>
      </button>
      <button type="button" className="duel-info" aria-label={`Stats of ${fullName(card)}`} onClick={onStats}>
        i
      </button>
    </div>
  )
}

// Every trait of a player with the numbers behind it, for those who want them.
function StatsSheet({ entry, onClose }) {
  const { card, profile } = entry
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="duel-sheet-backdrop" onClick={onClose}>
      <div className="duel-sheet" role="dialog" aria-modal="true" aria-label={`Stats of ${fullName(card)}`} onClick={(e) => e.stopPropagation()}>
        <button type="button" className="duel-sheet-close" aria-label="Close" onClick={onClose}>
          ✕
        </button>
        <div className="duel-sheet-head">
          <span className="duel-thumb big" aria-hidden="true">
            <CardFace card={card} />
          </span>
          <div>
            <h2>{fullName(card)}</h2>
            <p className="muted small">
              {card.title ?? 'Base card'} · {entry.position}
            </p>
            <p className={`small ${profile.real ? 'duel-real' : 'muted'}`}>
              {profile.real
                ? `Real tracking data from ${profile.game}`
                : `No tracking data for this player, so the stats are random, based on the position, and weaker than the real ones.`}
            </p>
          </div>
        </div>
        <ul className="duel-traits">
          {Object.entries(profile.traits).map(([k, t]) => (
            <li key={k}>
              <span>{t.label}</span>
              <span className="duel-bar" aria-hidden="true">
                <i style={{ width: `${t.value}%` }} className={t.value >= 65 ? 'up' : t.value <= 35 ? 'down' : ''} />
              </span>
              <b>{t.value}</b>
              <small className="muted">{t.evidence ?? t.use}</small>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// Why the play ended the way it did: the decisive moment, its chance against the same chance with average players, and
// the biggest reasons in plain words. The numbers and every step are behind "Show the numbers".
function Why({ play, onStats }) {
  const [open, setOpen] = useState(false)
  const { result } = play
  const { why } = result
  const youAttacked = result.attacker === 'you'
  const forYou = result.goal === youAttacked
  const yours = (f) => {
    const side = Object.values(result.attack).includes(f.card_id) ? 'attack' : 'defence'
    return (side === 'attack') === youAttacked
  }
  const helpsYou = (f) => (f.favours === 'attack') === youAttacked
  const title = { goal: 'Goal!', save: 'Saved!', block: 'Blocked!', battle: 'Puck lost!', interception: 'Intercepted!' }[result.ending]
  const better = why.chance.value > why.base
  return (
    <div className={`duel-why ${forYou ? 'good' : 'bad'}`}>
      <h2>{title}</h2>
      <p className="duel-why-headline">{why.headline}</p>

      <div className="duel-meter">
        <div className="duel-meter-top">
          <span>{why.chance.label}</span>
          <b>{pct(why.chance.value)}</b>
        </div>
        <div className="duel-meter-bar" aria-hidden="true">
          <i style={{ width: pct(why.chance.value) }} />
          <em style={{ left: pct(why.base) }} />
        </div>
        <small className="muted">
          With average players it would have been {pct(why.base)}
          {Math.abs(why.chance.value - why.base) >= 0.03 ? `: these players made it ${better ? 'higher' : 'lower'}.` : '.'}
        </small>
      </div>

      {why.reasons.length > 0 && (
        <>
          <h3>Why</h3>
          <ul className="duel-reasons">
            {why.reasons.map((r, i) => (
              <li key={i} className={helpsYou(r) ? 'up' : 'down'}>
                <span aria-hidden="true">{helpsYou(r) ? '▲' : '▼'}</span>
                <span>
                  {r.text}
                  <small>
                    {yours(r) ? 'your pick' : "your friend's pick"} · {helpsYou(r) ? 'helped you' : 'helped your friend'}
                  </small>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {why.context.map((c, i) => (
        <p key={i} className="small muted duel-context">
          {c}
        </p>
      ))}
      {why.luck && <p className="small duel-luck">{why.luck}</p>}

      <button type="button" className="link-button small" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? 'Hide the numbers' : 'Show the numbers'}
      </button>
      {open && (
        <div className="duel-numbers">
          <ol className="duel-steps">
            {result.steps.map((s, i) => (
              <li key={i}>
                <p>
                  {s.text}
                  {s.chance && (
                    <span className="duel-chance">
                      {s.chance.label}: <b>{pct(s.chance.value)}</b>
                    </span>
                  )}
                </p>
                {s.factors.length > 0 && (
                  <ul className="duel-factors">
                    {s.factors.map((f, j) => (
                      <li key={j} className={helpsYou(f) ? 'up' : 'down'}>
                        <span>
                          {f.name}: {f.label} <b>{f.value}</b>
                        </span>
                        <small className="muted">{f.evidence ?? 'No tracking data: random stats'}</small>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
          <p className="small muted">
            Tap a player for all their stats:{' '}
            {Object.values(result.cards).map((e, i) => (
              <span key={e.card.id}>
                {i > 0 && ', '}
                <button type="button" className="link-button" onClick={() => onStats(e)}>
                  {e.card.player.last_name}
                </button>
              </span>
            ))}
          </p>
        </div>
      )}
    </div>
  )
}

function Finish({ duel, reward, onOpen, onAgain }) {
  const { you, bot } = duel.score
  const title = duel.winner === 'you' ? 'You won the shootout!' : duel.winner === 'bot' ? 'Your friend won this one' : "It's a draw"
  return (
    <div className="duel-finish">
      <h2>{title}</h2>
      <p className="duel-final-score">
        {you}–{bot}
      </p>
      {reward && <p>{duel.winner === 'you' ? 'A free pack for playing, and a pack with a special card for the win.' : 'A free pack for playing.'}</p>}
      <div className="pack-actions">
        {reward && (
          <button type="button" className="pack-button" onClick={onOpen}>
            Open {duel.winner === 'you' ? 'your packs' : 'your pack'}
          </button>
        )}
        <button type="button" className="pack-button secondary" onClick={onAgain}>
          Play again
        </button>
      </div>
    </div>
  )
}
