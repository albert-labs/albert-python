# CLAUDE.md

@AGENTS.md
@OPINIONS.md

## Key Guidelines

- **Always use keyword-only arguments (`*`) for public methods** on collections, resources, and clients (`def method(self, *, ...)`). See `OPINIONS.md`.
- **Retries and timeouts are session-owned** (`DEFAULT_TIMEOUT`, `RETRYABLE_STATUSES` in `albert.core.session`): read-only calls issued with POST pass `retry_safe=True`, mutating calls are never marked retry-safe, and session-constructing entry points default `timeout=DEFAULT_TIMEOUT` (never `None`). See "Retries and timeouts" in `AGENTS.md`.

