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

// Where it goes. Every export is a NEW folder named with the date and time, so an earlier
// export is never overwritten or emptied.
function Destination({ summary, done }) {
  return (
    <>
      <p className="muted path">{done ? 'Yazıldı: ' : 'Yeni klasör oluşturulacak: '}{summary.path}</p>
      {!done && <p className="muted">Önceki dışa aktarmalar silinmez, üzerine yazılmaz. Gün ve saat klasör adına eklenir.</p>}
    </>
  )
}

// Images that are not in this YOLO / COCO export, with the reason, so nothing is left
// out unseen: not finished yet, or on the edit list (their labels are incomplete, they have
// an export of their own).
function LeftOut({ summary, done, onOpenImage }) {
  const list = summary.left_out ?? []
  if (list.length === 0) return null
  return (
    <div className="left-out">
      <p>
        <b>{done ? 'Dışarıda kalan' : 'Dışarıda kalacak'} resimler ({list.length})</b>
        <span className="muted"> · tıklayınca o resme gidersin</span>
      </p>
      <ul className="left-out-list">
        {list.map((item) => (
          <li key={item.id}>
            <button className="link" onClick={() => onOpenImage?.(item.file_name)}>{item.file_name}</button>
            <span className="reasons">
              {item.unfinished && <span className="status status-pending">tamamlanmadı</span>}
              {item.needs_edit && <span className="flag-chip">⚑ düzenlenecekler listesinde</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
// ExportDialog manages its own loading/done/exporting state.
// Props: onFetchPreview(format), onRunExport(format), onDone(result, format), onOpenImage(fileName), onClose
export default function ExportDialog({ onFetchPreview, onRunExport, onDone, onOpenImage, onClose }) {
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
                <Destination summary={summary} done={done} />
                <LeftOut summary={summary} done={done} onOpenImage={onOpenImage} />
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
                <Destination summary={summary} done={done} />
                <LeftOut summary={summary} done={done} onOpenImage={onOpenImage} />
              </>
            ) : (
              <>
                <p>
                  {done ? 'Yazıldı' : 'Yazılacak'}: <b>{summary.images}</b> resim,{' '}
                  <b>{summary.objects}</b> nesne
                  {summary.empty_images > 0 && <> · {summary.empty_images} resim nesnesiz</>}
                </p>
                <Destination summary={summary} done={done} />
                <p className="note">
                  Düzenlenecekler listesine eklediğin resimler (bitmiş olsun olmasın) ve şimdiki maskeleri, tek klasörde COCO
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
