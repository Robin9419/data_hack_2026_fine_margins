import { Link, Navigate, NavLink, Route, Routes, useParams } from 'react-router-dom'
import { api } from './api'
import { useEffect, useState } from 'react'
import { useAuth } from './auth'
import RewardBar from './components/RewardBar'
import ResultsModal from './components/ResultsModal'
import TimelineBar from './components/TimelineBar'
import Admin from './pages/Admin'
import CardDetail from './pages/CardDetail'
import Gallery from './pages/Gallery'
import Login from './pages/Login'
import PackOpening from './pages/PackOpening'
import PlayerProfile from './pages/PlayerProfile'
import Predictions from './pages/Predictions'
import Quiz from './pages/Quiz'
import Trade from './pages/Trade'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="muted">Loading…</p>
  return user ? children : <Navigate to="/login" replace />
}

// Old card page: a card now opens as a spotlight on its player's profile, or on the collection for cards without one.
function CardRedirect() {
  const { id } = useParams()
  const [to, setTo] = useState(null)
  useEffect(() => {
    api
      .card(id)
      .then((c) => setTo(c.player && (c.type === 'base' || c.type === 'special') ? `/players/${id}?card=${id}` : `/?card=${id}`))
      .catch(() => setTo('/'))
  }, [id])
  return to ? <Navigate to={to} replace /> : <p className="muted">Loading card…</p>
}

export default function App() {
  const { user, logout } = useAuth()

  return (
    <>
      <header className="topbar">
        <div className="topbar-in">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true" />
            Spengler Cup Cards
          </Link>
          {user && (
            <nav className="appnav" aria-label="Main">
              <NavLink to="/" end>Collection</NavLink>
              <NavLink to="/quiz">Quiz</NavLink>
              <NavLink to="/predict">Predictions</NavLink>
              <NavLink to="/trade">Trade</NavLink>
            </nav>
          )}
          {user && (
            <div className="topbar-user">
              <span>{user.username}</span>
              <NavLink to="/admin">Admin</NavLink>
              <button className="link-button" onClick={logout}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="app">
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
            path="/predict"
            element={
              <RequireAuth>
                <Predictions />
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
            path="/trade"
            element={
              <RequireAuth>
                <Trade />
              </RequireAuth>
            }
          />
          <Route
            path="/cards/:id"
            element={
              <RequireAuth>
                <CardRedirect />
              </RequireAuth>
            }
          />
          <Route
            path="/players/:cardId"
            element={
              <RequireAuth>
                <PlayerProfile />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/cards/:id"
            element={
              <RequireAuth>
                <CardDetail preview />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth>
                <Admin />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {user && <TimelineBar />}
      {user && <ResultsModal />}
      </div>
    </>
  )
}
