// All calls to the service go through this file.

async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // The service explains its own errors in `detail`; anything else means it is not reachable.
    throw new Error(body?.detail ?? `servis yanıt vermiyor (${res.status}), servis açık mı?`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const fetchPackage = () => request('/api/package')
export const fetchImage = (id) => request(`/api/images/${id}`)
export const imageFileUrl = (id) => `/api/images/${id}/file`

// What an export would write; nothing is written.
export const fetchExportPreview = () => request('/api/export/preview')

// Writes reviewed images to export/ as a YOLO-seg dataset; returns a summary.
export const postExport = () => request('/api/export', { method: 'POST' })

// decision: { action: 'accept' | 'change' | 'delete', ann_id, category_id? }
//        or { action: 'add', candidate_id, category_id }
// Returns the updated image detail.
export const postReview = (id, decision) =>
  request(`/api/images/${id}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  })

// COCO export
export const fetchCOCOExportPreview = () => request('/api/export/coco/preview')
export const postCOCOExport = () => request('/api/export/coco', { method: 'POST' })

// Project management
export const fetchProjects = () => request('/api/projects')

export const postProject = (data) =>
  request('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const activateProject = (id) =>
  request(`/api/projects/${id}/activate`, { method: 'POST' })

export const deleteProject = (id) =>
  request(`/api/projects/${id}`, { method: 'DELETE' })

// Image upload: body is a FormData — do NOT set Content-Type, browser handles boundary
export const postUploadProject = (formData) =>
  request('/api/projects/upload', { method: 'POST', body: formData })
