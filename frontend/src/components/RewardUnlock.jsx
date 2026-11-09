import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import RewardIcon from './RewardIcon'

// Keep acknowledgements per account in this browser. The first snapshot is the
// baseline, so signing in does not celebrate rewards earned before this feature.
export function newlyReachedRewards(rewards, acknowledged) {
  return rewards.filter((reward) => reward.reached && !acknowledged.includes(reward.id))
}

export default function RewardUnlock() {
  const { user, progress } = useAuth()
  const [pending, setPending] = useState([])
  const account = useRef(null)
  const acknowledged = useRef([])
  const dialog = useRef(null)
  const storageKey = user ? `reward-notifications:${user.id}` : null

  useEffect(() => {
    if (!storageKey || !progress) {
      account.current = null
      setPending([])
      return
    }
    if (account.current !== storageKey) {
      account.current = storageKey
      let saved = null
      try { saved = JSON.parse(localStorage.getItem(storageKey)) } catch { /* Storage may be unavailable. */ }
      acknowledged.current = Array.isArray(saved)
        ? saved
        : progress.rewards.filter((reward) => reward.reached).map((reward) => reward.id)
      try { localStorage.setItem(storageKey, JSON.stringify(acknowledged.current)) } catch { /* In-memory fallback. */ }
      setPending([])
    }
    const unlocked = newlyReachedRewards(progress.rewards, acknowledged.current)
    setPending((queue) => [...queue, ...unlocked.filter((reward) => !queue.some((item) => item.id === reward.id))])
  }, [storageKey, progress])

  // Hold the popup while packs are being opened (the /pack page); it shows once the user leaves it.
  const openingPacks = useLocation().pathname === '/pack'
  const reward = openingPacks ? undefined : pending[0]
  useEffect(() => {
    if (reward && !dialog.current.open) dialog.current.showModal()
    else if (!reward && dialog.current.open) dialog.current.close()
  }, [reward])

  const dismiss = () => {
    if (!reward) return
    acknowledged.current = [...acknowledged.current, reward.id]
    try { localStorage.setItem(storageKey, JSON.stringify(acknowledged.current)) } catch { /* In-memory fallback. */ }
    setPending((queue) => queue.slice(1))
  }

  return (
    <dialog ref={dialog} className="reward-unlock" aria-labelledby="reward-unlock-title" onCancel={(event) => { event.preventDefault(); dismiss() }}>
      {reward && <>
        <span className="reward-unlock-icon"><RewardIcon id={reward.id} /></span>
        <p className="eyebrow">{reward.points} points reached</p>
        <h2 id="reward-unlock-title">Reward unlocked!</h2>
        <p className="reward-unlock-name">{reward.title}</p>
        {['keychain', 'scarf', 'vip-raffle'].includes(reward.id) && user.favorite_team && <p className="muted">{user.favorite_team}</p>}
        {reward.id === 'vip-raffle' && <p className="muted small">You have unlocked entry into the VIP ticket raffle.</p>}
        <button type="button" className="primary" onClick={dismiss} autoFocus>{pending.length > 1 ? 'Next reward' : 'Continue collecting'}</button>
      </>}
    </dialog>
  )
}
