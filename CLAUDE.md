# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**CreativeAgent** is a multi-agent content & creative suite led by **רועי (Roi)**, the CEO/orchestrator. Roi is the mandatory entry point for every request in this workspace — he never does the work himself, he routes each request to the right team member(s) below (in parallel when a task spans domains) and returns one unified report. Full spec: [`PRD-roi.md`](PRD-roi.md), persona: [`.claude/agents/roi.md`](.claude/agents/roi.md).

- **יובל (Yuval)** — a paid-ad creative generator. Accepts a brief (Hebrew or English), selects smart platform/aspect-ratio defaults, and calls **Nano Banana 2** (`gemini-3.1-flash-image-preview` via `@google/genai`) to produce 2K production-ready ad images saved to `output/`.
- **יעל (Yael)** — a marketing content writer. Accepts a brief and produces ready-to-publish copy (LinkedIn posts, newsletters, ad copy, landing pages) saved as `.md` files to `output/`. When the brief needs a visual, Yael automatically dispatches Yuval and returns a complete `copy + creative` package.
- **ליאת (Liat)** — the team's web researcher. Given a topic from Roi, she checks her own search memory to avoid duplicate work, searches the live web, filters to high-quality sourced results, and saves the chosen source to `Content/` for a future content-writer agent to work from. She has no shell/API access and never dispatches other agents herself — she only reports back to Roi. Persona: [`.claude/agents/liat.md`](.claude/agents/liat.md).
- **נגה (Noga)** — *(not yet built)* the team's content rewriter; will take Liat's raw research and rewrite it in our voice for publishing.
- **מירב (Merav)** — *(not yet built)* the team's visual generator for content pieces; will be dispatched when a content piece needs images.

### Team roster & trigger keywords

Roi uses this table (rule-based, not free-form guessing) to decide who to dispatch. Yuval/Yael keywords below are inferred from their descriptions above (not yet formally confirmed); Liat's are as specified when she was built. Noga/Merav have no trigger keywords yet since those agents don't exist.

| Employee | Slug | Domain | Hebrew triggers | English triggers |
|---|---|---|---|---|
| יובל (Yuval) | `yuval` | Paid-ad creative / image generation | תמונה, קריאייטיב, פרסומת, באנר, מודעה ויזואלית | image, ad creative, banner, visual ad |
| יעל (Yael) | `yael` | Marketing copywriting | פוסט, ניוזלטר, מודעה, תוכן שיווקי, טקסט לפרסום | post, newsletter, ad copy, marketing content, landing page |
| ליאת (Liat) | `liat` | Web research — finding quality, current, sourced content | חפש, מצא, מחקר, מאמר על, חדש על, מה קורה עם, מקור על | search, find, research, article about, latest on, news on |
| נגה (Noga) | `noga` | Content rewriting in our voice *(agent not yet built)* | — | — |
| מירב (Merav) | `merav` | Visual generation for content pieces *(agent not yet built)* | — | — |

### New content pipeline (research → rewrite → visual)

When a request is about creating new content sourced from the internet:

1. Roi dispatches **Liat** to find a quality source.
2. Liat returns a file saved in `Content/`.
3. If the original request also asked for **rewriting/publishing** — Roi continues automatically:
   - Dispatches **Noga** on that file.
   - If Noga determines images are needed — Roi dispatches **Merav**.
   - Roi combines everything into `output/`.
4. If the request was only **"find me an article"** — Roi stops after Liat and returns her findings to the user.

## Setup

```bash
npm install
cp .env.example .env   # then add GEMINI_API_KEY
```

Place 2–6 brand/style reference images (`.png`, `.jpg`, `.jpeg`, `.webp`) in `references/` — they are automatically passed as style context to every Yuval generation call.

For Yael, place 2–6 writing samples (`.md`, `.txt`) in `references/writing/` — she loads them to match your tone of voice.

## Running

**Via Claude Code slash commands (preferred):**
```
/yuval <creative brief>       # image generation only
/yael <content brief>         # copy — auto-dispatches Yuval if visual is needed
```

**Direct CLI (Yuval only — Yael runs inside Claude):**
```bash
node scripts/generate.mjs \
  --brief "<brief text>" \
  --aspect 1:1|9:16|16:9|4:5 \
  --platform facebook|instagram|story|google|generic \
  --n <number of variants>
```

