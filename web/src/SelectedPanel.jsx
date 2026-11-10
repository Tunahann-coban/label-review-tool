import { STATE_LABELS } from './states'

// Nothing to accept on these: already decided, or added by the reviewer.
const ALREADY_DECIDED = ['accepted', 'changed', 'added']
// What the greyed-out accept button says instead, so it reads as done, not as broken.
const DONE_LABELS = { accepted: 'Onaylandı ✓', changed: 'Değiştirildi ✓', added: 'Eklendi ✓' }

// Actions for the selected object (accept, change class, delete), or for a selected
// candidate (pick a class to add it). The panel keeps the same rows (and height)
// in every mode, so the list below never jumps.
export default function SelectedPanel({ object, reasons, candidate, categories, categoryNames,
  onDecide, onAddCandidate, onCancel, saving }) {
  if (candidate) {
    return (
      <div className="selected-panel candidate-mode">
        <div className="selected-title">
          <b>Aday #{candidate.id}</b>
          {candidate.area != null && <span className="muted">alan {Math.round(candidate.area)} px²</span>}
        </div>
        <div className="info-line muted">Sınıf seçince nesne olarak eklenir.</div>
        <div className="info-line" />
        <div className="actions">
          <button onClick={onCancel} disabled={saving}>Vazgeç <kbd>Esc</kbd></button>
        </div>
        <label className="class-select">
          Sınıf:
          {/* no autoFocus: an arrow key on a focused select would add with the wrong class */}
          <select value="" disabled={saving} aria-label="Eklenecek sınıf"
            onChange={(e) => {
              onAddCandidate(Number(e.target.value))
              e.target.blur()  // give the keyboard shortcuts back
            }}>
            <option value="" disabled>sınıf seç…</option>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
      </div>
    )
  }

  const deleted = object?.state === 'deleted'
  const decided = Boolean(object) && ALREADY_DECIDED.includes(object.state)
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
        {object?.from_candidate != null && <span className="muted">aday #{object.from_candidate} üzerinden eklendi</span>}
      </div>
      <div className="info-line muted">
        {object?.state === 'changed' && <>ilk sınıf: {categoryNames[object.orig_category_id]}</>}
      </div>
      <div className="actions">
        <button className={decided ? 'accept decided' : 'accept'} onClick={() => onDecide('accept')}
          disabled={!object || saving || ALREADY_DECIDED.includes(object.state)}>
          {decided ? DONE_LABELS[object.state] : <>{deleted ? 'Geri al' : 'Onayla'} <kbd>Enter</kbd></>}
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
