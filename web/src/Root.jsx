import { useCallback, useState } from 'react'
import App from './App'
import HomePage from './HomePage'

export default function Root() {
  const [page, setPage] = useState('home')
  const [activeProjectId, setActiveProjectId] = useState(null)

  const goToReview = useCallback((projectId) => {
    setActiveProjectId(projectId)
    setPage('review')
  }, [])

  const goHome = useCallback(() => setPage('home'), [])

  if (page === 'review') {
    // key forces a full remount when the project changes, so App's fetchPackage runs fresh
    return <App key={activeProjectId} onGoHome={goHome} />
  }
  return <HomePage onSelectProject={goToReview} />
}
