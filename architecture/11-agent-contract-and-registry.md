# Phase 11 — Standardized Agent Contract & Extended Agent Registry

Goal, as specified: make it possible to add a future agent by writing one persona file + one registry entry + referencing it in workflow config — **zero edits to `roi.md`**. This phase defines the contract every agent (existing or future) conforms to, and extends Phase 10's Agent Registry to make that contract's specifics queryable per agent. Still design-only — no files created or modified.

## 1. Why a contract, and why it stays lightweight

Per Phase 1's research and this project's own established culture, forcing every agent into rigid JSON-schema-validated output would be a bigger change than this system's scale justifies — every agent today communicates in well-structured **prose**, and that prose is already reliably informative (Roi, an LLM, reads it and acts on it correctly, as this entire session's own transcript demonstrates repeatedly). The contract below therefore has two layers, deliberately kept separate:

1. **The conceptual schema** (this section) — what information must exist, regardless of format.
2. **The textual convention** (§3) — the concrete, minimal way each agent already-mostly expresses that information today, tightened into a standard shape Roi can reliably locate. This is edits to *report structure*, not a rewrite of any agent's reasoning or domain logic.

## 2. The Agent Contract — conceptual schema

Every agent, on every dispatch, is understood to receive and return the following. This is what the Agent Registry (§4) declares *specifically* per agent; this section defines the *shape* every declaration fills in.

