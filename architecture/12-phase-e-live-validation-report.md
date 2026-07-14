# Phase E — Live Integration Validation Report

Date: 2026-07-14. Scope: real, live validation of the implemented orchestration layer (Agent Registry, Agent Contract, Roi's planning loop, the `seo-gated-content` pilot workflow) — not a re-read of the design, actual execution. Every finding below is labeled **VERIFIED** (I independently checked it — file existence, tool schemas, git diffs) or **SELF-REPORTED** (from a dispatched agent's own transcript, internally consistent and cross-checked where possible, but not independently re-derived by me from scratch). No architecture file was modified as part of this validation. No commit has been made.

## 1. Integration Test Report (Test 1 + Test 2)

### 1.1 What was run

A real, live dispatch of the `roi` subagent (not a simulation) with the request "write a blog article about 5 common marketing-automation mistakes in small businesses" — an explicit test topic, chosen as generically on-brand but not a strategic commitment. This incurred real costs: live web research (Liat-equivalent research folded into Dani's SEO research), live Airtable reads, one real OpenAI `gpt-image-2` image generation. Image generation was capped at one (of two placeholders Noga produced) by explicit test instruction, to bound cost — this is a deliberate test-scope decision, not a system failure.

### 1.2 Workflow matching — **VERIFIED**

`seo-gated-content.yaml`'s `trigger.content_type: [blog]` and `keywords_he` matched the request ("מאמר" + "בלוג"). I independently confirmed only one file exists in `.claude/workflows/` (checked directly), so there was no ambiguity to resolve.

### 1.3 Execution order & parallelism — **VERIFIED**

Confirmed via three independent sources agreeing: (a) Roi's own reported plan, (b) the sequence and timing of the three task-completion notifications I received directly (Merav's image and Dani's post-review arrived as two *separate*, temporally-overlapping notifications — not sequential), (c) the task list itself showing `dani_post_review` (#38) and `merav_images` (#39) both `in_progress` simultaneously before either completed. Order actually executed: `strategic_gate` (yael) → `dani_pre_write` (dani) → `noga_write` (noga) → **[`dani_post_review` (dani) ∥ `merav_images` (merav), genuinely concurrent]** → `combine` (roi). This matches the YAML's dependency graph exactly — both parallel steps depend only on `noga_write`, not on each other.

### 1.4 Agent Contract reporting — **VERIFIED**

Every agent's report used the new standardized status vocabulary: Yael → `domain_verdict` (fits), Dani → `domain_verdict` twice (non-blocking notes, correctly not treated as errors), Merav → `success`. I read these directly in the task notifications, not just Roi's paraphrase of them.

### 1.5 Artifacts — **VERIFIED independently on disk**, not just trusted from agent reports

| Claimed artifact | Checked | Result |
|---|---|---|
| `output/5-marketing-automation-mistakes-small-business.md` + `.html` | `ls`, `grep` | Exist, 16KB/20KB, real content |
| `dani/outputs/5-marketing-automation-mistakes-small-business-seo.md` | `ls` | Exists, 13KB |
| `merav/outputs/blog/2026-07-14-automation-mistakes-header.png` + `.txt` | `ls` | Exist, 1.5MB PNG (real image, not a stub) |
| Image actually embedded in the `.html`, not just mentioned | `grep -B2 -A2` | Confirmed: real `<img>` tag, correct relative path, real alt-text |
| Unresolved second placeholder left explicitly marked, not silently dropped | `grep` on the `.md` | Confirmed: `{{IMAGE_NEEDED: ...}}` preserved verbatim with an explicit "not produced in this test" note and Dani's pre-prepared alt-text |
| Readability numbers real, not invented | Cross-referenced against `readability_he.py`'s actual behavior (built and tested earlier this session) | Plausible and internally consistent (19.0% long sentences, 0.8% passive) — script genuinely caught that Noga's own self-estimate (~24%) was off, which is exactly the kind of thing a real deterministic check should catch and a rubber-stamp wouldn't |

### 1.6 Deviations found — the actual point of this test

**Deviation 1 (significant): task-tracking tools became unavailable mid-run.** Roi self-reported that `TaskUpdate`/`TaskList`/`TaskGet` stopped being available partway through execution ("exists but is not enabled in this context"), after the two parallel steps completed. **This is corroborated, not just self-reported**: when I checked the task list myself at that point, tasks #38 (`dani_post_review`) and #39 (`merav_images`) were indeed still showing `in_progress` despite the work being genuinely done — matching Roi's account exactly. I fixed this manually after independently verifying the real artifacts existed. **This means: as designed today, if a session actually ended at that exact point, a resumed Roi reading `TaskList` would see two "in_progress" steps that are actually complete, and — per the resume logic in `architecture/05-workflow-engine-design.md` §11 — might needlessly re-dispatch Dani and Merav for work already done.** This is the single most important finding of this validation.

**Deviation 2 (minor, design-clarity gap): no formal "primary artifact" existed for `dani_pre_write`.** The registry (`_registry.yaml`) doesn't declare a file path for Dani's pre-write brief — only for his post-write package. Roi correctly improvised by passing the brief as reported text rather than a file reference, which is actually consistent with how `CLAUDE.md` already describes this step ("Roi folds that SEO brief into the brief it hands to Noga") — but it's a real gap between the schema's implied model (primary artifact = a file) and this specific step's actual shape (primary artifact = text). Worth a one-line clarification in `_schema.md`: "inputs_from" may resolve to a file path or to reported text, not always a file.

**Non-deviation, correctly handled**: Roi found a pre-existing, unrelated task (#30, this validation project's own tracking) in `TaskList` at startup and correctly left it alone rather than treating it as part of the workflow run it was executing — good evidence the "check for an existing open run" logic (§11) discriminates correctly rather than grabbing any open task indiscriminately.

**One real-world side-finding, not an architecture bug**: Yael's gate verdict (`fits`) came with a genuine scheduling observation — the current July content plan has no open week for this test topic. This is exactly the kind of legitimate non-blocking note the design is supposed to surface, working as intended.

## 2. State Transition Validation (Test 2, continued)

Traced against Phase 5's designed state machine using the actual pilot run plus the Test 3 dry-run (§3):

- `pending → ready → in_progress → completed`: **VERIFIED** for all 6 steps of the real run (with the caveat in Deviation 1 — the *tool-level* status update for 2 of the 6 steps had to be corrected manually rather than happening automatically).
- No step was observed transitioning to `in_progress` before its `depends_on` were `completed` — **VERIFIED**, consistent with the hard guard rule in `roi.md`.
- **Critical gap, VERIFIED directly against the tool's own schema (not just an agent's claim)**: I checked `TaskUpdate`'s actual parameter definition — its `status` field only accepts `pending`, `in_progress`, `completed`, `deleted`. **There is no `failed` and no `awaiting_approval` value in the real tool**, despite both being referenced as target states in `roi.md`'s new instructions and in Phase 5's designed state diagram. Roi's own Test 3 answer independently surfaced this exact gap and improvised the same fix I would have suggested (encode the richer state in `metadata`, leave the tool-level `status` at the nearest supported value). This is a genuine design/implementation mismatch, not a hypothetical concern — it's real today, in the currently-deployed `_registry.yaml`/`roi.md`.

## 3. Failure Simulation Report (Test 3)

Run as a **synthetic dry-run** (Roi reasoning against real design docs with injected hypothetical step outcomes), not a full costly re-execution of the pipeline — deliberately, to keep this test cheap while still exercising the real decision logic written into the live `roi.md`. This is a scope choice I'm flagging explicitly, not something to mistake for a full live re-run.

| Check | Result |
|---|---|
| Distinguishes `execution_error` from `domain_verdict` | **Correct**, and correctly identified the *only* valid discriminator is the literal `status` field, not message tone/content — quoted the exact source lines for both. |
| Retry counting (`max_attempts` includes first attempt) | **Correct**, matches `_schema.md`'s documented semantics exactly. |
| No backoff, immediate re-dispatch | **Correct**, matches design. |
| On retry exhaustion: does not silently continue | **Correct**, and backed by two independent mechanisms — the explicit "never present partial as complete" rule, *and* the structural fact that a `failed` (non-`completed`) step can never satisfy a downstream `depends_on`, so `noga_write` is mechanically unreachable even if the prose rule were somehow missed. |
| Partial-run state preserved correctly (earlier successful steps not invalidated by a later failure) | **Correct** — explicitly confirmed `strategic_gate`'s `fits` verdict stays valid and wouldn't be re-run on resume. |
| `domain_verdict` never retried | **Correct**, cited both the status-vocabulary table and the checklist rule verbatim. |
| Human-approval branch (`awaits_human_approval`) | **Correctly reasoned** as hypothetical (not active on the real pilot's `strategic_gate` today), correctly distinguished "step never dispatched at all" (approval-gated) from "step dispatched, then fails" (retry-gated) — these are different mechanisms and Roi kept them separate. |
| New gap surfaced | No formal mapping exists from an agent's free-text error description to the `retry.on` categories (`tool_error`/`empty_output`/`timeout`) — today this classification is entirely Roi's judgment call, undocumented as a rule. Minor, but worth a sentence in `_schema.md`. |
| Same `failed`/`awaiting_approval` tool-schema gap as §2 | Surfaced independently here too, before I cross-checked it myself — increases confidence this is a real, not a one-off, issue. |

## 4. Backward Compatibility Report (Test 5)

- **VERIFIED via git diff (done prior to this live test, re-confirmed here)**: the pre-existing routing table and connection-description sections in `roi.md` are byte-identical to before this project began — only additive sections were introduced.
- **VERIFIED live**: dispatched Roi with an Instagram-caption request (no matching workflow file — only `seo-gated-content.yaml` exists, and it explicitly excludes Instagram). Roi correctly identified "no match," correctly fell back to the pre-existing routing table, and correctly re-derived the *exact* pre-existing rules without prompting: Yael's gate still required for a new topic, Dani still excluded (blog/LinkedIn only), Gefen still on-request-only. This is the fallback path's core promise, holding up under a real dispatch.
- **Not independently re-verified in this pass** (reasonable inference, not direct proof): that Noga/Merav/Dani/Yael/Gefen behave identically when dispatched via the *old* ad hoc path specifically — their persona files only changed by the additive "## דוח לרועי" section (Phase B), and Test 1 already proved that section doesn't interfere with their domain logic when dispatched via the *new* path. I did not spend additional budget re-running a full ad hoc dispatch to prove the old path bit-for-bit, since the persona changes are identical regardless of which path dispatches them.

## 5. Runtime Constraints Discovered During Pilot

Consolidating the single cross-cutting finding from this validation (detailed in §1.6 Deviation 1, §2, and §3) in one place, now that it has been fixed:

**The constraint**: `TaskUpdate`'s real `status` field supports exactly four values — `pending`, `in_progress`, `completed`, `deleted`. The original design (`architecture/05-workflow-engine-design.md` §3, written before any live execution) assumed literal tool support for `failed`, `awaiting_approval`, and `retry_pending` as well. This was an untested assumption that turned out to be wrong, caught only by actually running the pilot: two real steps (`dani_post_review`, `merav_images`) completed their real work but the tracker itself got stuck showing `in_progress`, because the tool genuinely has no way to record anything richer.

**How it was found**: not by inspection — by a real dispatched Roi self-reporting the tool became "not enabled in this context" mid-run, which I then independently corroborated by checking the actual task list and by directly re-checking `TaskUpdate`'s own parameter schema (its documented `status` enum).

**The fix applied (this round, documentation-only, no mechanism change)**:
- `.claude/workflows/_schema.md` now has one canonical "State mapping" table translating every designed state onto the real four values plus a documented `metadata.engine_state`/`outcome_status`/`error`/`blocked_reason`/`approval_prompt` convention. This table is the single source of truth; nothing else duplicates it.
- `architecture/05-workflow-engine-design.md` §2–3 corrected to stop asserting the four real values were "exactly" sufficient, and now points to the schema doc's mapping instead of re-describing it.
- `.claude/agents/roi.md`'s "שכבת התכנון" §3 corrected to stop instructing an impossible literal action ("mark the step as `failed`") and instead points to the same canonical mapping.

**Why this is sufficient** (not a new layer, per this round's explicit constraint): the actual *behavior* Roi follows — retry per policy, halt on exhaustion, never present partial as complete, distinguish `domain_verdict` from `execution_error` — is unchanged and was already validated working correctly in §3's failure simulation, including the exhaustion case reasoning through the fix independently before I applied it centrally. Only the *technical description of how that behavior gets recorded* was wrong; fixing three documents to say the same, now-accurate thing closes the gap without touching the planning loop, without adding a tool, and without adding a new abstraction layer.

## 6. Remaining Risks

1. ~~**(Highest priority)** The `TaskUpdate` status-enum gap~~ — **resolved this round**, see §5. Retained here struck-through rather than deleted, so the risk list stays an honest record of what was found and fixed, not just what's currently open.
2. Error-type classification (§3) has no formal rule — low priority, but will accumulate inconsistency across workflows if left undocumented.
3. Real test artifacts now exist in the repo (`Content/`, `output/`, `dani/outputs/`, `merav/outputs/`) from this test run. All four directories are already `.gitignore`d, so there's no risk of them landing in a commit by accident — but they're real disk artifacts and the article is, per Yael's own note, plausibly usable if the July calendar gets adjusted. Worth an explicit decision (keep as a real draft candidate, or discard as test waste) rather than leaving it ambiguous.
4. Only one of eight cataloged workflows is migrated. This was always the plan (§9's phased roadmap), not a new risk — flagged here only so it's not mistaken for "done."
5. Cost visibility: nothing in the Agent Contract tracks actual spend (API cost) per run. Not a correctness risk, but worth considering before this runs unattended/at higher frequency.

## 7. Recommended Next Steps

1. ~~Patch `_schema.md` with the `metadata`-based state-tracking convention~~ — **done, this round** (§5). No longer blocking.
2. Decide on the test article's fate (§6.3) — separate from the architecture work.
3. Proceed to migrate the next workflow per the roadmap's existing ordering (W1, research-only — the simplest remaining case), per `architecture/09-implementation-roadmap.md` §6 Phase B — no longer blocked on item 1.
4. Continue to hold off on committing anything until you've reviewed this report and the artifacts directly.

No commit has been made. Awaiting explicit approval.
