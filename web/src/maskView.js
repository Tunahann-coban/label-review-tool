// Mask display modes, in the order the M key cycles through them.
export const MASK_VIEWS = [
  { id: 'fill', label: 'Dolu' },
  { id: 'outline', label: 'Kenar' },
  { id: 'hidden', label: 'Gizli' },
]

export const nextMaskView = (current) => {
  const i = MASK_VIEWS.findIndex((v) => v.id === current)
  return MASK_VIEWS[(i + 1) % MASK_VIEWS.length].id
}
