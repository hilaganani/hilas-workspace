# Phase 1 — Research Summary: Orchestration Frameworks

Research date: 2026-07-14. Scope: study proven orchestration architectures to inform Roi's redesign — not to copy any of them, but to borrow validated patterns and understand the trade-offs each one made.

## 1. Anthropic's own guidance (highest-priority source — this is a Claude Code project)

Two primary sources: Anthropic's [multi-agent research system engineering post](https://www.anthropic.com/engineering/multi-agent-research-system) and their [when-to-use-multi-agent-systems guide](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them).

**The load-bearing warning, stated up front because it should gate everything else in this document**: Anthropic's own guidance is to *start with a single agent* and only add multi-agent complexity when there's evidence it's needed. Multi-agent systems cost **3–10x more tokens** than single-agent ones (their research system specifically: ~15x); every subagent is a new failure point and a coordination cost. CreativeAgent already has 6 built agents plus a planned 7th capability — this document does not recommend adding orchestration machinery beyond what the existing scale justifies. Phase 4–5 return to this constraint explicitly.

**Three justified reasons to use multiple agents** (all three already apply to CreativeAgent, which is why the existing design is sound):
- **Context protection** — an SEO specialist's research context shouldn't pollute a copywriter's voice/style context.
- **Parallelization** — Liat researching while nothing else needs to happen first, or Noga+Dani's brief and Merav's images being independent once dispatched.
- **Specialization** — narrow toolsets and prompts (Merav's image-only remit, Noga's zero-API remit) outperform one generalist juggling every domain.

**Orchestrator-worker pattern, concretely**: a lead agent plans (using extended thinking), decomposes into subtasks with *objective + output format + tool guidance + explicit boundaries* for each, spawns workers in parallel where independent, and workers report back to the lead rather than to each other. This is structurally identical to Roi today. The stated anti-patterns to avoid: vague task descriptions (causes duplication/gaps), spawning subagents for simple queries that don't need decomposition, sequential execution of genuinely independent work, and treating a subagent's first success as final without verification.

**Context-centric decomposition, not stage-centric**: split agents where *context* naturally isolates (a research domain, a specialized toolset), not by *pipeline stage* (e.g., splitting "write" and "edit" into two agents créates coordination overhead for no isolation benefit). This directly validates CreativeAgent's existing per-domain agent boundaries (Liat=research, Noga=writing, Merav=visuals, Dani=SEO, Yael=strategy, Gefen=platform-specific) over any alternative that would slice by pipeline stage instead.

**Verification as its own subagent, not inline self-checking**: the most reliable pattern for QA is a dedicated verifier with minimal context transfer doing blackbox validation, explicitly instructed to run complete checks before declaring success (guards against "early victory" false-positives). Relevant directly to Phase 4/7 — a QA loop, if added, should be a distinct step/agent, not folded into the producing agent's own self-report.

## 2. LangGraph

Graph-based orchestration: nodes = computation steps (LLM call, tool call, parse), edges = transitions including conditional branching. Three multi-agent patterns: **supervisor** (one orchestrator delegates to sub-agents — matches Roi today), **hierarchical** (nested supervisors), **collaborative** (peer agents share a message queue, no central authority).

**Strength**: durable **checkpointing** — state saved at every node, survives process restarts, supports human-in-the-loop interrupts (pause a workflow for approval, resume days later), and "time travel" debugging (replay from any checkpoint). Enterprise deployments pair this with a Postgres/Redis-backed checkpointer for multi-instance durability.

**Weakness / trade-off**: the graph must be defined in code up front (Python), state schema is explicit and must be designed carefully, and the checkpointing infrastructure (a real database) is more operational surface than a single-operator project needs.

**Applicable to CreativeAgent**: the *supervisor pattern* is already Roi's shape. The *checkpoint-and-resume-for-human-approval* idea is directly relevant — CreativeAgent already has one real instance of this (the weekly plan email → wait for "אישרתי" in a later session → resume). Phase 5 generalizes this into a reusable pattern instead of a one-off.

## 3. Google Agent Development Kit (ADK)

Three agent types: **LLM Agents** (reasoning), **Workflow Agents** (deterministic orchestration — sequential/parallel/loop primitives, no LLM call needed to decide the *shape* of execution), **Custom Agents** (bespoke logic). Agents organize in a **tree hierarchy**, which structurally limits which agent can hand control to which other agent — a built-in blast-radius control.

