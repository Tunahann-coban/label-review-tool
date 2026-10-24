import { useEffect, useState } from 'react'
import { fetchHello } from './api'

export default function App() {
  const [message, setMessage] = useState('...')
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchHello()
      .then((data) => setMessage(data.message))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <main className="app">
      <h1>Label Review Tool</h1>
      {error ? <p className="error">Servise ulaşılamadı: {error}</p> : <p>Servis diyor ki: <b>{message}</b></p>}
    </main>
  )
}
