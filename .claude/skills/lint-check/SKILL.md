---
name: lint-check
description: Run ruff check and format on Python files. Invoke before committing any Python changes.
model: haiku
version: 1.0.0
---

# Lint Check

Run from the project root. Fix every failure before moving on.

## 1. Ruff auto-fix

```bash
uv run ruff check --fix .
```

## 2. Ruff format

```bash
uv run ruff format .
```

## 3. Verify clean

```bash
uv run ruff check .
```

Zero violations required.

## Rules

- Never use `# noqa` to silence lint — fix the code.
- Type hints required on all function signatures.
- Report results as: `lint ✓ | format ✓` or list failures.
