import { formatMatchDate } from '../format'
import { nationOf } from '../nations'
import { teamOf, teamStyle } from '../teams'
import CardIcon from './CardIcon'
import FormBars from './FormBars'
import PlayerPhoto from './PlayerPhoto'

// Card kinds are described in docs/CARD_TYPES.md. Front of a card, identity only, no KPIs (they are on the back):
//   base         photo, name, position, team
//   profile      team-colour frame, tag (Sniper, Playmaker, ...) as icon and line above the name
//   performance  dark glitter card with its own accent colour, label on the side (Player of the Match, ...)
//   collector    gold card for a player whose cards are all collected
//   road         Road to Final: evolving card with the rating per game as bars; the last stage is the Champion look
//   context      moment, stadium or trophy: a scene instead of a player portrait
// state: 'owned' (full colour), 'locked' (gallery: grayed out photo only, no info) or 'hidden' (a mystery card in
// a pack: no photo, name or archetype, so nothing leaks before it is revealed).
// Editions: 'stadium' gets the foil frame; 'fullart', 'ice' and 'gold' are print finishes.
// A legend has its own black-and-gold design with a black and white photo; a locked legend shows only its club.

const FINISHES = ['fullart', 'ice', 'gold']
const BASE_SYMBOL = '●' // the basic rarity: a lightly filled dot, no tier, no special
const POS_SHORT = { Forward: 'FWD', Defender: 'DEF', Goalkeeper: 'GK' }

// A team logo on a small white disc, for the game in the top left corner.
function GameLogo({ name }) {
  const { logo } = teamOf(name)
  return <i className="card-gl">{logo && <img src={logo} alt={name} />}</i>
}

// Tooltip over the game next to the jersey number: both teams with their score, the winner highlighted.
function GameTip({ game }) {
  const rows = [
    [game.home_team, game.home_score, game.home_score > game.away_score],
    [game.away_team, game.away_score, game.away_score > game.home_score],
  ]
  const detail = [game.stage, game.date && formatMatchDate(game.date)].filter(Boolean).join(' · ')
  return (
    <span className="card-game-tip" role="tooltip">
      {rows.map(([name, score, won]) => (
        <span key={name} className={`tip-row ${won ? 'won' : ''}`}>
          <GameLogo name={name} />
          <span className="tip-team">{name}</span>
          <b>{score}</b>
        </span>
      ))}
      {detail && <small>{detail}</small>}
    </span>
  )
}

// Centre ice with faceoff circle and hash marks, drawn faint in the middle of every player card.
function Rink() {
  return (
    <>
      <div className="card-rink" aria-hidden="true">
        <svg viewBox="0 0 100 140" fill="none" stroke="#fff" strokeWidth="0.6" preserveAspectRatio="none">
          <circle cx="72" cy="64" r="13" />
          <circle cx="72" cy="64" r="1.4" fill="#fff" />
          <path d="M56 64h4M84 64h4M72 48v3M72 77v3" />
          <path d="M-4 100a40 40 0 0 1 40 40" strokeWidth="0.8" />
        </svg>
      </div>
      <div className="card-scratch" aria-hidden="true" />
    </>
  )
}

const ARCHETYPES = {
  Sniper: { icon: 'target', color: '#ff6a4a' },
  'Volume Shooter': { icon: 'burst', color: '#ff6a4a' },
  'Chance Creator': { icon: 'burst', color: '#ffd76a' },
  'Go-To Scorer': { icon: 'flag', color: '#ff6a4a' },
  Playmaker: { icon: 'nodes', color: '#b98bff' },
  'Pressure Reliever': { icon: 'nodes', color: '#b98bff' },
  Speedster: { icon: 'bolt', color: '#19e6ff' },
  'Shot Blocker': { icon: 'shield', color: '#45ff92' },
  Workhorse: { icon: 'flame', color: '#ff9a3c' },
  'Shot Stopper': { icon: 'shield', color: '#7cc4ff' },
}
const PERFORMANCE_ICON = { motm: 'star', gamewinner: 'burst', wall: 'shield', recordbreaker: 'bolt' }
// Label, icon, frame tier and rarity symbol per context card.
const CONTEXT = {
  moment: { label: 'Moment', icon: 'star', tier: 'elite', rarity: '★★★' },
  stadium: { label: 'Stadium', icon: 'flag', tier: 'silver', rarity: '◆' },
  trophy: { label: 'Trophy', icon: 'trophy', tier: 'elite', rarity: '★★★' },
}

const kindOf = (card) => card.kind ?? (card.type === 'base' ? 'base' : 'profile')

