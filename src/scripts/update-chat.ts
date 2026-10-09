// DOM glue for /update chat mode. All server text is rendered with
// textContent (never innerHTML). Logic lives in src/lib/updates/*.
import { createApiClient, describeError, DEFAULT_FALLBACK_EMAIL } from '../lib/updates/api-client.mjs';
import { formatHints, hintLine, hintsDiffer } from '../lib/updates/hints-view.mjs';

export function initUpdateChat(page: HTMLElement, type: string, slug: string): void {
  const api = createApiClient({
    fetch: (...a: Parameters<typeof fetch>) => fetch(...a),
    baseUrl: page.dataset.apiUrl || 'https://updates.jtlapp.net',
  });
  const storeKey = `update-session:${type}:${slug}`;
  const transcript = document.getElementById('chat-transcript')!;
  const chatSection = document.getElementById('update-chat')!;
  const hintsBody = document.getElementById('hints-body')!;

  let fallbackEmail = DEFAULT_FALLBACK_EMAIL;
  let sessionId: string | null = null;
  let saved: any[] = [];
  let proposed: any[] = [];
  let ended = false;
  let busy = false;
  let confirmed = false;
  let turnsLeft: number | null = null;
  let entityName = '';

  // --- build static chat controls (no server text) ---
  const status = el('p', 'chat-status');
  status.setAttribute('role', 'status');
  const notices = el('div', 'chat-notices');
  const form = document.createElement('form');
  form.className = 'chat-form';
  const label = el('label', '', 'Your message');
  label.htmlFor = 'chat-input';
  const input = document.createElement('textarea');
  input.id = 'chat-input';
  input.rows = 3;
  input.maxLength = 4000;
  const sendBtn = el('button', 'chat-send', 'Send') as HTMLButtonElement;
  sendBtn.type = 'submit';
  const hintEl = el('p', 'chat-hint', 'Enter to send, Shift+Enter for a new line.');
  const turns = el('p', 'chat-turns');
  const restart = el('button', 'chat-restart', 'Start again') as HTMLButtonElement;
  restart.type = 'button';
  restart.hidden = true;
  const retry = el('button', 'chat-retry', 'Try again') as HTMLButtonElement;
  retry.type = 'button';
  retry.hidden = true;
  form.append(label, input, sendBtn, hintEl);
  chatSection.append(notices, status, turns, form, retry, restart);

  function el(tag: string, cls = '', text = ''): HTMLElement {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  function setBusy(b: boolean) {
    busy = b;
    input.disabled = b || ended;
    sendBtn.disabled = b || ended;
    form.setAttribute('aria-busy', String(b));
    const c = hintsBody.querySelector<HTMLButtonElement>('.hints-confirm');
    if (c) c.disabled = b;
  }

  function setStatus(text: string) {
    status.textContent = text;
  }

  function addMessage(role: 'user' | 'assistant', text: string) {
    const m = el('div', `chat-msg chat-${role}`);
    const who = el('strong', 'chat-who', role === 'user' ? 'You' : 'Assistant');
    const body = el('p', 'chat-text');
    body.textContent = text; // preserved newlines via CSS white-space
    m.append(who, body);
    transcript.append(m);
    m.scrollIntoView?.({ block: 'nearest' });
  }

  function renderTurns() {
    turns.textContent = turnsLeft === null ? '' : `${turnsLeft} message${turnsLeft === 1 ? '' : 's'} left in this conversation.`;
  }

  function renderNotices(list: unknown) {
    notices.replaceChildren();
    for (const n of Array.isArray(list) ? list : []) {
      const p = el('p', 'chat-notice');
      p.setAttribute('role', 'note');
      p.textContent = typeof n === 'string' ? n : String((n as any)?.text ?? (n as any)?.message ?? '');
      if (p.textContent) notices.append(p);
    }
  }

  function renderHints() {
    hintsBody.replaceChildren();
    const section = (title: string, hints: any[]) => {
      const h = el('h3', 'hints-sub', title);
      hintsBody.append(h);
      const lines = formatHints(hints);
      if (!lines.length) {
        hintsBody.append(el('p', 'hints-empty', 'None yet.'));
        return;
      }
      const ul = el('ul', 'hints-list');
      for (const l of lines) {
        const li = el('li', `hint hint-${l.kind}`);
        li.textContent = hintLine(l);
        ul.append(li);
      }
      hintsBody.append(ul);
    };
    section('Currently saved', saved);
    const changed = hintsDiffer(saved, proposed);
    if (changed) section('Proposed changes', proposed);
    if (changed && !ended) {
      const b = el('button', 'hints-confirm', 'Confirm these hints') as HTMLButtonElement;
      b.type = 'button';
      b.disabled = busy;
      b.addEventListener('click', onConfirm);
      hintsBody.append(b);
    } else if (!changed && !confirmed) {
      hintsBody.append(el('p', 'hints-empty', 'No changes proposed yet.'));
    }
    if (confirmed) {
      const done = el('p', 'hints-done');
      done.setAttribute('role', 'status');
      hintsBody.append(done);
      done.textContent = confirmedMessage;
    }
  }
  let confirmedMessage = '';

  function showError(err: any, { retryable = true } = {}) {
    setBusy(false);
    setStatus(describeError(err, fallbackEmail));
    if (err.endsSession) {
      ended = true;
      restart.hidden = false;
    }
    if (err.code === 'not_found') {
      ended = true;
    }
    input.disabled = busy || ended;
    sendBtn.disabled = busy || ended;
    if (err.code === 'rate_limited' && err.retryAfter) {
      input.disabled = true;
      sendBtn.disabled = true;
      setTimeout(() => setBusy(false), Math.min(err.retryAfter, 120) * 1000);
    }
    retry.hidden = !(retryable && err.code === 'upstream_unavailable');
  }

  function endSession(message?: string) {
    ended = true;
    restart.hidden = false;
    if (message) setStatus(message);
    setBusy(false);
    renderHints();
  }

  function applyView(v: any) {
    sessionId = v.session_id ?? sessionId;
    fallbackEmail = v.fallback_email || fallbackEmail;
    saved = v.hints || [];
    proposed = v.proposed_hints || saved;
    if (typeof v.turns_left === 'number') turnsLeft = v.turns_left;
    if (v.entity?.name) entityName = v.entity.name;
    renderTurns();
  }

  async function start() {
    transcript.replaceChildren();
    notices.replaceChildren();
    ended = false;
    confirmed = false;
    restart.hidden = true;
    retry.hidden = true;
    setStatus('Starting…');
    setBusy(true);
    try {
      let v: any = null;
      const prior = safeGet();
      if (prior) {
        try {
          v = await api.get(prior);
        } catch {
          v = null; // fall through to a fresh session
        }
      }
      if (v) {
        applyView(v);
        for (const m of v.messages || []) addMessage(m.role === 'user' ? 'user' : 'assistant', m.text);
        if (v.status === 'ended') ended = true;
      } else {
        v = await api.start(type, slug);
        applyView(v);
        addMessage('assistant', v.greeting || 'Hello!');
      }
      safeSet(sessionId);
      setStatus(entityName ? `Updating: ${entityName}` : '');
      if (ended) endSession('This conversation has ended.');
      else {
        renderHints();
        setBusy(false);
        input.focus();
      }
    } catch (err) {
      renderHints();
      showError(err);
      if ((err as any).code === 'upstream_unavailable' || (err as any).code === 'network' || (err as any).code === 'rate_limited') {
        retry.hidden = false;
      }
    }
  }

  async function onSend() {
    const text = input.value.trim();
    if (!text || busy || ended || !sessionId) return;
    retry.hidden = true;
    setStatus('');
    setBusy(true);
    addMessage('user', text);
    try {
      const r = await api.send(sessionId, text);
      input.value = '';
      addMessage('assistant', r.reply);
      proposed = r.proposed_hints || proposed;
      if (typeof r.turns_left === 'number') turnsLeft = r.turns_left;
      renderTurns();
      renderNotices(r.notices);
      confirmed = false;
      renderHints();
      if (r.status === 'ended') {
        endSession(r.ended_reason === 'turn_cap' ? 'This conversation has reached its limit.' : 'This conversation has ended.');
      } else {
        setBusy(false);
        input.focus();
      }
    } catch (err) {
      // The server drops the turn on failure; remove our optimistic echo.
      transcript.lastElementChild?.remove();
      showError(err);
      renderHints();
    }
  }

  async function onConfirm() {
    if (!sessionId || busy) return;
    setBusy(true);
    try {
      const r = await api.confirm(sessionId);
      saved = r.hints || saved;
      if (r.saved) {
        proposed = saved;
        confirmed = true;
        confirmedMessage = `Hints saved. They take effect after the ${r.effective || 'next scheduled scrape'}.`;
      } else {
        confirmed = true;
        confirmedMessage = 'No changes to save: the saved hints already match.';
      }
      renderHints();
      setBusy(false);
    } catch (err) {
      showError(err);
      renderHints();
    }
  }

  function safeGet(): string | null {
    try { return sessionStorage.getItem(storeKey); } catch { return null; }
  }
  function safeSet(id: string | null) {
    try { id ? sessionStorage.setItem(storeKey, id) : sessionStorage.removeItem(storeKey); } catch { /* ignore */ }
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); onSend(); });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); onSend(); }
  });
  restart.addEventListener('click', () => { safeSet(null); sessionId = null; start(); });
  retry.addEventListener('click', () => {
    retry.hidden = true;
    if (!sessionId) { start(); return; }
    setStatus('');
    if (input.value.trim()) onSend();
  });

  start();
}
