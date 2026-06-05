---
name: tests-runner
description: Use before running tests in bots/finance/. Commands, env setup, reading failures.
version: 1.1.0
---

Always run from `bots/finance/`:

```bash
uv run pytest          # full suite
uv run pytest -x       # stop on first failure
uv run pytest -v --lf  # verbose, only last failures
uv run pytest tests/unit/test_queries.py::test_name
```

## Reading failures

- **Import error** — missing env var; check `.env.test` covers all `Settings` fields
- **`OperationalError`** — schema mismatch; in-memory SQLite reflects current models, not migrations
- **`assert status_code` fails** — print `resp.json()` to see error body
- **Handler not triggered** — handlers are called directly (mocked Message), not via polling

Run full suite before marking done: `uv run pytest -q`. Report the count.
