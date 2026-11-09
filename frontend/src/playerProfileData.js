export const samePlayer = (a, b) => a.first_name === b.first_name && a.last_name === b.last_name && a.team === b.team

export function adminPlayerCards(map, cardId) {
  const player = map.get(cardId)?.player
  return player
    ? [...map.values()].filter((c) => c.type !== 'reward' && c.player && samePlayer(c.player, player))
    : []
}

export function visiblePlayerGames(games, player, playedIds, admin) {
  return games?.[`${player.team}#${player.jersey}`]?.filter((g) => admin || playedIds.has(g.game))
}
