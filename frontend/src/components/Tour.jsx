import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../auth'

// First-time walkthrough: dims the page and spotlights one part of the app at a time with a short explanation.
// It starts on Home after a brand-new account has opened its starter pack (see markTourPending in auth.jsx) and can
// be replayed from the menu. Targets are found by their data-tour attribute; a step whose target is missing (e.g. on
// a narrow screen) is shown centered instead.

const STEPS = [
  {
    title: 'Welcome to Spengler Cup Cards',
    text: 'Your starter pack is in. Here is a 1-minute look at everything you can do to grow your collection during the tournament.',
  },
  {
    target: 'rewards',
    title: 'Points & rewards',
    text: 'Every card you own is worth points: base 5, specials 10, legends 25. Hover the markers to see the real rewards you unlock along the way.',
  },
  {
    target: 'activities',
    title: 'Your daily to-do list',
    text: 'Claim your free daily pack, follow a social channel or add match tickets for bonus packs. New activities appear each gameday.',
  },
  {
    target: 'highlights',
    title: 'Your best cards',
    text: 'Your rarest and newest cards show up here. Tap any card to flip it and see the stats and clips behind it.',
  },
  {
    target: 'nav-collection',
    title: 'Collection',
    text: 'Every card in the set, owned or still locked. Filter by club and see what you need to complete a team and unlock its legends.',
  },
  {
    target: 'nav-quiz',
    title: 'Quiz',
    text: '3 trivia questions per gameday about the latest games. Every right answer wins an Impact Special card.',
  },
  {
    target: 'nav-predict',
    title: 'Predictions',
    text: 'Call the winner, the first goal and a key stat before each game. Right calls earn you extra packs.',
  },
  {
    target: 'nav-trade',
    title: 'Trade',
    text: 'Got duplicates? Trade 3 spares for 1 card you do not have yet.',
  },
  {
    target: 'nav-duel',
    title: 'Shootout duel',
    text: 'Challenge a friend: pick players for the attack and the defence, then watch the play. Every player is good at different things, taken from how they really played. Every duel earns a pack, a win also a special card.',
  },
  {
    target: 'timeline',
    title: 'Tournament timeline',
    text: 'Follow the Spengler Cup day by day. New cards, quizzes and predictions open as the tournament moves on.',
  },
  {
    target: 'guide',
    title: 'Card guide',
    text: 'Not sure what a card means or how to get it? The guide explains every card type, award and stat in plain words.',
  },
  {
    target: 'menu',
    title: 'You are all set',
    text: 'You can replay this tour any time from the menu. Good luck completing your collection!',
  },
]

const PAD = 8 // space between the target and the spotlight edge
const GAP = 14 // space between the spotlight and the popover
const BLOCKERS = 'dialog[open], .results-overlay, .unlock, .spotlight, .pack-stage'

const pendingKey = (user) => `tour-pending:${user.username}`

// Called on sign-up of a new account: the tour starts once they are on Home.
export function markTourPending(username) {
  try {
    localStorage.setItem(`tour-pending:${username}`, '1')
  } catch {}
}

// Opens the tour from anywhere (the menu item).
export function startTour() {
  window.dispatchEvent(new Event('tour:start'))
}

const findTarget = (id) => {
  if (!id) return null
  // Several elements can share an id (e.g. hidden duplicates); pick the first visible one.
  for (const el of document.querySelectorAll(`[data-tour="${id}"]`)) {
    const r = el.getBoundingClientRect()
    if (r.width > 0 && r.height > 0) return el
  }
  return null
}

