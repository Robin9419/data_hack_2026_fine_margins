import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

// Two quiet ways to earn free base cards: follow the Spengler Cup Instagram (once) or buy match tickets (per ticket).
export default function FreeCards() {
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const [info, setInfo] = useState(null)
  const [tickets, setTickets] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.bonusInfo().then(setInfo).catch(() => {})
  }, [])

  if (!info) return null
  const { instagram, tickets: ticketInfo } = info
  const cardCount = tickets * ticketInfo.cards_per_ticket

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
      if (err.status === 409) setInfo({ ...info, instagram: { ...instagram, claimed: true } })
    }
  }

  return (
    <div className="free-cards">
      <div className="free-offer">
        <div>
          <strong>Follow Spengler Cup on Instagram</strong>
          <small>{instagram.cards} free base cards, once per account.</small>
        </div>
        {instagram.claimed ? (
          <span className="free-done">Claimed ✓</span>
        ) : (
          <button type="button" disabled={busy} onClick={() => claim(api.bonusInstagram)}>
            Sign up
          </button>
        )}
      </div>

      <div className="free-offer">
        <div>
          <strong>Buy match tickets</strong>
          <small>{ticketInfo.cards_per_ticket} free base cards for every ticket.</small>
        </div>
        <div className="free-tickets">
          <button type="button" aria-label="Fewer tickets" disabled={tickets <= 1} onClick={() => setTickets(tickets - 1)}>
            −
          </button>
          <span>{tickets}</span>
          <button type="button" aria-label="More tickets" disabled={tickets >= ticketInfo.max} onClick={() => setTickets(tickets + 1)}>
            +
          </button>
          <button type="button" className="free-claim" disabled={busy} onClick={() => claim(() => api.bonusTickets(tickets))}>
            Get {cardCount} cards
          </button>
        </div>
      </div>
      {error && <p className="free-error">{error}</p>}
    </div>
  )
}