**Strength**: separating "does an LLM decide what happens next" (LLM Agent) from "is the shape of execution fixed and just needs to run" (Workflow Agent) is a clean, useful distinction most frameworks blur.

**Weakness / trade-off**: heavier framework investment (Vertex AI integration, enterprise connectors) than a solo-operator project needs; the tree-hierarchy constraint is valuable but adds a modeling step CreativeAgent doesn't currently need at its size.

**Applicable to CreativeAgent**: the **LLM Agent vs. Workflow Agent distinction** is the single most useful idea here, and maps directly onto a recurring theme in this project's history — routing ("which agent handles X") should be **deterministic** (a lookup, not a fresh LLM judgment call every time), while *what each agent does with its task* stays LLM-driven. Roi's original design already leaned this way ("rule-based, not free-form guessing" — see `PRD-roi.md`); Phase 4 makes this an explicit architectural rule rather than an implicit convention.

## 4. OpenAI Agents SDK

Two patterns: **Manager pattern** (a central LLM orchestrates specialists *as tools it calls*, synthesizes results itself) and **Handoffs pattern** (decentralized — an agent transfers the entire conversation to a peer, who takes over). Code-first: workflow logic is expressed in normal code rather than a pre-declared graph, which trades declarative clarity for flexibility.

**Strength**: guardrails (validate inputs/outputs, fail fast) and tracing are first-class, not bolted on.

**Weakness / trade-off**: handoffs are harder to reason about after the fact than a manager pattern, since control genuinely leaves the orchestrator — good for open-ended conversation routing, worse for auditable pipelines with a required final report (which is exactly what CreativeAgent needs — Roi must always produce one unified answer to the user).

**Applicable to CreativeAgent**: confirms the **Manager pattern over Handoffs** is the right choice here — Roi calling agents as delegated tasks and synthesizing the result itself (current design) rather than ever fully transferring control away. Not recommending handoffs for CreativeAgent.

## 5. CrewAI (Crews vs. Flows)

**Crews** = a team of agents collaborating autonomously on a task, stateless, runs once to completion — good for adaptive, open-ended problem solving. **Flows** = an event-driven orchestration layer *around* crews/tasks that adds explicit state, conditional routing, branching, and persistence — deterministic and production-oriented. CrewAI's own guidance: *"for any production-ready application, start with a Flow. Use a Crew within a Flow step when a specific step needs autonomous collaboration."*

**Strength**: this two-layer split (deterministic control layer + autonomous execution layer, composed) maps almost exactly onto what Phase 4–6 need to design for Roi: a **workflow layer** that's deterministic and inspectable, with each **step** dispatching to an agent that reasons autonomously within its own scope.

**Weakness / trade-off**: another framework-specific vocabulary and runtime; not something to adopt wholesale, just the layering idea.

**Applicable to CreativeAgent**: this is the clearest external validation of the target shape — separate "*which steps run, in what order, with what data flowing between them*" (deterministic, config-driven, Phase 6) from "*what each agent does inside its step*" (autonomous, prompt-driven, unchanged).

## 6. Temporal (durable execution)

Workflows (orchestration logic) run on Workers that poll a Temporal Server, which persists all execution state durably (Postgres-backed event sourcing). Activities (actual side-effecting work — an API call, a send) get automatic retry with backoff, and are guaranteed effectively-once — critical for "act-only-once" operations like sending an email or publishing a post. The **Saga pattern** makes compensation (undo logic) a first-class part of workflow code, run automatically when a downstream step fails.

