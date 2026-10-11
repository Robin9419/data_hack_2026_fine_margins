import { createContext, useContext, useEffect, useState } from 'react'
import { api, clearToken, getToken, setToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Reward-bar state: points, reward milestones and collection counts. Pages update it with setProgress.
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))

  // Restore the session on page load.
  useEffect(() => {
    if (!getToken()) return
    api
      .me()
      .then((data) => {
        setUser(data.user)
        setProgress(data.progress)
      })
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const login = async (username) => {
    const data = await api.login(username)
    setToken(data.token)
    setUser(data.user)
    api.me().then((me) => setProgress(me.progress))
    return data
  }

  const logout = async () => {
    await api.logout().catch(() => {})
    clearToken()
    setUser(null)
    setProgress(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, progress, setProgress }}>{children}</AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
