import { EDIT_LIST_LABEL, IMAGE_STATUS_LABELS, shortDate } from './states'

// The image's own state, big and on the left; the two marks as toggles on the right.
//   Tamamlandı: "I am finished with this photo here." Pressing it opens the next
//               unfinished photo.
//   Düzenlenecekler'e ekle: "this one still needs masks drawn elsewhere (Roboflow)."
//               Independent of the first: a photo can be both. Pressing it keeps the
//               photo open, so it can still be marked done.
// A pressed toggle stays clearly "on" (it is not greyed out); pressing it again undoes it.
export default function ImageStatusBar({ status, needsEdit, statusBy, statusAt, editBy, editAt,
  editors, reviewer, onToggleDone, onToggleEdit, saving }) {
  const done = status === 'reviewed'
  const doneWhen = shortDate(statusAt)
  const editWhen = shortDate(editAt)

  return (
    <div className={done ? 'status-bar is-done' : 'status-bar'}>
      <div className="status-now">
        <span className="status-icon" aria-hidden="true">{done ? '✓' : '•••'}</span>
        <div className="status-text">
          <div className="status-title">{done ? 'Tamamlandı' : 'Bekliyor'}</div>
          <span className="sr-only">{IMAGE_STATUS_LABELS[status]}</span>
          <div className="who muted">
            {done && statusBy && <>{statusBy}{doneWhen && ` · ${doneWhen}`}</>}
            {!done && <>henüz tamamlanmadı</>}
          </div>
          {needsEdit && (
            <span className="flag-chip">
              ⚑ {EDIT_LIST_LABEL}{editBy && ` · ${editBy}`}{editWhen && ` · ${editWhen}`}
            </span>
          )}
          {(editors?.length > 0 || reviewer) && (
            <div className="who muted">
              {editors?.length > 0 && <>düzenleyen: {editors.join(', ')}</>}
              {editors?.length > 0 && reviewer && ' · '}
              {reviewer && <>senin adın: {reviewer}</>}
            </div>
          )}
        </div>
      </div>

      <div className="status-actions">
        <button className={needsEdit ? 'mark mark-edit on' : 'mark mark-edit'} aria-pressed={needsEdit}
          onClick={onToggleEdit} disabled={saving}
          title={needsEdit ? 'Listeden çıkarmak için tekrar tıkla' : 'Elle maske eklenecek resimlere ekle'}>
          {needsEdit ? <>Düzenlenecekler&apos;de ⚑<span className="undo">geri al</span></>
            : <>Düzenlenecekler&apos;e ekle ⚑</>} <kbd>D</kbd>
        </button>
        <button className={done ? 'mark mark-done on' : 'mark mark-done primary'} aria-pressed={done}
          onClick={onToggleDone} disabled={saving}
          title={done ? 'Geri almak için tekrar tıkla' : 'Bu resmi bitirdim, sıradaki bekleyene geç'}>
          {done ? <>Tamamlandı ✓<span className="undo">geri al</span></> : <>Tamamlandı olarak işaretle ✓</>} <kbd>T</kbd>
        </button>
      </div>
    </div>
  )
}
