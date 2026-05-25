# Hermes PI — Spec-Driven Setup Brief for Claude Code

You are helping Nazar (Lviv, Ukraine; Senior SDET; Python primary) deploy a personal AI agent called **Hermes PI** to Railway. We are using **Spec-Driven Development** via GitHub Spec Kit. The spec is the source of truth; code is generated from it.

This document is the **bootstrap brief**. It tells you how to set up the SDD workflow, write the constitution, and what to specify for each feature. The actual specs, plans, and tasks live in `specs/` and are produced by `/speckit.*` slash commands inside Claude Code — not in this file.

---

## Part 1 — Context & guardrails

### What already exists (do not modify)

- **Hermes Agent upstream** (do not vendor, do not fork): `https://github.com/NousResearch/hermes-agent`
- **Railway template we deploy**: `mazshakibaii/hermes-agent-railway` via `https://railway.com/deploy/hermes-agent-with-official-dashboard`
- **Volume mount path** (fixed by template): `/root/.hermes`
- **Legacy fork to DELETE at the end**: `sova-claw/hermes-agent`

### Repository structure (two repos, deliberately)

- **`hermes-pi`** — this repo. Specs, Hermes custom skills, Dockerfile, Railway config. Connected to Railway for autodeploy.
- **`hermes-pi-vault`** — separate private repo containing Nazar's Obsidian vault. Cloned by the `obsidian-vault` skill at runtime; never directly part of the Railway build.

Two repos are used so that the agent's GitHub MCP token (Feature 004) can be scoped to `hermes-pi` only, with no access to vault contents. The vault skill uses a separate, more narrowly scoped token (`HERMES_VAULT_GIT_TOKEN`) for vault read/write. This separation of concerns is intentional: a prompt-injection attack that compromises one token cannot reach the other repo.

### Final stack

| Layer | Choice |
|---|---|
| Agent runtime | Hermes Agent via Railway template |
| LLM | OpenRouter |
| Messaging | Telegram + Slack (Socket Mode) |
| Notion | Official remote MCP `https://mcp.notion.com/mcp` |
| Obsidian | Private GitHub repo `hermes-pi-vault` cloned to `/root/.hermes/vault` |
| Self-update | Railway autodeploy on push to `main` of `hermes-pi`; agent edits via GitHub MCP, PR-only |
| Persistence | Railway volume at `/root/.hermes` |
| SDD tooling | GitHub Spec Kit installed as Claude Code skills |

### Hard rules (never violate)

1. **Specs before code.** No file under `skills/`, no Dockerfile changes, no railway.toml changes without a corresponding `specs/NNN-feature/spec.md` and `plan.md` merged first.
2. **One feature per branch.** Branches named `NNN-short-slug` (e.g. `003-obsidian-skill`). Spec Kit uses the branch name to pick the active spec.
3. **Never push to `main` directly.** All changes via PR, even when working alone. The branch protection rule will reject direct pushes anyway.
4. **No secrets in repo, ever.** All tokens live in Railway env vars or the Hermes dashboard. If you see a token in a file, stop and tell Nazar.
5. **Free trial budget is real.** Railway $5 trial credit lasts ~2–3 weeks of always-on Hermes. Flag cost impact before adding a second service or heavy workload.
6. **Verify before assuming.** MCP server package names, Hermes config schema, and Railway template behavior may have shifted since this brief was written (May 25, 2026). Read the actual Hermes docs at `https://hermes-agent.nousresearch.com/docs` before touching config.
7. **Token separation is mandatory.** The GitHub PAT used by the agent for code changes (Feature 004) must NOT have any access to `hermes-pi-vault`. The vault skill (Feature 003) uses a different token with access to the vault repo only.

---

## Part 2 — Bootstrap (do this once, before any feature)

### Step 1: Verify Phase 0 prerequisites with Nazar

