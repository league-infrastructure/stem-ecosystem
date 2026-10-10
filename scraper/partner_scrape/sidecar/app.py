"""Starlette app for the update-chat API (contract: sprint 044 architecture).

This is the composition root: it wires routes to the resolver, session
store, agent, hint writer and transcript writer. It holds no model or
storage logic of its own. Endpoints are plain ``def`` so blocking store I/O
runs in Starlette's threadpool.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from importlib import metadata
from typing import Any, Callable

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from partner_scrape.hints import HintError, HintStore, HintWriter, actor_for
from partner_scrape.sidecar.agent import Agent, ContextBuilder, EchoAgent, ToolUseAgent
from partner_scrape.sidecar.config import SidecarConfig
from partner_scrape.sidecar.limits import Limits, RateLimited, TurnstileVerifier
from partner_scrape.sidecar.llm import GuardClient, LLMUnavailable
from partner_scrape.sidecar.resolver import ENTITY_TYPES, EntityResolver
from partner_scrape.sidecar.sessions import Session, SessionStore, utcnow
from partner_scrape.sidecar.transcripts import TranscriptWriter
from partner_scrape.storage import Store

log = logging.getLogger(__name__)

EFFECTIVE = "next scheduled scrape"

#: error code -> HTTP status (the API contract)
ERROR_STATUS = {
    "bad_request": 400,
    "not_found": 404,
    "session_expired": 410,
    "session_ended": 409,
    "message_too_long": 413,
    "rate_limited": 429,
    "spend_cap_reached": 503,
    "turnstile_failed": 403,
    "upstream_unavailable": 502,
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = ERROR_STATUS[code]
        self.headers = headers or {}


def _version() -> str:
    try:
        return metadata.version("partner-scrape")
    except metadata.PackageNotFoundError:
        return "unknown"


def client_ip(request: Request) -> str:
    """Caller IP: first X-Forwarded-For hop (Caddy sits in front), else the peer."""
    fwd = request.headers.get("x-forwarded-for", "")
    first = fwd.split(",")[0].strip()
    if first:
        return first
    return request.client.host if request.client else ""


def _body(request_json: Any) -> dict[str, Any]:
    if not isinstance(request_json, dict):
        raise ApiError("bad_request", "Request body must be a JSON object.")
    return request_json


class UpdateService:
    """Route handlers plus the collaborators they share."""

    def __init__(
        self,
        config: SidecarConfig,
        resolver: EntityResolver,
        hints: HintStore,
        writer: HintWriter,
        transcripts: TranscriptWriter,
        agent: Agent,
        sessions: SessionStore,
        guard: GuardClient | None = None,
        limits: Limits | None = None,
    ):
        self.limits = limits
        self.config = config
        self.resolver = resolver
        self.hints = hints
        self.writer = writer
        self.transcripts = transcripts
        self.agent = agent
        self.sessions = sessions
        self.guard = guard

    # -- helpers -----------------------------------------------------------
    def _session(self, session_id: str) -> Session:
        s = self.sessions.get(session_id)
        if s is None:
            raise ApiError(
                "session_expired",
                "This session has expired. Please start a new one.",
            )
        return s

    def _view(self, s: Session) -> dict[str, Any]:
        return {
            "session_id": s.id,
            "entity": s.entity.public(),
            "hints": self.hints.hints(s.entity.slug),
            "proposed_hints": s.proposed_hints,
            "limits": {
                "max_message_chars": self.config.max_message_chars,
                "max_turns": self.config.max_turns,
            },
            "turns_left": max(self.config.max_turns - s.user_turns, 0),
            "fallback_email": self.config.fallback_email,
            "greeting": (
                f"Hi! I can help point our scraper at the right pages for "
                f"{s.entity.name}, or tell it what to skip. I can't change "
                f"listing facts here; tell me where on your own website the "
                f"correct information lives."
            ),
        }

    def _upstream_error(self) -> ApiError:
        return ApiError(
            "upstream_unavailable",
            "Our assistant is temporarily unavailable, so nothing was changed. "
            f"Please try again in a few minutes or email {self.config.fallback_email}.",
        )

    @staticmethod
    def _guard_action(s: Session, verdict) -> str:
        """allow | redirect | end. Records the offense for non-legitimate verdicts.

        The first borderline, off-topic or injection-looking message is
        redirected; spam/abuse, a high-confidence injection or a second
        offense ends the session.
        """
        if verdict.legitimate:
            return "allow"
        s.guard_offenses += 1
        if (
            verdict.category in ("spam", "abuse")
            or (verdict.category == "injection" and verdict.confidence == "high")
            or s.guard_offenses >= 2
        ):
            return "end"
        return "redirect"

    def _redirect_message(self) -> str:
        return (
            "I can only help with pointing the scraper at the right pages on your "
            "website (and what part of a page to focus on), what to ignore, or a "
            "rebrand. I couldn't act on that last message. Which page or detail "
            "would you like me to look at?"
        )

    def _end_message(self, reason: str) -> str:
        if reason == "turn_cap":
            why = "We've reached the limit for this conversation."
        else:
            why = "I can't continue this conversation."
        return f"{why} Please email {self.config.fallback_email} for anything else."

    def _rate(self, fn, *args) -> None:
        try:
            fn(*args)
        except RateLimited as exc:
            raise ApiError(
                "rate_limited",
                "Too many requests. Please wait a bit and try again.",
                headers={"Retry-After": str(exc.retry_after)},
            ) from None

    def _check_spend(self) -> None:
        if self.limits is not None and self.limits.spend.cap_reached():
            raise ApiError(
                "spend_cap_reached",
                "Our assistant has reached its daily limit. Please try again "
                f"tomorrow or email {self.config.fallback_email}.",
            )

    def _record_spend(self, usage: list[dict[str, Any]]) -> None:
        if self.limits is not None and usage:
            self.limits.spend.record(usage)

    # -- handlers ----------------------------------------------------------
    def healthz(self, request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": _version()})

    def start(self, request: Request) -> JSONResponse:
        data = _body(_read_json(request))
        type_, slug = data.get("type"), data.get("slug")
        if type_ not in ENTITY_TYPES or not isinstance(slug, str) or not slug:
            raise ApiError(
                "bad_request",
                f"'type' must be one of {', '.join(ENTITY_TYPES)} and 'slug' a non-empty string.",
            )
        ip = client_ip(request)
        if self.limits is not None:
            if not self.limits.verify_turnstile(data.get("turnstile_token"), ip):
                raise ApiError("turnstile_failed", "Human verification failed. Please try again.")
            self._check_spend()
            self._rate(self.limits.check_session_start,
                       self.transcripts.ip_hash(ip), f"{type_}:{slug}")
        entity = self.resolver.resolve(type_, slug)
        if entity is None:
            raise ApiError(
                "not_found",
                f"We couldn't find that listing. Please email {self.config.fallback_email}.",
            )
        s = self.sessions.create(entity, self.transcripts.ip_hash(client_ip(request)))
        s.proposed_hints = self.hints.hints(entity.slug)
        self.transcripts.write(s)
        return JSONResponse(self._view(s), status_code=201)

    def get(self, request: Request) -> JSONResponse:
        s = self._session(request.path_params["session_id"])
        view = self._view(s)
        view["status"] = s.status
        view["messages"] = [{"role": m["role"], "text": m["text"]} for m in s.messages]
        return JSONResponse(view)

    def message(self, request: Request) -> JSONResponse:
        s = self._session(request.path_params["session_id"])
        data = _body(_read_json(request))
        text = data.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ApiError("bad_request", "'text' must be a non-empty string.")
        if len(text) > self.config.max_message_chars:
            raise ApiError(
                "message_too_long",
                f"Messages are limited to {self.config.max_message_chars} characters.",
            )
        with s.lock:
            if s.status != "active":
                raise ApiError("session_ended", self._end_message(s.ended_reason or "turn_cap"))
            self._check_spend()
            if self.limits is not None:
                self._rate(self.limits.check_message, s.ip_hash,
                           f"{s.entity.type}:{s.entity.slug}")
            spent_before = len(s.usage)
            try:
                return self._message_locked(s, text)
            finally:
                self._record_spend(s.usage[spent_before:])

    def _message_locked(self, s: Session, text: str) -> JSONResponse:
        ts = _stamp(self.sessions.clock())
        verdict = None
        if self.guard is not None:
            try:
                verdict = self.guard.classify(s.entity.name, s.messages, text)
            except LLMUnavailable as exc:
                log.warning("guard unavailable (session %s): %s", s.id, exc)
                raise self._upstream_error() from None  # fail closed
            if verdict.usage:
                s.usage.append(verdict.usage.to_dict())
        s.messages.append({"role": "user", "text": text, "ts": ts})
        if verdict is not None:
            action = self._guard_action(s, verdict)
            s.guard_log.append({
                "turn": s.user_turns, "category": verdict.category,
                "reason": verdict.reason, "confidence": verdict.confidence,
                "action": action,
            })
            if action == "redirect":
                log.info("guard redirected session %s: %s: %s", s.id,
                         verdict.category, verdict.reason)
                reply = self._redirect_message()
                if s.user_turns >= self.config.max_turns:
                    s.status, s.ended_reason = "ended", "turn_cap"
                    reply = f"{reply}\n\n{self._end_message('turn_cap')}"
                s.messages.append({"role": "assistant", "text": reply, "ts": ts})
                self.transcripts.write(s)
                return JSONResponse({
                    "reply": reply, "proposed_hints": s.proposed_hints,
                    "status": s.status, "ended_reason": s.ended_reason,
                    "turns_left": max(self.config.max_turns - s.user_turns, 0),
                    "notices": [],
                })
        if verdict is not None and not verdict.legitimate:
            s.status, s.ended_reason = "ended", "guard"
            s.guard_reason = f"{verdict.category}: {verdict.reason}"
            log.info("guard ended session %s: %s", s.id, s.guard_reason)
            reply = self._end_message("guard")
            s.messages.append({"role": "assistant", "text": reply, "ts": ts})
            self.transcripts.write(s)
            return JSONResponse({
                "reply": reply, "proposed_hints": s.proposed_hints,
                "status": s.status, "ended_reason": s.ended_reason,
                "turns_left": max(self.config.max_turns - s.user_turns, 0),
                "notices": [],
            })
        try:
            turn = self.agent.respond(s, text)
        except LLMUnavailable as exc:
            log.warning("agent unavailable (session %s): %s", s.id, exc)
            s.messages.pop()  # the turn did not happen; let the user retry
            raise self._upstream_error() from None
        s.usage.extend(u.to_dict() for u in turn.usage)
        reply, notices = turn.reply, list(turn.notices)
        if turn.proposed_hints is not None:
            s.proposed_hints = turn.proposed_hints
        if s.user_turns >= self.config.max_turns:
            s.status, s.ended_reason = "ended", "turn_cap"
            reply = f"{reply}\n\n{self._end_message('turn_cap')}"
        s.messages.append({"role": "assistant", "text": reply, "ts": ts})
        self.transcripts.write(s)
        return JSONResponse({
            "reply": reply,
            "proposed_hints": s.proposed_hints,
            "status": s.status,
            "ended_reason": s.ended_reason,
            "turns_left": max(self.config.max_turns - s.user_turns, 0),
            "notices": notices,
        })

    def confirm(self, request: Request) -> JSONResponse:
        s = self._session(request.path_params["session_id"])
        with s.lock:
            if s.status == "ended" and s.ended_reason == "guard":
                raise ApiError("session_ended", self._end_message("guard"))
            e = s.entity
            try:
                entry = self.writer.put_hints(
                    e.slug, s.proposed_hints, actor_for(s.id),
                    domains=e.domains, current_website=e.website,
                )
            except HintError as exc:
                raise ApiError("bad_request", str(exc)) from None
            s.confirmed = True
            self.transcripts.write(s)
        return JSONResponse({
            "saved": entry is not None,
            "hints": self.hints.hints(e.slug),
            "effective": EFFECTIVE,
        })


def _stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(request: Request) -> Any:
    raw = getattr(request.state, "raw_body", None)
    if raw is None:
        raise ApiError("bad_request", "Missing request body.")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ApiError("bad_request", "Request body is not valid JSON.") from None


def create_app(
    config: SidecarConfig,
    *,
    data_store: Store,
    history_store: Store,
    hints_store: Store,
    agent: Agent | None = None,
    guard: GuardClient | None = None,
    clock: Callable[[], datetime] = utcnow,
    fetcher: Any = None,
    turnstile: TurnstileVerifier | None = None,
) -> Starlette:
    """Build the app from explicit collaborators (tests pass fakes/LocalStores)."""
    service = UpdateService(
        config=config,
        resolver=EntityResolver(data_store),
        hints=HintStore(hints_store),
        writer=HintWriter(hints_store, history_store, fetcher=fetcher),
        transcripts=TranscriptWriter(history_store, config.ip_hash_salt),
        agent=agent or EchoAgent(),
        sessions=SessionStore(config.idle_minutes, clock),
        guard=guard,
        limits=Limits(config, history_store, clock, turnstile),
    )

    def error_response(err: ApiError) -> JSONResponse:
        return JSONResponse(
            {"error": {
                "code": err.code, "message": err.message,
                "fallback_email": config.fallback_email,
            }},
            status_code=err.status,
            headers=err.headers,
        )

    async def on_api_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, ApiError)
        return error_response(exc)

    async def on_http_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, HTTPException)
        if exc.status_code == 404:
            return error_response(ApiError("not_found", "No such endpoint."))
        return error_response(ApiError("bad_request", exc.detail or "Bad request."))

    def with_body(fn: Callable[[Request], JSONResponse]):
        # Read the body asynchronously, then run the blocking handler in the
        # threadpool.
        from starlette.concurrency import run_in_threadpool

        async def endpoint(request: Request) -> JSONResponse:
            request.state.raw_body = await request.body() if request.method == "POST" else None
            return await run_in_threadpool(fn, request)

        return endpoint

    routes = [
        Route("/healthz", with_body(service.healthz), methods=["GET"]),
        Route("/v1/sessions", with_body(service.start), methods=["POST"]),
        Route("/v1/sessions/{session_id}", with_body(service.get), methods=["GET"]),
        Route("/v1/sessions/{session_id}/messages", with_body(service.message), methods=["POST"]),
        Route("/v1/sessions/{session_id}/confirm", with_body(service.confirm), methods=["POST"]),
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=list(config.allowed_origins),
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
            max_age=600,
        )
    ]
    app = Starlette(
        routes=routes,
        middleware=middleware,
        exception_handlers={ApiError: on_api_error, HTTPException: on_http_error},
    )
    app.state.service = service
    return app


def create_app_from_env() -> Starlette:
    """Production factory (``uvicorn --factory partner_scrape.sidecar.app:create_app_from_env``)."""
    import os

    from partner_scrape import config as scraper_config

    from partner_scrape.sidecar.llm import AnthropicAgentClient, build_guard

    config = SidecarConfig.from_env(os.environ)
    data_store = scraper_config.get_data_store()
    history_store = scraper_config.get_history_store()
    hints_store = scraper_config.get_hints_store()
    agent = ToolUseAgent(
        AnthropicAgentClient(),
        ContextBuilder(data_store, history_store),
        fallback_email=config.fallback_email,
        saved_hints=HintStore(hints_store).hints,
    )
    return create_app(
        config,
        data_store=data_store,
        history_store=history_store,
        hints_store=hints_store,
        agent=agent,
        guard=build_guard(config.guard_backend, os.environ, model=config.openrouter_guard_model),
    )
