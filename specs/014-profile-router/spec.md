# Spec 014: Profile Router

## Problem

"Profile," "project," and "devops" are conflated in user-facing language but mean different things in code:

- `/project <name>` (`hermes/plugins/agent-silence/commands.py`) picks a **GitHub repo** for Doer — a standalone bot/service — to edit. It is not a persona switch.
- The only real **profile** (persona + domain tools + memory) is the finance conversational assistant (`bots/finance/finance_api/domains/assistant/loop.py`) — but it's reachable only by texting `@sova_finance_bot` directly. Hermes and `/project` never route to it.
- **Devops** is modeled as a selectable destination (a separate bot you dispatch to) when it's actually a **capability every profile carries** — for maintaining its own bot's code.

Net effect: there is no real profile-switching in Hermes, and a working dispatch substrate (`DoerGateway._discover_agent_urls`, which already discovers every `AGENT_*_URL`) sits half-used, hardwired to a single destination.

## Solution

Two moves, both building on what already exists:

### 1. Absorb Doer into Hermes

Doer's loop (`bots/doer/doer_api/agent/loop.py`) is generic — the same GitHub tools (`read_file` / `write_file` / `create_pr` / `merge_pr`) regardless of target repo, parameterized only by `PROJECTS[name].repo` (`bots/doer/doer_api/agent/projects.py`). It carries no domain logic, so folding it into Hermes does not violate the bot-independence rule (that rule protects *domain* logic — finance/wishlist tools that need their own DB/API access — not generic infrastructure).

Move the loop and its `PROJECTS`-style repo registry into Hermes as a built-in devops capability, scoped per profile. Retire `bots/doer/` as a standalone Railway service. Grep-verified: nothing outside `bots/doer/` calls its tools — nothing else to migrate.

### 2. Generalize dispatch for domain conversation

`DoerGateway._discover_agent_urls` (`hermes/plugins/agent-silence/doer.py:69-73`) already discovers every `AGENT_*_URL` (Finance is already registered there for command-silencing), but `dispatch()` is hardwired to POST only to `AGENT_DOER_URL` (`doer.py:53-65`, `config.py:23`).

Extend the discovery contract so each domain bot can register itself as a profile owner — e.g. `GET /bot/profile` returning `{name, description, dispatch_path}`, alongside the existing `GET /bot/commands`. Replace the hardwired dispatch URL with routing-by-profile-owner: domain Q&A goes to the owning bot's assistant; devops requests stay in Hermes.

`/profile <name>` (repurposing `/project`) then splits by intent:

- **Devops intent** ("fix a bug in the finance bot") → handled by Hermes itself, via its built-in generic GitHub loop scoped to that profile's repo
- **Domain intent** ("what did I spend on food?") → routed to the profile-owning bot's own assistant, which holds the data and domain tools

## Architecture

```
                    Telegram (supergroup, topic-routed)
                                  │
                                  ▼
            ┌──────────────────────────────────────────────┐
            │   Hermes (orchestrator)                      │
            │   /profile <name>                            │
            │                                              │
            │   ├─ devops capability (BUILT IN — absorbed  │
            │   │  from Doer's generic GitHub loop;        │
            │   │  scoped to the selected profile's repo   │
            │   │  via the PROJECTS-style registry)        │
            │   │                                          │
            │   └─ domain conversation → routes to the     │
            │      profile-owning bot's assistant          │
            └──────────────────────┬───────────────────────┘
                                   │  (only for domain Q&A —
                                   │   devops stays in Hermes)
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
   finance bot's              wishlist bot's              <next> bot's
   assistant                  assistant                   assistant
   (own tools + memory,       (own tools + memory,        (own tools + memory,
    own DB — domain logic      own DB — domain logic       own DB — domain logic
    stays where the data is)   stays where the data is)    stays where the data is)
```

## Acceptance criteria

- [ ] `/profile finance` + a domain question routes to the finance bot's conversational assistant (not through any GitHub-editing path)
- [ ] `/profile finance` + a devops-flavored request ("fix this bug") runs Hermes' built-in loop scoped to `sova-claw/hermes-finance` — same end capability Doer provides today, no separate service in the hop
- [ ] `bots/doer/` is retired as a standalone Railway service with zero loss of capability (grep-verified: no other callers)
- [ ] Profile discovery is generic (`AGENT_*_URL` + `GET /bot/profile`) — adding a new domain bot doesn't require touching the router's code
- [ ] Active-profile state migrates cleanly from `/project` to `/profile` (migration note or compatibility alias for existing users)

## Cite for implementers

- `hermes/plugins/agent-silence/{commands.py:90-160, doer.py, config.py:23}`
- `bots/doer/doer_api/agent/{loop.py, projects.py, tools.py}`
- `bots/finance/finance_api/domains/assistant/loop.py`
- `bots/finance/finance_api/domains/bot/handlers.py:13,339-356`

## Out of scope

- Domain tools/memory for new profiles beyond finance and wishlist (future specs, per profile)
- Subagent delegation within a profile's devops loop (future — Doer's loop today is single-pass)
