import { GROUPS } from './navigation'

// Moving between photos, right above the photo it is about.
//   Önceki / Sonraki  the neighbouring photo, in the group chosen in the Resimler tab
//                     (the bar says so when it is not "Tümü")
//   Bekleyene geç     jumps to the next photo that is not finished yet
export default function ImageNav({ fileName, position, count, group, onGroup, canPrev, canNext,
  onPrev, onNext, canJump, onJump }) {
  const groupLabel = GROUPS.find((g) => g.id === group)?.label
  return (
    <div className="image-nav">
      <div className="nav-step">
        <button onClick={onPrev} disabled={!canPrev} title="Önceki resim">
          ← Önceki <kbd>P</kbd>
        </button>
        <button onClick={onNext} disabled={!canNext} title="Sonraki resim">
          Sonraki → <kbd>N</kbd>
        </button>
      </div>

      <div className="nav-title" title={fileName}>
        <span className="nav-file">{fileName}</span>
        <span className="nav-count muted">
          {position != null ? `${position} / ${count}` : `– / ${count}`}
          {group !== 'all' && <> · {groupLabel} grubunda <button className="link" onClick={() => onGroup('all')}>tümüne dön</button></>}
        </span>
      </div>

      <button className="nav-jump" onClick={onJump} disabled={!canJump}
        title="Henüz tamamlanmamış sıradaki resme geç">
        Bekleyene geç ⏭ <kbd>B</kbd>
      </button>
    </div>
  )
}