function LockedReward({ card }) {
  const ctx = CONTEXT[card.context_type]
  return (
    <div className="card-face locked reward-locked" style={teamStyle(card.player?.team ?? 'HC Davos')}>
      {card.player && <PlayerPhoto player={card.player} className="card-art" />}
      <div className="card-info">
        <p className="card-archetype chip">
          <CardIcon name={ctx?.icon ?? 'gift'} />
          {ctx?.label ?? 'Collector'}
        </p>
        <p className="card-name">{card.title}</p>
        <p className="card-meta unlock-rule">{card.unlock}</p>
      </div>
    </div>
  )
}

export default function CardFace({ card, state = 'owned', nameLayout = 'vertical' }) {
  if (card.type === 'legend' && state !== 'hidden') return <LegendFace card={card} locked={state === 'locked'} />

  if (state === 'locked') {
    if (card.type === 'reward') return <LockedReward card={card} />
    return (
      <div className="card-face locked" style={teamStyle(card.player.team)}>
        <PlayerPhoto player={card.player} className="card-art" />
      </div>
    )
  }

  if (state !== 'owned') {
    return (
      <div className={`card-face mystery ${state}`}>
        <span className="mystery-mark">?</span>
        <div className="card-info">
          <p className="card-archetype">? ? ?</p>
          <p className="card-name">Mystery player</p>
        </div>
      </div>
    )
  }

  const kind = kindOf(card)
  if (kind === 'context') return <ContextFace card={card} />
  const { player, match } = card
  const team = teamOf(player.team)
  const nation = nationOf(player.nationality)
  const stadium = card.edition === 'stadium'
  const finish = FINISHES.includes(card.edition) ? card.edition : null
  const archetype = ARCHETYPES[card.title] ?? { icon: 'star', color: '#ffd76a' }
  const road = kind === 'road' ? card.road : null
  const champion = road?.stage === 4
  const dark = kind === 'performance' || champion // the dark glitter look with the surname on the side
  const sideText = champion ? 'Champion' : card.title
  const vertical = dark && nameLayout !== 'horizontal'
  const classes = [
    'card-face',
    'owned',
    kind,
    dark ? 'fa' : '',
    dark && !vertical ? 'hname' : '',
    kind === 'collector' ? 'tier-gold' : '',
    kind === 'performance' ? `special-${card.special_type}` : '',
    champion ? 'performance special-champion' : '',
    stadium ? 'edition-stadium' : '',
    finish ? `finish-${finish}` : '',
  ]
  const rarity =
    dark || kind === 'road' || kind === 'collector'
      ? '★★★'
      : kind === 'profile'
        ? '◆'
        : kind === 'base'
          ? BASE_SYMBOL
          : null
  const game = match && (kind === 'profile' || kind === 'performance') ? match : null
  const pos = POS_SHORT[player.position]
  // The tag (archetype etc.): an icon in the top left corner and its name as a line above the player name.
  const tag =
    dark
      ? { icon: champion ? 'trophy' : PERFORMANCE_ICON[card.special_type], color: 'var(--s1)', line: false }
      : kind === 'profile'
      ? { icon: archetype.icon, color: archetype.color, label: card.title }
      : road
        ? { icon: 'flag', color: '#ffd76a', label: 'Road to Final' }
        : kind === 'collector'
          ? { icon: 'gift', color: '#ffd76a', label: `Collector · ${card.requires.length}/${card.requires.length}` }
          : null

  return (
    <div className={classes.filter(Boolean).join(' ')} style={{ ...teamStyle(player.team), ...(tag ? { '--tc': tag.color } : {}) }}>
      <div className="card-inner" style={dark ? { '--llen': sideText.length } : undefined}>
        <PlayerPhoto player={player} className="card-art" />
        {dark && player.action_video_url && (
          <video className="card-action" src={player.action_video_url} poster={player.action_image_url ?? undefined} autoPlay loop muted playsInline />
        )}
        {dark && !player.action_video_url && player.action_image_url && (
          <img className="card-action" src={player.action_image_url} style={player.action_focus ? { objectPosition: player.action_focus } : undefined} alt="" referrerPolicy="no-referrer" loading="lazy" />
        )}
        {(dark || kind === 'collector' || (road && road.stage >= 3)) && <div className="card-glitter" aria-hidden="true" />}
        {finish && <div className="card-layer" aria-hidden="true" />}

        {tag && (
          <div className="card-tag" style={{ '--tc': tag.color }}>
            <span className="card-tag-icon">
              <CardIcon name={tag.icon} />
            </span>
          </div>
        )}
        <div className="card-corner">
          {team.logo && (
            <span className="card-logo">
              <img src={team.logo} alt={team.name} />
            </span>
          )}
          {pos && <span className="card-pos">{pos}</span>}
        </div>
        {stadium && <span className="edition-badge">🏟 Stadium</span>}
        {dark && (
          <span className="card-sidelabel">{sideText}</span>
        )}
        {dark && tag && (
          <div className="card-tag card-tag-end" style={{ '--tc': tag.color }}>
            <span className="card-tag-icon">
              <CardIcon name={tag.icon} />
            </span>
          </div>
        )}
        {dark && !vertical && (
          <div className="card-hname" style={{ '--nlen': player.last_name.length }}>
            <small>
              <i>#{player.jersey}</i> {player.first_name}
            </small>
            <b>
              {player.last_name}
              {nation && <img className="card-flag" src={`https://flagcdn.com/w80/${nation.iso}.png`} alt={nation.code} title={player.nationality} loading="lazy" onError={(e) => e.currentTarget.remove()} />}
            </b>
          </div>
        )}
        {vertical && (
          <div className="card-vname">
            {nation && <img className="card-flag" src={`https://flagcdn.com/w80/${nation.iso}.png`} alt={nation.code} title={player.nationality} loading="lazy" onError={(e) => e.currentTarget.remove()} />}
            <span className="card-vtext" style={{ '--nlen': player.last_name.length }}>
              <b>{player.last_name}</b>
              <small>
                <i>#{player.jersey}</i> {player.first_name}
              </small>
            </span>
          </div>
        )}

        <div className="card-info">
          {road && <FormBars road={road} />}
          {tag && tag.line !== false && (
            <p className="card-tagline" style={{ '--tc': tag.color }}>
              <CardIcon name={tag.icon} />
              {tag.label}
            </p>
          )}
          {!dark && (
            <p className="card-name" style={{ '--nlen': player.last_name.length }}>
              <span className="card-first">{player.first_name}</span>
              {player.last_name}
              {nation && <img className="card-flag" src={`https://flagcdn.com/w80/${nation.iso}.png`} alt={nation.code} title={player.nationality} loading="lazy" onError={(e) => e.currentTarget.remove()} />}
            </p>
          )}
          {(!dark || game) && (
            <p className="card-meta">
              {!dark && (
                <span className="card-no">
                  <span>
                    <small>#</small>
                    {player.jersey}
                  </span>
                </span>
              )}
              {kind === 'base' && <span className="card-team">{team.name}</span>}
              {game && (
                <span className="card-game">
                  <GameLogo name={game.home_team} />
                  <b>
                    {game.home_score}–{game.away_score}
                  </b>
                  <GameLogo name={game.away_team} />
                  <GameTip game={game} />
                </span>
              )}
            </p>
          )}
          <p className="card-foot">
            <span className={`card-rarity ${kind === 'base' ? 'faint' : ''}`}>{rarity}</span>
            <CardIcon name="trophy" />
          </p>
        </div>
      </div>
    </div>
  )
}

