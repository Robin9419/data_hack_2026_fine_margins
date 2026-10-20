import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api'
import { useAuth } from './auth'

const TournamentContext = createContext(null)

// Where the signed-in user is on the simulated 2025 Spengler Cup timeline (before, a gameday, after), today's games
// with their predictions and the results so far. The timeline bar, the gallery and the predictions page share it.
// justPlayed holds the games the last move along the timeline played, for the results pop-up.
export function TournamentProvider({ children }) {
  const { user, setProgress } = useAuth()
  const [tournament, setTournament] = useState(null)
  const [justPlayed, setJustPlayed] = useState([])
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(() => api.tournament().then(setTournament).catch(() => {}), [])

  useEffect(() => {
    if (user) refresh()
    else setTournament(null)
  }, [user, refresh])

  const setStage = async (stage) => {
    if (busy || stage === tournament?.stage) return
    setBusy(true)
    try {
      const data = await api.setStage(stage)
      setTournament(data.tournament)
      setProgress(data.progress)
      setJustPlayed(data.just_played)
    } finally {
      setBusy(false)
    }
  }

  const predict = async (gameId, questionId, optionId) => setTournament(await api.predict(gameId, questionId, optionId))
  const dismissResults = useCallback(() => setJustPlayed([]), [])

  return (
    <TournamentContext.Provider value={{ tournament, busy, refresh, setStage, predict, justPlayed, dismissResults }}>
      {children}
    </TournamentContext.Provider>
  )
}

export const useTournament = () => useContext(TournamentContext)
