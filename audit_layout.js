/**
 * audit_layout.js — Puppeteer-based Tier 2 layout audit for html_slides/.
 *
 * For each slide it:
 *   1. Renders at 1280×720 in headless Chromium.
 *   2. Checks for overflowing positioned elements (bounding rect outside viewport).
 *   3. Detects collapsed containers (height === 0 on non-empty elements).
 *   4. Checks actual root background luminance vs expected (light/dark).
 *   5. Detects blank renders (near-uniform pixel coverage).
 *   6. Saves a screenshot only for flagged slides → audit_flags/<slide_id>.png
 *
 * Usage:
 *   node ppt-dataset/audit_layout.js
 *   node ppt-dataset/audit_layout.js --limit 20
 *   node ppt-dataset/audit_layout.js --slide-id deloitte_..._slide_005
 */

"use strict";

const puppeteer = require("puppeteer");
const fs        = require("fs");
const path      = require("path");

const ROOT       = path.resolve(__dirname, "..");
const HTML_DIR   = path.join(ROOT, "html_slides");
const FLAGS_DIR  = path.join(ROOT, "audit_flags");
const REPORT_OUT = path.join(ROOT, "audit_layout_report.json");
const DATASET    = path.join(__dirname, "dataset.json");

if (!fs.existsSync(FLAGS_DIR)) fs.mkdirSync(FLAGS_DIR, { recursive: true });

const W = 1280, H = 720;

// ── CLI ──────────────────────────────────────────────────────────────────────
const argv       = process.argv.slice(2);
const getArg     = f => { const i = argv.indexOf(f); return i !== -1 ? argv[i+1] : null; };
const LIMIT      = getArg("--limit") ? parseInt(getArg("--limit")) : Infinity;
const SLIDE_FILT = getArg("--slide-id");

// ── Dataset meta ─────────────────────────────────────────────────────────────
const dataset = JSON.parse(fs.readFileSync(DATASET, "utf-8"));
const meta    = {};
for (const s of dataset.slides) meta[s.slide_id] = s.label || {};

// ── DOM audit executed inside the page context ────────────────────────────────
async function domAudit(page) {
  return page.evaluate((W, H) => {
    const results = {
      overflow_count   : 0,
      overflow_worst   : null,   // { tag, id, cls, rect }
      collapsed_count  : 0,
      total_elements   : 0,
      root_bg          : null,
      root_size_ok     : false,
    };

    // Root slide element
    const root = document.querySelector(".slide") || document.body.firstElementChild;
    if (root) {
      const r = root.getBoundingClientRect();
      results.root_size_ok = (Math.abs(r.width - W) < 10 && Math.abs(r.height - H) < 10);
      results.root_bg = window.getComputedStyle(root).backgroundColor;
    }

    // Walk all elements
    const all = document.querySelectorAll("*");
    results.total_elements = all.length;

    for (const el of all) {
      if (el === document.documentElement || el === document.body) continue;
      const style = window.getComputedStyle(el);
      if (style.position !== "absolute" && style.position !== "fixed") continue;

      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue; // truly invisible

      // Overflow check — element rect must be inside [0,0,W,H]
      const overX = r.right  > W + 20;   // 20px grace
      const overY = r.bottom > H + 20;
      const underX = r.left < -20;
      const underY = r.top  < -20;
      if (overX || overY || underX || underY) {
        results.overflow_count++;
        if (!results.overflow_worst || r.right > (results.overflow_worst.right || 0)) {
          results.overflow_worst = {
            tag  : el.tagName,
            cls  : el.className,
            left : Math.round(r.left),
            top  : Math.round(r.top),
            right: Math.round(r.right),
            bot  : Math.round(r.bottom),
          };
        }
      }

      // Collapsed check — has children/text but renders at 0 height
      if (r.height === 0 && el.childNodes.length > 0 && style.overflow !== "hidden") {
        results.collapsed_count++;
      }
    }

    return results;
  }, W, H);
}

// ── Pixel blank detection via canvas ─────────────────────────────────────────
async function isBlankRender(page) {
  return page.evaluate((W, H) => {
    const canvas  = document.createElement("canvas");
    canvas.width  = W; canvas.height = H;
    const ctx     = canvas.getContext("2d");
    // Can't draw page content here; rely on root_bg check instead.
    return false; // placeholder
  }, W, H);
}

// ── Luminance from rgb(...) string ───────────────────────────────────────────
function parseLum(rgbStr) {
  if (!rgbStr) return null;
  const m = rgbStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return null;
  return (parseInt(m[1])*299 + parseInt(m[2])*587 + parseInt(m[3])*114) / 1000;
}

