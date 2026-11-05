import { Link, Navigate, NavLink, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { api } from './api'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from './auth'
import CardGuide from './components/CardGuide'
import RewardBar from './components/RewardBar'
import RewardUnlock from './components/RewardUnlock'
import ResultsModal from './components/ResultsModal'
import TimelineBar from './components/TimelineBar'
import Admin from './pages/Admin'
import CardDetail from './pages/CardDetail'
import Gallery from './pages/Gallery'
import Home from './pages/Home'
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
      .then((c) => setTo(c.player && (c.type === 'base' || c.type === 'special') ? `/players/${id}?card=${id}` : `/collection?card=${id}`))
      .catch(() => setTo('/collection'))
  }, [id])
  return to ? <Navigate to={to} replace /> : <p className="muted">Loading card…</p>
}

export default function App() {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const inAdmin = pathname.startsWith('/admin')
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  // Close the menu after navigating (Admin, Exit admin) or signing out.
  useEffect(() => setMenuOpen(false), [pathname, user])

  // Close the menu on a click outside it or Escape.
  useEffect(() => {
    if (!menuOpen) return
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target) && !e.target.closest('.menu-button')) setMenuOpen(false)
    }
    const onKey = (e) => e.key === 'Escape' && setMenuOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [menuOpen])

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
              <NavLink to="/" end>Home</NavLink>
              <NavLink to="/collection">Collection</NavLink>
              <NavLink to="/quiz">Quiz</NavLink>
              <NavLink to="/predict">Predictions</NavLink>
              <NavLink to="/trade">Trade</NavLink>
            </nav>
          )}
          {user && (
            <div className="topbar-user">
              <CardGuide />
              <button
                type="button"
                className="menu-button"
                aria-label="Menu"
                aria-expanded={menuOpen}
                aria-controls="user-menu"
                onClick={() => setMenuOpen((o) => !o)}
              >
                <span aria-hidden="true" />
                <span aria-hidden="true" />
                <span aria-hidden="true" />
              </button>
              {menuOpen && (
                <div className="user-menu" id="user-menu" ref={menuRef}>
                  <span className="user-menu-name">{user.username}</span>
                  {inAdmin ? (
                    <Link to="/" className="admin-link">Exit admin</Link>
                  ) : (
                    <Link to="/admin" className="admin-link">Admin</Link>
                  )}
                  <button className="link-button" onClick={logout}>
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="app">
      <RewardBar />
      <RewardUnlock />

      <main>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Home />
              </RequireAuth>
            }
          />
          <Route
            path="/collection"
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
            path="/cards/:id/info"
            element={
              <RequireAuth>
                <CardDetail />
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
