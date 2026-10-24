import { STATE_LABELS } from './states'

// Actions for the selected object: accept, change class, delete.
export default function SelectedPanel({ object, categories, categoryNames, onDecide, saving }) {
  if (!object) {
    return <div className="selected-panel empty">Bir nesne seç: listeden ya da resme tıklayarak.</div>
  }

  const deleted = object.state === 'deleted'
  const name = categoryNames[object.category_id] ?? `#${object.category_id}`

  return (
    <div className="selected-panel">
      <div className="selected-title">
        <b>{name}</b>
        <span className="muted">
          skor {object.score != null ? object.score.toFixed(2) : '–'} · {STATE_LABELS[object.state]}
        </span>
      </div>
      {object.state === 'changed' && (
        <div className="muted">ilk sınıf: {categoryNames[object.orig_category_id]}</div>
      )}
      <div className="actions">
        <button className="accept" onClick={() => onDecide('accept')}
          disabled={saving || ['accepted', 'changed'].includes(object.state)}>
          {deleted ? 'Geri al' : 'Onayla'} <kbd>Enter</kbd>
        </button>
        <button className="delete" onClick={() => onDecide('delete')} disabled={saving || deleted}>
          Sil <kbd>Del</kbd>
        </button>
      </div>
      <label className="class-select">
        Sınıf:
        <select value={object.category_id} disabled={saving}
          onChange={(e) => {
            onDecide('change', Number(e.target.value))
            e.target.blur()  // give the keyboard shortcuts back
          }}>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
    </div>
  )
}
