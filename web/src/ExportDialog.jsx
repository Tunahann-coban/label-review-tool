import { useEffect, useRef } from 'react'

// Export window: shows what will be written (preview) with an "export" button,
// then what was written. summary = preview or result from the service.
export default function ExportDialog({ summary, done, loading, exporting, error, onExport, onClose }) {
  const exportButton = useRef(null)

  // keyboard users land on the main action
  useEffect(() => {
    if (summary && !done) exportButton.current?.focus()
  }, [summary, done])

  const empty = summary && summary.images === 0

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="export-title"
        onClick={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <h2 id="export-title">{done ? 'Dışa aktarıldı' : 'Dışa aktar (YOLO-seg)'}</h2>
          <button className="icon" onClick={onClose} aria-label="Kapat">✕</button>
        </div>

        {loading && <p className="muted">Hazırlanıyor...</p>}
        {error && <p className="error">{error}</p>}

        {summary && (
          <>
            <p>
              {done ? 'Yazıldı' : 'Yazılacak'}: <b>{summary.images}</b> resim, <b>{summary.objects}</b> nesne
              {summary.empty_images > 0 && <> · {summary.empty_images} resim nesnesiz</>}
            </p>
            <p className="muted path">{summary.path}</p>

            {summary.pending_images > 0 && (
              <p className="note">
                {summary.pending_images} resim henüz incelenmedi, {done ? 'aktarılmadı' : 'aktarılmayacak'}.
              </p>
            )}
            {summary.untouched_objects > 0 && (
              <p className="note warn">
                {summary.untouched_objects} nesneye hiç dokunulmadı (onay, düzeltme yok);
                hattın verdiği hâliyle {done ? 'aktarıldı' : 'aktarılacak'}.
              </p>
            )}

            <table>
              <thead><tr><th>no</th><th>sınıf</th><th>nesne</th></tr></thead>
              <tbody>
                {summary.per_class.map((c) => (
                  <tr key={c.index} className={c.count === 0 ? 'muted' : ''}>
                    <td>{c.index}</td><td>{c.name}</td><td>{c.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {summary.warnings.length > 0 && (
              <>
                <p><b>Uyarılar ({summary.warnings.length})</b></p>
                <ul className="warnings">
                  {summary.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </>
            )}
          </>
        )}

        <div className="dialog-actions">
          <button onClick={onClose}>{done ? 'Kapat' : 'Vazgeç'} <kbd>Esc</kbd></button>
          {!done && (
            <button ref={exportButton} className="primary" onClick={onExport}
              disabled={!summary || empty || exporting}>
              {exporting ? 'Aktarılıyor...' : 'Dışa aktar'}
            </button>
          )}
        </div>
        {empty && <p className="muted">Aktarılacak incelenmiş resim yok.</p>}
      </div>
    </div>
  )
}
