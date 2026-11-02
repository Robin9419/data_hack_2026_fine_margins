import { useAuth } from '../auth'
import RewardIcon from './RewardIcon'

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
        <span className="reward-next">
          {next ? <><RewardIcon id={next.id} />{next.points - points} pts to {next.title}</> : 'All rewards unlocked!'}
        </span>
      </div>
      <div className="reward-track" role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={points}>
        <div className="reward-fill" style={{ width: `${Math.min(100, (points / max) * 100)}%` }} />
        {rewards.map((r) => {
          const pct = (r.points / max) * 100
          const edge = pct < 15 ? 'start' : pct > 85 ? 'end' : 'mid'
          const status = r.reached ? 'Unlocked' : `${r.points - points} pts to go`
          return (
            <div
              key={r.id}
              className={`reward-pin edge-${edge}`}
              style={{ left: `${pct}%` }}
              tabIndex={0}
              aria-label={`${r.title} at ${r.points} points. ${status}`}
            >
              <span className={`reward-mark ${r.reached ? 'reached' : ''}`}>
                <RewardIcon id={r.id} />
                <small>{r.points}</small>
              </span>
              <span className="reward-tip" role="tooltip">
                <span className="reward-tip-icon" aria-hidden="true"><RewardIcon id={r.id} /></span>
                <span className="reward-tip-text">
                  <strong>{r.title}</strong>
                  <small>{r.points} pts</small>
                </span>
                <span className={`reward-tip-state ${r.reached ? 'done' : ''}`}>{status}</span>
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
