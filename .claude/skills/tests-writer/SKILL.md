---
name: tests-writer
description: Use before writing any test in bots/finance/. Fixtures, patterns, assertion rules.
version: 1.1.0
---

## Fixtures (from `tests/conftest.py`)

| Fixture | Gives you |
|---|---|
| `session` | SQLite in-memory `Session`, schema created fresh each test |
| `client` | `httpx.AsyncClient` wired to FastAPI app |

`conftest.py` sets all required env vars via `monkeypatch` (autouse). Never set env vars in test files.

## Patterns

```python
# Query test
def test_balances(session):
    session.add(Account(monobank_id="x", name="Black", currency="UAH", balance=100.0))
    session.commit()
    result = get_account_balances(session)
    assert result[0]["balance"] == 100.0

# Handler test — call directly, never start polling
async def test_owner_gate(session):
    message = MagicMock()
    message.from_user.id = 999  # not owner
    message.answer = AsyncMock()
    await cmd_status(message)
    message.answer.assert_not_called()

# Health
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
```

After a write: call `session.expire_all()` before re-reading. Assert specific fields, not full dicts.

**Never mock the DB** — use in-memory SQLite. Mock/real divergence has caused production bugs.
