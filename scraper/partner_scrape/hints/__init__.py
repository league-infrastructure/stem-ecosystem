"""Per-entity scraping hints: schema, validation, storage, archiving writer."""

from partner_scrape.hints.consume import EVENT_ROLES, context_hints, exclude_matcher, hints_fingerprint, load_hints, page_hint_urls
from partner_scrape.hints.model import KINDS, PAGE_ROLES, empty_hints, hints_of
from partner_scrape.hints.store import HintStore, hints_key
from partner_scrape.hints.validate import (
    HintError,
    domains_of,
    on_domain,
    validate_hint,
    validate_hints,
)
from partner_scrape.hints.writer import CHANGES_KEY, HintWriter, actor_for

__all__ = [
    "KINDS", "PAGE_ROLES", "empty_hints", "hints_of", "HintStore", "hints_key",
    "HintError", "domains_of", "on_domain", "validate_hint", "validate_hints",
    "EVENT_ROLES", "context_hints", "exclude_matcher", "hints_fingerprint", "load_hints",
    "page_hint_urls",
    "CHANGES_KEY", "HintWriter", "actor_for",
]
