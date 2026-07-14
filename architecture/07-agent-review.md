# Phase 7 — Agent-by-Agent Review

Verdict for each agent: **unchanged**, **simplified**, **expanded**, or **merged** — with justification. Governing rule carried over from every prior phase: recommend a change only where there's an identified, concrete problem or an already-validated need (per the Marketing OS Audit), never speculatively.

| Agent | Verdict | Why |
|---|---|---|
| Roi | **Expanded** | Per Phase 4 — gains `Write`+`Task*` tools and the plan/execute/monitor/report loop. This is the whole point of the project. |
| Liat | **Unchanged** | Minimal, well-scoped, no audit finding or validated need points at a change. |
| Noga | **Unchanged** | Already gained narrow Smoove access this session; no further change indicated. Future publishing-workflow integration (below) adds a tool when that workflow is actually built, not a persona overhaul now. |
| Merav | **Expanded** (future, conditional) | See §1. |
| Dani | **Unchanged**, with a named future split trigger | See §2. |
| Yael | **Unchanged** | Single clear responsibility, well-scoped; natural future owner of a performance-recap capability (Marketing OS Audit item #12), not a change to make now. |
| Gefen | **Unchanged** | On-request-only pattern is working exactly as designed; no audit finding suggests change. |
| Bar (planned) | **Do not build** | Reaffirming the Marketing OS Audit's finding — see §3. |

No **merge** candidates were found. See §4 for the two pairs actually considered and rejected.

## 1. Merav — the concrete case for expansion (video)

The Marketing OS Audit already identified this precisely: short-form video is the largest content-format gap in the whole system, and the Remotion skill suite (`remotion-create`, `remotion-render`, `remotion-captions`, `remotion-markup`) is *already installed* in `.claude/skills/` from this session, unwired to any agent. Per the "prefer capability over agent" mandate governing this entire redesign, video generation should become **Merav's** remit, not a new agent's — she is already "the visual generator," and video is a visual capability, not a different context. This is a direct application of Phase 1's context-centric decomposition principle: the context that matters here is "translates a content brief into a visual asset using brand guidelines," which is identical whether the asset is a PNG or an MP4.

**Not recommended now**: actually wiring this. The Marketing OS Audit already flagged the real cost (a Node/render pipeline setup this project doesn't have yet) and this remains a P1 item to schedule deliberately, not something to bundle into the orchestrator redesign.

## 2. Dani — largest agent, not yet a split candidate

Dani owns 11 of the project's 17 domain-specific skills (Phase 2's audit). This is the single agent most likely to eventually justify a split, so it's reviewed explicitly rather than passed over.

**Why not now**: all 11 skills load via progressive disclosure — invoked individually, only when relevant to the specific task at hand (a technical audit doesn't load keyword-research's content, and vice versa). There is no evidence of context bloat *within a single task* (each dispatch of Dani only pulls in the 1–3 skills that task actually needs). The concern Phase 2 flagged is about **discoverability and persona-doc maintainability** as the count keeps growing, not about runtime context cost today.

**The named future split trigger** (so this doesn't have to be re-litigated from scratch later): if a 12th+ SEO skill is added, or if Dani's persona file itself becomes hard to navigate (a subjective but checkable signal — compare against the 500-line guidance Phase 1's Claude Code Skills research established for individual skill files, applied loosely to persona-file readability too), reconsider splitting along the clearest existing seam: the **pre/post-write content-SEO loop** (5 skills, tightly coupled to Noga's writing cycle) vs. the **five standalone consult skills** (technical audit, content refresh, competitor analysis, content planning, strategy advisor — already documented as a separate "on explicit request only" mode in Dani's own persona). That seam already exists structurally in how Dani's persona is written today; a split, if it ever happens, would formalize an existing internal boundary rather than invent a new one.

## 3. Bar — confirming "do not build," with the orchestrator-specific reasoning added

The Marketing OS Audit already recommended against building Bar as a 7th agent, on business-capability grounds (LinkedIn publishing+analytics, not a LinkedIn persona, was the actual gap). This review adds the orchestration-specific reasoning: per Phase 1's research, adding an agent is the *expensive* way to add a capability (new context boundary, new coordination overhead, new persona to maintain) — a *tool* Noga and Dani can both call achieves the same business outcome (LinkedIn posts get published, with analytics feeding back) at a fraction of the coordination cost. This redesign's Phase 6 config format makes it easy to add "LinkedIn publish" as a step type usable by *either* agent's existing workflows, without a new persona ever entering the picture.

## 4. Merge candidates considered and rejected

- **Gefen + Noga?** Rejected. Gefen's context is platform-specific tactical knowledge (current Instagram algorithm/format conventions); Noga's is cross-platform brand voice. Merging would force one agent to hold both contexts simultaneously for every dispatch, even when a task only needs one — a direct violation of Phase 1's context-centric decomposition principle, and it would also break Gefen's correctly-scoped "on-request-only" trigger model (folding her into Noga would make her either always-on or invisible, neither of which matches how she's actually used today).
- **Dani + Yael?** Rejected. Dani is SEO-tactical (keyword/technical/on-page); Yael is business-strategic (which services, which customer-journey stage, when). These are genuinely different reasoning domains with different inputs (SERP data vs. business strategy doc) and different audiences for their output (Noga's brief vs. the user's monthly calendar) — merging would recreate exactly the "one generalist juggling many domains" anti-pattern Phase 1's research warns against.

## 5. Future capabilities, mapped to owners (not new agents)

| Capability | Owner | Rationale |
|---|---|---|
| Video generation | Merav (expand) | Same visual-asset context, different medium (§1). |
| Voice/audio generation | **No owner recommended yet** | No validated need exists anywhere in this project's current strategy/workflows — speculative until a concrete use case surfaces; do not pre-build. |
| Publishing (social) | Noga + Dani (new shared tool/skill) | Per Marketing OS Audit P0 #2 and §3 above — a tool both can invoke, not a persona. |
| Analytics (GA4, beyond the Search Console work already done) | Dani (skill) + Yael (consumer of a future recap capability) | Mirrors the already-successful Search Console pattern exactly. |
| QA / verification | Workflow-level `qa` step type (Phase 5) | Not a standing agent — inline, minimal-context verifier dispatched per workflow, per Phase 1's verification-subagent pattern. |

This table is the direct answer to the "consider future additions" instruction: every one of them resolves to an existing agent gaining a scoped capability, a shared tool, or a workflow-engine mechanism — none of them resolve to a new persona.
