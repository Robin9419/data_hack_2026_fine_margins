import { useEffect, useState } from 'react'
import { api } from './api'

// One request per session; the full data of every card, including locked ones.
let promise = null

export function loadAllCards() {
  if (!promise) {
    promise = api
      .adminCards()
      .then(({ cards }) => new Map(cards.map((c) => [c.id, c])))
      .catch((err) => {
        promise = null
        throw err
      })
  }
  return promise
}

// The map of id → full card, or null while loading (or if it could not be loaded).
export function useAllCards() {
  const [map, setMap] = useState(null)
  useEffect(() => {
    let active = true
    loadAllCards()
      .then((m) => { if (active) setMap(m) })
      .catch(() => {})
    return () => { active = false }
  }, [])
  return map
}
