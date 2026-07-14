# Phase 9 — Implementation Roadmap

This is a plan, not a change log — nothing described here has been implemented. Per this project's explicit instructions, no code/config/persona files are modified as part of Phases 1–9; this roadmap is what *would* happen once the design is approved.

## 1. File changes required

| File | Change | Phase driving it |
|---|---|---|
| `.claude/agents/roi.md` | Add `Write`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet` to tool grant (scoped and justified, mirroring Dani's enumerated-Bash-uses documentation style). Add the plan→execute→monitor→report loop description. Add "consult `.claude/workflows/` for a matching template before falling back to ad hoc dispatch" instruction. | Phase 4 |
| `.claude/workflows/_schema.md` (**new**) | Documents every YAML field, required vs. optional, one fully-commented example. | Phase 6 |
| `.claude/workflows/*.yaml` (**new**, 8 files) | One per multi-step workflow from the catalog (W1–W4, W6–W8, W10). W9 (standalone consults) intentionally gets no file — see Phase 6 §2. | Phases 3, 6 |
| `yael/decisions-log.md` (**new**, gitignored working file, created on first use) | Append-only decisions/learnings log. | Phase 8 |
| `CLAUDE.md` | Update to describe the config-driven architecture at a summary level; **not** duplicate the full YAML content (avoids recreating the exact duplication problem Phase 2 flagged). | Phases 2, 6 |
| `PRD-roi.md` | Needs a substantial revision or a versioned successor (`PRD-roi-v2.md`) reflecting Roi's new responsibilities — out of scope to draft until the design in Phases 4–6 is approved, since a PRD should describe an approved target, not a proposal. | Phase 4 |
| Every other agent persona (`liat.md`, `noga.md`, `merav.md`, `dani.md`, `yael.md`, `gefen.md`) | **No changes** in this initial rollout — Phase 7's verdict for all of them was "unchanged." | Phase 7 |

## 2. New folders

```
.claude/workflows/     — workflow YAML definitions + schema doc (Phase 6)
architecture/           — this design itself (Phases 1–9), already created
```

No other new top-level folders are needed — every workflow's actual deliverables continue to land in the existing `output/`, `dani/outputs/`, `merav/outputs/`, `yael/outputs/`, `gefen/outputs/` structure, unchanged.

## 3. Migration strategy

Because CreativeAgent has no running code today — everything is markdown persona files interpreted by Claude at dispatch time — there is no data migration in the traditional sense. "Migration" here means: introducing the config-driven path **alongside** the existing ad hoc path, not replacing it outright.

**Concretely**: Phase 4's design already builds this in — if no workflow YAML matches a request, Roi falls back to exactly today's behavior (reasoning from `CLAUDE.md`'s roster table and its own judgment). This means the rollout can be **incremental by construction**: a workflow that doesn't have a YAML file yet simply continues to work exactly as it does today, with zero risk of breakage, until its YAML is authored and validated.

## 4. Backward compatibility

- **The standalone single-agent consult path (W9) is untouched** — Dani's five standalone skills, Merav's direct generation, Liat's direct research, Gefen's profile work all continue exactly as today; they were deliberately excluded from the config layer (Phase 6 §2) because they gain nothing from it.
- **Every existing agent persona is untouched** in this rollout (Phase 7). Nothing about *what* any specialist does changes.
- **The fallback-to-ad-hoc behavior is the compatibility guarantee**, not a migration script — an incompletely-migrated workflow degrades gracefully to today's behavior rather than failing.

## 5. Testing strategy

No automated test suite is proposed (this is a prompt/config system, not software with a build step) — instead, a **pilot-and-validate** approach:

1. **Dry-run the pilot workflow** (W3, already fully specified as a worked example in Phase 6 §3) against a real SEO-content request, and compare Roi's actual behavior turn-by-turn against the documented state diagram (Phase 5 §3) — specifically checking: does it correctly persist tasks before dispatching, does it correctly fan-out Merav's images if needed, does it correctly gate on Yael's verdict for a genuinely new topic.
2. **Deliberately break the pilot's YAML** (e.g. rename a step's `id` so a `depends_on` reference is dangling) and confirm Roi's behavior is a clear reported error or fallback — not a silent wrong result.
3. **Simulate an interrupted run**: start the pilot workflow, stop after the first step completes (new session), and confirm a fresh Roi invocation correctly detects the in-progress run via `TaskList` and resumes rather than restarting from scratch (Phase 5 §11).
4. Only after the pilot passes all three checks does the second workflow get authored.

## 6. Rollout plan (phased, not big-bang)

**Phase A — Foundation + one pilot workflow.**
- Update `roi.md` with the new tool grant and operating loop.
- Author `.claude/workflows/_schema.md` and exactly one workflow file: `seo-gated-content.yaml` (W3) — chosen as the pilot because it's the most structurally complex cataloged workflow (two-pass same-agent dependency, a real gate, a fan-out) and already fully worked out in Phase 6 §3, so validating it validates the hardest case first.
- Run the three tests in §5.

**Phase B — Remaining workflows, one at a time.**
- Author and validate W1, W2, W4, W6, W7, W8, W10 individually, in roughly this order (simplest/lowest-risk first): W1 (single agent, trivial) → W4 (two-agent, no fan-out) → W2 (fan-out, no gate) → W8 (single agent, external side effect) → W10 (single agent, external side effect) → W6 (single agent, multi-internal-step) → W7 (the cross-session case — hardest, done last once resumability is proven on simpler workflows first).
- Each addition is independently low-risk because of the fallback guarantee (§4) — a mistake in workflow #5's YAML doesn't affect workflows #1–4.

**Phase C — Documentation catch-up.**
- Update `CLAUDE.md`'s architecture section and write `PRD-roi-v2.md` (or revise `PRD-roi.md` in place) to describe the now-validated system, once Phase B is complete — documentation follows proven behavior, not the other way around, avoiding Phase 2's core "docs vs. reality drift" risk by construction.

**Phase D — Explicitly out of scope for this rollout, tracked separately.**
- Phase 7's flagged future items (Merav video expansion, Dani split-if-triggered, a shared publishing tool for Noga/Dani) are independent initiatives with their own trade-offs already documented in Phase 7 and the Marketing OS Audit — not bundled into the orchestrator rollout, and not started until separately approved.

## 7. Estimated implementation order (single-track, no code — this is authoring/config work)

1. `roi.md` tool grant + loop description
2. `.claude/workflows/_schema.md`
3. `.claude/workflows/seo-gated-content.yaml` (pilot)
4. Pilot validation (§5, all three checks)
5. `yael/decisions-log.md` convention + one-line mentions in `roi.md`/`yael.md`
6. Remaining 7 workflow YAMLs, one at a time with validation, per §6 Phase B ordering
7. `CLAUDE.md` + `PRD-roi.md` updates
8. Stop — Phase D items require separate, explicit approval before starting

## 8. Implementation risks

| Risk | Mitigation |
|---|---|
| Roi's new tool grant (`Write`, `Task*`) becomes an unscoped capability expansion over time (scope creep) | Document the exact, enumerated uses in `roi.md` (mirroring Dani's five-Bash-uses pattern) — not "Roi can write files," but "Roi writes only task records and reads only `.claude/workflows/`" |
| YAML authoring errors (dangling `depends_on`, cycles) go unnoticed until a real run hits them | Pilot-first rollout (§6) surfaces this on the hardest workflow early; a lightweight validator script is flagged (Phase 6 §6) as a natural fast-follow, not built now |
| Increased token/turn cost from Roi's added planning/tracking overhead | Expected modest (task CRUD is cheap relative to agent dispatch) but should be observed during the pilot, not assumed — if the pilot shows meaningfully higher cost for no behavioral benefit over today, that's a signal to simplify before rolling out further, not a reason to abandon the design |
| Documentation drift resumes after Phase C if future workflow edits go directly into YAML without any doc review | Not fully solvable by structure alone; the config-driven design at least ensures *behavior* stays correct even if a summary doc lags, which is a strictly better failure mode than today's "prose is the only source of truth and can silently diverge from itself" |
| A future contributor (or Claude session) edits a workflow YAML without understanding the fallback/gate/retry semantics | `_schema.md` (step 2) exists specifically to make this self-service; revisit if repeated authoring mistakes suggest the schema needs simplification |

---

## Status: all 9 phases complete. Stopping here per the governing instruction — no code, workflow files, or persona edits have been created. Awaiting approval before any implementation begins.

**Documents produced** (all under `architecture/`):
1. `01-research-summary.md`
2. `02-architecture-review.md`
3. `03-workflow-catalog.md`
4. `04-orchestrator-design.md`
5. `05-workflow-engine-design.md`
6. `06-configuration-design.md`
7. `07-agent-review.md`
8. `08-memory-architecture.md`
9. `09-implementation-roadmap.md` (this document)