### Inputs
- **`required`**: the minimum data a dispatch must include for the agent to proceed at all (e.g., Dani's pre-write step requires a topic/brief; Noga requires either a source file or a direct brief — never neither).
- **`optional`**: data that changes behavior but isn't blocking if absent (e.g., Liat's research file, if it exists, sharpens Dani's brief but Dani proceeds without it).
- **`implicit`**: context an agent always loads itself regardless of what Roi passes (e.g., Noga always reads `noga/style-guide.md` if present; Merav always scans `merav/reference/`). Implicit inputs are declared in the registry so Roi (and a future workflow author) knows they exist without needing to pass them explicitly — this is not new behavior, just naming what every agent already does today.

### Outputs
- **`deliverables`**: the actual work product — either **artifacts** (files, see below) or **verbal-only content** (e.g. Gefen's per-post briefs, which the existing design deliberately never saves to a file). The contract requires every agent to be explicit about which kind it produced, because downstream steps need to know whether to expect a file path or inline text.
- **`summary`**: a short human-readable account of what was done — already how every agent reports today.

### Metadata
Accompanies every response, always the same shape regardless of agent: `agent_id`, `skills_used` (which of the agent's owned skills fired, if any — useful for the decisions log, Phase 8, and for debugging), `timestamp`.

### Artifacts
For any file produced: `path`, `type` (draft / final / package / log-entry), and — critically for Phase 10's Shared Workflow Context — whether it's the step's **primary** deliverable (what downstream steps should consume) or a **side artifact** (e.g. Dani's SEO package is primary for the SEO-review step, but a byproduct like an intermediate research note would be a side artifact nobody downstream needs).

### Status
One of a fixed, small vocabulary, mapping directly onto Phase 5's step-state machine:
- `success` — deliverables complete, nothing blocking.
- `partial_success` — some deliverables produced, others explicitly not (e.g. Merav generated 2 of 3 images, one failed) — **not** the same as `success`, must never be silently upgraded to it.
- `domain_verdict` — the agent did its job correctly and the *result itself* is a decision, not a deliverable (Yael's fits/needs-adjustment/new-strategic-move; Dani's non-blocking improvement notes). **This is explicitly not an error** — Phase 5 §6 already established retries must never target a valid domain judgment; this status value is what makes that distinction checkable rather than left to inference.
- `blocked_needs_input` — the agent cannot proceed without something only the user/Roi can supply (e.g. Merav needing a source photo that doesn't exist in `hila-photos/`).
- `blocked_needs_approval` — the agent has a deliverable ready but it sits behind a human approval gate (Phase 10 §13) before anything further happens (e.g. a future auto-publish step).
- `execution_error` — a real failure (tool/API error, timeout, malformed response) — the **only** status value Phase 5's retry policy ever acts on.

### Handoff
How this agent's output becomes another agent's input. Every artifact marked **primary** (see Artifacts, above) is what Phase 10 §9's Shared Workflow Context attaches under this step's id; a downstream step's `inputs_from: [this_step]` in Phase 6's schema resolves to that primary artifact (plus the summary) — never to side artifacts, and never requiring the downstream agent to know anything about how the upstream agent internally works.

### Error reporting
Only for `status: execution_error`. Shape: `error_type` (`tool_failure` / `timeout` / `malformed_output` / `dependency_missing`), `message` (human-readable), `retriable` (boolean — informs Phase 5 §6's bounded retry). A `domain_verdict` or `blocked_needs_*` status never populates this — those are successful diagnoses, not errors, exactly per Phase 10 §12's finding that CreativeAgent's existing side-effect-gating design means most "failures" are actually just correctly-identified blockers, not something to compensate for.

## 3. The textual convention (how this looks in practice, today's format)

No agent needs a rewrite. Every persona already ends its workflow description with a "what it reports to Roi" section (verified across all 6 built agents this session) — the contract just standardizes that section's structure:

```markdown
## דוח לרועי
- **סטטוס**: success | partial_success | domain_verdict | blocked_needs_input | blocked_needs_approval | execution_error
- **תוצרים ראשיים**: <נתיב קובץ + סוג, או "בעל פה בלבד">
- **תוצרים משניים**: <אם יש>
- **תקציר**: <כמה משפטים>
- **[אם domain_verdict]**: <הפסוק/הערות, לא באות דרך ערוץ שגיאה>
- **[אם execution_error]**: <סוג שגיאה, הודעה, retriable כן/לא>
```

This is a **small addition** to each existing persona file (a labeled final section), not a redesign of any agent's reasoning — every field already exists today as unstructured prose (e.g. Dani already always says whether something is a non-blocking note vs. a real problem); this just gives it a consistent, greppable header Roi can rely on across all agents instead of Roi having to re-infer structure from each agent's differently-phrased prose every time.

## 4. Extended Agent Registry

Extending Phase 10 §4's proposed `.claude/agents/_registry.yaml` with the fields requested. One entry per agent — shown here as a table for readability; the actual file is YAML, one block per agent, matching this row-for-row.

| Field | Roi | Liat | Noga | Merav | Dani | Yael | Gefen |
|---|---|---|---|---|---|---|---|
| **id** | `roi` | `liat` | `noga` | `merav` | `dani` | `yael` | `gefen` |
| **status** | active | active | active | active | active | active | active |
| **domain** | orchestration | trend research | content writing | visual generation | SEO | strategy | Instagram |
| **capabilities** (owned skills) | none (dispatches only) | `WebSearch`/`WebFetch` research | writing formats (newsletter/blog/social); `smoove-newsletter` | `gpt-image-gen` (generate + edit) | 11 `seo-*`/`google-search-console` skills | `airtable-read`, `docx-export` | `WebSearch`/`WebFetch` |
| **accepted inputs (required)** | user request | topic/keywords | source file **or** direct brief | image brief | topic/brief (pre-write) **or** finished draft (post-write) | period to plan **or** a topic to gate | post topic/brief, or explicit profile-structure request |
| **accepted inputs (optional)** | — | — | Liat's research file | brand-guidelines applicability flag; source photo requirement flag | Liat's research file (pre-write); pre-write brief (post-write, for comparison) | — | current strategic priority (from Yael, if relayed) |
| **accepted inputs (implicit)** | `.claude/agents/_registry.yaml`, `.claude/workflows/*.yaml` | `liat/Memory/searches.md` | `noga/style-guide.md`, `noga/reference/` | `merav/reference/`, `merav/brand-guidelines.md` | — | `yael/strategy.md` | `yael/strategy.md`, `yael/outputs/` (profile-structure mode only) |
| **produced outputs** | unified report only (no artifacts of its own) | `Content/*.md` | `output/*.md`+`.html`; Smoove draft campaign (separate step) | `merav/outputs/{type}/*.png` + `.txt` | `dani/outputs/*-seo.md` or subfolder report; Airtable record (publish-log only) | `yael/outputs/*.md`+`.docx`; gate verdict (no file) | `gefen/outputs/*-profile-structure.md`; verbal brief/review (no file) |
| **typical dependencies** (per Phase 3's catalog) | none — always entry point | none | Liat (W2/W3) or none (direct brief); Dani's pre-write brief (W3) | Noga's placeholder list (W2/W3) | none (pre-write) / Noga's draft (post-write) | none (monthly plan) / — (gate: reads own strategy doc) | Yael's strategy (profile mode) / none (tactical brief mode) |
| **required tools** | `Agent`, `Read`, `Glob`, `Grep` **+ new**: `Write`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet` (Phase 4) | `WebSearch`, `WebFetch`, `Read`, `Write`, `Edit`, `Glob`, `Grep` | `Read`, `Write`, `Edit`, `Glob`, `Grep` **+** `Bash` (scoped to `smoove-newsletter` only) | `Read`, `Write`, `Bash` (scoped to `gpt-image-gen`), `Glob` | `WebSearch`, `WebFetch`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash` (scoped to 5 named uses) | `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash` (scoped to `airtable-read` + `docx-export`) | `WebSearch`, `WebFetch`, `Read`, `Write`, `Edit`, `Glob`, `Grep` |
| **optional integrations** (degrade gracefully if absent) | — | — | Smoove (`SMOOVE_API_KEY`/`SMOOVE_LIST_ID`) | — | PageSpeed Insights (`PAGESPEED_API_KEY`), Search Console (`GOOGLE_SEARCH_CONSOLE_*`), Airtable write (publish-log only) | — | — |

**Template row for a hypothetical future 8th agent** (proving the "add without touching Roi" claim concretely — not a proposal to build this, purely illustrative):

| Field | `voice-gen` (hypothetical) |
|---|---|
| id | `voice-gen` |
| status | planned |
| domain | audio/voice generation |
| capabilities | a future `tts-api` skill |
| accepted inputs (required) | script text |
| accepted inputs (optional) | voice-profile selection |
| produced outputs | `voice/outputs/*.mp3` |
| typical dependencies | Noga's script (if from a video/podcast workflow) |
| required tools | `Read`, `Write`, `Bash` (scoped to `tts-api` only) |
| optional integrations | — |

Adding this agent for real would mean: write `voice-gen.md` conforming to §2's contract, append this row to `_registry.yaml`, reference `voice-gen` in whichever workflow YAML needs it (Phase 6). **`roi.md` requires zero edits** — its planning logic (Phase 4 §3) already reads `depends_on`/`agent` fields generically from workflow config and looks up whatever agent id it finds in `_registry.yaml`; it has no agent-specific branching to update. This is the concrete mechanism that satisfies the stated goal.

## 5. Why this achieves "no changes to Roi's orchestration logic"

Tracing it through Phase 4's design directly: Roi's plan-execution loop (Phase 4 §3) dispatches steps via the `Agent` tool using whatever `agent` id a workflow step names, and interprets the response using the standard status vocabulary (§2) — neither of those operations names a specific agent anywhere in `roi.md`'s own logic. The *only* place agent-specific knowledge lives is `_registry.yaml` (input/output shape, tools, dependencies) and each agent's own persona file (domain logic) — both of which are data/config Roi *reads*, not code Roi *contains*. This is precisely Google ADK's LLM-Agent-vs-Workflow-Agent separation (Phase 1 §3) applied concretely: *whether and how to dispatch* is a generic, data-driven operation; *what happens inside the dispatch* is each agent's own business, invisible to and unneeded by Roi's orchestration logic.

## 6. Backward compatibility check

Applying §2's contract to the 6 built agents' **current, actual** behavior (not a hypothetical): every one of them already reports a summary, already distinguishes files-produced from verbal-only output, already distinguishes a blocking problem from a non-blocking note, and already has a described (if not literally labeled) trigger for "can't proceed without X" (Merav's missing-photo case, Yael's missing-strategy-doc case). The only real change needed for existing agents is the small "## דוח לרועי" labeled-section addition (§3) — a documentation tightening, consistent with how every other phase of this design has avoided touching agent domain logic. No agent's actual reasoning, tool access, or workflow behavior changes because of this phase.

## 7. Update to the Phase 9 roadmap

| File | Change |
|---|---|
| `.claude/agents/_registry.yaml` | Now includes the full extended schema from §4 (capabilities, inputs, outputs, dependencies, tools, integrations) — supersedes Phase 10's thinner version |
| Every existing agent persona (`liat.md`, `noga.md`, `merav.md`, `dani.md`, `yael.md`, `gefen.md`) | **One small addition each**: the standardized "## דוח לרועי" closing section (§3) — everything else about them remains exactly as Phase 7 concluded (unchanged) |
| `.claude/workflows/_schema.md` | Add: the status vocabulary (§2) and the handoff mechanism (§2/§10 §9), so workflow authors know what values a step's outcome can take |
| `.claude/agents/roi.md` | No change beyond what Phase 4/10 already specified — this phase confirms no *additional* Roi changes are needed, which is itself the validation this phase was asked to produce |

Still nothing implemented. Awaiting approval alongside the rest of Phases 1–10 before any of this is built.
