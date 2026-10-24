// Candidates that can still be added: the ones not already used by a live added object.
export function availableCandidates(detail) {
  const used = new Set(
    detail.objects.filter((o) => o.from_candidate != null && o.state !== 'deleted').map((o) => o.from_candidate),
  )
  return detail.candidates.filter((c) => !used.has(c.id))
}
