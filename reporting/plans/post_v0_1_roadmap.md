# Post-v0.1.0 Roadmap

- Author: Codex
- Date: 2026-04-18
- Status: draft for execution
- Starting point: `main @ 8412e4a` (`v0.1.0` already released)

This document follows the same planning structure as the comprehensive
rebuild plan. It does not replace that plan; it begins after the Phase 7
release checkpoint and covers the next cycle of work.

---

## 1. Executive summary

Health Agent Infra has shipped `v0.1.0` as a **local-first, governed
runtime for a multi-domain personal health agent**. The rebuild plan is
complete: six domains are live, synthesis is active, review persistence
exists, the package is published, and the runtime has a strong test
floor.

The next cycle should not be another broad rebuild. The architecture is
good enough now that the work should shift from "make the runtime exist"
to "make the runtime more legible, more longitudinal, more grounded, and
more honestly evaluated."

This roadmap uses Google Research's September 30, 2025 article,
[*The anatomy of a personal health agent*](https://research.google/blog/the-anatomy-of-a-personal-health-agent/),
as a **lens**, not as a replacement architecture. The useful lessons are:

- clearer role separation
- better explicit memory
- multi-level evaluation
- grounded explanation

The core recommendation is:

1. **Close shipped-truth gaps first** — especially the packaged `hai
   eval` contradiction found in the release audit.
2. **Make the runtime easier to explain** — add role-map, query-taxonomy,
   and memory-model docs.
3. **Turn auditability into a product surface** — add a real explain path
   over proposals, firings, recommendations, and supersession.
4. **Add explicit user memory to SQLite with honest write surfaces** —
   goals, preferences, constraints, durable context.
5. **Build a real skill-harness eval pilot** — move beyond deterministic
   runtime scoring before adding more agent-facing surface.
6. **Add a read-only grounded expert layer** — explanation first, no
   recommendation mutation.

The expected outcome of this cycle is not "more domains." It is a more
credible and extensible post-v1 platform.

---

## 2. Locked decisions

### 2.1 Architecture

| # | Decision |
|---|---|
| 1 | **Keep the v1 code-vs-skill boundary.** Runtime code continues to own projection, classification, policy, synthesis, validation, and persistence. Skills continue to own rationale, uncertainty surfacing, and clarifying questions only. |
| 2 | **Treat local SQLite as the primary memory system.** New "memory" work extends explicit on-device state; it does not expand hidden chat memory or introduce an opaque embedding store. |
| 3 | **Grounded explanation is read-only first.** A future grounded expert layer may explain and cite, but it may not mutate recommendations until it has its own eval surface. |
| 4 | **Evaluation remains a first-class product surface.** If `hai eval` is presented as public, it must work from an installed package outside a source checkout. If that is not shipped, docs must say so plainly. |
| 5 | **No broad product re-scope in this cycle.** No meal-level nutrition, no symptom triage, no multi-user/hosted pivot, no prompt-heavy rewrite of deterministic runtime logic. |
| 6 | **Future expansion should follow seams already present.** New work should prefer extension-path docs and bounded modules (memory, research, adapters, eval harness) over architectural rewrites. |
| 7 | **Explainability becomes first-class.** The audit chain in SQLite (`proposal_log`, `daily_plan`, `x_rule_firing`, `recommendation_log`, supersession pointers) should be inspectable through a supported CLI surface, not only by manual SQL. |

### 2.2 Product framing

Health Agent Infra should now be described as a four-part system:

- **Runtime analyst** — pull, clean, project, classify, policy, synthesis
- **Coach** — readiness skills, synthesis skill, human-facing guidance
- **Memory** — accepted state, proposals, plans, reviews, future goals and
  preferences
- **Grounded expert** — future read-only explainer / research layer

This framing is additive. It does not imply a multi-agent runtime
rewrite. It is a more legible way of describing the architecture that
already exists.

### 2.3 Evaluation stance

Two eval layers are now explicitly distinct:

- **Deterministic runtime evals** — already strong; classify/policy/X-rule
  correctness, schema behavior, atomic persistence
- **Skill-harness evals** — currently the major known gap; needed to score
  the real skill-mediated system on bounded correctness and rationale
  quality

The next cycle should improve the second without regressing the first.

### 2.4 Source and privacy policy for future grounding

Any grounded-expert work in this cycle must follow these rules:

- grounding is **read-only** and out of synthesis
- grounding sources must be explicitly allowlisted and documented
- every substantive claim in the pilot must either cite a source or
  abstain
- no silent internet retrieval occurs inside `hai daily`, `hai
  synthesize`, or other recommendation-producing surfaces
- user data remains local by default; if any future grounding call sends
  user context outside the machine, that path must be explicit and
  operator-initiated

---

## 3. Target architecture for the next cycle

The shipped v1 runtime remains the base:

```
pull / intake
    ↓
projectors
    ↓
accepted_*_state_daily
    ↓
hai state snapshot
    ↓
domain proposals
    ↓
synthesis
    ↓
daily_plan + x_rule_firing + recommendation_log
    ↓
review_event + review_outcome
```

The target addition for the next cycle is:

```
                       ┌─────────────────────────────┐
                       │     user memory tables      │
                       │ goals / preferences /       │
                       │ constraints / context       │
                       └─────────────┬───────────────┘
                                     │
                                     ▼
pull / intake → projectors → accepted state → state snapshot → proposals
                                                     │
                                                     ├── coach skills
                                                     │
                                                     └── grounded expert
                                                         (read-only, cited)
                                                             │
                                                             ▼
                                                       explanation layer

proposals → synthesis → daily_plan + recommendations → review
                        │
                        └── hai explain

human/operator writes ──> hai memory ... ──> user memory tables
```

Expected new top-level additions:

- an explainability surface over the audit chain
- explicit user memory in SQLite
- a packaged or honestly de-scoped eval runner
- a real skill-harness eval pilot
- a read-only grounded expert / research layer
- clearer extension-path documentation

This is an expansion of the v1 platform, not a replacement.

---

## 4. Phases

### Phase A — Shipped-truth alignment (timeboxed: 2–3 days)

**Goal**: make the installed package, public docs, and release claims
agree on what is actually shipped.

The post-release audit found a concrete contradiction: `hai eval` is
presented as a public CLI surface, but the released package only
registers it when a repo-local `safety/evals/` tree is reachable. That
means the command behaves differently from inside a checkout versus from
an installed wheel outside the repo root.

**Deliverables**:

1. **Eval packaging decision**
   - Choose one of:
     - Package the eval runner, scenarios, and rubrics as a real shipped
       feature under `src/health_agent_infra/evals/`
     - Or de-scope `hai eval` from the public package surface and
       describe it as a repository/developer harness

2. **Implementation of the chosen path**
   - If shipped:
     - add `src/health_agent_infra/evals/__init__.py`
     - add `src/health_agent_infra/evals/runner.py`
     - add `src/health_agent_infra/evals/cli.py`
     - add packaged scenarios/rubrics
     - register `hai eval` unconditionally
   - If de-scoped:
     - remove `hai eval` from user-facing docs and public CLI claims
     - keep `safety/evals/` as an explicit repo-only harness

3. **Packaging verification**
   - A wheel-installed test that runs from outside the repo root and
     verifies the truth of the chosen path

**Acceptance criteria**:

- installed package behavior matches docs exactly
- no repo-root-dependent CLI behavior remains undocumented
- release notes, README, STATUS, and installed `hai --help` agree
- one wheel-installed verification runs from outside the repo root and
  proves the chosen `hai eval` behavior directly

**Effort**: 2–3 days

---

### Phase B — Positioning, taxonomy, and memory docs (timeboxed: 3–4 days)

**Goal**: make the architecture legible in the same way the rebuild plan
made the runtime executable.

The runtime is stronger than the current conceptual docs. The next step
is to explain it with the same discipline it was built with.

**Deliverables**:

1. **Role-map / positioning doc**
   - `reporting/docs/personal_health_agent_positioning.md`
   - Explains runtime analyst / coach / memory / grounded expert roles
   - Explicitly positions the project relative to the Google PHA framing

2. **Query taxonomy**
   - `reporting/docs/query_taxonomy.md`
   - Suggested buckets:
     - current state understanding
     - action planning
     - "why did the system recommend this?"
     - longitudinal pattern review
     - grounded topic explanation
     - human-input routing

3. **Memory model**
   - `reporting/docs/memory_model.md`
   - Covers:
     - raw evidence memory
     - accepted state memory
     - decision memory
     - outcome memory
     - missing adaptive memory

4. **Doc alignment pass**
   - minimal updates to README / architecture / tour if the new docs
     expose contradictions

**Acceptance criteria**:

- a new reader can explain the system without inventing chat-memory,
  voice-note, or "general AI coach" assumptions
- the local-first memory story is explicit
- the role split is described consistently across active docs

**Effort**: 3–4 days

---

### Phase C — Explainability + explicit user memory (1–1.5 weeks)

**Goal**: turn the local audit chain and new user memory into supported,
inspectable product surfaces rather than leaving them as SQLite-only
capabilities.

This is the most valuable architecture extension after v0.1.0. It is
also the cleanest way to deepen "memory" and "trust" without sliding
into opaque model state.

**Deliverables**:

1. **Migration 007**
   - add user-memory tables for:
     - goals
     - preferences
     - constraints
     - durable context notes

2. **Core memory module**
   - `src/health_agent_infra/core/memory/schemas.py`
   - `src/health_agent_infra/core/memory/store.py`
   - `src/health_agent_infra/core/memory/projector.py`

3. **Memory write/read CLI**
   - add a supported surface such as:
     - `hai memory set|list|archive`
     - or `hai intake goal|preference|constraint|context`
   - the chosen surface must be explicit, scriptable, and JSON-emitting

4. **Explainability CLI**
   - add a supported audit view such as:
     - `hai explain --for-date <d> --user-id <u>`
     - or `hai explain --daily-plan-id <id>`
   - it should reconstruct, from persisted state:
     - proposals used
     - X-rule firings
     - final recommendations
     - supersession status if relevant

5. **Snapshot exposure**
   - expose bounded user-memory state via `hai state snapshot`

6. **Tests**
   - `safety/tests/test_user_memory.py`
   - `safety/tests/test_cli_explain.py`
   - `safety/tests/test_cli_memory.py`
   - persistence, update behavior, snapshot visibility

**Acceptance criteria**:

- user goals/preferences/constraints are stored locally in SQLite
- memory can be created, listed, and archived without touching the DB
- at least one canonical plan can be explained end-to-end from persisted
  state only
- `hai explain` exposes proposal ids, firing ids, recommendation ids, and
  supersession linkage when present
- no hidden adaptive behavior is introduced
- no write surface bypass is introduced for memory or explainability

**Effort**: 1–1.5 weeks

---

### Phase D — Skill-harness eval pilot (1 week, timeboxed)

**Goal**: stand up a small but real harness that invokes an actual skill
path and scores both bounded correctness and rationale quality.

This is the most important evaluation follow-up after the deterministic
runner and should happen before adding more agent-facing explanation
surface.

**Deliverables**:

1. **Pilot harness**
   - `safety/evals/skill_harness/runner.py`

2. **Pilot scenarios**
   - `safety/evals/skill_harness/scenarios/recovery/...`

3. **Pilot rubric**
   - `safety/evals/skill_harness/rubrics/recovery.md`

4. **Execution note / RFC**
   - `reporting/plans/skill_harness_rfc.md`
   - records how the pilot is invoked, what remains blocked, and what
     "good enough" means for broader rollout

**Recommended scope**:

- one domain: recovery
- one skill: `recovery-readiness`
- 3–5 frozen scenarios
- score:
  - bounded action correctness
  - rationale quality

**Acceptance criteria**:

- at least one real skill path is exercised end-to-end by the harness
- rationale quality is scored by a written rubric, not only by ad hoc
  author judgment
- at least 4 of 5 pilot scenarios, or the equivalent timeboxed set,
  score ≥2/3 on bounded action correctness
- no scenario scores 0 on rationale quality without a blocker note
- `safety/evals/skill_harness_blocker.md` is meaningfully reduced or
  superseded by the new pilot docs

**Effort**: 1 week, timeboxed

---

### Phase E — Grounded expert prototype (1 week)

**Goal**: add a read-only grounded explainer layer for health-topic and
recommendation-context questions.

This is where the Google "domain expert" role is genuinely useful, but
only if it is introduced conservatively and under the source/privacy
policy above.

**Deliverables**:

1. **Grounded expert scope doc**
   - `reporting/docs/grounded_expert_scope.md`
   - makes explicit that the layer explains and cites, but does not
     mutate recommendations

2. **Research / retrieval module**
   - `src/health_agent_infra/core/research/sources.py`
   - `src/health_agent_infra/core/research/retrieval.py`

3. **Read-only skill**
   - `src/health_agent_infra/skills/expert-explainer/SKILL.md`

4. **Initial eval scenarios**
   - `safety/evals/scenarios/expert/...`

**Example questions in scope**:

- "What does elevated sleep debt mean in this system?"
- "Why would low protein soften strength?"
- "What does body battery measure?"

**Out of scope for this phase**:

- symptom triage
- diagnosis
- recommendation mutation
- hidden retrieval inside synthesis

**Acceptance criteria**:

- the layer can answer bounded explainer questions with citations
- every substantive claim in the pilot scenarios either cites or abstains
- no unsupported actionable claim appears in the pilot outputs
- citations are inspectable and reproducible
- no action mutation enters the runtime through this layer

**Effort**: 1 week

---

### Phase F — Extension-path documentation (2–3 days)

**Goal**: make the next extension easier for contributors than the last
one was for the core team.

The most useful next contributor doc is one clean extension path, not
more philosophy.

**Deliverables**:

1. **Pull-adapter extension doc**
   - `reporting/docs/how_to_add_a_pull_adapter.md`
   - covers:
     - adapter contract
     - evidence shape
     - projection expectations
     - required tests
     - definition of done

2. **Optional follow-on**
   - `reporting/docs/how_to_add_a_domain.md`

**Acceptance criteria**:

- a contributor can understand how to add a second wearable adapter
  without reverse engineering the whole repo

**Effort**: 2–3 days

---

### Phase G — Deferred / later bets (not part of the immediate cycle)

These are intentionally later. They should not block Phases A–F.

**Candidates**:

1. **Adaptive learning loop**
   - likely starts as `reporting/plans/learning_loop_rfc.md`
   - only after explicit user memory and skill-harness evals exist

2. **Additional pull adapters**
   - Apple Health most likely first

3. **Optional MCP wrapper**
   - useful, but secondary to truthful eval shipping, explicit memory,
     grounded explanation, and skill-harness evaluation

4. **Meal-level nutrition re-gate**
   - only after the retrieval problem is revisited explicitly

---

## 5. Recommended sequencing

If work happens strictly in order, use this sequence:

1. Phase A — shipped-truth alignment
2. Phase B — positioning, taxonomy, and memory docs
3. Phase C — explainability + explicit user memory
4. Phase D — skill-harness eval pilot
5. Phase E — grounded expert prototype
6. Phase F — extension-path documentation
7. Phase G — deferred bets

Why this order:

- Phase A fixes the only known release-surface contradiction.
- Phase B makes the next work legible.
- Phase C turns auditability and memory into real product surfaces.
- Phase D improves the biggest remaining eval gap before more agent-facing
  functionality lands.
- Phase E then adds grounded explanation on top of a stronger eval base.
- Phase F lowers the cost of future contributors and adapter work once the
  nearer-term product surfaces are clearer.

---

## 6. Definition of success for the next cycle

This cycle is successful if all of the following become true:

- installed package behavior and public docs agree on all public CLI
  surfaces
- the role-map and memory-model story are documented clearly
- user goals / preferences / constraints exist as explicit local memory
- the audit chain is explorable through a supported CLI surface
- at least one real skill-harness eval pilot runs end-to-end
- a read-only grounded expert layer exists for explanation
- extension seams are documented well enough that a new adapter or
  bounded feature can land without another repo-wide rebuild

---

## 7. Explicit non-goals for this cycle

Until the earlier phases land, do not broaden into:

- meal-level nutrition
- USDA / food taxonomy productization
- symptom triage or diagnosis
- hidden chat-memory adaptation
- action-changing grounded retrieval
- prompt-heavy rewrites of deterministic runtime logic
- another broad "rebuild plan" shape
