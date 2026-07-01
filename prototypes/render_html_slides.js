/**
 * Stage 2 – HTML/CSS slide validator & renderer.
 *
 * For each .html file in html_slides/, this script:
 *   1. Opens the file in a headless Chromium browser at 1280×720.
 *   2. Takes a screenshot → render_previews/<slide_id>.png
 *   3. Compares the render to the source PNG via pixel-level similarity.
 *   4. Writes a summary report: html_slides/render_report.json
 *
 * Prerequisites:
 *   npm install puppeteer
 *
 * Usage:
 *   node prototypes/render_html_slides.js
 *   node prototypes/render_html_slides.js --limit 10
 *   node prototypes/render_html_slides.js --slide-id accenture_..._slide_003
 *   node prototypes/render_html_slides.js --skip-existing
 */

const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");

// ── paths ──────────────────────────────────────────────────────────────────

const ROOT = path.resolve(__dirname, "..");
const HTML_DIR = path.join(ROOT, "html_slides");
const PREVIEW_DIR = path.join(ROOT, "render_previews");
const REPORT_PATH = path.join(HTML_DIR, "render_report.json");

if (!fs.existsSync(PREVIEW_DIR)) fs.mkdirSync(PREVIEW_DIR, { recursive: true });

const W = 1280;
const H = 720;

// ── CLI args ───────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const getArg = (flag) => {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : null;
};
const hasFlag = (flag) => args.includes(flag);

const LIMIT = getArg("--limit") ? parseInt(getArg("--limit")) : Infinity;
const SLIDE_ID_FILTER = getArg("--slide-id") || null;
const SKIP_EXISTING = hasFlag("--skip-existing");

// ── simple pixel similarity (grayscale MSE) ─────────────────────────────────
// Uses only Node built-ins — no sharp or jimp required for a rough check.
// Returns a similarity score 0–100 (100 = identical).

function roughSimilarity(pngPathA, pngPathB) {
  // Without an image decoding library we cannot do pixel comparison.
  // Return null to indicate "not computed"; install sharp for real scores.
  return null;
}

// ── main ───────────────────────────────────────────────────────────────────

async function main() {
  if (!fs.existsSync(HTML_DIR)) {
    console.error(`html_slides/ not found at ${HTML_DIR}. Run slides_to_html.py first.`);
    process.exit(1);
  }

  let htmlFiles = fs
    .readdirSync(HTML_DIR)
    .filter((f) => f.endsWith(".html"))
    .map((f) => path.join(HTML_DIR, f));

  if (SLIDE_ID_FILTER) {
    htmlFiles = htmlFiles.filter((f) =>
      path.basename(f, ".html") === SLIDE_ID_FILTER
    );
    if (!htmlFiles.length) {
      console.error(`No HTML file found for slide_id: ${SLIDE_ID_FILTER}`);
      process.exit(1);
    }
  }

  if (SKIP_EXISTING) {
    htmlFiles = htmlFiles.filter(
      (f) => !fs.existsSync(path.join(PREVIEW_DIR, path.basename(f, ".html") + ".png"))
    );
  }

  if (htmlFiles.length > LIMIT) htmlFiles = htmlFiles.slice(0, LIMIT);

  const total = htmlFiles.length;
  console.log(`Rendering ${total} HTML slides → ${PREVIEW_DIR}`);

  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });

  const report = [];
  let ok = 0;
  let fail = 0;

  for (let i = 0; i < htmlFiles.length; i++) {
    const htmlFile = htmlFiles[i];
    const slideId = path.basename(htmlFile, ".html");
    const outPng = path.join(PREVIEW_DIR, `${slideId}.png`);
    const srcPng = path.join(ROOT, "slides", `${slideId}.png`);

    process.stdout.write(`[${String(i + 1).padStart(4)}/${total}] → ${slideId}`);

    try {
      await page.goto(`file:///${htmlFile.replace(/\\/g, "/")}`, {
        waitUntil: "networkidle0",
        timeout: 15000,
      });
      await page.screenshot({ path: outPng, clip: { x: 0, y: 0, width: W, height: H } });

      const srcExists = fs.existsSync(srcPng);
      const similarity = srcExists ? roughSimilarity(outPng, srcPng) : null;

      const entry = {
        slide_id: slideId,
        status: "ok",
        render_png: path.relative(ROOT, outPng),
        source_png: srcExists ? path.relative(ROOT, srcPng) : null,
        similarity_score: similarity,
      };
      report.push(entry);
      ok++;
      console.log(`  OK  → ${path.basename(outPng)}`);
    } catch (err) {
      console.log(`  FAIL: ${err.message}`);
      report.push({ slide_id: slideId, status: "fail", error: err.message });
      fail++;
    }
  }

  await browser.close();

  fs.writeFileSync(REPORT_PATH, JSON.stringify({ ok, fail, slides: report }, null, 2));
  console.log(`\nDone — ${ok} rendered, ${fail} failed.`);
  console.log(`Report written to: ${REPORT_PATH}`);
  console.log(`Preview PNGs in:   ${PREVIEW_DIR}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
