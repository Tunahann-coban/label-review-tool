// First pending image after the current one, wrapping around to the start,
// so skipped images are found again. null when no other image is pending.
export function findNextPending(images, index) {
  for (let step = 1; step < images.length; step++) {
    const i = (index + step) % images.length
    if (images[i].status !== 'reviewed') return i
  }
  return null
}
