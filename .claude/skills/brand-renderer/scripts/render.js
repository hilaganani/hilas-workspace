#!/usr/bin/env node
/**
 * brand-renderer — generic skill, not Merav-specific.
 *
 * Public API is asset_type + assets + content only. Callers never see template
 * filenames, pixel dimensions, or CSS - that mapping lives in catalog.json and
 * is this script's own internal concern.
 *
 * Reads brand colors/fonts from the shared brand/ folder at the repo root
 * (not a private copy) so any future capability can share the same source.
 *
 * Usage:
 *   node render.js --config path/to/content.json
 *
 * Config shape:
 *   {
 *     "asset_type": "instagram_quote" | "instagram_story" | "linkedin_banner",
 *     "assets": { "background": "/path/to/existing-concept-image.png" },
 *     "content": { "headline": "...", "caption": "...", "credit": "..." },
 *     "out": "/path/to/final.png"
 *   }
 */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const SKILL_ROOT = path.join(__dirname, "..");
const TEMPLATES_DIR = path.join(SKILL_ROOT, "templates");
const CATALOG_PATH = path.join(__dirname, "catalog.json");
const BRAND_ROOT = path.join(SKILL_ROOT, "..", "..", "..", "brand");

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function mimeFor(file) {
  const ext = path.extname(file).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  return "image/png";
}

function fileToDataUri(file, mime) {
  return `data:${mime};base64,${fs.readFileSync(file).toString("base64")}`;
}

function buildFontFaces(tokens) {
  let css = "";
  for (const role of Object.values(tokens.fonts)) {
    for (const [weight, relPath] of Object.entries(role.files)) {
      const uri = fileToDataUri(path.join(BRAND_ROOT, relPath), "font/ttf");
      css += `@font-face { font-family: "${role.family}"; src: url("${uri}") format("truetype"); font-weight: ${weight}; }\n`;
    }
  }
  return css;
}

function toKebabCase(s) {
  return s.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
}

function buildTokensCss(tokens) {
  const lines = ["--font-heading: \"" + tokens.fonts.heading.family + "\", sans-serif;",
                 "--font-body: \"" + tokens.fonts.body.family + "\", sans-serif;"];
  for (const group of Object.values(tokens.colors)) {
    for (const [name, def] of Object.entries(group)) {
      lines.push(`--${toKebabCase(name)}: ${def.hex};`);
    }
  }
  return `:root {\n  ${lines.join("\n  ")}\n}`;
}

async function render(config) {
  if (!config.asset_type) throw new Error("Missing required field: asset_type");
  const catalog = loadJson(CATALOG_PATH);
  const spec = catalog[config.asset_type];
  if (!spec) {
    throw new Error(`Unknown asset_type "${config.asset_type}". Available: ${Object.keys(catalog).join(", ")}`);
  }

  const backgroundPath = config.assets && config.assets.background;
  if (!backgroundPath || !fs.existsSync(backgroundPath)) {
    throw new Error(`assets.background not found: ${backgroundPath}`);
  }

  const tokens = loadJson(path.join(BRAND_ROOT, "tokens.json"));
  const content = config.content || {};
  const sizes = spec.defaultSizes;

  let html = fs.readFileSync(path.join(TEMPLATES_DIR, spec.template), "utf-8");
  const replacements = {
    "{{FONT_FACES}}": buildFontFaces(tokens),
    "{{TOKENS_CSS}}": buildTokensCss(tokens),
    "{{BACKGROUND}}": fileToDataUri(backgroundPath, mimeFor(backgroundPath)),
    "{{WIDTH}}": spec.width,
    "{{HEIGHT}}": spec.height,
    "{{HEADLINE_SIZE}}": sizes.headline,
    "{{CAPTION_SIZE}}": sizes.caption,
    "{{CREDIT_SIZE}}": sizes.credit,
    "{{HEADLINE}}": escapeHtml(content.headline),
    "{{CAPTION}}": escapeHtml(content.caption),
    "{{CREDIT}}": escapeHtml(content.credit),
  };
  for (const [key, val] of Object.entries(replacements)) {
    html = html.split(key).join(String(val));
  }

  if (!config.out) throw new Error("Missing required field: out");
  fs.mkdirSync(path.dirname(config.out), { recursive: true });
  const tmpHtmlPath = path.join(path.dirname(config.out), `.tmp-brand-renderer-${Date.now()}.html`);
  fs.writeFileSync(tmpHtmlPath, html, "utf-8");

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: spec.width, height: spec.height } });
    await page.goto("file://" + tmpHtmlPath);
    await page.screenshot({ path: config.out });
  } finally {
    await browser.close();
    fs.unlinkSync(tmpHtmlPath);
  }

  if (!fs.existsSync(config.out) || fs.statSync(config.out).size === 0) {
    throw new Error(`Render produced no output (or 0 bytes) at ${config.out}`);
  }
  return config.out;
}

async function main() {
  const args = process.argv.slice(2);
  const configIdx = args.indexOf("--config");
  if (configIdx === -1) {
    console.error("Usage: node render.js --config path/to/content.json");
    process.exit(1);
  }
  const config = loadJson(args[configIdx + 1]);
  const outPath = await render(config);
  console.log("Rendered:", outPath);
}

main().catch(err => { console.error(err.message); process.exit(1); });
