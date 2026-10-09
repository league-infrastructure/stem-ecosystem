// Fetch wrapper for the update-agent sidecar API. Pure: `fetch` and the base
// URL are injected so tests can use a fake. All failures throw UpdateApiError.

export const DEFAULT_FALLBACK_EMAIL = 'partners@sdstemecosystem.org';

export class UpdateApiError extends Error {
  constructor({ code, message, status = 0, retryAfter = null, fallbackEmail = null }) {
    super(message || code);
    this.name = 'UpdateApiError';
    this.code = code;
    this.status = status;
    this.retryAfter = retryAfter; // seconds, or null
    this.fallbackEmail = fallbackEmail;
  }

  /** True when the same request may sensibly be tried again. */
  get retryable() {
    return ['upstream_unavailable', 'rate_limited', 'network'].includes(this.code);
  }

  /** True when the session can no longer accept messages. */
  get endsSession() {
    return this.code === 'session_expired' || this.code === 'session_ended';
  }
}

function parseRetryAfter(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? Math.ceil(n) : null;
}

export function createApiClient({ fetch: fetchImpl, baseUrl }) {
  const base = String(baseUrl || '').replace(/\/+$/, '');

  async function call(method, path, body) {
    let res;
    try {
      res = await fetchImpl(`${base}${path}`, {
        method,
        headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new UpdateApiError({ code: 'network', message: 'Could not reach the update service.' });
    }
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) {
      const err = (data && data.error) || {};
      throw new UpdateApiError({
        code: err.code || (res.status >= 500 ? 'upstream_unavailable' : 'bad_request'),
        message: err.message,
        status: res.status,
        retryAfter: parseRetryAfter(res.headers?.get?.('Retry-After')),
        fallbackEmail: err.fallback_email || null,
      });
    }
    if (data === null || typeof data !== 'object') {
      throw new UpdateApiError({
        code: 'upstream_unavailable',
        message: 'Unexpected response from the update service.',
        status: res.status,
      });
    }
    return data;
  }

  const sid = (id) => encodeURIComponent(id);
  return {
    start(type, slug, turnstileToken) {
      const body = { type, slug };
      if (turnstileToken) body.turnstile_token = turnstileToken;
      return call('POST', '/v1/sessions', body);
    },
    send(sessionId, text) {
      return call('POST', `/v1/sessions/${sid(sessionId)}/messages`, { text });
    },
    confirm(sessionId) {
      return call('POST', `/v1/sessions/${sid(sessionId)}/confirm`, {});
    },
    get(sessionId) {
      return call('GET', `/v1/sessions/${sid(sessionId)}`);
    },
  };
}

/**
 * Friendly, user-facing text for an error. Always plain text (callers render
 * with textContent). `fallbackEmail` is used when the error carries none.
 */
export function describeError(err, fallbackEmail = DEFAULT_FALLBACK_EMAIL) {
  const email = err?.fallbackEmail || fallbackEmail || DEFAULT_FALLBACK_EMAIL;
  switch (err?.code) {
    case 'rate_limited': {
      const s = err.retryAfter;
      const wait = s ? ` Please wait about ${s} second${s === 1 ? '' : 's'} and try again.` : ' Please wait a bit and try again.';
      return `You're sending requests too quickly.${wait}`;
    }
    case 'spend_cap_reached':
      return `Our assistant has reached its daily limit. Please try again tomorrow or email ${email}.`;
    case 'session_expired':
      return 'This conversation has expired. You can start again.';
    case 'session_ended':
      return `This conversation has ended. Please start again, or email ${email} for anything else.`;
    case 'upstream_unavailable':
      return `Our assistant is temporarily unavailable and nothing was changed. Please try again in a few minutes, or email ${email}.`;
    case 'message_too_long':
      return 'That message is too long. Please shorten it and send it again.';
    case 'not_found':
      return `We couldn't find that listing. Please email ${email}.`;
    case 'turnstile_failed':
      return 'Human verification failed. Please reload the page and try again.';
    case 'network':
      return `We couldn't reach the update service. Check your connection and try again, or email ${email}.`;
    case 'bad_request':
      return err.message || `Something was wrong with that request. Please try again, or email ${email}.`;
    default:
      return `Something went wrong. Please try again, or email ${email}.`;
  }
}
