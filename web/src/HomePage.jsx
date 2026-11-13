import { useCallback, useEffect, useState } from 'react'
import { activateProject, deleteProject, fetchProjects, postProject } from './api'
import CreateProjectDialog from './CreateProjectDialog'

export default function HomePage({ onSelectProject }) {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [offline, setOffline] = useState(false)
  const [activating, setActivating] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  useEffect(() => {
    let timer
    const load = () =>
      fetchProjects()
        .then((data) => { setProjects(data); setLoading(false); setOffline(false) })
        .catch(() => { setOffline(true); timer = setTimeout(load, 2000) })
    load()
    return () => clearTimeout(timer)
  }, [])

  const handleOpen = useCallback(async (projectId) => {
    setActivating(projectId)
    try {
      await activateProject(projectId)
      onSelectProject(projectId)
    } catch (err) {
      alert(`Proje açılamadı: ${err.message}`)
      setActivating(null)
    }
  }, [onSelectProject])

  const handleDelete = async (projectId) => {
    if (!confirm('Proje listeden kaldırılsın mı? Dosyalar silinmez.')) return
    try {
      await deleteProject(projectId)
      setProjects((ps) => ps.filter((p) => p.id !== projectId))
    } catch (err) {
      alert(`Silinemedi: ${err.message}`)
    }
  }

  const handleAdd = (project) => {
    setProjects((ps) => [...ps, project])
    setShowAddForm(false)
  }

  const handleCreated = async (project) => {
    setShowCreateDialog(false)
    setActivating(project.id)
    try {
      await activateProject(project.id)
      onSelectProject(project.id)
    } catch (err) {
      alert(`Proje oluşturuldu ama açılamadı: ${err.message}`)
      setProjects((ps) => [...ps, project])
      setActivating(null)
    }
  }

  if (offline) {
    return (
      <main className="home">
        <div className="home-offline">
          <p className="error">Servise ulaşılamıyor. Servisi başlattın mı?</p>
          <code>.venv\Scripts\python server\server.py</code>
          <p className="muted">Servis açılınca sayfa kendiliğinden yüklenecek.</p>
        </div>
      </main>
    )
  }

  return (
    <main className="home">
      <header className="home-topbar">
        <span className="home-brand">Label Review Tool</span>
      </header>

      <div className="home-content">
        <div className="home-header">
          <div className="home-title">
            <h1 className="home-heading">Projeler</h1>
            <p className="muted">Bir paketi aç, etiketleri incele, YOLO ya da COCO olarak dışa aktar.</p>
          </div>
          <div className="home-actions">
            <button
              onClick={() => { setShowAddForm((v) => !v); setShowCreateDialog(false) }}
              className={showAddForm ? 'on' : ''}>
              + Klasör ekle
            </button>
            <button
              className={`primary${showCreateDialog ? ' on' : ''}`}
              onClick={() => { setShowCreateDialog((v) => !v); setShowAddForm(false) }}>
              + Görsel yükle
            </button>
          </div>
        </div>

        {showAddForm && (
          <AddProjectForm onAdd={handleAdd} onCancel={() => setShowAddForm(false)} />
        )}

        {loading ? (
          <p className="muted home-loading">Yükleniyor...</p>
        ) : projects.length === 0 ? (
          <div className="home-empty">
            <EmptySticker />
            <p>Henüz proje yok. Bir klasör ekle ya da görsel yükle.</p>
            <button className="primary" onClick={() => setShowAddForm(true)}>+ Klasör ekle</button>
          </div>
        ) : (
          <ul className="project-list">
            {projects.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                activating={activating === p.id}
                onOpen={() => handleOpen(p.id)}
                onDelete={() => handleDelete(p.id)}
              />
            ))}
          </ul>
        )}
      </div>

      {showCreateDialog && (
        <CreateProjectDialog onCreated={handleCreated} onCancel={() => setShowCreateDialog(false)} />
      )}
    </main>
  )
}

