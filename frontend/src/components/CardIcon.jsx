const ICONS = {
  star: <path fill="currentColor" d="M12 2l2.9 6.9 7.1.6-5.4 4.7 1.6 7L12 17.5 5.8 21.2l1.6-7L2 9.5l7.1-.6z" />,
  target: (
    <g fill="none" stroke="currentColor" strokeWidth="2.2">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
    </g>
  ),
  nodes: (
    <g fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="5" cy="6" r="2.5" fill="currentColor" />
      <circle cx="19" cy="6" r="2.5" fill="currentColor" />
      <circle cx="12" cy="18" r="2.5" fill="currentColor" />
      <path d="M7 7l3.5 9M17 7l-3.5 9M7.5 6h9" />
    </g>
  ),
  burst: <path fill="currentColor" d="M12 1l2.2 6.1L20 4l-3.1 5.8L23 12l-6.1 2.2L20 20l-5.8-3.1L12 23l-2.2-6.1L4 20l3.1-5.8L1 12l6.1-2.2L4 4l5.8 3.1z" />,
  flag: <path fill="currentColor" d="M5 2h2v20H5zM8 3h11l-2.5 4L19 11H8z" />,
  bolt: <path fill="currentColor" d="M13 2L4 14h7l-1 8 10-13h-7z" />,
  shield: <path fill="currentColor" d="M12 2l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V5z" />,
  flame: <path fill="currentColor" d="M12 2s5 4.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 1-3.5S9 11 10.5 11C10.5 7 12 2 12 2z" />,
  // The Spengler Cup: a glass ball held by four hockey sticks on a round base.
  trophy: (
    <g fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="6.2" r="5" fill="currentColor" stroke="none" />
      <path d="M5 20.4L10 12.6Q7.8 11.6 7 8.8M19 20.4L14 12.6Q16.2 11.6 17 8.8" />
      <path d="M9.4 20.4l1.6-9.6M14.6 20.4L13 10.8" />
      <path d="M9.2 12.9h5.6" strokeWidth="2" />
      <ellipse cx="12" cy="21.6" rx="8.6" ry="1.3" fill="currentColor" stroke="none" />
    </g>
  ),
  gift: (
    <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="8" width="18" height="5" rx="1" />
      <path d="M5 13v8h14v-8M12 8v13M12 8C10 4 6 4 7 7c.5 1.2 3 1 5 1zM12 8c2-4 6-4 5-1-.5 1.2-3 1-5 1z" />
    </g>
  ),
}

export default function CardIcon({ name }) {
  return (
    <svg className="card-icon" viewBox="0 0 24 24" aria-hidden="true">
      {ICONS[name] ?? ICONS.star}
    </svg>
  )
}
