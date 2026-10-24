import { useEffect, useRef } from 'react'
import { objectColor } from './colors'
import { STATE_ICONS, STATE_LABELS } from './states'

// Right-hand list of the image's objects, suspects on top.
// items: [{ obj, colorIndex, reasons }] already ordered (see suspects.js).
export default function ObjectList({ items, categoryNames, selectedId, onSelect, threshold, onThreshold,
  candidateCount, showCandidates, onToggleCandidates }) {
  const selectedRef = useRef(null)

  // When the selection comes from the image, bring the row into view.
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'nearest' })
  }, [selectedId])

  const liveCount = items.filter((it) => it.obj.state !== 'deleted').length
  const suspectCount = items.filter((it) => it.reasons.length > 0).length

  return (
    <div className="object-list">
      <div className="list-header">
        <h2>
          Nesneler ({liveCount})
          {suspectCount > 0 && <span className="muted"> · {suspectCount} şüpheli</span>}
        </h2>
        <label className="threshold">
          <span>Şüpheli eşiği</span>
          <input type="range" min="0" max="1" step="0.05" value={threshold} aria-label="Şüpheli eşiği"
            onChange={(e) => onThreshold(Number(e.target.value))}
            onPointerUp={(e) => e.currentTarget.blur()} />
          <output>{threshold.toFixed(2)}</output>
        </label>
        <button className={showCandidates ? 'candidate-toggle on' : 'candidate-toggle'}
          onClick={onToggleCandidates} aria-pressed={showCandidates}>
          {showCandidates ? 'Adayları gizle' : 'Adayları göster'} ({candidateCount})
        </button>
      </div>
      <ul>
        {items.map(({ obj, colorIndex, reasons }) => {
          const selected = obj.id === selectedId
          const classes = [selected && 'selected', `state-${obj.state}`].filter(Boolean).join(' ')
          return (
            <li key={obj.id} ref={selected ? selectedRef : null} className={classes}
              onClick={() => onSelect(selected ? null : obj.id)}>
              <span className="swatch" style={{ background: objectColor(colorIndex) }} />
              <span className="name">{categoryNames[obj.category_id] ?? `#${obj.category_id}`}</span>
              {reasons.length > 0 && <span className="badge" title={reasons.join(', ')}>şüpheli</span>}
              <span className="state-icon" title={STATE_LABELS[obj.state]}>{STATE_ICONS[obj.state]}</span>
              <span className="score">{obj.score != null ? obj.score.toFixed(2) : '–'}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
