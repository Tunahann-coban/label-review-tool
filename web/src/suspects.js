// Suspect = what the pipeline gave is doubtful: low score, or class "unknown".
// Judged on the pipeline's original output, not on the reviewer's decisions,
// so the list does not reshuffle while you work; only the threshold reorders it.

export const DEFAULT_THRESHOLD = 0.5

// ids of categories named "unknown" (there may be none)
export const unknownCategoryIds = (categories) =>
  new Set(categories.filter((c) => c.name.trim().toLowerCase() === 'unknown').map((c) => c.id))

const pipelineCategory = (obj) => (obj.state === 'changed' ? obj.orig_category_id : obj.category_id)

// Reasons the object is suspect; empty list means it is not.
// Objects the reviewer added are never suspect: they are not pipeline output.
export function suspectReasons(obj, threshold, unknownIds) {
  const reasons = []
  if (obj.from_candidate != null) return reasons
  if (obj.score != null && obj.score < threshold) reasons.push('skor eşiğin altında')
  if (unknownIds.has(pipelineCategory(obj))) reasons.push('sınıf: unknown')
  return reasons
}

/**
 * Objects with their color index (position in the package, so colors never
 * change) and suspect reasons. Suspects first, lowest score first; the rest
 * keep the package order.
 */
export function orderObjects(objects, threshold, unknownIds) {
  const items = objects.map((obj, colorIndex) => ({
    obj, colorIndex, reasons: suspectReasons(obj, threshold, unknownIds),
  }))
  const score = (it) => it.obj.score ?? Infinity
  const suspects = items.filter((it) => it.reasons.length > 0)
    .sort((a, b) => score(a) - score(b) || a.colorIndex - b.colorIndex)
  const rest = items.filter((it) => it.reasons.length === 0)
  return [...suspects, ...rest]
}
