import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchExportPreview, fetchImage, fetchPackage, postExport, postReview } from './api'
import ExportDialog from './ExportDialog'
import Toast from './Toast'
import ImageViewer from './ImageViewer'
import ObjectList from './ObjectList'
import SelectedPanel from './SelectedPanel'
import { DEFAULT_THRESHOLD, catchAllCategories, orderObjects } from './suspects'
import Toolbar from './Toolbar'
import { findNextPending } from './navigation'
import { availableCandidates } from './candidates'

// Keyboard shortcuts must not fire while typing in a form field.
const isFormField = (el) => ['INPUT', 'SELECT', 'TEXTAREA'].includes(el?.tagName)

export default function App() {
  const [pkg, setPkg] = useState(null)
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [offline, setOffline] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [exporting, setExporting] = useState(false)
  // export window: null when closed, else { summary, done, loading, error }
  const [exportDialog, setExportDialog] = useState(null)
  const [toast, setToast] = useState(null)  // { kind, text }
  const closeToast = useCallback(() => setToast(null), [])
  const [showCandidates, setShowCandidates] = useState(false)
  const [selectedCandidateId, setSelectedCandidateId] = useState(null)

  // One selection at a time: an object or a candidate.
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
    let stale = false  // ignore a slow answer for an image we already left
    fetchImage(imageId)
      .then((data) => { if (!stale) setDetail(data) })
      .catch((err) => setError(err.message))
    return () => { stale = true }
  }, [imageId, clearSelection])

  // category_id -> name, always taken from the package
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

  // Every decision is saved right away; the service answers with the updated image.
  const save = useCallback(async (decision) => {
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await postReview(current.image.id, decision)
      setDetail(updated)
      setPkg((p) => ({
        ...p,
        images: p.images.map((img) => (img.id === updated.image.id ? { ...img, status: updated.status } : img)),
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
    // skip decisions that would change nothing, so the log stays meaningful
    if (action === 'accept' && ['accepted', 'changed', 'added'].includes(selected.state)) return
    if (action === 'delete' && selected.state === 'deleted') return
    if (action === 'change' && categoryId === selected.category_id) return
    save({ ann_id: selected.id, action, category_id: categoryId ?? null })
  }, [selected, saving, save])

  // Adding a candidate selects the new object, so it can be checked right away.
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

  // The toolbar button only opens the window with a preview; the export itself
  // runs from the button inside the window.
  const openExport = async () => {
    setExportDialog({ loading: true })
    try {
      setExportDialog({ summary: await fetchExportPreview() })
    } catch (err) {
      setExportDialog({ error: err.message })
    }
  }

  const closeExport = useCallback(() => { if (!exporting) setExportDialog(null) }, [exporting])

  const runExport = async () => {
    setExporting(true)
    try {
      const result = await postExport()
      setExportDialog({ summary: result, done: true })
      setToast({ kind: 'success', text: `✓ Dışa aktarıldı: ${result.images} resim, ${result.objects} nesne → ${result.path}` })
    } catch (err) {
      setExportDialog((d) => ({ ...d, error: err.message }))
      setToast({ kind: 'error', text: `Dışa aktarılamadı: ${err.message}` })
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.altKey || e.metaKey) return
      // while the export window is open, only Esc works (closes it); Enter/Del must not
      // touch the object behind the window
      if (exportDialog) {
        if (e.key === 'Escape') closeExport()
        return
      }
      if (e.key === 'Escape') {
        // also from a form field: Esc leaves the class list and drops the selection
        e.target.blur?.()
        clearSelection()
        return
      }
      if (isFormField(e.target)) return
      if (e.key === 'Enter') decide('accept')
      else if (e.key === 'Delete') decide('delete')
      else if (e.key === 'n' || e.key === 'N') go(1)
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
        saving={saving} saveError={saveError} onExport={openExport} exporting={exporting} />
      {exportDialog && (
        <ExportDialog summary={exportDialog.summary} done={exportDialog.done} loading={exportDialog.loading}
          error={exportDialog.error} exporting={exporting} onExport={runExport} onClose={closeExport} />
      )}
      <Toast toast={toast} onClose={closeToast} />
      {current ? (
        <div className="workspace">
          <ImageViewer detail={current} categoryNames={categoryNames}
            selectedId={selectedId} onSelect={selectObject}
            candidates={showCandidates ? candidates : null}
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
