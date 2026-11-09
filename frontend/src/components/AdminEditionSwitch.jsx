import { useSearchParams } from 'react-router-dom'

export const editionQuery = (edition) => edition === 'stadium' ? '?edition=stadium' : ''

export function withEdition(card, edition) {
  return card.kind === 'profile' || card.kind === 'performance'
    ? { ...card, edition }
    : card
}

export function useAdminEdition() {
  const [params, setParams] = useSearchParams()
  const edition = params.get('edition') === 'stadium' ? 'stadium' : 'standard'
  const setEdition = (value) => setParams((current) => {
    if (value === 'stadium') current.set('edition', value)
    else current.delete('edition')
    return current
  }, { replace: true })
  return [edition, setEdition]
}

export default function AdminEditionSwitch({ edition, onChange }) {
  return (
    <div className="seg" role="group" aria-label="Impact Special edition">
      {[['standard', 'Standard'], ['stadium', 'Stadium']].map(([value, label]) => (
        <button key={value} type="button" className={edition === value ? 'on' : ''}
          aria-pressed={edition === value} onClick={() => onChange(value)}>
          {label}
        </button>
      ))}
    </div>
  )
}