These are credentials Nazar must create himself. Do NOT ask him to paste them into your chat. He pastes them into Railway env vars or the Hermes dashboard directly. Confirm each is done:

- [ ] Railway account signed up via GitHub (Full Trial, not Limited)
- [ ] OpenRouter API key created
- [ ] Telegram bot token from `@BotFather`
- [ ] Telegram user ID from `@userinfobot`
- [ ] Slack app with Socket Mode enabled — bot token (`xoxb-`) and app token (`xapp-`)
- [ ] **Two GitHub fine-grained PATs, separately scoped:**
  - `HERMES_VAULT_GIT_TOKEN` — scoped to `hermes-pi-vault` only, `contents:write`
  - `HERMES_GITHUB_PAT` — scoped to `hermes-pi` only, `contents:write` + `pull_requests:write`
- [ ] Two empty GitHub repos created (private): `hermes-pi` and `hermes-pi-vault`
- [ ] Existing Obsidian vault pushed to `hermes-pi-vault`

Do not proceed until all are confirmed.

### Step 2: Initialize the project with Spec Kit

In the working directory (which is the local clone of `hermes-pi`), run:

```bash
uvx --from git+https://github.com/github/spec-kit.git specify init . \
  --integration claude \
  --integration-options="--skills"
```

This installs Spec Kit's slash commands as Claude Code skills and creates the `.specify/` folder structure.

Verify the install:
- `.specify/memory/` exists
- `.claude/skills/` contains the speckit skills
- Slash commands `/speckit.constitution`, `/speckit.specify`, `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze`, `/speckit.implement` are available

### Step 3: Write the constitution

Run `/speckit.constitution` and provide the principles from **Part 3** of this brief verbatim. Review the generated `.specify/memory/constitution.md` before committing.

### Step 4: Initial commit and push

```bash
git init
git add .
git commit -m "chore: bootstrap hermes-pi with spec-kit"
git branch -M main
git remote add origin git@github.com:<nazar-username>/hermes-pi.git
git push -u origin main
```

Enable branch protection on `main`: require PR, require 1 review (Nazar himself), no direct pushes, no force pushes.

---

## Part 3 — The constitution (provide this to `/speckit.constitution`)

The system shall be deployable to Railway free trial without additional paid services for the first 30 days.

The system shall use the Hermes Agent runtime from Nous Research as deployed by the `mazshakibaii/hermes-agent-railway` template. Hermes itself shall not be forked or vendored — only configured.

The system shall use two GitHub repositories: `hermes-pi` for code, specs, and deploy configuration, and `hermes-pi-vault` for the Obsidian vault. The two repositories shall be accessed by separate Personal Access Tokens with non-overlapping scopes, so that compromise of one token cannot affect the other repository.

All persistent state shall live under the Railway volume mounted at `/root/.hermes`. No application state shall be written outside this path.

All credentials shall be provided via Railway environment variables or the Hermes dashboard. No credential shall be committed to either repository, ever, including in `.env.example` files (use placeholder names only like `<your-token-here>`).

All external integrations shall be added as MCP servers configured through the Hermes dashboard or `config.yaml`, not as bespoke Python integrations. Exception: when an MCP server does not exist for a required capability (currently: Obsidian vault via Git), a Hermes skill shall be written instead.

All code changes shall flow through pull requests against the `main` branch of `hermes-pi`. The branch protection rule shall reject direct pushes. This applies to both human commits and agent-proposed commits.

When the agent proposes changes to the `hermes-pi` repository, it shall create a branch named `hermes-proposal/<short-slug>` and open a pull request. It shall never push to `main` directly. The GitHub Personal Access Token used by the agent shall be scoped to `pull_requests:write` and `contents:write` on `hermes-pi` only, with branch protection enforcing review before merge.

Every feature shall begin with `/speckit.specify`, followed by `/speckit.clarify` to resolve ambiguities, then `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze`, and only then `/speckit.implement`. No code shall be written outside this loop.

