// Display text for object states in review files.
export const STATE_LABELS = {
  auto: 'dokunulmadı',
  accepted: 'onaylandı',
  changed: 'değiştirildi',
  deleted: 'silindi',
  added: 'eklendi',
}

// Display text for the image's own status (not its objects'). Being on the edit list
// is a separate mark, see EDIT_LIST_LABEL.
export const IMAGE_STATUS_LABELS = {
  pending: 'bekliyor',
  reviewed: 'tamamlandı',
}
export const EDIT_LIST_LABEL = 'düzenlenecekler listesinde'

// "8 Kas 22:10" (review files store ISO text); '' when there is no date
export function shortDate(iso) {
  const d = iso ? new Date(iso) : null
  if (!d || Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export const STATE_ICONS = {
  auto: '',
  accepted: '✓',
  changed: '✎',
  deleted: '✗',
  added: '+',
}
