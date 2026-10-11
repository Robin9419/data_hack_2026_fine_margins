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

export const api = {
  login: (username) => request('/login', { method: 'POST', body: { username } }),
  logout: () => request('/logout', { method: 'POST' }),
  me: () => request('/me'),
  cards: () => request('/cards'),
  card: (id) => request(`/cards/${id}`),
  reset: () => request('/reset', { method: 'POST' }),
  quizStart: (venue) => request('/quiz/start', { method: 'POST', body: { venue } }),
  quizAnswer: (questionId, optionId) =>
    request(`/quiz/${questionId}/answer`, { method: 'POST', body: { option_id: optionId } }),
}
