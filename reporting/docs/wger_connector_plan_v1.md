# wger connector plan v1

This document defines the bounded v1 role of **wger** inside Health Lab.

Core rules:
- wger is a **gym-domain source system / component**
- wger is **not** the architecture
- Health Lab keeps its own canonical schema, provenance rules, and agent-facing contracts
- manual structured gym logs remain the source-of-truth path for this doctrine interval

## Why keep a bounded wger surface in v1

wger remains a useful exploratory connector substrate because it is:
- open-source
- API-exposed
- more controllable as an integration substrate than a closed consumer UI
- aligned with the project thesis of agent-first health infrastructure over inspectable source systems

Those benefits justify a bounded prototype surface. They do **not** make wger the preferred flagship source of truth.

## v1 role

wger is a bounded exploratory non-flagship connector prototype.

Interpretation for this doctrine interval:
- Garmin = passive recovery / activity / physiology flagship anchor
- typed manual readiness and manual structured gym logs = Health Lab-owned human-input anchors
- wger = optional mock-backed connector prototype for later convergence into canonical gym objects
- Cronometer = nutrition / supplements bridge/reference

## Current proof maturity

The live repo proof for wger is bounded to a disposable local mock of published wger API endpoints plus deterministic transform outputs and replay checks.

That is enough to classify wger as a real prototype connector surface on the tree.

It is **not** a claim that:
- a live self-hosted or Docker-backed wger runtime was proved on this host
- wger is required for flagship completion
- the legacy trio day gate should be reopened as current flagship truth

## Architectural rule

Source systems are interchangeable.

Health Lab owns the canonical health evidence model.
Agent-facing tools must operate over Health Lab normalized state, not directly over wger-native schemas.

## Proposed repo surfaces

### pull
- `pull/sources/wger/`
  - bounded source acquisition
  - raw receipts
  - auth/session handling where needed for the prototype surface
  - incremental sync state
  - retry and resume behavior inside the bounded proof surface

### clean
- `clean/transforms/wger/` or `clean/transforms/resistance_training/`
  - deterministic mapping from wger source records into Health Lab canonical artifacts
  - provenance attachment
  - conflict expression if later multiple gym sources coexist

## Canonical targets

wger must map into Health Lab canonical objects, not become the canonical object model.

Primary canonical targets:
- `training_session`
- `exercise_catalog`
- `exercise_alias`
- `gym_set_record`
- `program_block`

Derived metrics expected around the same domain:
- volume
- estimated 1RM
- weekly hard sets
- density
- adherence

## v1 adapter contract intent

The bounded wger prototype should:
- preserve stable source identity from wger receipts
- emit stable Health Lab canonical IDs
- attach provenance on every normalized output
- support incremental pull, not full-history refetch by default
- support durable resume after interruption
- keep source independence so another gym source can be added later without changing the canonical contract

## Non-goals for this slice

This document does not:
- make wger the flagship or preferred v1 resistance-training source of truth
- make wger the only possible future gym source
- require Health Lab to mirror wger-native data structures exactly
- remove support for manual gym inputs as a fallback or coexistence path
- finalize every resistance-training metric formula in the same slice