**Strength**: this is the industrial-strength answer to "what if a step fails halfway through a multi-step process" — exactly the class of problem "retry failed steps," "recover gracefully from failures," and "resumable workflows" (all named in the user's brief) point at.

**Weakness / trade-off**: Temporal is a real distributed system — a server, a database, worker processes. Running it is a genuine operational commitment, wildly disproportionate to a solo-operator content studio with (today) maybe a handful of workflow runs per week. This is the clearest example in this research of a pattern worth **borrowing the idea from, not the infrastructure**.

**Applicable to CreativeAgent**: borrow **idempotent effectful steps + explicit retry policy + compensation as documented (not automated) behavior**. Do not adopt Temporal itself, or anything resembling its operational footprint. Phase 5 designs a lightweight, file-based equivalent of "durable state" appropriate to this project's actual scale — not a durable-execution engine.

## 7. Azure Durable Functions

Serverless orchestration functions with the **fan-out/fan-in** pattern as the headline capability: an orchestrator dispatches N parallel activities, then aggregates all results once every branch completes (`Task.WhenAll`-equivalent), all backed by automatic checkpointing so a crash mid-fan-out resumes correctly rather than restarting.

**Strength**: fan-out/fan-in is *exactly* CreativeAgent's most common real shape already — e.g. "Noga writes → Merav generates 3 images in parallel → Roi waits for all → combines into one file." Naming this pattern explicitly is useful for Phase 5's engine design.

**Weakness / trade-off**: like Temporal, this assumes a serverless/cloud runtime CreativeAgent doesn't have or need.

**Applicable to CreativeAgent**: adopt the **fan-out/fan-in vocabulary and semantics** (dispatch N independent tasks, wait for all, then proceed) as one of the workflow engine's core primitives (Phase 5) — this is not new behavior, Roi already does this informally; formalizing it just makes it inspectable and reusable across workflows instead of implicit in each agent's persona prose.

## 8. Model Context Protocol (MCP)

Client-server protocol (JSON-RPC 2.0) connecting an agent to *tools and data sources* — not to other agents. As of 2026, MCP is the de facto standard (97M+ monthly SDK downloads, every major vendor). The relevant distinction found in this research: **MCP is for agent→tool**, a separate emerging protocol (A2A, agent-to-agent) is for **agent→agent** negotiation/delegation — CreativeAgent doesn't need A2A, since Roi's subagent dispatch already handles agent-to-agent coordination through Claude Code's native subagent mechanism, not through a wire protocol.

**Applicable to CreativeAgent**: MCP is already how this project reaches Airtable, Make, Google Drive, Canva, etc (see this session's own work wiring `google-search-console` and `smoove-newsletter`). The main architectural lesson for Phase 6/7: **new capabilities should keep arriving as MCP servers or Skills, not as new agents** — this is already the standing instruction for this project and this research confirms it's the industry-standard shape, not a CreativeAgent-specific constraint.

## 9. Claude Code's own subagent/skill primitives (already available, underused for orchestration specifically)

From this session's own tool surface and earlier research into Skills (see prior work this session): Claude Code subagents (`.claude/agents/*.md`) already support `context: fork` skill execution, tool-scoped permissions per agent, and — relevant to Phase 5 specifically — this environment already exposes `TaskCreate`/`TaskUpdate`/`TaskList` (structured, persistent task tracking used throughout this very session), `ScheduleWakeup`/`CronCreate` (scheduled/delayed resumption), and a scheduled-tasks MCP already used for the weekly plan email. **These are real, already-available building blocks for a lightweight workflow engine** — not hypothetical infrastructure Phase 5 needs to invent from scratch.

## Synthesis: what CreativeAgent should actually borrow

| Pattern | Source | Verdict |
|---|---|---|
| Supervisor/orchestrator-worker, context-centric agent boundaries | Anthropic guidance, LangGraph | **Keep** — this is already Roi's shape; formalize, don't replace |
| Manager pattern (dispatch-and-synthesize) over Handoffs | OpenAI Agents SDK | **Keep** — Roi must always own the final report |
| Deterministic routing layer + autonomous execution layer, composed | CrewAI Flows/Crews | **Adopt as the core shape** for Phases 4–6 |
| LLM Agent vs. Workflow Agent distinction (routing = lookup, not judgment) | Google ADK | **Adopt** — makes routing auditable and fast |
| Fan-out/fan-in as an explicit, named primitive | Azure Durable Functions | **Adopt** — formalizes what Roi already does informally |
| Checkpoint + resume for human-in-the-loop approval | LangGraph | **Adopt in lightweight form** — generalize the existing weekly-email approval pattern |
| Idempotent effectful steps, explicit retry policy, documented compensation | Temporal | **Borrow the concepts, not the infrastructure** |
| Full durable-execution server, distributed workers, event-sourced DB | Temporal, Durable Functions | **Reject as infrastructure** — disproportionate to current scale; revisit only if run volume grows by an order of magnitude |
| 3–10x token cost of multi-agent coordination | Anthropic guidance | **Governing constraint** — every addition in Phases 4–6 must earn its coordination overhead |

Phase 4 onward treats this table as the design brief.
