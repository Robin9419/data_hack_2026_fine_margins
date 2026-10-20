import { teamOf } from '../teams'

export function TeamLogo({ name }) {
  const team = teamOf(name)
  return team.logo ? <img className="team-logo" src={team.logo} alt="" /> : null
}

export default function TeamName({ name, right }) {
  return (
    <span className={`game-team ${right ? 'right' : ''}`}>
      <TeamLogo name={name} />
      <span>{name}</span>
    </span>
  )
}
