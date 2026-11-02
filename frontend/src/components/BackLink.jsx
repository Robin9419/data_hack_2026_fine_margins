import { Link, useNavigate } from 'react-router-dom'

// The one back button every page starts with; fixed block so the content below never jumps.
export default function BackLink({ to = '/collection', label = 'Back to collection', history = false }) {
  const navigate = useNavigate()
  const onClick = (e) => {
    if (history && window.history.state?.idx > 0) {
      e.preventDefault()
      navigate(-1)
    }
  }
  return (
    <div className="page-back">
      <Link to={to} className="back-link" aria-label={label} onClick={onClick}>Back</Link>
    </div>
  )
}
