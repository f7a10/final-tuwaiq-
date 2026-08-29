export function compareButtonLabel(hasPreview, comparisonVisible) {
  if (!hasPreview) return "إظهار قبل / بعد";
  return comparisonVisible ? "إخفاء المقترح" : "إظهار قبل / بعد";
}

export function setElementHidden(element, hidden) {
  element.toggleAttribute("hidden", hidden);
}
