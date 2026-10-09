"""Update-agent sidecar: a small HTTP service for the site's update chat.

Requires the optional ``sidecar`` extra (starlette, uvicorn). The chat only
ever produces scraping *hints*; it never supplies published facts.
"""
