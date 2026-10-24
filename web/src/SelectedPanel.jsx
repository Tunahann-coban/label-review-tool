import { STATE_LABELS } from './states'

// Actions for the selected object: accept, change class, delete.
// The panel keeps the same rows (and height) with or without a selection,
// so the list below never jumps when you select something.
export default function SelectedPanel({ object, reasons, categories, categoryNames, onDecide, saving }) {
  const deleted = object?.state === 'deleted'
  const name = object && (categoryNames[object.category_id] ?? `#${object.category_id}`)

  return (
    <div className={object ? 'selected-panel' : 'selected-panel empty'}>
      <div className="selected-title">
        <b>{object ? name : 'Seçili nesne yok'}</b>
        {object && (
          <span className="muted">
            skor {object.score != null ? object.score.toFixed(2) : '–'} · {STATE_LABELS[object.state]}
          </span>
        )}
      </div>
      <div className="info-line">
        {!object && <span className="muted">Listeden ya da resme tıklayarak seç.</span>}
        {reasons.length > 0 && (
          <><span className="badge">şüpheli</span> <span className="muted">{reasons.join(', ')}</span></>
        )}
      </div>
      <div className="info-line muted">
        {object?.state === 'changed' && <>ilk sınıf: {categoryNames[object.orig_category_id]}</>}
      </div>
      <div className="actions">
        <button className="accept" onClick={() => onDecide('accept')}
          disabled={!object || saving || ['accepted', 'changed'].includes(object.state)}>
          {deleted ? 'Geri al' : 'Onayla'} <kbd>Enter</kbd>
        </button>
        <button className="delete" onClick={() => onDecide('delete')} disabled={!object || saving || deleted}>
          Sil <kbd>Del</kbd>
        </button>
      </div>
      <label className="class-select">
        Sınıf:
        <select value={object?.category_id ?? ''} disabled={!object || saving} aria-label="Sınıf"
          onChange={(e) => {
            onDecide('change', Number(e.target.value))
            e.target.blur()  // give the keyboard shortcuts back
          }}>
          {!object && <option value="">–</option>}
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
    </div>
  )
}
