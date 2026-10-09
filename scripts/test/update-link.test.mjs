import { test } from 'node:test';
import assert from 'node:assert/strict';
import { updateHref } from '../../src/lib/updates/link.mjs';

test('builds href with type and slug', () => {
  assert.equal(updateHref('', 'partner', 'fleet-science-center'), '/update?type=partner&slug=fleet-science-center');
});
test('normalizes trailing slash on base', () => {
  assert.equal(updateHref('/partner-scrape/', 'team', 'frc-1'), '/partner-scrape/update?type=team&slug=frc-1');
});
test('encodes special characters', () => {
  assert.equal(updateHref('', 'club', 'a b&c'), '/update?type=club&slug=a+b%26c');
});
test('falls back to bare /update without slug', () => {
  assert.equal(updateHref('/x', 'club', ''), '/x/update');
});

import { opportunityUpdateTarget } from '../../src/lib/updates/link.mjs';
test('opportunity links to its partner when the partner record exists', () => {
  assert.deepEqual(
    opportunityUpdateTarget({ partner_id: 1, slug: 'opp' }, [{ id: 1, slug: 'p1' }]),
    { type: 'partner', slug: 'p1' },
  );
});
test('opportunity without a partner record links by its own slug', () => {
  assert.deepEqual(
    opportunityUpdateTarget({ partner_id: 99, slug: 'opp' }, [{ id: 1, slug: 'p1' }]),
    { type: 'opportunity', slug: 'opp' },
  );
});
