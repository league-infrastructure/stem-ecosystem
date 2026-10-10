// Format scraping hints into readable labelled lines. Pure, no DOM.
// Hint kinds: page {role,url,focus?}, exclude {match,reason}, note {text},
// identity {name?,website?}.

const ROLE_LABELS = {
  about: 'About',
  contact: 'Contact',
  events: 'Events',
  camps: 'Camps',
  programs: 'Programs',
  other: 'Page',
};

/** "https://www.visitcmod.org/calendar/" -> "visitcmod.org/calendar" */
export function shortUrl(url) {
  const s = String(url ?? '').trim();
  if (!s) return '';
  try {
    const u = new URL(s);
    const path = u.pathname.replace(/\/+$/, '');
    return `${u.host.replace(/^www\./, '')}${path}${u.search}`;
  } catch {
    return s.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/+$/, '');
  }
}

function matchText(match) {
  const m = String(match ?? '');
  return m.startsWith('re:') ? `pattern ${m.slice(3)}` : m;
}

/** One hint -> { kind, label, text }, or null when unusable. */
export function formatHint(hint) {
  if (!hint || typeof hint !== 'object') return null;
  switch (hint.kind) {
    case 'page':
      return { kind: 'page', label: ROLE_LABELS[hint.role] || ROLE_LABELS.other, text: hint.focus ? `${shortUrl(hint.url)} \u2014 focus: ${String(hint.focus)}` : shortUrl(hint.url) };
    case 'exclude': {
      const reason = hint.reason ? ` (${hint.reason})` : '';
      return { kind: 'exclude', label: 'Skip', text: `${matchText(hint.match)}${reason}` };
    }
    case 'note':
      return { kind: 'note', label: 'Note', text: String(hint.text ?? '') };
    case 'identity': {
      const parts = [];
      if (hint.name) parts.push(`name "${hint.name}"`);
      if (hint.website) parts.push(`website ${shortUrl(hint.website)}`);
      return { kind: 'identity', label: 'Identity', text: parts.join(', ') };
    }
    default:
      return null;
  }
}

/** Hints list -> readable lines (unknown kinds dropped). */
export function formatHints(hints) {
  return (Array.isArray(hints) ? hints : []).map(formatHint).filter(Boolean);
}

/** Plain-text form, e.g. "Events: visitcmod.org/calendar". */
export function hintLine(line) {
  return `${line.label}: ${line.text}`;
}

function canon(hints) {
  return (Array.isArray(hints) ? hints : [])
    .map((h) => JSON.stringify(Object.fromEntries(Object.entries(h || {}).sort(([a], [b]) => (a < b ? -1 : 1)))))
    .sort();
}

/** True when proposed differs from saved (order-insensitive). */
export function hintsDiffer(saved, proposed) {
  const a = canon(saved);
  const b = canon(proposed);
  return a.length !== b.length || a.some((x, i) => x !== b[i]);
}
