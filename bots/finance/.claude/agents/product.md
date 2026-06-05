---
name: "finance-product"
description: "Product owner for bots/finance/. Extends common product agent."
model: sonnet
color: purple
memory: project
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/product.md` first.

**Live:** Monobank sync (hourly) · `/balance` · `/stats [period] [mode]` · `/budget` · REST API · Hermes skill

**Bugs (fix first):**
| Issue | Severity |
|---|---|
| Multi-currency totals summed without conversion | High |
| `/sync` blocks event loop (`time.sleep`) | High |
| `is_fop` overwritten on every sync | Medium |
| Category emoji drift — most show 📦 | Medium |

Specs: `specs/NNN-slug/spec.md` (repo root).