export default function Tour() {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const [step, setStep] = useState(null) // index into STEPS while the tour is open
  const [rect, setRect] = useState(null) // spotlight rect in viewport coordinates, null = centered step
  const [pos, setPos] = useState(null) // popover position
  const popRef = useRef(null)
  const nextRef = useRef(null)

  const close = useCallback(() => {
    setStep(null)
    if (user) {
      try {
        localStorage.removeItem(pendingKey(user))
      } catch {}
    }
  }, [user])

  // Start after sign-up, once on Home and no pack, unlock or results pop-up is in the way.
  useEffect(() => {
    if (!user || pathname !== '/' || step !== null) return
    let pending = false
    try {
      pending = localStorage.getItem(pendingKey(user)) === '1'
    } catch {}
    if (!pending) return
    const timer = setInterval(() => {
      if (document.querySelector(BLOCKERS) || !findTarget('activities')) return
      clearInterval(timer)
      setStep(0)
    }, 600)
    return () => clearInterval(timer)
  }, [user, pathname, step])

  // Replay from the menu.
  useEffect(() => {
    const onStart = () => setStep(0)
    window.addEventListener('tour:start', onStart)
    return () => window.removeEventListener('tour:start', onStart)
  }, [])

  // Signing out or leaving Home ends the tour.
  useEffect(() => {
    if (step !== null && (!user || pathname !== '/')) setStep(null)
  }, [user, pathname, step])

  // Scroll the target into view when the step changes.
  useEffect(() => {
    if (step === null) return
    const el = findTarget(STEPS[step].target)
    if (el) el.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    else window.scrollTo({ top: 0 })
  }, [step])

  // Keep the spotlight and popover glued to the target while it moves (scroll, resize, layout changes).
  useLayoutEffect(() => {
    if (step === null) return
    let frame
    const measure = () => {
      const el = findTarget(STEPS[step].target)
      const r = el?.getBoundingClientRect()
      const next = r ? { top: r.top - PAD, left: r.left - PAD, width: r.width + PAD * 2, height: r.height + PAD * 2 } : null
      setRect((prev) =>
        prev && next && ['top', 'left', 'width', 'height'].every((k) => Math.abs(prev[k] - next[k]) < 0.5) ? prev : next,
      )
      frame = requestAnimationFrame(measure)
    }
    measure()
    return () => cancelAnimationFrame(frame)
  }, [step])

  // Place the popover below the spotlight if it fits, otherwise above, clamped to the viewport.
  useLayoutEffect(() => {
    if (step === null || !popRef.current) return
    const pop = popRef.current.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight
    if (!rect) {
      setPos({ top: Math.max(16, (vh - pop.height) / 2), left: Math.max(16, (vw - pop.width) / 2), placement: 'center' })
      return
    }
    const below = rect.top + rect.height + GAP
    const above = rect.top - GAP - pop.height
    const fitsBelow = below + pop.height <= vh - 16
    const top = fitsBelow ? below : above >= 16 ? above : Math.max(16, vh - pop.height - 16)
    const left = Math.min(Math.max(16, rect.left + rect.width / 2 - pop.width / 2), vw - pop.width - 16)
    const arrow = Math.min(Math.max(20, rect.left + rect.width / 2 - left), pop.width - 20)
    setPos({ top, left, arrow, placement: fitsBelow ? 'below' : above >= 16 ? 'above' : 'center' })
  }, [rect, step])

  // Keyboard: arrows to move, Escape to skip. Focus the main button for keyboard users.
  useEffect(() => {
    if (step === null) return
    nextRef.current?.focus({ preventScroll: true })
    const onKey = (e) => {
      if (e.key === 'Escape') close()
      else if (e.key === 'ArrowRight') setStep((s) => (s < STEPS.length - 1 ? s + 1 : s))
      else if (e.key === 'ArrowLeft') setStep((s) => Math.max(0, s - 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [step, close])

  if (step === null) return null
  const s = STEPS[step]
  const last = step === STEPS.length - 1

  return createPortal(
    <div className="tour" role="presentation">
      {/* Clicks on the dimmed page are swallowed so the tour is not lost by accident. */}
      <div className="tour-blocker" />
      {rect ? (
        <div className="tour-hole" style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }} />
      ) : (
        <div className="tour-dim" />
      )}
      <div
        ref={popRef}
        className={`tour-pop tour-${pos?.placement ?? 'center'}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-title"
        aria-describedby="tour-text"
        style={{ top: pos?.top ?? -9999, left: pos?.left ?? -9999, '--arrow': `${pos?.arrow ?? 0}px` }}
      >
        <p className="tour-count">
          {step + 1} / {STEPS.length}
        </p>
        <h2 id="tour-title">{s.title}</h2>
        <p id="tour-text">{s.text}</p>
        <div className="tour-dots" aria-hidden="true">
          {STEPS.map((_, i) => (
            <span key={i} className={i === step ? 'on' : i < step ? 'done' : ''} />
          ))}
        </div>
        <div className="tour-actions">
          {!last && (
            <button type="button" className="link-button tour-skip" onClick={close}>
              Skip tour
            </button>
          )}
          {step > 0 && (
            <button type="button" className="tour-back" onClick={() => setStep(step - 1)}>
              Back
            </button>
          )}
          <button type="button" ref={nextRef} className="tour-next" onClick={() => (last ? close() : setStep(step + 1))}>
            {step === 0 ? 'Show me around' : last ? 'Start collecting' : 'Next'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
