import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatFooterDate } from '../../src/lib/footer-dates.mjs';

test('3 am PT scrape (next day in UTC) shows the Pacific date', () => {
  // 2026-10-09T03:43:06Z is 8:43 pm PDT on Oct 8.
  const r = formatFooterDate('2026-10-09T03:43:06Z');
  assert.equal(r.label, 'October 8, 2026');
  assert.equal(r.iso, '2026-10-09T03:43:06.000Z');
  assert.match(r.title, /8:43 PM PDT/);
});

test('10:00 UTC (3 am PDT) stays on the same Pacific day', () => {
  const r = formatFooterDate('2026-10-09T10:00:00Z');
  assert.equal(r.label, 'October 9, 2026');
  assert.match(r.title, /3:00 AM PDT/);
});

test('winter uses PST', () => {
  const r = formatFooterDate('2026-01-15T02:00:00Z');
  assert.equal(r.label, 'January 14, 2026');
  assert.match(r.title, /PST/);
});

test('accepts Date objects; missing or invalid returns null', () => {
  assert.equal(formatFooterDate(new Date('2026-10-09T12:00:00Z')).label, 'October 9, 2026');
  assert.equal(formatFooterDate(undefined), null);
  assert.equal(formatFooterDate('nonsense'), null);
});
