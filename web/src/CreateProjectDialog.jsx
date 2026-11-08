import { useRef, useState } from 'react'
import { postUploadProject } from './api'

export default function CreateProjectDialog({ onCreated, onCancel }) {
  const [name, setName] = useState('')
  const [reviewer, setReviewer] = useState(() => {
    try { return localStorage.getItem('last_reviewer') || '' } catch { return '' }
  })
  const [imageFiles, setImageFiles] = useState(null)
  const [annotationFile, setAnnotationFile] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const imageInputRef = useRef(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!imageFiles?.length) { setError('En az bir resim seç'); return }
    setSubmitting(true)
    setError(null)
    const fd = new FormData()
    fd.append('name', name)
    fd.append('reviewer', reviewer)
    for (const f of imageFiles) fd.append('images', f)
    if (annotationFile) fd.append('annotations', annotationFile)
    try {
      const project = await postUploadProject(fd)
      try { localStorage.setItem('last_reviewer', reviewer) } catch { /* storage blocked: just not remembered */ }
      onCreated(project)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="dialog-backdrop" onClick={submitting ? undefined : onCancel}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="create-title"
        onClick={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <h2 id="create-title">Yeni proje — görsel yükle</h2>
          <button className="icon" onClick={onCancel} disabled={submitting} aria-label="Kapat">✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="cp-name">Proje adı</label>
            <input id="cp-name" type="text" value={name}
              onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="form-field">
            <label htmlFor="cp-reviewer">İnceleyici</label>
            <input id="cp-reviewer" type="text" value={reviewer}
              onChange={(e) => setReviewer(e.target.value)} required />
          </div>
          <div className="form-field">
            <label>Resimler</label>
            <input ref={imageInputRef} type="file" multiple accept="image/*"
              onChange={(e) => setImageFiles(e.target.files)} required />
            {imageFiles?.length > 0 && (
              <span className="muted form-hint">{imageFiles.length} resim seçildi</span>
            )}
          </div>
          <div className="form-field">
            <label>
              annotations.json <span className="muted">(opsiyonel)</span>
            </label>
            <input type="file" accept=".json"
              onChange={(e) => setAnnotationFile(e.target.files[0] || null)} />
            {annotationFile && <span className="muted form-hint">{annotationFile.name}</span>}
          </div>

          {!annotationFile && (
            <p className="note">
              annotations.json olmadan proje boş oluşturulur — kategori listesi için dosyayı manuel düzenle.
            </p>
          )}

          {error && <p className="error">{error}</p>}

          <div className="dialog-actions">
            <button type="button" onClick={onCancel} disabled={submitting}>Vazgeç</button>
            <button type="submit" className="primary" disabled={submitting}>
              {submitting ? 'Yükleniyor...' : 'Proje oluştur'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
