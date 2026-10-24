// All calls to the service go through this file.

async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // The service explains its own errors in `detail`; anything else means it is not reachable.
    throw new Error(body?.detail ?? `servis yanıt vermiyor (${res.status}), servis açık mı?`)
  }
  return res.json()
}

export const fetchPackage = () => request('/api/package')
export const fetchImage = (id) => request(`/api/images/${id}`)
export const imageFileUrl = (id) => `/api/images/${id}/file`

// Writes reviewed images to export/ as a YOLO-seg dataset; returns a summary.
export const postExport = () => request('/api/export', { method: 'POST' })

// decision: { ann_id, action: 'accept' | 'change' | 'delete', category_id? }
// Returns the updated image detail.
export const postReview = (id, decision) =>
  request(`/api/images/${id}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  })
