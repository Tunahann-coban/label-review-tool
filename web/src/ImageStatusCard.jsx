import { IMAGE_STATUS_LABELS, shortDate } from './states'

const WHO_LABELS = {
  reviewed: 'tamamlayan',
  needs_edit: 'işaretleyen',
  pending: 'bekliyora alan',
}

// What happens to the whole image: done ("Tamamla"), to edit elsewhere ("Düzenlenecek"),
// or back to pending. Decisions on its objects are always saved at once and are not
// touched by this; only the group the image sits in changes.
// Below the buttons: who put the image in this state, who changed its objects, and the
// name your own changes are saved under.
export default function ImageStatusCard({ status, statusBy, statusAt, editors, reviewer, onSet, saving }) {
  const when = shortDate(statusAt)
  return (
    <div className="status-card">
      <div className="status-card-head">
        <b>Bu resim</b>
        <span className={`status status-${status}`}>{IMAGE_STATUS_LABELS[status]}</span>
      </div>
      <div className="actions">
        <button className="primary" onClick={() => onSet('reviewed')} disabled={saving || status === 'reviewed'}>
          Tamamla ✓ <kbd>T</kbd>
        </button>
        <button onClick={() => onSet('needs_edit')} disabled={saving || status === 'needs_edit'}>
          Düzenlenecek ⚑ <kbd>D</kbd>
        </button>
      </div>
      <div className="who muted">
        {statusBy && <div>{WHO_LABELS[status]}: <b>{statusBy}</b>{when && ` · ${when}`}</div>}
        {editors?.length > 0 && <div>düzenleyen: {editors.join(', ')}</div>}
        {reviewer && <div>senin adın: {reviewer}</div>}
      </div>
      {status !== 'pending' && (
        <button className="ghost back-to-pending" onClick={() => onSet('pending')} disabled={saving}>
          Bekliyora al
        </button>
      )}
    </div>
  )
}