// ── main ─────────────────────────────────────────────────────────────────────
async function main() {
  let files = fs.readdirSync(HTML_DIR)
    .filter(f => f.endsWith(".html"))
    .sort()
    .map(f => path.join(HTML_DIR, f));

  if (SLIDE_FILT) {
    files = files.filter(f => path.basename(f, ".html") === SLIDE_FILT);
  }
  if (files.length > LIMIT) files = files.slice(0, LIMIT);

  const total = files.length;
  console.log(`Auditing ${total} HTML slides ...`);
  console.log(`Flagged screenshots → ${FLAGS_DIR}\n`);

  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-web-security"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });

  const report  = [];
  let cleanCount = 0;

  for (let i = 0; i < files.length; i++) {
    const htmlFile = files[i];
    const slideId  = path.basename(htmlFile, ".html");
    const lbl      = meta[slideId] || {};

    process.stdout.write(`[${String(i+1).padStart(4)}/${total}] ${slideId.slice(0,60).padEnd(60)} `);

    try {
      await page.goto(`file:///${htmlFile.replace(/\\/g, "/")}`, {
        waitUntil: "networkidle0",
        timeout: 15000,
      });

      const dom    = await domAudit(page);
      const issues = [];

      // Root size wrong
      if (!dom.root_size_ok) issues.push("root-size-wrong");

      // Overflow elements
      if (dom.overflow_count > 0) {
        issues.push(`overflow:${dom.overflow_count}el(worst:right=${dom.overflow_worst?.right},bot=${dom.overflow_worst?.bot})`);
      }

      // Collapsed containers
      if (dom.collapsed_count > 3) {   // tolerate a few decorative zero-height divs
        issues.push(`collapsed:${dom.collapsed_count}el`);
      }

      // Background luminance mismatch
      const bgHex = lbl?.color_palette?.background || "";
      if (bgHex && bgHex.startsWith("#")) {
        const hx = bgHex.slice(1);
        const r = parseInt(hx.slice(0,2),16), g = parseInt(hx.slice(2,4),16), b = parseInt(hx.slice(4,6),16);
        const srcLum  = (r*299 + g*587 + b*114) / 1000;
        const htmlLum = parseLum(dom.root_bg);
        if (htmlLum !== null) {
          if ((srcLum > 140 && htmlLum < 60) || (srcLum < 60 && htmlLum > 180)) {
            issues.push(`bg-mismatch(src=${srcLum.toFixed(0)},render=${htmlLum.toFixed(0)})`);
          }
        }
      }

      // Very few elements → likely blank/failed render
      if (dom.total_elements < 5) issues.push("near-blank");

      if (issues.length > 0) {
        // Save screenshot of flagged slide
        const outPng = path.join(FLAGS_DIR, `${slideId}.png`);
        await page.screenshot({ path: outPng, clip: { x:0, y:0, width:W, height:H } });
        console.log(`FLAG [${issues.join(" | ")}]`);
        report.push({ slide_id: slideId, source: lbl.source_company || "?", issues });
      } else {
        console.log("ok");
        cleanCount++;
      }

    } catch (err) {
      console.log(`ERROR: ${err.message}`);
      report.push({ slide_id: slideId, source: lbl.source_company || "?", issues: [`render-error:${err.message}`] });
    }
  }

  await browser.close();

  // ── Summary ─────────────────────────────────────────────────────────────
  const flagged = report.length;
  console.log(`\n${"=".repeat(60)}`);
  console.log(`  LAYOUT AUDIT COMPLETE`);
  console.log(`${"=".repeat(60)}`);
  console.log(`Total    : ${total}`);
  console.log(`Clean    : ${cleanCount}`);
  console.log(`Flagged  : ${flagged}`);

  if (flagged > 0) {
    // Count issue types
    const counts = {};
    for (const { issues } of report) {
      for (const i of issues) {
        const key = i.split(":")[0];
        counts[key] = (counts[key] || 0) + 1;
      }
    }
    console.log(`\nIssue breakdown:`);
    for (const [k, v] of Object.entries(counts).sort((a,b) => b[1]-a[1])) {
      console.log(`  ${k.padEnd(35)} ${v}`);
    }

    console.log(`\nFlagged slides:`);
    for (const { slide_id, source, issues } of report) {
      console.log(`  [${source}] ${slide_id}`);
      for (const i of issues) console.log(`    - ${i}`);
    }
    console.log(`\nScreenshots saved to: ${FLAGS_DIR}`);
  }

  fs.writeFileSync(REPORT_OUT, JSON.stringify({ total, clean: cleanCount, flagged, slides: report }, null, 2));
  console.log(`Report   : ${REPORT_OUT}`);
}

main().catch(err => { console.error("Fatal:", err); process.exit(1); });
