---
name: project-miniapp-status
description: Mini app is a single miniapp.html (vanilla JS, 8 tabs), deployed and working — focus now on usability improvements
metadata:
  type: project
---

Mini app is `finance_api/static/miniapp.html` — 427-line vanilla JS + inline CSS, served as a static file from FastAPI. Deployed and working. No React/Vite build.

**Current tabs (8):** Home, Pockets, Debt, Goals, Trips, Buy List, Forecast, Settings

**Why it feels ugly:** too many tabs, spending breakdown is plain text rows with no visual hierarchy, all cards look the same regardless of importance.

**Two options discussed for improvement:**
1. Polish the single-file approach — trim to 3-4 tabs, improve Home to look like a real dashboard (big balance number, spending bars, better account list). Fast to ship.
2. Rebuild as React/Vite TWA — proper component structure, real design system, better ceiling but 1-2 week investment.

**Decision not yet made** — user hasn't chosen direction yet.

**How to apply:** When asked about mini app work, confirm which direction (polish vs rebuild) before writing code. Tab reduction and Home screen redesign are the highest-leverage changes either way.

See also: [[project-usability-focus]]
