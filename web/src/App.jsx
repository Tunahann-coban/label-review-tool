import { useEffect, useMemo, useState } from 'react'
import { fetchImage, fetchPackage } from './api'
import ImageViewer from './ImageViewer'

export default function App() {
  const [pkg, setPkg] = useState(null)
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [offline, setOffline] = useState(false)

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

  const total = pkg.images.length
  const go = (delta) => setIndex((i) => Math.min(total - 1, Math.max(0, i + delta)))
  const current = detail?.image.id === imageId ? detail : null

  return (
    <main className="app">
      <header className="toolbar">
        <button onClick={() => go(-1)} disabled={index === 0}>← Önceki</button>
        <span>{index + 1} / {total} · {pkg.images[index].file_name}</span>
        <button onClick={() => go(1)} disabled={index === total - 1}>Sonraki →</button>
      </header>
      {current ? (
        <>
          <ImageViewer detail={current} categoryNames={categoryNames} />
          <p>{current.objects.length} nesne, {current.candidates.length} aday</p>
        </>
      ) : (
        <p>Yükleniyor...</p>
      )}
    </main>
  )
}
