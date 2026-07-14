# Workflow config schema

Every file in this directory (except this one) is a YAML workflow definition Roi reads when planning a multi-step run (see `.claude/agents/roi.md`, section "שכבת התכנון"). Full design rationale lives in `architecture/04-*.md` through `architecture/06-*.md` and `architecture/10-11-*.md` — this file is the practical reference for authoring/editing a workflow, kept short on purpose.

Standalone single-agent work (e.g. Dani's five solo SEO skills, Merav generating one image directly) does **not** need a file here — Roi's fallback path (the existing routing table in `roi.md` and `CLAUDE.md`) already handles those. Only author a file here for genuinely multi-step, multi-agent coordination.

## Top-level fields

```yaml
id: <unique-slug>              # matches the filename (without .yaml)
workflow:
  name: <same-as-id>           # kept as its own block (not just the top-level id) so
  version: <semver, e.g. 1.0.0>  # a workflow's version is unambiguous even if this
  last_updated: <YYYY-MM-DD>     # file is ever referenced/copied outside its filename
description: >
  What this workflow is for, in a sentence or two.

trigger:
  # Free-form matching hints Roi uses to decide this workflow applies.
  # Keep this narrow enough that it doesn't collide with another workflow's trigger.
  content_type: [...]          # optional, e.g. [blog, website, linkedin]
  keywords_he: [...]
  keywords_en: [...]

deliverables:
  # The end products a successful run produces — for the user-facing final report,
  # not consumed by the engine itself.
  - <deliverable_id>

steps:
  - id: <step-id>               # unique within this workflow
    agent: <agent-id>           # must exist in .claude/agents/_registry.yaml, status: active
    type: agent | gate | qa | synthesis   # default: agent
    depends_on: [<step-id>, ...]          # empty/omitted = no dependency, eligible immediately
    inputs_from: [<step-id>, ...]         # which prior steps' PRIMARY artifacts this step consumes
    run_if: <condition-name>              # optional — see "Conditions" below
    retry:
      max_attempts: <int>
      on: [tool_error, empty_output, timeout]   # execution-class failures only — never domain_verdict
    awaits_human_approval: true|false     # optional, default false — see "Human approval gates"
    fan_out: per_placeholder | <n>        # optional — this step dispatches multiple parallel instances

completion_criteria:
  - <plain-language checks a human or a future validator script can verify>
```

## Execution context & shared workflow context

Resolved once, at plan-instantiation time, from the incoming request: a flat set of key-value flags (e.g. `needs_images: true`, `content_type: blog`). This is what `run_if` conditions check against. As each step completes, its **primary** artifact (see the Agent Contract, `architecture/11-agent-contract-and-registry.md` §2) is attached to this same shared context under the step's id — this is what `inputs_from` resolves against. Both live in the run's `TaskCreate`/`TaskUpdate` `metadata`, not in a separate store (see `architecture/05-workflow-engine-design.md` §2).

## Status vocabulary (what a step's outcome can be)

Every agent's report to Roi (see each persona's own "## דוח לרועי" section) uses one of:

| Status | Meaning | Roi's reaction |
|---|---|---|
| `success` | Deliverables complete | record step as done, continue |
| `partial_success` | Some deliverables produced, some explicitly not | record step as done, but carry the gap into the final report — never silently upgrade to `success` |
| `domain_verdict` | The agent's *answer itself* is the result (e.g. Yael's fits/needs-adjustment/new-strategic-move) | record step as done — **this is not a failure**, never retried |
| `blocked_needs_input` | Agent can't proceed without something only the user/Roi can supply | halt the run at this step, report to user — see "State mapping" below for how this is recorded |
| `blocked_needs_approval` | Deliverable ready, but sits behind a human approval gate | see "State mapping" below |
| `execution_error` | Real failure (tool/API error, timeout, malformed output) | apply the step's `retry` policy if any attempts remain; otherwise halt — see "State mapping" below for how this is recorded |

"Record step as done" / "halt" above describe the *conceptual* outcome. **How that outcome is actually written to `TaskUpdate` is not one-to-one** — see the next section. This gap was found empirically during the `seo-gated-content` pilot (`architecture/12-phase-e-live-validation-report.md`, "Runtime Constraints Discovered During Pilot"), not designed in from the start.

## State mapping — designed states vs. real `TaskUpdate` capability

**This section is the single canonical reference for how workflow-step outcomes are recorded.** Every other document (`architecture/05-workflow-engine-design.md`, `roi.md`) refers back to this table rather than repeating it — do not duplicate this mapping elsewhere.

`TaskUpdate`'s real `status` field accepts exactly four values: `pending`, `in_progress`, `completed`, `deleted`. It does **not** support `failed`, `awaiting_approval`, `blocked`, or `retry_pending` — these were part of the originally *designed* state machine (`architecture/05-workflow-engine-design.md` §3) but are not states the actual tool understands. No tool change is being requested or assumed; the mapping below is how the existing four values represent the richer designed vocabulary, using `metadata` to carry the distinction the `status` field itself cannot.

