# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**CreativeAgent** is a two-agent content & creative suite:

- **יובל (Yuval)** — a paid-ad creative generator. Accepts a brief (Hebrew or English), selects smart platform/aspect-ratio defaults, and calls **Nano Banana 2** (`gemini-3.1-flash-image-preview` via `@google/genai`) to produce 2K production-ready ad images saved to `output/`.
- **יעל (Yael)** — a marketing content writer. Accepts a brief and produces ready-to-publish copy (LinkedIn posts, newsletters, ad copy, landing pages) saved as `.md` files to `output/`. When the brief needs a visual, Yael automatically dispatches Yuval and returns a complete `copy + creative` package.

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
| `.claude/agents/yuval.md` | Yuval subagent persona — orchestrates brief → prompt expansion → `generate.mjs` invocation → returns output path |
| `.claude/agents/yael.md` | Yael subagent persona — orchestrates brief → tone loading → copy writing → optional Yuval dispatch → returns `.md` + optional `.png` |
| `.claude/commands/yuval.md` | `/yuval` slash command — forwards `$ARGUMENTS` to the yuval subagent |
| `.claude/commands/yael.md` | `/yael` slash command — forwards `$ARGUMENTS` to the yael subagent |
| `.claude/skills/nano-banana-maker.md` | Supporting skill for Yuval — Hebrew text rendering discipline for Nano Banana 2 |
| `.claude/skills/content-craft.md` | Supporting skill for Yael — format-specific output structures, quality checklist, golden rules |
| `references/` | Visual style references (Yuval); not committed |
| `references/writing/` | Writing tone references for Yael (`.md` / `.txt`); not committed |
| `output/` | All generated artifacts — PNGs `<YYYYMMDD-HHMM>-<slug>-<n>.png` (Yuval) and `.md` `<YYYYMMDD-HHMM>-<slug>.md` (Yael); gitignored |

## Key Behaviour Details

- **Reference loading**: `generate.mjs` reads every supported image in `references/` and sends them as `inlineData` multipart parts alongside the text prompt. No references → model uses a modern minimal aesthetic.
- **Prompt construction**: `buildPrompt()` combines the brief, platform hints, aspect ratio, and a style-reference instruction block. The persona is baked into the prompt text itself.
- **Model**: `gemini-3.1-flash-image-preview` (Nano Banana 2) — called with `generateContent`; requires `config.responseModalities: ["TEXT","IMAGE"]` and `config.imageConfig: { aspectRatio, imageSize: "2K" }`. Image returns as `inlineData` in `response.candidates[].content.parts`.
- **Yuval agent workflow**: (1) glob references, (2) decode brief → pick platform/aspect, (3) expand brief into a rich design prompt, (4) run `node scripts/generate.mjs`, (5) return file path + design decisions.
- **Yael agent workflow**: (1) glob `references/writing/` for tone samples, (2) decode brief → pick format/tone/goal, (3) write full copy + variants following `content-craft.md`, (4) save `.md` to `output/`, (5) if visual is needed — build design brief and dispatch `yuval` via the Agent tool, (6) return copy + image paths + decision summary.
- **Product separation**: Yael owns strategy + words; Yuval owns visual + execution. Yael passes Yuval exact verbatim headline/CTA text — never "something similar".
