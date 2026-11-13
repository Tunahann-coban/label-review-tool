import { MASK_VIEWS } from './maskView'

// Top bar: only what concerns the whole project, so it stays short: the way back to the
// projects page, how masks are drawn, overall progress and the export. Moving between
// photos is in the bar above the photo (ImageNav).
export default function Toolbar({ images, saving, saveError, onExport, maskView, onMaskView, onGoHome }) {
  const total = images.length
  const reviewed = images.filter((img) => img.status === 'reviewed').length
  const needsEdit = images.filter((img) => img.needs_edit).length
  const done = reviewed === total
  const summary = `${reviewed} / ${total} tamamlandı${needsEdit > 0 ? ` · ${needsEdit} düzenlenecek` : ''}`

  return (
    <header className="toolbar">
      <div className="toolbar-group">
        {onGoHome && <button className="primary" onClick={onGoHome} title="Proje listesine dön">← Projeler</button>}
      </div>

      <div className="segmented" role="group" aria-label="Maske görünümü">
        <span className="muted">Maske <kbd>M</kbd></span>
        {MASK_VIEWS.map((v) => (
          <button key={v.id} aria-pressed={maskView === v.id} className={maskView === v.id ? 'on' : ''}
            onClick={() => onMaskView(v.id)}>{v.label}</button>
        ))}
      </div>

      <div className="toolbar-group toolbar-end">
        {saving && <span className="muted">kaydediliyor...</span>}
        {saveError && <span className="error">Kaydedilemedi: {saveError}</span>}
        <div className="progress" title={summary}>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${(100 * reviewed) / total}%` }} />
          </div>
          <span>{done ? 'hepsi tamamlandı ✓' : summary}</span>
        </div>
        {/* disabled until something is done or marked: nothing to export before that */}
        <button className="primary" onClick={onExport} disabled={reviewed === 0 && needsEdit === 0}>Dışa aktar</button>
      </div>
    </header>
  )
}