// Moment (the scorer with the score), stadium and trophy (a photo of the place or the cup).
function ContextFace({ card }) {
  const ctx = CONTEXT[card.context_type]
  const moment = card.context_type === 'moment'
  return (
    <div className={`card-face owned context ctx-${card.context_type} tier-${ctx.tier}`} style={teamStyle(card.player?.team ?? 'HC Davos')}>
      <div className="card-inner">
        {moment ? (
          <PlayerPhoto player={card.player} className="card-art" />
        ) : (
          <div className="card-art">
            <img src={card.image_url} alt={card.image_alt} style={{ objectPosition: card.image_position }} referrerPolicy="no-referrer" loading="lazy" />
          </div>
        )}
        {card.context_type === 'trophy' && <div className="card-glitter" aria-hidden="true" />}
        <p className="card-label">
          <CardIcon name={ctx.icon} />
          {ctx.label}
        </p>
        {moment && <p className="card-bigscore">{card.headline}</p>}
        <div className="card-info">
          <p className="card-name">
            <span className="card-first">{moment ? `Final goal · ${formatMatchDate(card.match.date)}` : card.headline}</span>
            {moment ? card.player.last_name : card.title}
          </p>
          <p className="card-foot">
            <span className="card-rarity">{ctx.rarity}</span>
            <CardIcon name="trophy" />
          </p>
        </div>
      </div>
    </div>
  )
}

function LegendFace({ card, locked }) {
  const { player } = card
  if (locked) {
    return (
      <div className="card-face legend locked-legend">
        <span className="legend-star" aria-hidden="true">★</span>
        <div className="card-info">
          <p className="card-archetype">Club legend</p>
          <p className="card-name">{player.team}</p>
          <p className="card-meta">Collect the club's cards to unlock</p>
        </div>
      </div>
    )
  }
  return (
    <div className="card-face legend">
      <PlayerPhoto player={player} className="card-art" />
      <span className="legend-ribbon">★ Legend</span>
      <div className="card-info">
        <p className="card-archetype">Club legend</p>
        <p className="card-name">
          <span className="card-first">{player.first_name}</span>
          {player.last_name}
        </p>
        <p className="card-meta">{player.team}</p>
      </div>
    </div>
  )
}
