// Image groups ("folders" on screen; the files never move). An image's status is
// 'pending' | 'reviewed' (= tamamlandı) | 'needs_edit' (= düzenlenecek).
export const GROUPS = [
  { id: 'all', label: 'Tümü' },
  { id: 'pending', label: 'Bekleyen' },
  { id: 'reviewed', label: 'Tamamlanan' },
  { id: 'needs_edit', label: 'Düzenlenecek' },
]

export const inGroup = (image, group) => group === 'all' || image.status === group

export function countByGroup(images) {
  const counts = { all: images.length, pending: 0, reviewed: 0, needs_edit: 0 }
  for (const img of images) counts[img.status] = (counts[img.status] ?? 0) + 1
  return counts
}

// Index of the image `delta` places away from `index`, counting only images of the
// group. If the current image is not in the group (it was just moved out of it),
// forward goes to the group's first image and back to its last.
export function moveInGroup(images, group, index, delta) {
  const inside = []
  images.forEach((img, i) => { if (inGroup(img, group)) inside.push(i) })
  if (inside.length === 0) return index
  const pos = inside.indexOf(index)
  if (pos === -1) return delta > 0 ? inside[0] : inside[inside.length - 1]
  return inside[Math.min(inside.length - 1, Math.max(0, pos + delta))]
}

// First pending image after the current one, wrapping around to the start,
// so skipped images are found again. null when no other image is pending.
// Images marked "needs edit" are decided, so they are not pending.
export function findNextPending(images, index) {
  for (let step = 1; step < images.length; step++) {
    const i = (index + step) % images.length
    if (images[i].status === 'pending') return i
  }
  return null
}
