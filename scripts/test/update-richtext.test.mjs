import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseInline, parseMessage } from '../../src/lib/updates/richtext.mjs';

test('bold is parsed', () => {
  assert.deepEqual(parseInline('Please **Confirm** now'), [
    { type: 'text', text: 'Please ' },
    { type: 'bold', text: 'Confirm' },
    { type: 'text', text: ' now' },
  ]);
});

test('unclosed or empty markers stay literal', () => {
  assert.deepEqual(parseInline('a **b c'), [{ type: 'text', text: 'a **b c' }]);
  assert.deepEqual(parseInline('a ** ** b'), [{ type: 'text', text: 'a ** ** b' }]);
});

test('bare URLs become links, trailing punctuation excluded', () => {
  const s = parseInline('See https://x.org/events, then done.');
  assert.deepEqual(s[1], { type: 'link', text: 'https://x.org/events', href: 'https://x.org/events' });
  assert.equal(s[2].text, ', then done.');
});

test('only http(s) is linked', () => {
  assert.deepEqual(parseInline('javascript:alert(1) ftp://a.b/c'), [
    { type: 'text', text: 'javascript:alert(1) ftp://a.b/c' },
  ]);
});

test('HTML is left as plain text', () => {
  assert.deepEqual(parseInline('<img src=x onerror=1>'), [{ type: 'text', text: '<img src=x onerror=1>' }]);
});

test('paragraphs and line breaks', () => {
  const p = parseMessage('one\ntwo\n\nthree');
  assert.equal(p.length, 2);
  assert.equal(p[0].length, 2);
  assert.equal(p[1][0][0].text, 'three');
  assert.deepEqual(parseMessage('   '), []);
});
