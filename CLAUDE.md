# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**CreativeAgent** is a multi-agent content & creative suite led by **רועי (Roi)**, the CEO/orchestrator. Roi is the mandatory entry point for every request in this workspace — he never does the work himself, he routes each request to the right team member(s) below (in parallel when a task spans domains) and returns one unified report. Full spec: [`PRD-roi.md`](PRD-roi.md), persona: [`.claude/agents/roi.md`](.claude/agents/roi.md).

The team is planned at **7 people total**; **4 are built and active today** (Liat, Noga, Merav, Dani). The other 3 are named, real roadmap slots — not generic placeholders — but have no persona files yet.

**Built & active:**

- **ליאת (Liat)** — trend researcher. Given a topic from Roi, focused specifically on **marketing and automation** trends and deep research, she checks her own search memory to avoid duplicate work, searches the live web, filters to high-quality sourced results, and saves the chosen source to `Content/` for Noga to work from. She has no shell/API access and never dispatches other agents herself — she only reports back to Roi. Persona: [`.claude/agents/liat.md`](.claude/agents/liat.md).
- **נגה (Noga)** — content writer. Produces newsletters, blog posts (each with a table when the data fits one, plus several custom-generated images sourced from Merav), and social posts for LinkedIn, Facebook/Instagram, and TikTok (text captions/scripts — she has no image or video capability herself). Can rewrite a raw article from `Content/` (Liat's research) or work directly from a brief. Saves output as `.md` + styled `.html` to `output/`. No shell/web/API access and never dispatches other agents — she reports back to Roi and flags which images are needed. Persona: [`.claude/agents/noga.md`](.claude/agents/noga.md).
- **מירב (Merav)** — visual generator. Takes an image brief (usually relayed by Roi from Noga's `{{IMAGE_NEEDED: ...}}` placeholders) and calls **`gpt-image-2`** (OpenAI Images API) through the `gpt-image-gen` skill to produce content images, saved to `merav/outputs/` alongside a `.txt` of the prompt used. Scans `merav/reference/` for style consistency across images, and — for social-media images, any content going on the user's own website/blog (the default for her content), or explicitly "branded" requests — follows `merav/brand-guidelines.md` (color palette, graphic style, tone). No web access beyond the API call itself and never dispatches other agents. Persona: [`.claude/agents/merav.md`](.claude/agents/merav.md).
- **דני (Dani)** — SEO specialist. Runs twice around Noga, only for content going to the **website/blog or LinkedIn** (not Facebook/Instagram/TikTok): **before** Noga writes, he researches live (target keyword, competitors, heading structure) and hands Roi a pre-writing SEO brief (primary/secondary keywords, title options, recommended H2/H3 structure, target length); **after** Noga finishes, he reviews her draft against that brief and produces a publish-ready SEO package — SEO title, meta description, URL slug, keywords used, alt-text suggestions per image, plus non-blocking improvement notes. One-pass only: he never forces a rewrite or edits Noga's files himself. Saves his package to `dani/outputs/<name>-seo.md`. Has live web access (`WebSearch`/`WebFetch`) but no other API access and never dispatches other agents — reports to Roi only. Persona: [`.claude/agents/dani.md`](.claude/agents/dani.md).

**Planned, not yet built:**

- **יעל (Yael)** — strategic advisor for the business's services and marketing. (Note: an earlier, unrelated "Yael" — a marketing copywriter who dispatched an image-generation agent called Yuval — existed briefly in this project's early planning and was fully deleted; this is a distinct future role that happens to reuse the name.)
- **בר (Bar)** — LinkedIn marketer.
- **גפן (Gefen)** — Instagram marketer.

### Team roster & trigger keywords

Roi uses this table (rule-based, not free-form guessing) to decide who to dispatch. Only built agents have trigger keywords; the 3 planned agents have a role but no persona file yet, so Roi cannot dispatch them.

| Employee | Slug | Domain | Hebrew triggers | English triggers |
|---|---|---|---|---|
| ליאת (Liat) | `liat` | Trend/deep research on marketing & automation topics | חפש, מצא, מחקר, מגמות, מאמר על, חדש על, מה קורה עם, מקור על, שיווק, אוטומציות | search, find, research, trends, article about, latest on, news on, marketing, automation |
| נגה (Noga) | `noga` | Content writing/rewriting: newsletters, blog posts, social posts | שכתב, ערוך, נסח מחדש, תרגם, סכם, מאמר, תוכן, פוסט, ניוזלטר, בלוג, סושיאל, לינקדאין, אינסטגרם, טיקטוק | rewrite, edit, rephrase, translate, summarize, article, content, post, newsletter, blog, social, linkedin, instagram, tiktok |
| מירב (Merav) | `merav` | Content image generation (gpt-image-2) | תמונה של, ציור של, תיצור תמונה, איור, תמונה, ויזואל, עיצוב לתמונה | image of, picture of, generate image, illustration, draw, image, visual, graphic |
| דני (Dani) | `dani` | SEO: pre-writing brief for Noga + post-writing review/metadata, website/blog or LinkedIn content only | SEO, קידום אתרים, מילות מפתח, מטא תיאור, כותרת SEO, אופטימיזציה לגוגל, דירוג בגוגל | seo, keyword research, meta description, title tag, search ranking, optimize for search |
| יעל (Yael) | `yael` | Strategic advisor for services/marketing *(not yet built)* | — | — |
| בר (Bar) | `bar` | LinkedIn marketing *(not yet built)* | — | — |
| גפן (Gefen) | `gefen` | Instagram marketing *(not yet built)* | — | — |

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

### Noga ↔ Merav connection (article with images)

When Roi receives a request to create an article/post that needs images, the full loop is:

1. Roi dispatches **Noga** to write the piece.
2. While writing, Noga marks every place an image is needed with a `{{IMAGE_NEEDED: "detailed description, including desired style for Merav"}}` placeholder directly in her `.md` output — she does not generate images herself.
3. Noga reports back to Roi: a summary of what she wrote, plus the full list of every `{{IMAGE_NEEDED: ...}}` placeholder she left.
4. Roi dispatches **Merav** with those placeholder descriptions as image briefs.
5. Roi takes Merav's generated images and combines them into Noga's `.md` and `.html` files, replacing each placeholder with the corresponding image.
6. Roi saves the final, combined version to `output/`.

### Dani ↔ Noga connection (SEO for website/LinkedIn content)

When Roi receives a request to write a blog/website article or a LinkedIn post (not Facebook/Instagram/TikTok), the full loop is:

1. Roi dispatches **Dani** first, with the topic/brief (and Liat's research file, if any). Dani researches live and returns a pre-writing SEO brief: primary/secondary keywords, title options, recommended heading structure, target length.
2. Roi folds that SEO brief into the brief it hands to **Noga**, who writes as usual (including `{{IMAGE_NEEDED}}` placeholders where relevant).
3. Once Noga is done, Roi dispatches **Dani** again with Noga's final `.md`, this time to review it against his own pre-writing brief and produce a publish-ready SEO package: SEO title, meta description, URL slug, keywords used, alt-text suggestions per image, and non-blocking improvement notes.
4. Dani saves that package to `dani/outputs/<name>-seo.md` and reports it to Roi.
5. If the piece also needs images, Roi continues the Noga ↔ Merav loop above and combines everything — text, images, and Dani's SEO package — into one report and into `output/`.
6. Dani's improvement notes are suggestions only — Roi never sends Noga back for an automatic rewrite; the notes are surfaced to the user, who decides whether to request changes.

Dani can also be dispatched directly, without Noga, for a pure SEO consult or keyword research request.

## Setup

```bash
cp .env.example .env   # then add OPENAI_API_KEY
```

For Merav, place 2–6 style reference images (`.png`, `.jpg`, `.jpeg`, `.webp`) in `merav/reference/` — she scans them for style/palette/composition cues before generating each image, for visual consistency across the project. Her brand guidelines live at `merav/brand-guidelines.md` (transcribed from `merav/brand-guidelines.pdf`) — she follows these specifically for social-media images or explicitly "branded" requests.

For Noga, place your style guide at `noga/style-guide.md` and writing samples in `noga/reference/` — she loads both at the start of every task (if they exist) to write/rewrite content in our voice.

## Running

Roi, Liat, Noga, Merav, and Dani are all dispatched as subagents (no dedicated slash commands yet — see `PRD-roi.md` open questions for a possible future `/roi` command).

## Architecture

| Path | Role |
|------|------|
| `.claude/agents/roi.md` | Roi (CEO) subagent persona — mandatory entry point, routes/dispatches the team per the roster table, aggregates results into one report |
| `.claude/agents/liat.md` | Liat subagent persona — checks search memory → searches the web for marketing/automation trends → filters by quality → saves source to `Content/` → logs to `liat/Memory/searches.md` → reports to Roi |
| `.claude/agents/noga.md` | Noga subagent persona — reads style guide/reference → writes/rewrites newsletters, blog posts, or social posts (marking `{{IMAGE_NEEDED: ...}}` placeholders where images belong) → saves `.md`+`.html` to `output/` → reports to Roi with the placeholder list |
| `.claude/agents/merav.md` | Merav subagent persona — scans `merav/reference/` for style → expands an image brief → calls the `gpt-image-gen` skill (`gpt-image-2`) → verifies the output file → returns file path(s) to Roi |
| `.claude/agents/dani.md` | Dani subagent persona — before Noga writes: researches live and hands Roi a pre-writing SEO brief (keywords, heading structure, target length); after Noga writes: reviews her draft and produces a publish-ready SEO package (title, meta description, slug, keywords, alt-text, non-blocking notes) → saves to `dani/outputs/` → reports to Roi |
| `.claude/skills/gpt-image-gen/SKILL.md` | Wrapper skill for the OpenAI Images API (`gpt-image-2`) — curl recipe + Python fallback for base64 decoding |
| `merav/reference/` | Merav's style/brand reference images, used for cross-image visual consistency; not committed |
| `merav/brand-guidelines.md` | Merav's brand guidelines (colors, typography, logo rules, graphic style, tone) — followed for social-media/explicitly-branded image requests; not committed |
| `merav/outputs/` | Merav's generated images (`<YYYY-MM-DD>-<slug>.png`) plus a matching `.txt` of the prompt used for each; not committed |
| `dani/outputs/` | Dani's SEO packages (`<name>-seo.md`), matching Noga's output filenames; not committed |
| `output/` | Final combined artifacts — Noga's `.md`+`.html` pairs (with Merav's images embedded by Roi in place of the `{{IMAGE_NEEDED}}` placeholders); gitignored |
| `liat/Memory/searches.md` | Liat's search log — checked before every new search to avoid duplicate research within 30 days; not committed |
| `Content/` | Raw research sources Liat saves for Noga to write from, `<YYYY-MM-DD>-<slug>.md`; not committed |
| `noga/style-guide.md` | Noga's writing style guide (may not exist yet — she falls back to a clear, professional default and flags it if missing); not committed |
| `noga/reference/` | Example texts in our writing voice, for Noga to match; not committed |

## Key Behaviour Details

- **Liat agent workflow**: (1) receive topic/keywords from Roi (marketing/automation focus), (2) Grep `liat/Memory/searches.md` for a similar search in the last 30 days — if found, ask Roi whether to reuse or re-search, (3) `WebSearch` + `WebFetch` the most promising sources, (4) filter by the quality criteria in `.claude/agents/liat.md` and pick the best one, (5) save it to `Content/<YYYY-MM-DD>-<slug>.md` with the source link at the top, (6) log the search in `liat/Memory/searches.md`, (7) report the filename, a 1–2 sentence summary, and the source link back to Roi. Liat never calls Noga or any other agent directly.
- **Noga agent workflow**: (1) pull an article from `Content/` or work from a direct brief, (2) read `noga/style-guide.md` and `noga/reference/` if not already read this session (fall back to a clear professional default if they don't exist yet), (3) write/rewrite in our voice for the requested format (newsletter, blog post with a table if the data fits one and `{{IMAGE_NEEDED: "..."}}` placeholders wherever an image belongs, or a platform-specific social post/caption for LinkedIn, Facebook/Instagram, or TikTok) — stripping any links/CTAs/self-promotion pointing back to a source author, while keeping organic brand mentions inside the story itself, (4) save `<name>.md` and a styled `<name>.html` (inline `<style>`, no external build tooling) to `output/`, (5) report back to Roi: a summary plus the full list of `{{IMAGE_NEEDED}}` placeholders left in the piece. Noga never calls Merav or any other agent directly, and never generates the images herself.
- **Merav agent workflow**: (1) receive an image brief from Roi (usually one of Noga's `{{IMAGE_NEEDED}}` descriptions), (2) scan `merav/reference/` for style/palette/composition cues if it isn't empty, (3) check whether the request is for a social-media image, content going on the user's own website/blog (the default), or explicitly "branded" — if so, read `merav/brand-guidelines.md` and apply its color palette/graphic style/tone, (4) expand the brief into a rich design prompt combining the request with the extracted style and/or brand guidelines, (5) call the `gpt-image-gen` skill (model `gpt-image-2` — never substitute another model; API failures are almost always a bad key or bad parameters, not the model name), (6) save the image to `merav/outputs/<YYYY-MM-DD>-<slug>.png` plus a matching `.txt` of the prompt used, (7) verify the file exists and is larger than 0 bytes before reporting success, (8) report the file path(s), which references were used, and whether brand guidelines were applied, back to Roi. Merav never calls other agents. Roi is responsible for embedding Merav's images into Noga's `.md`/`.html` files in place of the `{{IMAGE_NEEDED}}` placeholders and saving the final combined version to `output/`.
- **Dani agent workflow**: runs twice around Noga, for website/blog or LinkedIn content only. **Pre-write**: (1) receive the topic/brief from Roi (plus Liat's research file, if relevant), (2) `WebSearch`/`WebFetch` to identify a primary keyword, 2–4 secondary keywords, search intent, and the heading structure/length of currently top-ranking pages, (3) assemble a pre-writing SEO brief (keywords, 1–3 title options, recommended H2/H3 structure, target length, internal/external linking ideas), (4) report it to Roi, who folds it into Noga's brief. **Post-write**: (5) receive Noga's finished `.md` from Roi, (6) review it against his own pre-writing brief (keyword placement, heading structure), (7) produce a publish-ready SEO package — SEO title (50–60 chars), meta description (150–160 chars), URL slug, keywords actually used, alt-text suggestions per image/`{{IMAGE_NEEDED}}` placeholder, and non-blocking improvement notes, (8) save it to `dani/outputs/<name>-seo.md`, (9) report the file path plus the package inline to Roi. Dani never edits Noga's files, never blocks or forces a rewrite (one-pass review only), and never calls other agents.
