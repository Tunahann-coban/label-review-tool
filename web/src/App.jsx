import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchCOCOExportPreview, fetchExportPreview, fetchImage, fetchPackage,
  postCOCOExport, postExport, postReview,
} from './api'
import ExportDialog from './ExportDialog'
import Toast from './Toast'
import ImageViewer from './ImageViewer'
import ObjectList from './ObjectList'
import SelectedPanel from './SelectedPanel'
import { DEFAULT_THRESHOLD, catchAllCategories, orderObjects } from './suspects'
import Toolbar from './Toolbar'
import { findNextPending } from './navigation'
import { availableCandidates } from './candidates'
import { nextMaskView } from './maskView'

// Keyboard shortcuts must not fire while typing in a form field.
const isFormField = (el) => ['INPUT', 'SELECT', 'TEXTAREA'].includes(el?.tagName)

export default function App({ onGoHome }) {
  const [pkg, setPkg] = useState(null)
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [offline, setOffline] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [exportDialog, setExportDialog] = useState(false)
  const [toast, setToast] = useState(null)
  const closeToast = useCallback(() => setToast(null), [])
  const [showCandidates, setShowCandidates] = useState(false)
  const [maskView, setMaskView] = useState('fill')
  const [selectedCandidateId, setSelectedCandidateId] = useState(null)

  const selectObject = useCallback((id) => { setSelectedId(id); setSelectedCandidateId(null) }, [])
  const selectCandidate = useCallback((id) => { setSelectedCandidateId(id); setSelectedId(null) }, [])
  const clearSelection = useCallback(() => { setSelectedId(null); setSelectedCandidateId(null) }, [])

  // Retry until the service is up, so the page can be opened first
  useEffect(() => {
    let timer
    const load = () =>
      fetchPackage()
        .then((data) => { setPkg(data); setOffline(false) })
        .catch(() => { setOffline(true); timer = setTimeout(load, 2000) })
    load()
    return () => clearTimeout(timer)
  }, [])

  const imageId = pkg?.images[index]?.id

  useEffect(() => {
    if (imageId == null) return
    clearSelection()
    setSaveError(null)
    let stale = false
    fetchImage(imageId)
      .then((data) => { if (!stale) setDetail(data) })
      .catch((err) => setError(err.message))
    return () => { stale = true }
  }, [imageId, clearSelection])

  const categoryNames = useMemo(
    () => Object.fromEntries((pkg?.categories ?? []).map((c) => [c.id, c.name])),
    [pkg],
  )

  const total = pkg?.images.length ?? 0
  const go = useCallback(
    (delta) => setIndex((i) => Math.min(total - 1, Math.max(0, i + delta))),
    [total],
  )

  const catchAll = useMemo(() => catchAllCategories(pkg?.categories ?? []), [pkg])

  const current = detail?.image.id === imageId ? detail : null
  const selected = current?.objects.find((o) => o.id === selectedId) ?? null

  const orderedItems = useMemo(
    () => (current ? orderObjects(current.objects, threshold, catchAll) : []),
    [current, threshold, catchAll],
  )
  const selectedReasons = orderedItems.find((it) => it.obj.id === selectedId)?.reasons ?? []
  const nextPendingIndex = pkg ? findNextPending(pkg.images, index) : null

  const candidates = useMemo(() => (current ? availableCandidates(current) : []), [current])
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId) ?? null

  const save = useCallback(async (decision) => {
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await postReview(current.image.id, decision)
      setDetail(updated)
      setPkg((p) => ({
        ...p,
        images: p.images.map((img) =>
          img.id === updated.image.id ? { ...img, status: updated.status } : img),
      }))
      return updated
    } catch (err) {
      setSaveError(err.message)
      return null
    } finally {
      setSaving(false)
    }
  }, [current])

  const decide = useCallback((action, categoryId) => {
    if (!selected || saving) return
    if (action === 'accept' && ['accepted', 'changed', 'added'].includes(selected.state)) return
    if (action === 'delete' && selected.state === 'deleted') return
    if (action === 'change' && categoryId === selected.category_id) return
    save({ ann_id: selected.id, action, category_id: categoryId ?? null })
  }, [selected, saving, save])

  const addCandidate = useCallback(async (categoryId) => {
    if (!selectedCandidate || saving) return
    const candidateId = selectedCandidate.id
    const updated = await save({ action: 'add', candidate_id: candidateId, category_id: categoryId })
    const added = updated?.objects.find((o) => o.from_candidate === candidateId && o.state === 'added')
    if (added) selectObject(added.id)
  }, [selectedCandidate, saving, save, selectObject])

  const toggleCandidates = () => {
    setShowCandidates((v) => !v)
    setSelectedCandidateId(null)
  }

  // Export: dialog manages its own state; App just opens it and handles the toast
  const openExport = useCallback(() => setExportDialog(true), [])
  const closeExport = useCallback(() => setExportDialog(false), [])

  const fetchPreviewForFormat = useCallback((format) => {
    return format === 'yolo' ? fetchExportPreview() : fetchCOCOExportPreview()
  }, [])

  const runExportForFormat = useCallback((format) => {
    return format === 'yolo' ? postExport() : postCOCOExport()
  }, [])

  const handleExportDone = useCallback((result, format) => {
    const count = format === 'yolo'
      ? `${result.images} resim, ${result.objects} nesne`
      : `${result.images} resim, ${result.annotations} nesne`
    setToast({ kind: 'success', text: `✓ Dışa aktarıldı: ${count} → ${result.path}` })
  }, [])

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.altKey || e.metaKey) return
      if (exportDialog) {
        if (e.key === 'Escape') closeExport()
        return
      }
      if (e.key === 'Escape') {
        e.target.blur?.()
        clearSelection()
        return
      }
      if (isFormField(e.target)) return
      if (e.key === 'Enter') decide('accept')
      else if (e.key === 'Delete') decide('delete')
      else if (e.key === 'n' || e.key === 'N') go(1)
      else if (e.key === 'm' || e.key === 'M') setMaskView(nextMaskView)
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decide, go, clearSelection, exportDialog, closeExport])

  if (error) return <main className="app"><p className="error">Hata: {error}</p></main>
  if (offline) {
    return (
      <main className="app">
        <p className="error">Servise ulaşılamıyor. Servisi başlattın mı?</p>
        <code>.venv\Scripts\python server\server.py --package sample_package --reviewer tunahan</code>
        <p>Servis açılınca sayfa kendiliğinden yüklenecek.</p>
      </main>
    )
  }
  if (!pkg) return <main className="app">Yükleniyor...</main>

  return (
    <main className="app">
      <Toolbar images={pkg.images} index={index} onGo={go}
        nextPendingIndex={nextPendingIndex} onNextPending={() => setIndex(nextPendingIndex)}
        saving={saving} saveError={saveError} onExport={openExport}
        maskView={maskView} onMaskView={setMaskView} onGoHome={onGoHome} />
      {exportDialog && (
        <ExportDialog
          onFetchPreview={fetchPreviewForFormat}
          onRunExport={runExportForFormat}
          onDone={handleExportDone}
          onClose={closeExport} />
      )}
      <Toast toast={toast} onClose={closeToast} />
      {current ? (
        <div className="workspace">
          <ImageViewer detail={current} categoryNames={categoryNames}
            selectedId={selectedId} onSelect={selectObject}
            candidates={showCandidates ? candidates : null} view={maskView}
            selectedCandidateId={selectedCandidateId} onSelectCandidate={selectCandidate} />
          <aside className="sidebar">
            <SelectedPanel object={selected} reasons={selectedReasons} candidate={selectedCandidate}
              categories={pkg.categories} categoryNames={categoryNames}
              onDecide={decide} onAddCandidate={addCandidate} onCancel={clearSelection} saving={saving} />
            <ObjectList items={orderedItems} categoryNames={categoryNames}
              selectedId={selectedId} onSelect={selectObject}
              threshold={threshold} onThreshold={setThreshold}
              candidateCount={candidates.length} showCandidates={showCandidates}
              onToggleCandidates={toggleCandidates} />
          </aside>
        </div>
      ) : (
        <p>Yükleniyor...</p>
      )}
    </main>
  )
}
