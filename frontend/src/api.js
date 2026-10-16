// Thin wrapper around the FastAPI backend. The session token lives in localStorage.
const TOKEN_KEY = 'hockeyCards.token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const error = new Error(data.detail || `Request failed (${res.status})`)
    error.status = res.status
    throw error
  }
  return data
}

export const TEST_GAMES_KEY = 'hockeyCards.testGames'

const testGames = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(TEST_GAMES_KEY))
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

export const api = {
  login: (username, favoriteTeam) =>
    request('/login', { method: 'POST', body: { username, favorite_team: favoriteTeam || null } }),
  teams: () => request('/teams'),
  logout: () => request('/logout', { method: 'POST' }),
  me: () => request('/me'),
  cards: (testGames = []) => request(`/cards${testGames.length ? `?test_games=${encodeURIComponent(testGames.join(','))}` : ''}`),
  testdata: () => request('/testdata'),
  adminCards: () => request('/admin/cards'),
  card: (id) =>
    // A Road to Final card depends on which test games are switched on.
    request(`/cards/${id}${id.startsWith('test-road-') ? `?test_games=${encodeURIComponent(testGames().join(','))}` : ''}`),
  dailyStatus: () => request('/daily'),
  dailyClaim: () => request('/daily/claim', { method: 'POST' }),
  tradeInfo: () => request('/trade'),
  trade: (cardIds) => request('/trade', { method: 'POST', body: { card_ids: cardIds } }),
  reset: () => request('/reset', { method: 'POST' }),
  quizStart: (venue) => request('/quiz/start', { method: 'POST', body: { venue } }),
  quizAnswer: (questionId, optionId) =>
    request(`/quiz/${questionId}/answer`, { method: 'POST', body: { option_id: optionId } }),
}
