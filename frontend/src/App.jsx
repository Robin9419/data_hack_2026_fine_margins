import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Login from './pages/Login'
import Gallery from './pages/Gallery'
import CardDetail from './pages/CardDetail'
import PackOpening from './pages/PackOpening'
import Quiz from './pages/Quiz'
import RewardBar from './components/RewardBar'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="muted">Loading…</p>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const { user, logout } = useAuth()

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          Hockey Performance Cards
        </Link>
        {user && (
          <div className="topbar-user">
            <span>{user.username}</span>
            <button className="link-button" onClick={logout}>
              Sign out
            </button>
          </div>
        )}
      </header>

      <RewardBar />

      <main>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Gallery />
              </RequireAuth>
            }
          />
          <Route
            path="/pack"
            element={
              <RequireAuth>
                <PackOpening />
              </RequireAuth>
            }
          />
          <Route
            path="/quiz"
            element={
              <RequireAuth>
                <Quiz />
              </RequireAuth>
            }
          />
          <Route
            path="/cards/:id"
            element={
              <RequireAuth>
                <CardDetail />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
