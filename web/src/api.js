// All calls to the service go through this file.

async function getJson(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path}: ${res.status}`)
  return res.json()
}

export const fetchHello = () => getJson('/api/hello')
