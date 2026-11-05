import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { useTournament } from '../tournament'
import { TeamLogo } from './TeamName'

const dayName = (iso) => new Date(iso).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// What the user can do right now at their stage of the tournament timeline. The one-off activities (packs to open,
// predictions, the daily card, the social channel of the day, trivia) disappear once done; trading and tickets stay.
export default function Activities() {
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const { tournament } = useTournament()
  const stage = tournament?.stage
  const [acts, setActs] = useState(null)
  const [tickets, setTickets] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  // The activities change with the stage, and with every pack opened (packs_waiting).
  useEffect(() => {
    if (stage) api.activities().then(setActs).catch((err) => setError(err.message))
  }, [stage, tournament?.packs_waiting])

  if (!tournament || !acts) return null

  // Every claim ends in the pack opening page; coming back remounts the gallery, which reloads the activities.
  const claim = async (request) => {
    setBusy(true)
    setError(null)
    try {
      const data = await request()
      setProgress(data.progress)
      navigate('/pack', { state: { pack: data.pack, title: data.title } })
    } catch (err) {
      setError(err.message)
      setBusy(false)
      api.activities().then(setActs).catch(() => {})
    }
  }

  const { predictions, social, trade, tickets: ticketInfo } = acts
  const items = []

  if (acts.packs_waiting > 0)
    items.push(
      <Activity
        key="packs"
        icon="📦"
        title={`Open your ${plural(acts.packs_waiting, 'pack')}`}
        text="Earned with your right predictions."
        action={
          <button type="button" className="activity-button" disabled={busy} onClick={() => claim(api.openAllPacks)}>
            Open
          </button>
        }
        highlight
      />,
    )
  if (predictions)
    items.push(
      <Activity
        key="predict"
        icon="🎯"
        title={predictions.tournament ? 'Predict the tournament' : 'Make your predictions'}
        text={
          predictions.tournament
            ? predictions.picks === 0
              ? `Champion, top scorer and more: ${predictions.questions} calls before the first game. Every right pick earns a pack.`
              : `${predictions.picks} of ${predictions.questions} picks made. They lock when the tournament starts.`
            : predictions.picks === 0
            ? `${plural(predictions.games, 'game')} today, ${predictions.questions} quick questions. Every right pick earns a pack.`
            : `${predictions.picks} of ${predictions.questions} picks made. Finish them before the games start.`
        }
        to="/predict"
        highlight
      />,
    )
  if (acts.daily)
    items.push(
      <Activity
        key="daily"
        icon="🎁"
        title="Your daily pack is ready"
        text="A free pack every day of the tournament."
        action={
          <button type="button" className="activity-button" disabled={busy} onClick={() => claim(api.dailyClaim)}>
            Claim
          </button>
        }
      />,
    )
  if (social)
    items.push(
      <Activity
        key="social"
        icon="📣"
        title={`Follow Spengler Cup on ${social.name}`}
        text={'A free pack for following. A new channel every day.'}
        action={
          <button type="button" className="activity-button" disabled={busy} onClick={() => claim(api.bonusSocial)}>
            Follow
          </button>
        }
      />,
    )
  if (acts.trivia > 0)
    items.push(
      <Activity
        key="trivia"
        icon="❓"
        title="Play trivia about the games"
        text={`Win special cards: ${acts.trivia} still to win. Answer at the stadium for the Stadium edition.`}
        to="/quiz"
      />,
    )
  const always = []
  if (trade.base_copies >= trade.cost)
    always.push(
      <Activity
        key="trade"
        icon="⇄"
        title={`Trade in ${trade.cost} base cards`}
        text="Swap any three for a random new card, maybe a special one."
        to="/trade"
      />,
    )
  always.push(
    <Activity
      key="tickets"
      icon="🎟"
      title="Buy match tickets"
      text={`${ticketInfo.packs_per_ticket} free packs for every ticket.`}
      action={
        <div className="activity-tickets">
          <button type="button" aria-label="Fewer tickets" disabled={tickets <= 1} onClick={() => setTickets(tickets - 1)}>
            −
          </button>
          <span>{tickets}</span>
          <button
            type="button"
            aria-label="More tickets"
            onClick={() => setTickets(tickets + 1)}
          >
            +
          </button>
          <button
            type="button"
            className="activity-button"
            disabled={busy}
            onClick={() => claim(() => api.bonusTickets(tickets))}
          >
            Buy
          </button>
        </div>
      }
    />,
  )

  return (
    <section className="activities" aria-labelledby="activities-title">
      <div className="section-header">
        <h1 id="activities-title">Activities</h1>
        <span className="muted">
          <StageLabel tournament={tournament} />
        </span>
      </div>
      {items.length > 0 ? (
        <div className="activity-list">{items}</div>
      ) : (
        <p className="muted small activity-empty">
          You've done everything for today. Move on in the timeline below for the next gameday.
        </p>
      )}
      <div className="activity-list secondary">{always}</div>
      {error && <p className="error small">{error}</p>}
    </section>
  )
}

function StageLabel({ tournament }) {
  const { stage, today, champion } = tournament
  if (stage === 'pre') return 'Before the tournament · starts Friday 26 December'
  if (stage === 'post')
    return champion ? (
      <>
        After the tournament · <TeamLogo name={champion} /> {champion} won the Spengler Cup
      </>
    ) : (
      'After the tournament'
    )
  return `${today[0]?.stage ?? 'Gameday'} · ${dayName(stage)}`
}

function Activity({ icon, title, text, to, action, highlight }) {
  const body = (
    <>
      <span className="activity-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="activity-text">
        <strong>{title}</strong>
        <small>{text}</small>
      </span>
    </>
  )
  const className = `activity ${highlight ? 'highlight' : ''}`
  if (to)
    return (
      <Link to={to} className={`${className} link`}>
        {body}
        <span className="activity-arrow" aria-hidden="true">
          →
        </span>
      </Link>
    )
  return (
    <div className={className}>
      {body}
      {action}
    </div>
  )
}
