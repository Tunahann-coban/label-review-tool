import { useCallback, useEffect, useRef, useState } from 'react'

const SET_NAMES = { train: 'eğitim', val: 'doğrulama', test: 'test' }

// Train / val / test by storage unit (server/splits.py): whole units per set.
function SplitTable({ splits }) {
  return (
    <table className="split-table">
      <thead><tr><th>küme</th><th>ünite</th><th>resim</th><th>nesne</th></tr></thead>
      <tbody>
        {Object.entries(SET_NAMES).map(([key, label]) => (
          <tr key={key} className={splits[key].images === 0 ? 'muted' : ''}>
            <td>{label}</td><td>{splits[key].units}</td><td>{splits[key].images}</td><td>{splits[key].objects}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// Images that are not "tamamlandı" stay out of the YOLO and COCO exports.
function NotDoneNote({ summary, done }) {
  if (!(summary.pending_images > 0)) return null
  const marked = summary.needs_edit_images ?? 0
  return (
    <p className="note">
      {summary.pending_images} resim henüz tamamlanmadı{marked > 0 && <> ({marked} tanesi düzenlenecek)</>},{' '}
      {done ? 'aktarılmadı' : 'aktarılmayacak'}.
    </p>
  )
}

// ExportDialog manages its own loading/done/exporting state.
// Props: onFetchPreview(format), onRunExport(format), onDone(result, format), onClose
export default function ExportDialog({ onFetchPreview, onRunExport, onDone, onClose }) {
  const exportButton = useRef(null)
  const [format, setFormat] = useState('yolo')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)

  const loadPreview = useCallback(async (fmt) => {
    setLoading(true)
    setSummary(null)
    setError(null)
    setDone(false)
    try {
      setSummary(await onFetchPreview(fmt))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [onFetchPreview])

  // load preview on mount and whenever format changes
  useEffect(() => { loadPreview(format) }, [format, loadPreview])

  useEffect(() => {
    if (summary && !done) exportButton.current?.focus()
  }, [summary, done])

  const handleFormatChange = (fmt) => {
    if (fmt !== format) setFormat(fmt)
  }

  const handleExport = async () => {
    setExporting(true)
    setError(null)
    try {
      const result = await onRunExport(format)
      setSummary(result)
      setDone(true)
      onDone?.(result, format)
    } catch (err) {
      setError(err.message)
    } finally {
      setExporting(false)
    }
  }

  const handleClose = () => { if (!exporting) onClose() }

  const empty = summary?.images === 0
  const formatLabel = { yolo: 'YOLO-seg', coco: 'COCO JSON', edit: 'düzenlenecekler' }[format]

  return (
    <div className="dialog-backdrop" onClick={handleClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="export-title"
        onClick={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <h2 id="export-title">{done ? 'Dışa aktarıldı' : `Dışa aktar (${formatLabel})`}</h2>
          <button className="icon" onClick={handleClose} aria-label="Kapat">✕</button>
        </div>

        {!done && (
          <div className="segmented" role="group" aria-label="Format">
            <span className="muted">Format</span>
            <button aria-pressed={format === 'yolo'} className={format === 'yolo' ? 'on' : ''}
              onClick={() => handleFormatChange('yolo')}>YOLO-seg</button>
            <button aria-pressed={format === 'coco'} className={format === 'coco' ? 'on' : ''}
              onClick={() => handleFormatChange('coco')}>COCO JSON</button>
            <button aria-pressed={format === 'edit'} className={format === 'edit' ? 'on' : ''}
              onClick={() => handleFormatChange('edit')}>Düzenlenecekler</button>
          </div>
        )}

        {loading && <p className="muted">Hazırlanıyor...</p>}
        {error && <p className="error">{error}</p>}

        {summary && (
          <>
            {format === 'yolo' ? (
              <>
                <p>
                  {done ? 'Yazıldı' : 'Yazılacak'}: <b>{summary.images}</b> resim,{' '}
                  <b>{summary.objects}</b> nesne
                  {summary.empty_images > 0 && <> · {summary.empty_images} resim nesnesiz</>}
                </p>
                <p className="muted path">{summary.path}</p>
                <NotDoneNote summary={summary} done={done} />
                {summary.untouched_objects > 0 && (
                  <p className="note warn">
                    {summary.untouched_objects} nesneye hiç dokunulmadı; hattın verdiği hâliyle{' '}
                    {done ? 'aktarıldı' : 'aktarılacak'}.
                  </p>
                )}
                <table>
                  <thead><tr><th>no</th><th>sınıf</th><th>nesne</th></tr></thead>
                  <tbody>
                    {summary.per_class?.map((c) => (
                      <tr key={c.index} className={c.count === 0 ? 'muted' : ''}>
                        <td>{c.index}</td><td>{c.name}</td><td>{c.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : format === 'coco' ? (
              <>
                <p>
                  {done ? 'Yazıldı' : 'Yazılacak'}: <b>{summary.images}</b> resim,{' '}
                  <b>{summary.annotations}</b> nesne
                </p>
                <p className="muted path">{summary.path}</p>
                <NotDoneNote summary={summary} done={done} />
              </>
            ) : (
              <>
                <p>
                  {done ? 'Yazıldı' : 'Yazılacak'}: <b>{summary.images}</b> resim,{' '}
                  <b>{summary.objects}</b> nesne
                  {summary.empty_images > 0 && <> · {summary.empty_images} resim nesnesiz</>}
                </p>
                <p className="muted path">{summary.path}</p>
                <p className="note">
                  Düzenlenecek diye işaretlediğin resimler ve şimdiki maskeleri, tek klasörde COCO
                  dosyasıyla (<code>_annotations.coco.json</code>). Roboflow&apos;a bu klasörü yükle.
                </p>
              </>
            )}
            {format !== 'edit' && summary.splits && <SplitTable splits={summary.splits} />}
            {summary.warnings?.length > 0 && (
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
          <button onClick={handleClose}>{done ? 'Kapat' : 'Vazgeç'} <kbd>Esc</kbd></button>
          {!done && (
            <button ref={exportButton} className="primary" onClick={handleExport}
              disabled={!summary || empty || exporting || loading}>
              {exporting ? 'Aktarılıyor...' : 'Dışa aktar'}
            </button>
          )}
        </div>
        {empty && (
          <p className="muted">
            {format === 'edit' ? 'Düzenlenecek olarak işaretlenmiş resim yok.' : 'Aktarılacak tamamlanmış resim yok.'}
          </p>
        )}
      </div>
    </div>
  )
}
