import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatHint, formatHints, hintLine, hintsDiffer, shortUrl } from '../../src/lib/updates/hints-view.mjs';

test('shortUrl strips scheme, www and trailing slash', () => {
  assert.equal(shortUrl('https://www.visitcmod.org/calendar/'), 'visitcmod.org/calendar');
  assert.equal(shortUrl('https://x.org/'), 'x.org');
  assert.equal(shortUrl('not a url/'), 'not a url');
  assert.equal(shortUrl(null), '');
});

test('page hints use role labels', () => {
  const l = formatHint({ kind: 'page', role: 'events', url: 'https://www.visitcmod.org/calendar' });
  assert.equal(hintLine(l), 'Events: visitcmod.org/calendar');
  assert.equal(hintLine(formatHint({ kind: 'page', role: 'camps', url: 'https://a.org/c' })), 'Camps: a.org/c');
  assert.equal(formatHint({ kind: 'page', role: 'weird', url: 'https://a.org' }).label, 'Page');
});

test('exclude, note and identity hints', () => {
  assert.equal(hintLine(formatHint({ kind: 'exclude', match: '/blog', reason: 'old news' })), 'Skip: /blog (old news)');
  assert.equal(hintLine(formatHint({ kind: 'exclude', match: 're:^/tag/' })), 'Skip: pattern ^/tag/');
  assert.equal(hintLine(formatHint({ kind: 'note', text: 'Camps are in summer' })), 'Note: Camps are in summer');
  assert.equal(
    hintLine(formatHint({ kind: 'identity', name: 'Acme', website: 'https://www.acme.org/' })),
    'Identity: name "Acme", website acme.org',
  );
  assert.equal(hintLine(formatHint({ kind: 'identity', website: 'https://acme.org' })), 'Identity: website acme.org');
});

test('formatHints drops unknown and malformed entries, tolerates non-arrays', () => {
  assert.equal(formatHints([{ kind: 'zzz' }, null, { kind: 'note', text: 'a' }]).length, 1);
  assert.deepEqual(formatHints(undefined), []);
});

test('server text is passed through verbatim (no HTML interpretation here)', () => {
  assert.equal(formatHint({ kind: 'note', text: '<img src=x onerror=1>' }).text, '<img src=x onerror=1>');
});

test('hintsDiffer is order-insensitive and detects changes', () => {
  const a = { kind: 'note', text: 'x' };
  const b = { kind: 'page', role: 'events', url: 'https://a.org' };
  assert.equal(hintsDiffer([a, b], [b, a]), false);
  assert.equal(hintsDiffer([a], [a, b]), true);
  assert.equal(hintsDiffer([a], [{ kind: 'note', text: 'y' }]), true);
  assert.equal(hintsDiffer([], undefined), false);
  assert.equal(hintsDiffer([{ kind: 'note', z: 1, a: 2 }], [{ a: 2, z: 1, kind: 'note' }]), false);
});