| Designed state | Needs its own persisted record? | Real `status` | `metadata` fields that carry the real meaning |
|---|---|---|---|
| `pending` (not yet ready — dependencies unmet) | yes | `pending` | *(none — absence of `engine_state` means exactly this)* |
| `ready` (dependencies satisfied, about to dispatch) | **no** — computed fresh each planning pass by checking whether every `depends_on` entry is recorded as done; never written to the tool | — | — |
| `in_progress` (agent actively dispatched, working) | yes | `in_progress` | *(none needed)* |
| `retry_pending` (between a failed attempt and the immediate re-dispatch) | **no** — per "Retry" below, re-dispatch is immediate with no backoff, so this exists only within a single turn and is never externally observable; if desired, an `attempts` counter can still be bumped on the `in_progress` record | `in_progress` | optional: `attempts: <int>` |
| `completed` — but the *Agent Contract* status that produced it varies | yes | `completed` | `outcome_status: success \| partial_success \| domain_verdict` — preserves which of the three non-failure statuses actually applies, since the tool's `completed` alone can't distinguish them |
| `failed` (retries exhausted, run halted at this step) | yes | `pending` — chosen over `in_progress` because no agent is actively working on it right now, and over `deleted` because the step must stay visible/auditable, not be treated as abandoned | `engine_state: failed`, `error: {error_type, message, retriable: false}` |
| `blocked` (agent reported `blocked_needs_input` or `blocked_needs_approval`) | yes | `pending` (same reasoning as `failed` — not currently being worked, must stay visible) | `engine_state: blocked_needs_input \| blocked_needs_approval`, `blocked_reason: <text>` |
| `awaiting_approval` (step config-gated by `awaits_human_approval: true`, dependencies met, not yet dispatched pending a human go-ahead) | yes | `pending` (nothing has been dispatched to an agent yet, so this is the most literal fit) | `engine_state: awaiting_approval`, `approval_prompt: <what the user is being asked to approve>` |
| `cancelled` (user stopped the run) | yes | `deleted` — this is the one case where "no longer being pursued" is the accurate meaning | `engine_state: cancelled`, `cancelled_at: <timestamp>` |

**Practical consequence for reading state back**: a real `status: pending` on a step that has already been dispatched once is not "hasn't started" — check `metadata.engine_state` first. A `TaskList` scan for "is this run still open" (per `roi.md`'s "בדוק ריצה פתוחה") should treat `pending` and `in_progress` identically as "not `completed`/`deleted`, still open" — this was already the documented behavior and needs no change (see `roi.md`, unchanged wording: "לא `completed`/`deleted`").

## Conditions (`run_if`)

Two kinds only, per `architecture/05-workflow-engine-design.md` §5 — deliberately not more:
1. A flag resolved from the execution context (e.g. `needs_images`).
2. A named upstream `gate`-type step's verdict (e.g. `strategic_gate == fits`).

## Human approval gates (`awaits_human_approval`)

A step marked `awaits_human_approval: true` is recorded as `pending` with `metadata.engine_state: awaiting_approval` (see "State mapping" above — there is no literal `awaiting_approval` tool status) once its dependencies are satisfied, and only proceeds once the user gives explicit affirmative confirmation in chat. This is the same mechanism whether the approval is a verdict-branch (Yael's gate), a cross-session pause (the weekly plan email), or an inline side-effect confirmation (e.g. a future auto-publish step) — see `architecture/10-design-review-addendum.md` §13.

## Fan-out / fan-in

`fan_out: per_placeholder` (or a fixed integer) means this step's agent is dispatched once per item (e.g. once per `{{IMAGE_NEEDED}}` in Noga's draft), all in parallel within the same turn; a downstream step naming this step in `depends_on` is not `ready` until **all** fanned-out instances complete (fan-in).

## Retry

Only ever targets `execution_error`. `max_attempts` is total attempts including the first; `on` lists which error types are retriable. No backoff — execution is human-paced within a chat session, so immediate re-dispatch is sufficient (see `architecture/05-workflow-engine-design.md` §6).

## Versioning & change tracking

Each workflow declares `workflow.version` (semver) and `workflow.last_updated`. **Git history is the actual changelog** — every edit to a workflow YAML is a normal git commit with a message explaining why, exactly like every other file in this project (persona files, skills). No separate changelog file or version-history table is maintained, deliberately: this project's architecture review (`architecture/02-architecture-review.md`) flagged duplicated sources of truth as the recurring weakness to avoid, and a second, hand-maintained "what changed in v1.1.0" log would immediately become a second thing that can drift from what git already records precisely.

**When to bump the version**: increment `version` (semver — patch for wording/threshold tweaks, minor for new optional steps, major for a changed step order or a removed/renamed step) whenever a workflow file changes, and bump `last_updated` alongside it. This gives Roi (and a human skimming the file) an at-a-glance signal that the shape of a workflow changed, without needing to `git log` it — while `git log`/`git blame` remain the source of truth for *why*, consistent with how the rest of this project already treats git as authoritative for history (see `architecture/08-memory-architecture.md` §1, which makes the same call for local output history).

## Validation checklist (manual today; a script is a flagged future fast-follow, not built yet)

- [ ] Every `agent` value exists in `.claude/agents/_registry.yaml` with `status: active`
- [ ] Every `depends_on`/`inputs_from` entry references a real `step.id` in this same file
- [ ] No dependency cycles
- [ ] `retry.on` never includes anything that could be a `domain_verdict`
- [ ] If `awaits_human_approval: true` appears, the workflow's description explains what the user is being asked to approve
