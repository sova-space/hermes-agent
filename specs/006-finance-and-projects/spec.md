# Spec 006: Finance skill + project context + ruff

## Items

### 1. Project context skill
Track the active project (hermes-agent / hermes-finance / coxit / personal) in a state
file at `/data/.hermes/current_project.txt`. Hermes tags relevant output with the active
project and responds to `/project` commands to switch or inspect it.

**Acceptance criteria:**
- `/project` → prints current project
- `/project <name>` → switches, confirms
- `/project list` → lists all known projects
- State persists across container restarts (file lives on the volume)

### 2. Finance skill
Hermes can answer money questions by calling the Monobank Finance API at
`https://finance-api-production-4d72.up.railway.app`. No custom code — Hermes uses its
built-in HTTP tools per the SKILL.md contract.

**Acceptance criteria:**
- "how much money on accounts?" → Hermes calls GET /accounts, returns balances
- "show my spending this month" → calls GET /transactions/spending?period=this_month
- `/finance` Telegram topic added (thread ID to be filled in after topic creation)

### 3. Ruff hook — hermes-finance
`hermes-finance/.claude/settings.json` gains a pre-commit hook that runs
`uv run ruff check . && uv run ruff format --check .` before any `git commit`.

### 4. Ruff config + hook — hermes-agent
`hermes-agent/ruff.toml` added. Same pre-commit hook wired in `.claude/settings.json`.

## Open questions
- Finance Telegram topic thread ID: `FILL_IN` — create topic in Hermes PI supergroup first.
