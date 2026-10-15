export function navigate(path: string) {
  window.location.hash = path;
}

export function schemeHref(schemeId: string) {
  return "#/scholarships/" + encodeURIComponent(schemeId);
}
