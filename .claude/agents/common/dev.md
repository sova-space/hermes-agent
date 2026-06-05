---
name: "dev"
description: "Common developer — shared Python/FastAPI/PTB conventions. Extended by project-specific dev agents."
model: sonnet
color: blue
---

- Python 3.12+, type hints everywhere, `ruff check` + `ruff format` before commit
- `structlog` only — `log = structlog.get_logger(__name__)`, snake_case events
- Named constants, no magic strings. Files under 300 lines.
- Catch specific exceptions only; bare `except Exception` only in health checks with `log.exception(...)`
- Secrets in Railway Variables only — never in code
- Alembic: `batch_alter_table`, real `downgrade()`, `server_default` for new NOT NULL columns
