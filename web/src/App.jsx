import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchImage, fetchPackage, postReview } from './api'
import ImageViewer from './ImageViewer'
import ObjectList from './ObjectList'
import SelectedPanel from './SelectedPanel'
import { DEFAULT_THRESHOLD, orderObjects, unknownCategoryIds } from './suspects'
import Toolbar from './Toolbar'
import { findNextPending } from './navigation'

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
    setSelectedId(null)
    setSaveError(null)
    let stale = false  // ignore a slow answer for an image we already left
    fetchImage(imageId)
      .then((data) => { if (!stale) setDetail(data) })
      .catch((err) => setError(err.message))
    return () => { stale = true }
  }, [imageId])

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

  const unknownIds = useMemo(() => unknownCategoryIds(pkg?.categories ?? []), [pkg])

  const current = detail?.image.id === imageId ? detail : null
  const selected = current?.objects.find((o) => o.id === selectedId) ?? null

  const orderedItems = useMemo(
    () => (current ? orderObjects(current.objects, threshold, unknownIds) : []),
    [current, threshold, unknownIds],
  )
  const selectedReasons = orderedItems.find((it) => it.obj.id === selectedId)?.reasons ?? []
  const nextPendingIndex = pkg ? findNextPending(pkg.images, index) : null

  // Every decision is saved right away; the service answers with the updated image.
  const decide = useCallback(async (action, categoryId) => {
    if (!selected || saving) return
    // skip decisions that would change nothing, so the log stays meaningful
    if (action === 'accept' && ['accepted', 'changed'].includes(selected.state)) return
    if (action === 'delete' && selected.state === 'deleted') return
    if (action === 'change' && categoryId === selected.category_id) return
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await postReview(current.image.id, {
        ann_id: selected.id, action, category_id: categoryId ?? null,
      })
      setDetail(updated)
      setPkg((p) => ({
        ...p,
        images: p.images.map((img) => (img.id === updated.image.id ? { ...img, status: updated.status } : img)),
      }))
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }, [current, selected, saving])

  useEffect(() => {
    const onKey = (e) => {
      if (isFormField(e.target) || e.ctrlKey || e.altKey || e.metaKey) return
      if (e.key === 'Enter') decide('accept')
      else if (e.key === 'Delete') decide('delete')
      else if (e.key === 'n' || e.key === 'N') go(1)
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [decide, go])

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
        saving={saving} saveError={saveError} />
      {current ? (
        <div className="workspace">
          <ImageViewer detail={current} categoryNames={categoryNames}
            selectedId={selectedId} onSelect={setSelectedId} />
          <aside className="sidebar">
            <SelectedPanel object={selected} reasons={selectedReasons} categories={pkg.categories}
              categoryNames={categoryNames} onDecide={decide} saving={saving} />
            <ObjectList items={orderedItems} categoryNames={categoryNames}
              selectedId={selectedId} onSelect={setSelectedId}
              threshold={threshold} onThreshold={setThreshold} />
          </aside>
        </div>
      ) : (
        <p>Yükleniyor...</p>
      )}
    </main>
  )
}
