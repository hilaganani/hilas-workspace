# Phase 8 — Memory Architecture

## 1. What exists today (per Phase 2's audit, restated for this phase's purpose)

- **Airtable** is already CreativeAgent's primary durable, structured memory — the existing-content table (publishing history), the monthly content planner, and the digital-product-ideas table (offers) are all read by Yael/Dani today and are the closest thing this project has to a real long-term memory store.
- **Local per-agent folders** (`dani/outputs/`, `merav/outputs/`, `yael/outputs/`, `noga/style-guide.md`) hold rich history, but are gitignored and machine-local — this session directly discovered the risk this creates (the Google Drive "backup" folder found earlier turned out to be a stale snapshot from before a machine switch, meaning a full week of this project's history existed nowhere durable during the gap).
- **Claude Code's own general-purpose memory system** (this session's `~/.claude/.../memory/`) exists but is explicitly scoped to *how Claude should collaborate with this user* (preferences, feedback, project facts) — not to *structured business data about content performance*. It should stay out of CreativeAgent's domain memory design; conflating the two would violate that system's own stated exclusions (don't store what's derivable from files/git, don't store ephemeral task detail).
- **No memory of *why* a decision was made** exists anywhere. This session generated at least three concrete instances of exactly the kind of thing worth remembering and currently isn't: "Canva doesn't achieve template-mode via this API, don't retry," "the old Drive folder is a stale one-time snapshot, not a live source," "the existing Make scenario is broken and uses a retired model." All three would have to be independently rediscovered by a future session with no memory of this one.

## 2. Should CreativeAgent maintain structured long-term memory? Yes — but extend what already works, don't replace it

The instinct to build a new, separate "memory system" should be resisted per this whole project's governing constraint (avoid unnecessary complexity, prefer extending proven infrastructure). Airtable is already proven, already has read/write skills, already holds three of the eight requested categories adequately. The real gap is narrower than "build a memory system" — it's: **one missing category (decisions/learnings) and a durability risk on categories that already exist locally but not centrally.**

## 3. Category-by-category recommendation

| Category | Current state | Recommendation | Automatic or curated? |
|---|---|---|---|
| **Campaigns** | Not tracked as a grouping concept anywhere | New Airtable table, linking related content items across channels (e.g. one course launch spans a newsletter + 3 social posts + a blog piece) | Curated — Yael creates/links entries during monthly planning, not auto-generated per post |
| **Successful / failed content** | No performance-feedback loop closes back to memory (Marketing OS Audit finding); raw data will exist once GA4 lands (Search Console already does) | **Do not build a separate memory table for raw metrics** — query Search Console/future GA4/Smoove live instead, since a cached copy would go stale exactly like the Drive backup did. Do add a small **qualitative learnings** field (see "decisions & learnings" below) for the human-judgment layer numbers alone don't capture ("this angle resonated, this one didn't, here's why we think so") | Curated, low-frequency, judgment-based |
| **Audience insights** | Static prose in `yael/strategy.md` | No new structure — stays prose, reviewed/updated by Yael periodically. Structuring this now would be premature; no workflow currently generates audience insight *events* to accumulate | N/A — remains temporary/prose by design |
| **Offers** | Already tracked (`digital-product-ideas` Airtable table) | No change — already the right home | Curated, as today |
| **Hooks** | Doesn't exist | **Defer.** A hooks library is only valuable once there's a performance signal to know which hooks actually worked — building it before the performance-feedback loop (Marketing OS Audit P0 #1, partially done via Search Console) would mean guessing at what's worth keeping. Revisit once GA4/Smoove-open-rate data exists | Deferred |
| **SEO history** | Already exists (`dani/outputs/`), richer now with Search Console | No new structure. **Durability flag**: this is local-only; same class of risk as the Drive-backup discovery. Not urgent (nothing lost yet), but worth the same caution | Automatic (already how Dani works), local |
| **Publishing history** | Already exists (existing-content Airtable table + Dani's publish-log skill) | No change — already adequate and already automatic-on-report (create-only, per the existing design) | Automatic, on explicit user report |
| **Brand decisions** | Exists only as static snapshots (`brand-guidelines.md`, `noga/style-guide.md`) — the *current* rules, not the *history* of why they were set or changed | **Add** — see below | Curated, lightweight |

## 4. The one concrete new piece: a decisions & learnings log

**What**: a single append-only file, `yael/decisions-log.md` (same gitignored, local-working-file convention as her other outputs — this is working memory, not a deliverable). Each entry: date, one-line decision or learning, one-line reason, which agent/session it came from.

**Example, using real entries this exact session would have produced**:
```markdown
## 2026-07-14
- Canva API doesn't support template/visual-editor mode via POST /v1/Campaigns-equivalent flows tested — don't retry without a genuinely new approach. (Merav investigation)
- Smoove campaign creation always lands in raw HTML editor mode, even with templateId set — same conclusion, don't retry. (Noga/smoove-newsletter investigation)
- Decided against building "Bar" (LinkedIn agent) — fold into a publishing tool Noga/Dani share instead. (Marketing OS Audit)
```

**Why this specific, minimal design**:
- **Solves the actual observed problem** (this session re-investigating things a prior session would have already settled) at near-zero cost — one file, no new skill, no new Airtable table, no new agent.
- **Consistent with Claude Code's own memory-system philosophy** already governing this project (the auto-memory system's own instructions: capture the *why*, not things derivable from files/git — a decisions log is exactly "the why" for domain decisions the general memory system correctly stays out of).
- **Who writes to it**: any agent, when it reaches a "we tried X, it doesn't work, here's why" or "we decided X over Y" moment — this is a natural byproduct of existing work, not a new task. Practically, Yael is the natural owner/curator since she already reads/writes strategic context, but any agent (Dani, Merav) can append.
- **Who reads it**: Roi, at planning time (Phase 4 §3), before dispatching — a cheap check that prevents exactly the redundant-investigation pattern observed today. This is a natural addition to Roi's new `Read` usage, not a new tool grant.

## 5. What should explicitly stay temporary (not memory)

- Anything already durably recorded in Airtable, git, or `output/`/`dani/outputs/` — do not duplicate it into a memory file, per the same "don't store what's derivable from files" principle used throughout this project.
- In-progress workflow state (Phase 5's task records) — this is *execution* state, not *domain* memory; it's cleaned up/archived once a run completes, not accumulated as long-term memory.
- Raw performance metrics — query live (Search Console/GA4/Smoove), never cache into memory, exactly to avoid the staleness risk this session already encountered once with the Drive backup.

## 6. Explicitly not recommended

- **A vector database / semantic search memory layer.** Nothing in this project's actual scale (a handful of workflow runs per week, a single operator) justifies this — it's the memory-architecture equivalent of the Temporal-vs-lightweight-engine decision in Phase 5, and the same reasoning applies.
- **Per-agent private memory files** beyond what already exists (Liat's search-dedup log is the one legitimate case, kept as-is — it solves a real, narrow problem: don't re-research the same topic within 30 days).
