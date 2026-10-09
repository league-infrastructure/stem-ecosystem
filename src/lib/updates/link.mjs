// Build the base-aware href for the /update page. Pure; used by UpdateLink.astro.
export function updateHref(base, type, slug) {
  const b = String(base || '').replace(/\/+$/, '');
  if (!type || slug === undefined || slug === null || slug === '') return `${b}/update`;
  const q = new URLSearchParams({ type: String(type), slug: String(slug) });
  return `${b}/update?${q.toString()}`;
}

// Update-link target for an opportunity page. Prefer the owning partner (by
// partner_id); when that partner record is missing, address the opportunity
// itself, which the sidecar resolves directly by its slug.
export function opportunityUpdateTarget(opp, partners) {
  const partner = (partners || []).find((p) => p.id === opp.partner_id);
  if (partner?.slug) return { type: 'partner', slug: partner.slug };
  if (opp.slug) return { type: 'opportunity', slug: opp.slug };
  return null;
}
