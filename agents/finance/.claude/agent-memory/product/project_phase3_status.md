---
name: project-phase3-status
description: Phase 3 new domains (Debt, Goals, Trips, Buy List, Forecast) — spec written, pending architect review before dev starts
metadata:
  type: project
---

Phase 3 spec written at `specs/010-phase3-new-domains/spec.md`. Phases 1 and 2 are complete (4 bug fixes + bot redesign with Mini App button). 40/40 tests passing.

**Why:** Phase 3 is the next planned milestone. The Mini App (Phase 7) and proactive notifications (Phase 8) both depend on these domains existing.

**How to apply:** When dev asks what to build next, Phase 3 is the answer. Spec must go through architect feasibility review (OQ1–OQ6) before dev starts, especially OQ1 (auth module placement) and OQ2 (Goals FK strategy).

Key open questions blocking dev:
- OQ1: Where does `verify_webapp_user` live (`core/auth/webapp.py` proposed)?
- OQ2: Goals progress — account FK (automatic) vs manual `current_amount`?
- OQ3: Forecast variable spend projection method (run-rate vs historical)?
- OQ4: Forecast multi-account aggregation strategy?

Migration sequence: 0007 is last migration. Next is 0008 (all Phase 3 tables in one migration).

See also: [[project-phase2-complete]]
