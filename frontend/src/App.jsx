import { Link, Navigate, NavLink, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import RewardBar from './components/RewardBar'
import ResultsModal from './components/ResultsModal'
import TimelineBar from './components/TimelineBar'
import Admin from './pages/Admin'
import CardDetail from './pages/CardDetail'
import Gallery from './pages/Gallery'
import Login from './pages/Login'
import PackOpening from './pages/PackOpening'
import Predictions from './pages/Predictions'
import Quiz from './pages/Quiz'
import Trade from './pages/Trade'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="muted">Loading…</p>
  return user ? children : <Navigate to="/login" replace />
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
              <Link to="/admin">Admin</Link>
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
                <CardDetail />
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
