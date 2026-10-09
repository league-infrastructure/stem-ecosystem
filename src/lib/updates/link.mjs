// Build the base-aware href for the /update page. Pure; used by UpdateLink.astro.
export function updateHref(base, type, slug) {
  const b = String(base || '').replace(/\/+$/, '');
  if (!type || slug === undefined || slug === null || slug === '') return `${b}/update`;
  const q = new URLSearchParams({ type: String(type), slug: String(slug) });
  return `${b}/update?${q.toString()}`;
}
