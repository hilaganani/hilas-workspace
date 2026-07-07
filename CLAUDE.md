# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**CreativeAgent** is a multi-agent content & creative suite led by **רועי (Roi)**, the CEO/orchestrator. Roi is the mandatory entry point for every request in this workspace — he never does the work himself, he routes each request to the right team member(s) below (in parallel when a task spans domains) and returns one unified report. Full spec: [`PRD-roi.md`](PRD-roi.md), persona: [`.claude/agents/roi.md`](.claude/agents/roi.md).

The team is planned at **7 people total**; **3 are built and active today** (Liat, Noga, Merav). The other 4 are named, real roadmap slots — not generic placeholders — but have no persona files yet.

**Built & active:**

- **ליאת (Liat)** — trend researcher. Given a topic from Roi, focused specifically on **marketing and automation** trends and deep research, she checks her own search memory to avoid duplicate work, searches the live web, filters to high-quality sourced results, and saves the chosen source to `Content/` for Noga to work from. She has no shell/API access and never dispatches other agents herself — she only reports back to Roi. Persona: [`.claude/agents/liat.md`](.claude/agents/liat.md).
- **נגה (Noga)** — content writer. Produces newsletters, blog posts (each with a table when the data fits one, plus several custom-generated images sourced from Merav), and social posts for LinkedIn, Facebook/Instagram, and TikTok (text captions/scripts — she has no image or video capability herself). Can rewrite a raw article from `Content/` (Liat's research) or work directly from a brief. Saves output as `.md` + styled `.html` to `output/`. No shell/web/API access and never dispatches other agents — she reports back to Roi and flags which images are needed. Persona: [`.claude/agents/noga.md`](.claude/agents/noga.md).
- **מירב (Merav)** — visual generator. Takes an image brief (usually relayed by Roi from Noga's report) and calls **Nano Banana 2** (`gemini-3.1-flash-image-preview` via `@google/genai`) through `scripts/generate.mjs` to produce 2K content images saved to `output/`. No web access and never dispatches other agents. Persona: [`.claude/agents/merav.md`](.claude/agents/merav.md).

**Planned, not yet built:**

- **יעל (Yael)** — strategic advisor for the business's services and marketing. (Note: an earlier, unrelated "Yael" — a marketing copywriter who dispatched an image-generation agent called Yuval — existed briefly in this project's early planning and was fully deleted; this is a distinct future role that happens to reuse the name.)
- **בר (Bar)** — LinkedIn marketer.
- **גפן (Gefen)** — Instagram marketer.
- **דני (Dani)** — SEO specialist.

### Team roster & trigger keywords

Roi uses this table (rule-based, not free-form guessing) to decide who to dispatch. Only built agents have trigger keywords; the 4 planned agents have a role but no persona file yet, so Roi cannot dispatch them.

| Employee | Slug | Domain | Hebrew triggers | English triggers |
|---|---|---|---|---|
| ליאת (Liat) | `liat` | Trend/deep research on marketing & automation topics | חפש, מצא, מחקר, מגמות, מאמר על, חדש על, מה קורה עם, מקור על, שיווק, אוטומציות | search, find, research, trends, article about, latest on, news on, marketing, automation |
| נגה (Noga) | `noga` | Content writing/rewriting: newsletters, blog posts, social posts | שכתב, ערוך, נסח מחדש, תרגם, סכם, מאמר, תוכן, פוסט, ניוזלטר, בלוג, סושיאל, לינקדאין, אינסטגרם, טיקטוק | rewrite, edit, rephrase, translate, summarize, article, content, post, newsletter, blog, social, linkedin, instagram, tiktok |
| מירב (Merav) | `merav` | Content image generation | תמונה, ויזואל, איור, עיצוב לתמונה | image, visual, illustration, graphic |
| יעל (Yael) | `yael` | Strategic advisor for services/marketing *(not yet built)* | — | — |
| בר (Bar) | `bar` | LinkedIn marketing *(not yet built)* | — | — |
| גפן (Gefen) | `gefen` | Instagram marketing *(not yet built)* | — | — |
| דני (Dani) | `dani` | SEO *(not yet built)* | — | — |

### New content pipeline (research → write → visual)

When a request is about creating new content sourced from the internet:

1. Roi dispatches **Liat** to find a quality source on the requested marketing/automation topic.
2. Liat returns a file saved in `Content/`.
3. If the original request also asked for **rewriting/publishing** — Roi continues automatically:
   - Dispatches **Noga** on that file.
   - Noga's report specifies which image(s) the piece needs — Roi dispatches **Merav** with that brief.
   - Roi combines everything into `output/`.
4. If the request was only **"find me an article"** — Roi stops after Liat and returns her findings to the user.

Noga can also be dispatched directly (without Liat) whenever the request is to write a newsletter/blog post/social post from a brief, or to rewrite/edit/translate/summarize content that's already available — she doesn't require Liat to have run first. Merav can also be dispatched directly whenever a request is purely about generating a content image.

## Setup

```bash
npm install
cp .env.example .env   # then add GEMINI_API_KEY
```

For Merav, place 2–6 brand/style reference images (`.png`, `.jpg`, `.jpeg`, `.webp`) in `references/` — they are automatically passed as style context to every image-generation call.

For Noga, place your style guide at `noga/style-guide.md` and writing samples in `noga/reference/` — she loads both at the start of every task (if they exist) to write/rewrite content in our voice.

## Running

Roi, Liat, Noga, and Merav are all dispatched as subagents (no dedicated slash commands yet — see `PRD-roi.md` open questions for a possible future `/roi` command).

**Direct CLI (Merav's engine, for testing without going through the agent persona):**
```bash
node scripts/generate.mjs \
  --brief "<rich design prompt>" \
  --aspect 1:1|9:16|16:9|4:5 \
  --n <number of variants>
```

`--brief` is required. `--aspect` and `--n` have defaults (`1:1`, `1`).

## Architecture

| Path | Role |
|------|------|
| `scripts/generate.mjs` | Merav's engine — parses CLI args, loads reference images as base64 inline data, builds the design prompt, calls the Gemini image model, writes PNGs to `output/` |
| `.claude/agents/roi.md` | Roi (CEO) subagent persona — mandatory entry point, routes/dispatches the team per the roster table, aggregates results into one report |
| `.claude/agents/liat.md` | Liat subagent persona — checks search memory → searches the web for marketing/automation trends → filters by quality → saves source to `Content/` → logs to `liat/Memory/searches.md` → reports to Roi |
| `.claude/agents/noga.md` | Noga subagent persona — reads style guide/reference → writes/rewrites newsletters, blog posts, or social posts → saves `.md`+`.html` to `output/` → reports to Roi with image needs flagged |
| `.claude/agents/merav.md` | Merav subagent persona — expands an image brief → runs `scripts/generate.mjs` → returns file path(s) to Roi |
| `references/` | Merav's visual style/brand references; not committed |
| `output/` | All generated artifacts — PNGs `<YYYYMMDD-HHMM>-<slug>-<n>.png` (Merav) and `.md`+`.html` pairs matching the source filename (Noga); gitignored |
| `liat/Memory/searches.md` | Liat's search log — checked before every new search to avoid duplicate research within 30 days; not committed |
| `Content/` | Raw research sources Liat saves for Noga to write from, `<YYYY-MM-DD>-<slug>.md`; not committed |
| `noga/style-guide.md` | Noga's writing style guide (may not exist yet — she falls back to a clear, professional default and flags it if missing); not committed |
| `noga/reference/` | Example texts in our writing voice, for Noga to match; not committed |

## Key Behaviour Details

- **Reference loading**: `generate.mjs` reads every supported image in `references/` and sends them as `inlineData` multipart parts alongside the text prompt. No references → model uses a modern minimal aesthetic.
- **Prompt construction**: `buildPrompt()` combines the brief, aspect ratio, and a style-reference instruction block. The persona is baked into the prompt text itself.
- **Model**: `gemini-3.1-flash-image-preview` (Nano Banana 2) — called with `generateContent`; requires `config.responseModalities: ["TEXT","IMAGE"]` and `config.imageConfig: { aspectRatio, imageSize: "2K" }`. Image returns as `inlineData` in `response.candidates[].content.parts`.
- **Liat agent workflow**: (1) receive topic/keywords from Roi (marketing/automation focus), (2) Grep `liat/Memory/searches.md` for a similar search in the last 30 days — if found, ask Roi whether to reuse or re-search, (3) `WebSearch` + `WebFetch` the most promising sources, (4) filter by the quality criteria in `.claude/agents/liat.md` and pick the best one, (5) save it to `Content/<YYYY-MM-DD>-<slug>.md` with the source link at the top, (6) log the search in `liat/Memory/searches.md`, (7) report the filename, a 1–2 sentence summary, and the source link back to Roi. Liat never calls Noga or any other agent directly.
- **Noga agent workflow**: (1) pull an article from `Content/` or work from a direct brief, (2) read `noga/style-guide.md` and `noga/reference/` if not already read this session (fall back to a clear professional default if they don't exist yet), (3) write/rewrite in our voice for the requested format (newsletter, blog post with a table if the data fits one, or a platform-specific social post/caption for LinkedIn, Facebook/Instagram, or TikTok) — stripping any links/CTAs/self-promotion pointing back to a source author, while keeping organic brand mentions inside the story itself, (4) save `<name>.md` and a styled `<name>.html` (inline `<style>`, no external build tooling) to `output/`, (5) report back to Roi, explicitly listing which image(s) the piece needs (brief per image) so Roi can dispatch Merav. Noga never calls Merav or any other agent directly.
- **Merav agent workflow**: (1) receive an image brief from Roi, (2) pick an aspect ratio appropriate to the platform/placement, (3) expand the brief into a rich design prompt, (4) run `node scripts/generate.mjs`, (5) return the file path(s) and design decisions to Roi. Merav never calls other agents.
