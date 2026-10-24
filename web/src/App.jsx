import { useEffect, useState } from 'react'
import { fetchImage, fetchPackage, imageFileUrl } from './api'

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
    fetchImage(imageId).then(setDetail).catch((err) => setError(err.message))
  }, [imageId])

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

  return (
    <main className="app">
      <header className="toolbar">
        <button onClick={() => go(-1)} disabled={index === 0}>← Önceki</button>
        <span>{index + 1} / {total} · {pkg.images[index].file_name}</span>
        <button onClick={() => go(1)} disabled={index === total - 1}>Sonraki →</button>
      </header>
      <section className="viewer">
        {imageId != null && <img src={imageFileUrl(imageId)} alt={pkg.images[index].file_name} />}
      </section>
      {detail && <p>{detail.objects.length} nesne, {detail.candidates.length} aday</p>}
    </main>
  )
}
