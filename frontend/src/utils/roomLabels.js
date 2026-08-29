const ROOM_LABELS_AR = Object.freeze({
  Bedroom: 'غرفة نوم',
  Kitchen: 'مطبخ',
  'Living Room': 'غرفة معيشة',
  Bathroom: 'دورة مياه',
  'Dining Room': 'غرفة طعام',
  Majlis: 'مجلس',
})

export function roomLabelAr(value) {
  return ROOM_LABELS_AR[value] || value || 'عنصر غير مصنف'
}
