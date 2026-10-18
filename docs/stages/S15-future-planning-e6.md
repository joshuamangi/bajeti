# S15: E6 Future planning (#115), design only

**Prompt:** P13  |  **Mode:** design-gate  |  **Depends on:** S11  |  **Suggested branch:** `feature/issue-115-future-planning-design`

## Goal

Design 1, 5 and 10 year goals and restructure scenarios, and how they relate to Targets. No code yet.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `models.py` (Target, Budget, Allocation, Category)
4. `docs/roadmap.md` and docs/backlog.md
5. `docs/design/` (analytics and recurring designs for conventions)
6. Budget and allocation services

### Outputs of earlier stages this stage relies on

- S11 Targets shape
- S13 and S14 designs for conventions

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: design (do not code yet) the future-planning feature. Output docs/design/future-planning.md and wait for my approval.

Spec: fixed 1, 5 and 10 year horizons. Per horizon, goals with target amounts linked to categories and a progress view (saved so far vs needed per month). Plus restructure scenarios (recession, retrenchment, raise) that copy current allocations, adjust them, and show how categories are cut or repurposed and how goal dates move.

Cover:
- Schema: Goal(horizon, name, target_amount, category_id?, target_date), Scenario(name, kind, parameters), ScenarioAllocation(scenario_id, category_id, amount); how this relates to existing Target (short/mid/long) so we do not duplicate concepts; recommend merging or linking and justify.
- Calculations with formulas and worked examples: required monthly saving = (target - saved) / months remaining; goal date shift when monthly saving changes; optional inflation adjustment (state the default and make it editable); income change handling.
- Essential vs discretionary: how categories get a flag (new column? tag?), and the default cut order in a recession scenario. Make the rules transparent and editable, never hidden.
- Scenario semantics: a scenario NEVER changes real allocations; "apply scenario" is an explicit, confirmed action that is undoable.
- What stays computed on read versus stored; performance on SQLite.
- UI sketches in words for mobile, and which parts need a prototype (use P12 [S16]'s workflow).
- Anything ambiguous: list as open questions for me.
```

## Watch out for

- Design only. Do not write a migration or model code in this stage.
- Keep it consistent with Targets from S11 rather than inventing a parallel model.

## Your part (Claude cannot or should not do these)

1. Answer the open questions in the design and approve it.

## Done when

- docs/design/future-planning.md covers schema, formulas with worked examples, essential versus discretionary rules, scenario semantics and open questions.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- docs/design/future-planning.md

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Which parts need a prototype (S16's workflow).
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S16-pwa-prototype-e5.md`: E5 PWA and prototype context bundle (#114).
