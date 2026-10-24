import { useEffect, useRef } from 'react'
import { objectColor } from './colors'
import { STATE_ICONS, STATE_LABELS } from './states'

// Right-hand list of the image's objects. Clicking a row selects the object.
export default function ObjectList({ objects, categoryNames, selectedId, onSelect }) {
  const selectedRef = useRef(null)

  // When the selection comes from the image, bring the row into view.
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'nearest' })
  }, [selectedId])

  return (
    <div className="object-list">
      <h2>Nesneler ({objects.filter((o) => o.state !== 'deleted').length})</h2>
      <ul>
        {objects.map((obj, i) => {
          const selected = obj.id === selectedId
          const classes = [selected && 'selected', `state-${obj.state}`].filter(Boolean).join(' ')
          return (
            <li key={obj.id} ref={selected ? selectedRef : null} className={classes}
              onClick={() => onSelect(selected ? null : obj.id)}>
              <span className="swatch" style={{ background: objectColor(i) }} />
              <span className="name">{categoryNames[obj.category_id] ?? `#${obj.category_id}`}</span>
              <span className="state-icon" title={STATE_LABELS[obj.state]}>{STATE_ICONS[obj.state]}</span>
              <span className="score">{obj.score != null ? obj.score.toFixed(2) : '–'}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
