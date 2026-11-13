// Image groups ("folders" on screen; the files never move). An image has two separate
// marks: status ('pending' | 'reviewed' = tamamlandı) and needs_edit (on the edit list,
// whether or not it is also finished). So one image can be in two groups.
export const GROUPS = [
  { id: 'all', label: 'Tümü' },
  { id: 'pending', label: 'Bekleyen' },
  { id: 'reviewed', label: 'Tamamlanan' },
  { id: 'needs_edit', label: 'Düzenlenecek' },
]

export function inGroup(image, group) {
  if (group === 'all') return true
  if (group === 'needs_edit') return Boolean(image.needs_edit)
  return image.status === group
}

export function countByGroup(images) {
  const counts = { all: images.length, pending: 0, reviewed: 0, needs_edit: 0 }
  for (const img of images) {
    if (img.status === 'reviewed') counts.reviewed += 1
    else counts.pending += 1
    if (img.needs_edit) counts.needs_edit += 1
  }
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

// First unfinished image after the current one, wrapping around to the start,
// so skipped images are found again. null when no other image is pending.
// Being on the edit list does not finish an image: it still counts as pending.
export function findNextPending(images, index) {
  for (let step = 1; step < images.length; step++) {
    const i = (index + step) % images.length
    if (images[i].status === 'pending') return i
  }
  return null
}
