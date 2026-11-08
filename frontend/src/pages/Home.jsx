import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAllCards } from '../allCards'
import { useAuth } from '../auth'
import Activities from '../components/Activities'
import CardSpotlight from '../components/CardSpotlight'
import CardTile from '../components/CardTile'
import { useTournament } from '../tournament'

const ROW_SIZE = 4

// Best cards order: legends, impact specials (profile and performance), ones to watch, collector, base cards.
const category = (c) =>
  c.type === 'legend' ? 0
  : c.type === 'special' && (c.kind === 'profile' || c.kind === 'performance') ? 1
  : c.kind === 'road' ? 2
  : c.kind === 'collector' ? 3
  : c.type === 'base' ? 4
  : 5
const byDateDesc = (a, b) => (b.match?.date ?? '').localeCompare(a.match?.date ?? '')
// Within a category, cards of the favorite team come first, then the newest.
const cardTeam = (c) => c.player?.team ?? c.team
const bestOrder = (favorite) => (a, b) => {
  const fa = favorite && cardTeam(a) === favorite ? 0 : 1
  const fb = favorite && cardTeam(b) === favorite ? 0 : 1
  return category(a) - category(b) || fa - fb || byDateDesc(a, b)
}

export default function Home() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, setProgress } = useAuth()
  const { tournament } = useTournament()
  const stage = tournament?.stage
  const newCardIds = location.state?.newCardIds ?? []
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [spotlight, setSpotlight] = useState(null)
  const allCards = useAllCards()
  const closeSpotlight = useCallback(() => setSpotlight(null), [])

  // The cards that exist change with the stage of the tournament timeline.
  useEffect(() => {
    if (!stage) return
    api
      .cards()
      .then((data) => {
        setCards(data.cards)
        setProgress(data.progress)
      })
      .catch((err) => setError(err.message))
  }, [stage])

  if (error) return <p className="error">{error}</p>
  if (!cards) return <p className="muted">Loading cards…</p>

  const realCards = cards
  const ownedCount = realCards.filter((c) => c.owned).length
  const owned = realCards.filter((c) => c.owned)
  const best = owned
    .slice()
    .sort(bestOrder(user?.favorite_team))
    .slice(0, ROW_SIZE)
  const bestIds = new Set(best.map((c) => c.id))
  const latest = owned
    .filter((c) => c.type === 'special' && !bestIds.has(c.id))
    .sort(byDateDesc)
    .slice(0, ROW_SIZE)

  const row = (title, list) =>
    list.length > 0 && (
      <>
        <h2 className="home-subtitle">{title}</h2>
        <div className="card-grid home-row">
          {list.map((card) => (
            <CardTile key={card.id} card={card} onOpen={setSpotlight} full={allCards?.get(card.id)} />
          ))}
        </div>
      </>
    )

  return (
    <section>
      {newCardIds.length > 0 && (
        <div className="banner home-banner">
          <span>
            {newCardIds.length} new {newCardIds.length === 1 ? 'card' : 'cards'} added to your collection.
          </span>
          <button type="button" className="link-button" onClick={() => navigate('/collection', { state: { newCardIds } })}>
            Open Collection ›
          </button>
        </div>
      )}

      <Activities />

      <div className="home-highlights" data-tour="highlights">
        <div className="section-header">
          <h1>Your Collection Highlights</h1>
          <div className="home-collection-link">
            <span className="muted">
              <strong>
                {ownedCount} / {realCards.length}
              </strong>{' '}
              Cards Collected
            </span>
            <Link to="/collection" className="pack-button">
              View Your Whole Collection ›
            </Link>
          </div>
        </div>
        {row('Best Cards', best)}
        {row('Latest Performances', latest)}
        {best.length === 0 && latest.length === 0 && (
          <p className="muted">No special cards yet. Open packs and make predictions to win some.</p>
        )}
      </div>

      {spotlight && <CardSpotlight card={spotlight} onClose={closeSpotlight} />}
    </section>
  )
}
