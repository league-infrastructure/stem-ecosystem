// Minimal, safe chat-text parser. Returns data only (no HTML): the DOM glue
// builds nodes with textContent, so nothing here can inject markup.
//
// parseMessage(text) -> paragraphs; paragraph -> lines; line -> segments.
// segment: { type: 'text', text } | { type: 'bold', text } | { type: 'link', text, href }

const TOKEN = /\*\*([^*\n]+?)\*\*|https?:\/\/[^\s<>"]+/g;

export function parseInline(line) {
  const out = [];
  let last = 0;
  const push = (s) => { if (s) out.push({ type: 'text', text: s }); };
  for (const m of line.matchAll(TOKEN)) {
    if (m[1] !== undefined) {
      if (!m[1].trim()) continue; // "** **" stays literal
      push(line.slice(last, m.index));
      out.push({ type: 'bold', text: m[1] });
      last = m.index + m[0].length;
    } else {
      // Trim trailing punctuation that is almost never part of the URL.
      let url = m[0];
      while (/[.,;:!?)\]'*]$/.test(url)) {
        if (url.endsWith(')') && (url.match(/\(/g) || []).length >= (url.match(/\)/g) || []).length) break;
        url = url.slice(0, -1);
      }
      if (!/^https?:\/\/[^/\s.]+\.[^\s]+|^https?:\/\/localhost/.test(url)) continue;
      push(line.slice(last, m.index));
      out.push({ type: 'link', text: url, href: url });
      last = m.index + url.length;
    }
  }
  push(line.slice(last));
  return out;
}

export function parseMessage(text) {
  return String(text ?? '')
    .replace(/\r\n?/g, '\n')
    .trim()
    .split(/\n{2,}/)
    .filter((p) => p.trim())
    .map((p) => p.split('\n').map(parseInline));
}
