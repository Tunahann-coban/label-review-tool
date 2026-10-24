// Suspect = what the pipeline gave is doubtful: low score, or a catch-all class
// ("misc_item" in BidVision, "unknown" in the sample data).
// Judged on the pipeline's original output, not on the reviewer's decisions,
// so the list does not reshuffle while you work; only the threshold reorders it.

export const DEFAULT_THRESHOLD = 0.5

// Catch-all class names: "nothing more specific fits". Compared case-insensitively.
export const CATCH_ALL_NAMES = ['misc_item', 'unknown']

// id -> name of the catch-all categories in the package (there may be none)
export const catchAllCategories = (categories) =>
  new Map(categories
    .filter((c) => CATCH_ALL_NAMES.includes(c.name.trim().toLowerCase()))
    .map((c) => [c.id, c.name.trim()]))

const pipelineCategory = (obj) => (obj.state === 'changed' ? obj.orig_category_id : obj.category_id)

// Reasons the object is suspect; empty list means it is not.
// Objects the reviewer added are never suspect: they are not pipeline output.
export function suspectReasons(obj, threshold, catchAll) {
  const reasons = []
  if (obj.from_candidate != null) return reasons
  if (obj.score != null && obj.score < threshold) reasons.push('skor eşiğin altında')
  const catchAllName = catchAll.get(pipelineCategory(obj))
  if (catchAllName != null) reasons.push(`sınıf: ${catchAllName}`)
  return reasons
}

/**
 * Objects with their color index (position in the package, so colors never
 * change) and suspect reasons. Suspects first, lowest score first; the rest
 * keep the package order.
 */
export function orderObjects(objects, threshold, catchAll) {
  const items = objects.map((obj, colorIndex) => ({
    obj, colorIndex, reasons: suspectReasons(obj, threshold, catchAll),
  }))
  const score = (it) => it.obj.score ?? Infinity
  const suspects = items.filter((it) => it.reasons.length > 0)
    .sort((a, b) => score(a) - score(b) || a.colorIndex - b.colorIndex)
  const rest = items.filter((it) => it.reasons.length === 0)
  return [...suspects, ...rest]
}
