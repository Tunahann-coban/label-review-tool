import { MASK_VIEWS } from './maskView'
import { IMAGE_STATUS_LABELS } from './states'

// Top bar: navigation, mask view, image status, progress and save feedback.
// Three groups (navigation | file | progress and export); the buttons come first
// so they never move when the file name length changes.
export default function Toolbar({ images, index, onGo, canPrev, canNext, onNextPending, nextPendingIndex,
  saving, saveError, onExport, maskView, onMaskView, onGoHome }) {
  const total = images.length
  const reviewed = images.filter((img) => img.status === 'reviewed').length
  const needsEdit = images.filter((img) => img.status === 'needs_edit').length
  const current = images[index]
  const done = reviewed === total
  const summary = `${reviewed} / ${total} tamamlandı${needsEdit > 0 ? ` · ${needsEdit} düzenlenecek` : ''}`

  return (
    <header className="toolbar">
      <div className="toolbar-group">
        {onGoHome && <button className="ghost" onClick={onGoHome} title="Ana sayfa">← Projeler</button>}
        <button onClick={() => onGo(-1)} disabled={!canPrev}>← Önceki</button>
        <button onClick={() => onGo(1)} disabled={!canNext}>Sonraki → <kbd>N</kbd></button>
        <button onClick={onNextPending} disabled={nextPendingIndex == null}>Sıradaki bekleyen</button>
      </div>

      <div className="segmented" role="group" aria-label="Maske görünümü">
        <span className="muted">Maske <kbd>M</kbd></span>
        {MASK_VIEWS.map((v) => (
          <button key={v.id} aria-pressed={maskView === v.id} className={maskView === v.id ? 'on' : ''}
            onClick={() => onMaskView(v.id)}>{v.label}</button>
        ))}
      </div>

      <div className="toolbar-group toolbar-file">
        <span className={`status status-${current.status}`}>{IMAGE_STATUS_LABELS[current.status]}</span>
        <span className="position" title={current.file_name}>
          <span className="count">{index + 1} / {total}</span>{current.file_name}
        </span>
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