function ProjectCard({ project, activating, onOpen, onDelete }) {
  const { reviewed, total } = project.progress
  const pct = total ? Math.round((reviewed / total) * 100) : 0

  return (
    <li className={[
      'project-card',
      project.is_active ? 'active-project' : '',
      !project.valid ? 'invalid-project' : '',
    ].filter(Boolean).join(' ')}>
      <div className="project-card-info">
        <div className="project-card-name">
          {project.name}
          {project.is_active && <span className="badge badge-info">aktif</span>}
          {!project.valid && <span className="badge badge-warn">hatalı</span>}
        </div>
        <div className="project-card-path" title={project.path}>{project.path}</div>
        <div className="project-card-meta">İnceleyici: {project.reviewer}</div>
        {!project.valid && project.error && (
          <div className="project-card-error">{project.error}</div>
        )}
      </div>

      <div className="project-card-progress">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="project-card-stat">
          {reviewed} / {total} tamamlandı
          {project.progress.needs_edit > 0 && <> · {project.progress.needs_edit} düzenlenecek</>}
        </span>
      </div>

      <div className="project-card-actions">
        <button className="primary" onClick={onOpen}
          disabled={activating || !project.valid}>
          {activating ? '...' : 'Aç'}
        </button>
        <button className="icon" onClick={onDelete} title="Listeden kaldır"
          disabled={activating}>✕</button>
      </div>
    </li>
  )
}

// Sticker for the empty state (DESIGN.md section 6): flat brand colors, white die-cut
// outline, slight tilt. A cardboard box with a detection box and label tag.
function EmptySticker() {
  const box = 'M30 52 L80 32 L130 52 L130 104 L80 124 L30 104 Z'
  return (
    <svg className="sticker" width="160" height="136" viewBox="0 0 160 136" aria-hidden="true">
      <g transform="rotate(-6 80 68)">
        <g fill="#fff" stroke="#fff" strokeWidth="10" strokeLinejoin="round">
          <path d={box} />
          <rect x="30" y="8" width="100" height="26" rx="13" />
        </g>
        <path d="M30 52 L80 72 L80 124 L30 104 Z" fill="#d2a26b" />
        <path d="M80 72 L130 52 L130 104 L80 124 Z" fill="#c48f58" />
        <path d="M30 52 L80 32 L130 52 L80 72 Z" fill="#efccaa" />
        <path d="M66 42 L90 52 L80 56 L56 46 Z" fill="#d8531e" />
        <rect x="38" y="62" width="84" height="50" rx="4" fill="none" stroke="#1f3146" strokeWidth="3"
          strokeDasharray="7 5" />
        <rect x="30" y="8" width="100" height="26" rx="13" fill="#1f3146" />
        <text x="80" y="25.5" textAnchor="middle" fontSize="11" fontWeight="600" fill="#fff"
          fontFamily="Inter, system-ui, sans-serif">box · 0.92</text>
      </g>
    </svg>
  )
}

function AddProjectForm({ onAdd, onCancel }) {
  const [path, setPath] = useState('')
  const [name, setName] = useState('')
  const [reviewer, setReviewer] = useState(() => {
    try { return localStorage.getItem('last_reviewer') || '' } catch { return '' }
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handlePathChange = (v) => {
    setPath(v)
    if (!name) {
      const stem = v.replace(/\\/g, '/').split('/').filter(Boolean).pop() || ''
      if (stem) setName(stem)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const project = await postProject({ name, path, reviewer })
      try { localStorage.setItem('last_reviewer', reviewer) } catch { /* storage blocked: just not remembered */ }
      onAdd(project)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <form className="add-project-form" onSubmit={handleSubmit}>
      <label>
        Klasör yolu
        <input type="text" value={path} onChange={(e) => handlePathChange(e.target.value)}
          placeholder="C:\kullanici\...\paket-klasoru" required />
      </label>
      <label>
        Proje adı
        <input type="text" value={name} onChange={(e) => setName(e.target.value)}
          placeholder="Paket adı" required />
      </label>
      <label>
        İnceleyici
        <input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value)}
          placeholder="isim" required />
      </label>
      {error && <span className="error form-error">{error}</span>}
      <div className="form-actions">
        <button type="button" onClick={onCancel}>Vazgeç</button>
        <button type="submit" className="primary" disabled={saving}>
          {saving ? 'Ekleniyor...' : 'Ekle'}
        </button>
      </div>
    </form>
  )
}

