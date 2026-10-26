import { MASK_VIEWS } from './maskView'

// Top bar: navigation, mask view, image status, progress and save feedback.
// Buttons come first so they never move when the file name length changes.
export default function Toolbar({ images, index, onGo, onNextPending, nextPendingIndex, saving, saveError,
  onExport, maskView, onMaskView, onGoHome }) {
  const total = images.length
  const reviewed = images.filter((img) => img.status === 'reviewed').length
  const current = images[index]
  const done = reviewed === total

  return (
    <header className="toolbar">
      {onGoHome && <button onClick={onGoHome} title="Ana sayfa">← Projeler</button>}
      <button onClick={() => onGo(-1)} disabled={index === 0}>← Önceki</button>
      <button onClick={() => onGo(1)} disabled={index === total - 1}>Sonraki → <kbd>N</kbd></button>
      <button onClick={onNextPending} disabled={nextPendingIndex == null}>Sıradaki bekleyen</button>
      <div className="segmented" role="group" aria-label="Maske görünümü">
        <span className="muted">Maske <kbd>M</kbd></span>
        {MASK_VIEWS.map((v) => (
          <button key={v.id} aria-pressed={maskView === v.id} className={maskView === v.id ? 'on' : ''}
            onClick={() => onMaskView(v.id)}>{v.label}</button>
        ))}
      </div>
      <span className={`status status-${current.status}`}>
        {current.status === 'reviewed' ? 'incelendi' : 'bekliyor'}
      </span>
      <span className="position" title={current.file_name}>{index + 1} / {total} · {current.file_name}</span>

      <div className="progress" title={`${reviewed} / ${total} incelendi`}>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${(100 * reviewed) / total}%` }} />
        </div>
        <span>{done ? 'hepsi incelendi ✓' : `${reviewed} / ${total} incelendi`}</span>
      </div>
      {/* disabled until at least one image is reviewed: nothing to export before that */}
      <button onClick={onExport} disabled={reviewed === 0}>Dışa aktar</button>

      {saving && <span className="muted">kaydediliyor...</span>}
      {saveError && <span className="error">Kaydedilemedi: {saveError}</span>}
    </header>
  )
}
