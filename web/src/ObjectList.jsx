import { useEffect, useRef } from 'react'
import { objectColor } from './colors'

// Right-hand list of the image's objects. Clicking a row selects the object.
export default function ObjectList({ objects, categoryNames, selectedId, onSelect }) {
  const selectedRef = useRef(null)

  // When the selection comes from the image, bring the row into view.
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'nearest' })
  }, [selectedId])

  return (
    <aside className="object-list">
      <h2>Nesneler ({objects.length})</h2>
      <ul>
        {objects.map((obj, i) => {
          const selected = obj.id === selectedId
          return (
            <li key={obj.id} ref={selected ? selectedRef : null}
              className={selected ? 'selected' : ''}
              onClick={() => onSelect(selected ? null : obj.id)}>
              <span className="swatch" style={{ background: objectColor(i) }} />
              <span className="name">{categoryNames[obj.category_id] ?? `#${obj.category_id}`}</span>
              <span className="score">{obj.score != null ? obj.score.toFixed(2) : '–'}</span>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
