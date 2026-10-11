import { useAuth } from '../auth'

// Reward progress shown at the top of every page. Each card is worth points (a stadium edition
// more than a home one) and the milestones on the bar are the (illustrative) rewards.
export default function RewardBar() {
  const { progress } = useAuth()
  if (!progress) return null

  const { points, max_points: max, rewards } = progress
  const next = rewards.find((r) => !r.reached)

  return (
    <div className="reward-bar" aria-label="Reward progress">
      <div className="reward-head">
        <strong>{points} pts</strong>
        <span>{next ? `${next.points - points} pts to ${next.icon} ${next.title}` : 'All rewards unlocked!'}</span>
      </div>
      <div className="reward-track" role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={points}>
        <div className="reward-fill" style={{ width: `${Math.min(100, (points / max) * 100)}%` }} />
        {rewards.map((r) => (
          <span
            key={r.id}
            className={`reward-mark ${r.reached ? 'reached' : ''}`}
            style={{ left: `${(r.points / max) * 100}%` }}
            title={`${r.title} at ${r.points} pts`}
          >
            {r.icon}
            <small>{r.points}</small>
          </span>
        ))}
      </div>
    </div>
  )
}
