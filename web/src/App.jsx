import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchCOCOExportPreview, fetchEditExportPreview, fetchExportPreview, fetchImage, fetchPackage,
  postCOCOExport, postEditExport, postExport, postMarks, postReview,
} from './api'
import ExportDialog from './ExportDialog'
import Toast from './Toast'
import ImageList from './ImageList'
import ImageNav from './ImageNav'
import ImageStatusBar from './ImageStatusBar'
import ImageViewer from './ImageViewer'
import ObjectList from './ObjectList'
import SelectedPanel from './SelectedPanel'
import { DEFAULT_THRESHOLD, catchAllCategories, orderObjects } from './suspects'
import Toolbar from './Toolbar'
import { findNextPending, inGroup, moveInGroup } from './navigation'
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
  const [group, setGroup] = useState('all')      // which "folder" Previous / Next walk through
  const [sideTab, setSideTab] = useState('objects')  // 'objects' | 'images'

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

  // Previous / Next stay inside the chosen group
  const go = useCallback(
    (delta) => setIndex((i) => (pkg ? moveInGroup(pkg.images, group, i, delta) : i)),
    [pkg, group],
  )
  const canPrev = pkg ? moveInGroup(pkg.images, group, index, -1) !== index : false
  const canNext = pkg ? moveInGroup(pkg.images, group, index, 1) !== index : false

  const catchAll = useMemo(() => catchAllCategories(pkg?.categories ?? []), [pkg])

  const current = detail?.image.id === imageId ? detail : null
  const selected = current?.objects.find((o) => o.id === selectedId) ?? null

  const orderedItems = useMemo(
    () => (current ? orderObjects(current.objects, threshold, catchAll) : []),
    [current, threshold, catchAll],
  )
  const selectedReasons = orderedItems.find((it) => it.obj.id === selectedId)?.reasons ?? []
  const nextPendingIndex = pkg ? findNextPending(pkg.images, index) : null
  const jumpToPending = useCallback(() => { if (nextPendingIndex != null) setIndex(nextPendingIndex) }, [nextPendingIndex])

  // where this photo stands inside the group Previous / Next walk through
  const inside = useMemo(
    () => (pkg ? pkg.images.map((_, i) => i).filter((i) => inGroup(pkg.images[i], group)) : []),
    [pkg, group])
  const position = inside.includes(index) ? inside.indexOf(index) + 1 : null

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

  // The two marks on the whole image: finished ("Tamamlandı") and on the edit list
  // ("Düzenlenecekler'e ekle"). Pressing "finished" on an unfinished image opens the next
  // unfinished one, so the queue keeps moving. The edit-list toggle keeps the image
  // open, so it can still be marked finished.
  const setMarks = useCallback(async (marks) => {
    if (!current || saving) return
    const finishing = current.status === 'pending' && marks.status === 'reviewed'
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await postMarks(current.image.id, marks)
      setDetail(updated)
      const images = pkg.images.map((img) =>
        img.id === updated.image.id
          ? { ...img, status: updated.status, needs_edit: updated.needs_edit, status_by: updated.status_by }
          : img)
      setPkg((p) => ({ ...p, images }))
      // say where the photo went: marking something is easy to miss otherwise
      const name = updated.image.file_name
      const said = []
      if (marks.status === 'reviewed') said.push(`✓ ${name} tamamlananlara eklendi`)
      if (marks.status === 'pending') said.push(`${name} bekleyenlere geri alındı`)
      if (marks.needs_edit === true) said.push(`⚑ ${name} düzenlenecekler listesine eklendi`)
      if (marks.needs_edit === false) said.push(`${name} düzenlenecekler listesinden çıkarıldı`)
      if (said.length) setToast({ kind: 'success', text: said.join(' · ') })
      if (finishing) {
        const next = findNextPending(images, index)
        if (next != null) setIndex(next)
      }
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }, [current, saving, pkg, index])

  const toggleDone = useCallback(
    () => current && setMarks({ status: current.status === 'reviewed' ? 'pending' : 'reviewed' }),
    [current, setMarks])
  const toggleEdit = useCallback(
    () => current && setMarks({ needs_edit: !current.needs_edit }),
    [current, setMarks])

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
  const openImageByName = useCallback((fileName) => {
    const i = pkg?.images.findIndex((img) => img.file_name === fileName) ?? -1
    if (i < 0) return
    setGroup('all')
    setIndex(i)
    setExportDialog(false)
  }, [pkg])
  const closeExport = useCallback(() => setExportDialog(false), [])

  const fetchPreviewForFormat = useCallback((format) => {
    if (format === 'edit') return fetchEditExportPreview()
    return format === 'yolo' ? fetchExportPreview() : fetchCOCOExportPreview()
  }, [])

  const runExportForFormat = useCallback((format) => {
    if (format === 'edit') return postEditExport()
    return format === 'yolo' ? postExport() : postCOCOExport()
  }, [])

  const handleExportDone = useCallback((result, format) => {
    const count = format === 'coco'
      ? `${result.images} resim, ${result.annotations} nesne`
      : `${result.images} resim, ${result.objects} nesne`
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
      else if (e.key === 'p' || e.key === 'P') go(-1)
      else if (e.key === 'b' || e.key === 'B') jumpToPending()
      else if (e.key === 'm' || e.key === 'M') setMaskView(nextMaskView)
      else if (e.key === 't' || e.key === 'T') toggleDone()
      else if (e.key === 'd' || e.key === 'D') toggleEdit()
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decide, go, jumpToPending, toggleDone, toggleEdit, clearSelection, exportDialog, closeExport])

  if (error) return <main className="app app-message"><p className="error">Hata: {error}</p></main>
  if (offline) {
    return (
      <main className="app app-message">
        <p className="error">Servise ulaşılamıyor. Servisi başlattın mı?</p>
        <code>.venv\Scripts\python server\server.py --package sample_package --reviewer tunahan</code>
        <p>Servis açılınca sayfa kendiliğinden yüklenecek.</p>
      </main>
    )
  }
  if (!pkg) return <main className="app app-message">Yükleniyor...</main>

  return (
    <main className="app">
      <Toolbar images={pkg.images}
        saving={saving} saveError={saveError} onExport={openExport}
        maskView={maskView} onMaskView={setMaskView} onGoHome={onGoHome} />
      {exportDialog && (
        <ExportDialog
          onFetchPreview={fetchPreviewForFormat}
          onRunExport={runExportForFormat}
          onDone={handleExportDone}
          onOpenImage={openImageByName}
          onClose={closeExport} />
      )}
      <Toast toast={toast} onClose={closeToast} />
      {current ? (
        <div className="workspace">
          <div className="stage-col">
            <ImageViewer detail={current} categoryNames={categoryNames}
              selectedId={selectedId} onSelect={selectObject}
              candidates={showCandidates ? candidates : null} view={maskView}
              selectedCandidateId={selectedCandidateId} onSelectCandidate={selectCandidate}
              header={(
                <ImageNav fileName={current.image.file_name} position={position}
                  count={inside.length} group={group} onGroup={setGroup}
                  canPrev={canPrev} canNext={canNext} onPrev={() => go(-1)} onNext={() => go(1)}
                  canJump={nextPendingIndex != null} onJump={jumpToPending} />
              )} />
            <ImageStatusBar status={current.status} needsEdit={current.needs_edit}
              statusBy={current.status_by} statusAt={current.status_at}
              editBy={current.edit_by} editAt={current.edit_at}
              editors={current.editors} reviewer={pkg.reviewer}
              onToggleDone={toggleDone} onToggleEdit={toggleEdit} saving={saving} />
          </div>
          <aside className="sidebar">
            <SelectedPanel object={selected} reasons={selectedReasons} candidate={selectedCandidate}
              categories={pkg.categories} categoryNames={categoryNames}
              onDecide={decide} onAddCandidate={addCandidate} onCancel={clearSelection} saving={saving} />
            <div className="segmented panel-tabs" role="group" aria-label="Liste">
              <button aria-pressed={sideTab === 'objects'} className={sideTab === 'objects' ? 'on' : ''}
                onClick={() => setSideTab('objects')}>Nesneler</button>
              <button aria-pressed={sideTab === 'images'} className={sideTab === 'images' ? 'on' : ''}
                onClick={() => setSideTab('images')}>Resimler ({pkg.images.length})</button>
            </div>
            {sideTab === 'objects' ? (
              <ObjectList items={orderedItems} categoryNames={categoryNames}
                selectedId={selectedId} onSelect={selectObject}
                threshold={threshold} onThreshold={setThreshold}
                candidateCount={candidates.length} showCandidates={showCandidates}
                onToggleCandidates={toggleCandidates} />
            ) : (
              <ImageList images={pkg.images} index={index} group={group} onGroup={setGroup}
                onPick={setIndex} />
            )}
          </aside>
        </div>
      ) : (
        <p className="app-message muted">Yükleniyor...</p>
      )}
    </main>
  )
}
