// All calls to the service go through this file.

async function getJson(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path}: ${res.status}`)
  return res.json()
}

export const fetchPackage = () => getJson('/api/package')
export const fetchImage = (id) => getJson(`/api/images/${id}`)
export const imageFileUrl = (id) => `/api/images/${id}/file`
