// Date formatting for the footer. Always rendered in America/Los_Angeles,
// regardless of the build machine's timezone.
const TZ = 'America/Los_Angeles';

/** Parse an ISO string / Date; returns null if missing or invalid. */
function toDate(value) {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * @returns {{ iso: string, label: string, title: string } | null}
 *  label: "October 8, 2026" (Pacific calendar day); title: full timestamp.
 */
export function formatFooterDate(value) {
  const d = toDate(value);
  if (!d) return null;
  const label = d.toLocaleDateString('en-US', {
    timeZone: TZ, year: 'numeric', month: 'long', day: 'numeric',
  });
  const title = d.toLocaleString('en-US', {
    timeZone: TZ, year: 'numeric', month: 'long', day: 'numeric',
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  });
  return { iso: d.toISOString(), label, title };
}
