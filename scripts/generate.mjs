#!/usr/bin/env node
/**
 * generate.mjs — Merav's image-generation engine.
 *
 * Calls Nano Banana 2 (gemini-3.1-flash-image-preview via @google/genai) to produce
 * production-ready content images (blog-post visuals, social-post images, etc.),
 * optionally styled by brand/reference images placed in references/.
 *
 * Usage:
 *   node scripts/generate.mjs --brief "<brief text>" [--aspect 1:1|9:16|16:9|4:5] [--n <count>]
 *
 * --brief is required. --aspect defaults to 1:1. --n defaults to 1.
 */

import { GoogleGenAI } from "@google/genai";
import { config as loadEnv } from "dotenv";
import { readdir, readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

loadEnv();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const REFERENCES_DIR = path.join(ROOT, "references");
const OUTPUT_DIR = path.join(ROOT, "output");

const SUPPORTED_IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const VALID_ASPECTS = new Set(["1:1", "9:16", "16:9", "4:5"]);

function parseArgs(argv) {
  const args = { aspect: "1:1", n: 1 };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--brief") args.brief = argv[++i];
    else if (arg === "--aspect") args.aspect = argv[++i];
    else if (arg === "--n") args.n = parseInt(argv[++i], 10);
  }
  return args;
}

function validateArgs(args) {
  if (!args.brief || !args.brief.trim()) {
    throw new Error("--brief is required (rich design prompt for the image).");
  }
  if (!VALID_ASPECTS.has(args.aspect)) {
    throw new Error(`--aspect must be one of: ${[...VALID_ASPECTS].join(", ")}`);
  }
  if (!Number.isInteger(args.n) || args.n < 1) {
    throw new Error("--n must be a positive integer.");
  }
}

async function loadReferenceImages() {
  let files = [];
  try {
    files = await readdir(REFERENCES_DIR);
  } catch {
    return []; // references/ missing entirely -> no style context
  }
  const imageFiles = files.filter((f) =>
    SUPPORTED_IMAGE_EXT.has(path.extname(f).toLowerCase())
  );
  const parts = [];
  for (const file of imageFiles) {
    const filePath = path.join(REFERENCES_DIR, file);
    const buffer = await readFile(filePath);
    const ext = path.extname(file).toLowerCase();
    const mimeType =
      ext === ".png"
        ? "image/png"
        : ext === ".webp"
        ? "image/webp"
        : "image/jpeg";
    parts.push({
      inlineData: { mimeType, data: buffer.toString("base64") },
    });
  }
  return parts;
}

function buildPrompt(brief, aspect, hasReferences) {
  const styleBlock = hasReferences
    ? "Match the visual style, palette, and mood of the attached brand/style reference images as closely as possible."
    : "No brand references were provided — use a modern, clean, minimal aesthetic appropriate for professional content marketing.";

  return [
    "You are Merav, the team's content visual generator.",
    "Produce a single, polished, production-ready image for a content piece (blog post, social post, or newsletter visual) based on the brief below.",
    `Aspect ratio: ${aspect}.`,
    styleBlock,
    "",
    "Brief:",
    brief,
  ].join("\n");
}

function slugify(text) {
  return text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 60) || "image";
}

function timestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(
    d.getHours()
  )}${pad(d.getMinutes())}`;
}

async function generateOne({ ai, prompt, aspect, index, slug }) {
  const response = await ai.models.generateContent({
    model: "gemini-3.1-flash-image-preview",
    contents: prompt,
    config: {
      responseModalities: ["TEXT", "IMAGE"],
      imageConfig: { aspectRatio: aspect, imageSize: "2K" },
    },
  });

  const parts = response?.candidates?.[0]?.content?.parts ?? [];
  const imagePart = parts.find((p) => p.inlineData);
  if (!imagePart) {
    throw new Error(
      `No image returned for variant ${index} — response contained no inlineData part.`
    );
  }

  await mkdir(OUTPUT_DIR, { recursive: true });
  const filename = `${timestamp()}-${slug}-${index}.png`;
  const filePath = path.join(OUTPUT_DIR, filename);
  await writeFile(filePath, Buffer.from(imagePart.inlineData.data, "base64"));
  return filePath;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  validateArgs(args);

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error(
      "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
    );
  }

  const ai = new GoogleGenAI({ apiKey });
  const referenceParts = await loadReferenceImages();
  const promptText = buildPrompt(args.brief, args.aspect, referenceParts.length > 0);
  const slug = slugify(args.brief.split(/\s+/).slice(0, 6).join(" "));

  const contents =
    referenceParts.length > 0
      ? [{ role: "user", parts: [{ text: promptText }, ...referenceParts] }]
      : promptText;

  const paths = [];
  for (let i = 1; i <= args.n; i++) {
    const filePath = await generateOne({
      ai,
      prompt: contents,
      aspect: args.aspect,
      index: i,
      slug,
    });
    paths.push(filePath);
    console.log(`Saved: ${filePath}`);
  }

  return paths;
}

main().catch((err) => {
  console.error(`generate.mjs failed: ${err.message}`);
  process.exit(1);
});
