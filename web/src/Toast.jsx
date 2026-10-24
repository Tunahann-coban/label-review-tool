import { useEffect } from 'react'

// Short notification in the bottom-right corner; closes itself after a few seconds.
// toast: { kind: 'success' | 'error', text } or null
export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(onClose, toast.kind === 'error' ? 8000 : 5000)
    return () => clearTimeout(timer)
  }, [toast, onClose])

  // the live region stays mounted so screen readers announce new messages
  return (
    <div className="toast-area" role="status" aria-live="polite">
      {toast && (
        <div className={`toast ${toast.kind}`}>
          <span>{toast.text}</span>
          <button className="icon" onClick={onClose} aria-label="Bildirimi kapat">✕</button>
        </div>
      )}
    </div>
  )
}
