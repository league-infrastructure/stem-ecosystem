---
id: '051'
title: Fix wheel smoke test
status: planning-docs
branch: sprint/051-fix-wheel-smoke-test
use-cases:
- SUC-001
issues:
- 91-wheel-smoke-test-fails-since-roster-moved-to-bucket.md
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 051: Fix wheel smoke test

## Goals

Make the "Scraper wheel smoke test" CI job pass again (issue 91).

## Problem

Since sprint 042 the roster, history, hints and logs stores default to the bucket, so the offline smoke test fails with missing DO_SPACES_* credentials.

## Solution

Point every store env var at local temp dirs and seed a one-partner local roster in `scraper/dev/wheel_smoke_test.py` and the workflow.

## Success Criteria

Smoke script passes locally and in CI with no credentials or network.

## Scope

In: `scraper/dev/wheel_smoke_test.py`, `.github/workflows/wheel-smoke.yml`. Out: scraper runtime code.

## Tickets

| # | Title | Depends on |
|---|-------|-----------|
| 001 | Fix wheel smoke test | none |