Every feature shall produce its artifacts under `specs/NNN-feature-slug/` matching the active Git branch name. Branches shall be named `NNN-short-slug` where NNN is a zero-padded three-digit ordinal.

Python code shall target Python 3.11+ and pass `ruff check` and `ruff format` with default rules before merge. Type hints are required on all function signatures.

When in doubt about Hermes Agent behavior, the system shall consult `https://hermes-agent.nousresearch.com/docs` rather than relying on prior knowledge.

The free-trial cost budget shall be considered a hard constraint. Any feature that would add a second always-on Railway service shall be explicitly approved by Nazar with a documented cost impact before being specified.

---

## Part 4 — Features to specify (in order)

For each feature, walk Nazar through the seven-command loop. Pause for his review after each command output. Do not chain commands.

### Feature 001 — Railway bootstrap deployment

**Branch:** `001-railway-bootstrap`

**`/speckit.specify` seed input:**
> Deploy the Hermes Agent to Railway using the `mazshakibaii/hermes-agent-railway` template. Configure OpenRouter as the LLM provider, Telegram as a messaging channel restricted to Nazar's user ID, and Slack via Socket Mode. Attach a persistent volume at `/root/.hermes`. The dashboard must be password-protected. Acceptance: both Telegram and Slack receive a reply within 5 seconds of a message; after a manual Railway redeploy, session history persists.

**Note for Claude Code:** This feature involves clicking buttons in Railway and the Hermes dashboard, not writing code. The `spec.md` should document the exact env vars, dashboard fields, and verification steps. The `tasks.md` will be a checklist Nazar executes, not commands you run. `/speckit.implement` becomes "verify each task is done."

### Feature 002 — Notion MCP integration

**Branch:** `002-notion-mcp`

**`/speckit.specify` seed input:**
> Add the official Notion remote MCP server (`https://mcp.notion.com/mcp`) to the Hermes configuration. Authenticate via OAuth on first use. Grant the integration access to a narrow set of pages chosen by Nazar (not the entire workspace). Acceptance: from Telegram, ask "list my Notion pages" and receive the correct list. Ask "create a Notion page titled 'Hermes PI test' under [page name Nazar specifies]" and verify it appears in Notion within 10 seconds.

**Note for Claude Code:** This is also configuration, not code. The deliverable is a documented `config.yaml` snippet plus a verification log. Use `/speckit.clarify` to ask Nazar which pages should be shared with the integration before drafting the plan.

### Feature 003 — Obsidian vault skill

**Branch:** `003-obsidian-skill`

**This is the first feature that involves writing code.** Take it seriously. Use all seven Spec Kit commands including `/speckit.clarify`, `/speckit.checklist`, and `/speckit.analyze`.

**`/speckit.specify` seed input:**
> Write a Hermes skill named `obsidian-vault` that gives the agent read and write access to Nazar's Obsidian vault, stored in the private GitHub repo `hermes-pi-vault`. The skill must:
> - Clone the repo to `/root/.hermes/vault` on first use if the directory is empty
> - Pull from origin before every read operation
> - Provide tools: `list_notes(folder)`, `read_note(path)`, `write_note(path, content)`, `append_to_note(path, content)`, `search_notes(query)`
> - On every write, commit with message `chore(hermes): <action> <filename>` and push to origin
> - Use a GitHub PAT from env var `HERMES_VAULT_GIT_TOKEN` for auth — this token must have access to `hermes-pi-vault` only
> - Constrain writes to a configurable allowlist of folders (default: `agent-inbox/` and `daily/`) — never write to `_templates/` or `_archive/`
>
> Acceptance: agent can list, read, search, and write to allowlisted folders; writes appear in the GitHub repo within 5 seconds; attempting to write outside the allowlist returns a clear error.