`--brief` is required. All other flags have defaults (`1:1`, `generic`, `1`).

## Architecture

| Path | Role |
|------|------|
| `scripts/generate.mjs` | Core engine for Yuval — parses CLI args, loads reference images as base64 inline data, builds the design prompt, calls the Gemini image model, writes PNGs to `output/` |
| `.claude/agents/roi.md` | Roi (CEO) subagent persona — mandatory entry point, routes/dispatches the team per the roster table, aggregates results into one report |
| `.claude/agents/yuval.md` | Yuval subagent persona — orchestrates brief → prompt expansion → `generate.mjs` invocation → returns output path |
| `.claude/agents/yael.md` | Yael subagent persona — orchestrates brief → tone loading → copy writing → optional Yuval dispatch → returns `.md` + optional `.png` |
| `.claude/agents/liat.md` | Liat subagent persona — checks search memory → searches the web → filters by quality → saves source to `Content/` → logs to `liat/Memory/searches.md` → reports to Roi |
| `.claude/commands/yuval.md` | `/yuval` slash command — forwards `$ARGUMENTS` to the yuval subagent |
| `.claude/commands/yael.md` | `/yael` slash command — forwards `$ARGUMENTS` to the yael subagent |
| `.claude/skills/nano-banana-maker.md` | Supporting skill for Yuval — Hebrew text rendering discipline for Nano Banana 2 |
| `.claude/skills/content-craft.md` | Supporting skill for Yael — format-specific output structures, quality checklist, golden rules |
| `references/` | Visual style references (Yuval); not committed |
| `references/writing/` | Writing tone references for Yael (`.md` / `.txt`); not committed |
| `output/` | All generated artifacts — PNGs `<YYYYMMDD-HHMM>-<slug>-<n>.png` (Yuval) and `.md` `<YYYYMMDD-HHMM>-<slug>.md` (Yael); gitignored |
| `liat/Memory/searches.md` | Liat's search log — checked before every new search to avoid duplicate research within 30 days; not committed |
| `Content/` | Raw research sources Liat saves for Noga to rewrite, `<YYYY-MM-DD>-<slug>.md`; not committed |

## Key Behaviour Details

- **Reference loading**: `generate.mjs` reads every supported image in `references/` and sends them as `inlineData` multipart parts alongside the text prompt. No references → model uses a modern minimal aesthetic.
- **Prompt construction**: `buildPrompt()` combines the brief, platform hints, aspect ratio, and a style-reference instruction block. The persona is baked into the prompt text itself.
- **Model**: `gemini-3.1-flash-image-preview` (Nano Banana 2) — called with `generateContent`; requires `config.responseModalities: ["TEXT","IMAGE"]` and `config.imageConfig: { aspectRatio, imageSize: "2K" }`. Image returns as `inlineData` in `response.candidates[].content.parts`.
- **Yuval agent workflow**: (1) glob references, (2) decode brief → pick platform/aspect, (3) expand brief into a rich design prompt, (4) run `node scripts/generate.mjs`, (5) return file path + design decisions.
- **Yael agent workflow**: (1) glob `references/writing/` for tone samples, (2) decode brief → pick format/tone/goal, (3) write full copy + variants following `content-craft.md`, (4) save `.md` to `output/`, (5) if visual is needed — build design brief and dispatch `yuval` via the Agent tool, (6) return copy + image paths + decision summary.
- **Product separation**: Yael owns strategy + words; Yuval owns visual + execution. Yael passes Yuval exact verbatim headline/CTA text — never "something similar".
- **Liat agent workflow**: (1) receive topic/keywords from Roi, (2) Grep `liat/Memory/searches.md` for a similar search in the last 30 days — if found, ask Roi whether to reuse or re-search, (3) `WebSearch` + `WebFetch` the most promising sources, (4) filter by the quality criteria in `.claude/agents/liat.md` and pick the best one, (5) save it to `Content/<YYYY-MM-DD>-<slug>.md` with the source link at the top, (6) log the search in `liat/Memory/searches.md`, (7) report the filename, a 1–2 sentence summary, and the source link back to Roi. Liat never calls Noga or any other agent directly.
