// Polygon helpers. Polygons are flat lists in image pixels: [x1, y1, x2, y2, ...]

// Ray casting: count how many edges a horizontal ray from (x, y) crosses.
export function pointInPolygon(x, y, flat) {
  let inside = false
  const n = flat.length / 2
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = flat[2 * i], yi = flat[2 * i + 1]
    const xj = flat[2 * j], yj = flat[2 * j + 1]
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

// Shoelace formula.
export function polygonArea(flat) {
  let sum = 0
  const n = flat.length / 2
  for (let i = 0, j = n - 1; i < n; j = i++) {
    sum += flat[2 * j] * flat[2 * i + 1] - flat[2 * i] * flat[2 * j + 1]
  }
  return Math.abs(sum) / 2
}

const segmentationArea = (seg) => seg.reduce((total, poly) => total + polygonArea(poly), 0)

// Object under the point; when several overlap, the smallest one wins,
// so a small object lying on a big one can still be picked.
export function objectAt(x, y, objects) {
  let best = null
  let bestArea = Infinity
  for (const obj of objects) {
    if (!obj.segmentation.some((poly) => pointInPolygon(x, y, poly))) continue
    const area = segmentationArea(obj.segmentation)
    if (area < bestArea) {
      best = obj
      bestArea = area
    }
  }
  return best
}
