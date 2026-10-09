import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createApiClient, describeError, UpdateApiError } from '../../src/lib/updates/api-client.mjs';

function fakeFetch(responder) {
  const calls = [];
  const f = async (url, init) => {
    calls.push({ url, init });
    return responder(url, init);
  };
  f.calls = calls;
  return f;
}
const json = (status, body, headers = {}) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: { get: (k) => headers[k] ?? null },
  json: async () => body,
});
const errBody = (code) => ({ error: { code, message: `msg ${code}`, fallback_email: 'help@x.org' } });

test('start posts type/slug (and turnstile token only when given)', async () => {
  const f = fakeFetch(() => json(201, { session_id: 's1' }));
  const c = createApiClient({ fetch: f, baseUrl: 'https://api.test/' });
  assert.equal((await c.start('partner', 'acme')).session_id, 's1');
  assert.equal(f.calls[0].url, 'https://api.test/v1/sessions');
  assert.equal(f.calls[0].init.method, 'POST');
  assert.deepEqual(JSON.parse(f.calls[0].init.body), { type: 'partner', slug: 'acme' });
  await c.start('partner', 'acme', 'tok');
  assert.equal(JSON.parse(f.calls[1].init.body).turnstile_token, 'tok');
});

test('send, confirm and get hit the right endpoints', async () => {
  const f = fakeFetch(() => json(200, { ok: true }));
  const c = createApiClient({ fetch: f, baseUrl: 'https://api.test' });
  await c.send('a/b', 'hello');
  await c.confirm('s1');
  await c.get('s1');
  assert.equal(f.calls[0].url, 'https://api.test/v1/sessions/a%2Fb/messages');
  assert.deepEqual(JSON.parse(f.calls[0].init.body), { text: 'hello' });
  assert.equal(f.calls[1].url, 'https://api.test/v1/sessions/s1/confirm');
  assert.equal(f.calls[2].url, 'https://api.test/v1/sessions/s1');
  assert.equal(f.calls[2].init.method, 'GET');
  assert.equal(f.calls[2].init.body, undefined);
});

const CODES = {
  bad_request: 400, not_found: 404, session_expired: 410, session_ended: 409, message_too_long: 413,
  rate_limited: 429, spend_cap_reached: 503, turnstile_failed: 403, upstream_unavailable: 502,
};

for (const [code, status] of Object.entries(CODES)) {
  test(`error code ${code} is normalized and has a friendly message`, async () => {
    const hdr = code === 'rate_limited' ? { 'Retry-After': '30' } : {};
    const c = createApiClient({ fetch: fakeFetch(() => json(status, errBody(code), hdr)), baseUrl: 'x' });
    const err = await c.send('s', 't').then(() => null, (e) => e);
    assert.ok(err instanceof UpdateApiError);
    assert.equal(err.code, code);
    assert.equal(err.status, status);
    assert.equal(err.fallbackEmail, 'help@x.org');
    const text = describeError(err);
    assert.ok(text.length > 10);
    if (['not_found', 'spend_cap_reached', 'upstream_unavailable', 'session_ended'].includes(code)) {
      assert.match(text, /help@x\.org/);
    }
  });
}

test('rate_limited carries Retry-After seconds and mentions them', async () => {
  const c = createApiClient({ fetch: fakeFetch(() => json(429, errBody('rate_limited'), { 'Retry-After': '42' })), baseUrl: 'x' });
  const err = await c.send('s', 't').catch((e) => e);
  assert.equal(err.retryAfter, 42);
  assert.equal(err.retryable, true);
  assert.match(describeError(err), /42 seconds/);
  assert.match(describeError(new UpdateApiError({ code: 'rate_limited', retryAfter: 1 })), /1 second\b/);
  assert.match(describeError(new UpdateApiError({ code: 'rate_limited' })), /wait a bit/);
});

test('retryable and endsSession flags', () => {
  assert.equal(new UpdateApiError({ code: 'upstream_unavailable' }).retryable, true);
  assert.equal(new UpdateApiError({ code: 'network' }).retryable, true);
  assert.equal(new UpdateApiError({ code: 'message_too_long' }).retryable, false);
  assert.equal(new UpdateApiError({ code: 'session_expired' }).endsSession, true);
  assert.equal(new UpdateApiError({ code: 'session_ended' }).endsSession, true);
  assert.equal(new UpdateApiError({ code: 'not_found' }).endsSession, false);
  assert.match(describeError(new UpdateApiError({ code: 'session_expired' })), /start again/i);
});

test('network failure maps to code network', async () => {
  const c = createApiClient({ fetch: async () => { throw new TypeError('fail'); }, baseUrl: 'x' });
  const err = await c.get('s').catch((e) => e);
  assert.equal(err.code, 'network');
  assert.match(describeError(err, 'fb@x.org'), /fb@x\.org/);
});

test('non-JSON error body and bad success body are handled', async () => {
  const bad = { ok: false, status: 502, headers: { get: () => null }, json: async () => { throw new Error('no'); } };
  const err = await createApiClient({ fetch: async () => bad, baseUrl: 'x' }).get('s').catch((e) => e);
  assert.equal(err.code, 'upstream_unavailable');
  const ok = { ok: true, status: 200, headers: { get: () => null }, json: async () => { throw new Error('no'); } };
  const err2 = await createApiClient({ fetch: async () => ok, baseUrl: 'x' }).get('s').catch((e) => e);
  assert.equal(err2.code, 'upstream_unavailable');
});

test('unknown code falls back to a generic message with the email', () => {
  assert.match(describeError(new UpdateApiError({ code: 'weird' }), 'a@b.org'), /a@b\.org/);
});

test('client script never uses innerHTML', () => {
  const src = readFileSync(new URL('../../src/scripts/update-chat.ts', import.meta.url), 'utf8');
  assert.equal(/innerHTML|outerHTML|insertAdjacentHTML/.test(src), false);
});
