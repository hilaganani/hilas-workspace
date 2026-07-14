# Phase 6 — Configuration-Driven Architecture

## 1. Format decision: YAML

**Recommendation: YAML**, one file per workflow, under a new `.claude/workflows/` directory.

**Justification, against the alternatives actually considered**:

| Criterion | YAML | JSON | Markdown-with-frontmatter (status quo) |
|---|---|---|---|
| Human-editable by the project's actual maintainer (non-engineer-by-trade, edits `.env`/persona files directly today) | Yes — this is exactly the population YAML was designed for (Kubernetes, GitHub Actions, Ansible all target the same "operators who aren't primarily software engineers" audience) | Technically fine, but no comments and stricter punctuation (trailing commas, quoting) make hand-editing more error-prone for this specific user | Currently how everything works, but per Phase 2's audit, prose config is exactly the thing causing duplicated/driftable logic |
| Supports inline comments explaining *why* a step exists | Yes (`#`) | No | Yes, but comments are indistinguishable from the rules themselves |
| Matches existing precedent in comparable tools | CrewAI Flows, GitHub Actions, Kubernetes, Ansible all use YAML for this exact "declarative pipeline" purpose (Phase 1) | Used more for data interchange than hand-authored pipelines | N/A |
| Diff-friendly in git | Yes | Yes | Yes |
| Parseable by both a future validator script *and* directly readable by Roi (an LLM) without a parser | Yes | Yes | No — prose requires re-interpretation, which is the duplication problem |

JSON was the closest alternative and is not a bad choice technically; YAML wins specifically on comment support and on matching the precedent of every comparable "declarative workflow definition" tool identified in Phase 1's research, which matters for anyone (including a future Claude session) who has seen those formats before and needs zero ramp-up to read this project's workflow files.

## 2. Where config lives

```
.claude/workflows/
  seo-gated-content.yaml       (W3)
  content-with-visuals.yaml    (W2)
  research-only.yaml           (W1)
  instagram-content.yaml       (W4)
  monthly-planning.yaml        (W6)
  weekly-plan-email.yaml       (W7)
  publish-report.yaml          (W8)
  newsletter-to-smoove.yaml    (W10)
  _schema.md                   (documents every field, required vs optional, with one fully-commented example)
```

Standalone single-agent consults (W9 — Dani's five solo skills, Merav direct generation, Liat direct research, Gefen profile work) **do not need a workflow file** — they're already just "dispatch one agent," which is Roi's fallback path (Phase 4 §3, the "no match" branch) and gains nothing from being expressed as a one-step YAML file. Config is for **multi-step** workflows specifically; this keeps the config surface proportional to actual coordination complexity, per Phase 1's governing constraint.

## 3. Schema, illustrated with a real cataloged workflow (W3)

```yaml
id: seo-gated-content
name: "SEO-gated blog/LinkedIn content pipeline"
description: >
  Blog/website or LinkedIn content where organic search matters:
  SEO research folds into the brief before writing, SEO review happens after.

trigger:
  content_type: [blog, website, linkedin]     # excludes facebook/instagram/tiktok — Dani's own documented boundary
  keywords_he: [SEO, קידום אתרים, מאמר, בלוג]
  keywords_en: [seo, article, blog post]

deliverables:
  - noga_draft            # output/*.md + *.html
  - dani_seo_package       # dani/outputs/<name>-seo.md
  - merav_images           # conditional

steps:
  - id: strategic_gate
    type: gate
    agent: yael
    run_if: is_new_topic            # skipped entirely for rewrite/edit/translate — matches W5's documented behavior
    verdicts: [fits, needs_adjustment, new_strategic_move]
    on_verdict:
      fits: continue
      needs_adjustment: surface_to_user_and_halt
      new_strategic_move: surface_to_user_and_halt

  - id: dani_pre_write
    agent: dani
    depends_on: [strategic_gate]
    retry: { max_attempts: 1, on: [tool_error, empty_output] }

  - id: noga_write
    agent: noga
    depends_on: [dani_pre_write]
    inputs_from: [dani_pre_write]    # Dani's brief is folded into Noga's dispatch prompt

  - id: dani_post_review
    agent: dani
    depends_on: [noga_write]
    inputs_from: [noga_write, dani_pre_write]   # reviews draft against his own earlier brief

  - id: merav_images
    agent: merav
    depends_on: [noga_write]
    run_if: needs_images              # resolved from Noga's {{IMAGE_NEEDED}} count, not a user flag
    fan_out: per_placeholder
    qa: null                          # no QA step defined for this workflow today — see §5

  - id: combine
    type: synthesis
    depends_on: [dani_post_review, merav_images]
    output: "output/<slug>.md + .html, dani/outputs/<slug>-seo.md"

completion_criteria:
  - dani_seo_package references the final draft (not a stale pre-write version)
  - all {{IMAGE_NEEDED}} placeholders resolved or explicitly reported as unresolved
```

This is a direct, lossless translation of W3 as already documented in Phase 3's catalog — nothing about *what* the workflow does changes; only its representation does.

## 4. How a new workflow gets added (the actual test of "config-driven")

To add, say, a future "video short from blog post" workflow: author one new YAML file declaring its steps/dependencies/agents. **Zero changes to `roi.md` or any specialist agent's persona are required** for the new workflow to become available — Roi's persona already says "consult `.claude/workflows/` for a matching template" (Phase 4); it does not enumerate workflows by name. This is the concrete backward-compatible test this design must pass, and it's why the schema (§3) captures everything workflow-specific (steps, dependencies, conditions, retries) as data rather than leaving any of it implicit in Roi's prose.

## 5. What stays out of config (deliberately)

- **Agent personas, prompts, and domain logic** stay exactly where they are today (`.claude/agents/*.md`) — config declares *that* Dani runs at a given step with given inputs, never *how* Dani does SEO research. This preserves the existing, working separation between "orchestration" (now data) and "domain expertise" (still prose, still owned by each specialist).
- **Trigger-keyword routing for standalone single-agent work** (W9) stays in `CLAUDE.md`'s existing roster table — only *multi-step* coordination moves to YAML, per §2's reasoning.
- **Skill-level logic** (`.claude/skills/*/SKILL.md`) is unaffected by this phase entirely — skills remain markdown, invoked by the agent that owns them, exactly as today.

## 6. Validation (forward-looking, not built in this phase)

Per the "Do NOT write code" constraint on this whole project, no validator is built now. Phase 9's roadmap flags a lightweight schema-check script (e.g. confirming every `depends_on` references a real step id, every `agent` is a real persona, no cycles in the dependency graph) as a natural, low-risk follow-up once the config format itself is approved — this is exactly the kind of deterministic, scriptable check that should be a script (per this project's own established "don't punt determinism to the LLM" convention, e.g. `readability_he.py`), not something Roi verifies by reading carefully each time.
