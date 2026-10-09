"""Per-entity scraping hints: schema, validation, storage, archiving writer."""

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
    "CHANGES_KEY", "HintWriter", "actor_for",
]