**`/speckit.clarify` must resolve at minimum:**
- How are merge conflicts handled when Nazar edits the same note from his laptop? (Likely answer: agent always rebases on pull; if conflict, abort write and surface to Nazar via the messaging channel.)
- What happens if the GitHub PAT is missing or expired? (Likely answer: skill fails fast with a clear error; does not silently degrade.)
- Should the agent's commits be signed? (Likely answer: yes if Nazar wants attestation, no otherwise — get his call.)
- What's the rate limit policy? Pulling on every read is expensive. (Likely answer: cache for N minutes, configurable.)
- File-locking / concurrency — what if two messages arrive that both write to the vault? (Likely answer: serialize writes with a file lock.)

**`/speckit.plan` must specify:**
- Python file layout under `skills/obsidian-vault/`
- Exact dependencies (likely just `gitpython` or shelling out to `git`)
- Error taxonomy and how errors surface to the user

### Feature 004 — Self-improvement loop via GitHub MCP

**Branch:** `004-self-update-loop`

**`/speckit.specify` seed input:**
> Add the official GitHub MCP server to Hermes configuration with the `HERMES_GITHUB_PAT` token scoped to `pull_requests:write` and `contents:write` on the `hermes-pi` repo only — explicitly NOT including `hermes-pi-vault`. Add a system-prompt addition (or SOUL.md entry) instructing the agent that any change to `hermes-pi` must be done by creating a branch named `hermes-proposal/<slug>` and opening a PR — never pushing to `main`. Acceptance: ask the agent "propose adding a cron job that posts a daily summary to Slack at 9am Kyiv time"; verify a branch and PR appear in `hermes-pi` on GitHub within 30 seconds; manually review and merge; verify Railway auto-redeploys; verify the cron job runs at the next 9am Kyiv. Additionally verify: the agent cannot list, read, or write anything in `hermes-pi-vault` using this token.

**`/speckit.clarify` must resolve:**
- Exact GitHub MCP server package name and version (verify against `https://github.com/modelcontextprotocol/servers` at time of implementation)
- Where the "never push to main" instruction lives (system prompt? SOUL.md? config.yaml comment?)
- What happens if the agent attempts a direct push despite the instruction — does branch protection alone catch it, or do we need a defensive check in the skill?

### Feature 005 onwards — TBD by Nazar

Future features (cron jobs, weekly Notion review, Slack daily digest, etc.) follow the same pattern. Nazar adds them as he discovers what he wants.

---

## Part 5 — Operating rules during execution

1. **One feature, one branch, one PR.** Never mix features.
2. **Run `/speckit.analyze` before `/speckit.implement`.** It catches inconsistencies between constitution / spec / plan / tasks. Treat its output as a blocking gate.
3. **Pause after every Spec Kit command for Nazar's review.** Do not chain commands. He's learning the workflow too.
4. **Specs are living documents.** If `/speckit.implement` reveals that the plan was wrong, update the plan first, get Nazar's approval, then continue.
5. **When Hermes docs and this brief disagree, the docs win.** This brief is a snapshot from May 25, 2026.
6. **Push back if something looks wrong.** Specs are checked by humans. If a spec asks you to do something dangerous (commit a secret, push to main, exceed the cost budget, give one token access to both repos), refuse and surface it.

---

## Part 6 — Done definition

Hermes PI is "done" (for this initial scope) when:

1. Features 001–004 are all merged to `main`.
2. Asking the bot via Telegram "summarize what you can do" yields: Telegram, Slack, Notion read/write, Obsidian vault read/write, GitHub PR creation.
3. The `hermes-pi` repo contains four `specs/NNN-*/` folders, each with a complete spec + plan + tasks + analyze report.
4. The `sova-claw/hermes-agent` legacy fork is deleted from GitHub.
5. A `README.md` in `hermes-pi` documents the deploy, the constitution location, the two-repo structure, and how to add Feature 005+.

Ship a Notion page (via the bot, as a final test) titled "Hermes PI — operating manual" that summarizes the constitution and the four features for Nazar's future reference.