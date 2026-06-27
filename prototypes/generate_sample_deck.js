/**
 * generate_sample_deck.js
 * Renders a 5-slide deck from deck_spec.json produced by generate_sample_deck.py.
 *
 * Usage:  node generate_sample_deck.js <path/to/deck_spec.json>
 */

const fs   = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

// Instance used only to resolve ShapeType / ChartType enum strings.
// A fresh instance is created inside build() for the actual deck.
const _ref = new pptxgen();

const specPath = process.argv[2];
if (!specPath || !fs.existsSync(specPath)) {
  console.error("Usage: node generate_sample_deck.js <deck_spec.json>");
  process.exit(1);
}
const SPEC = JSON.parse(fs.readFileSync(specPath, "utf8"));
const W = 13.333, H = 7.5;

// ── palette ───────────────────────────────────────────────────────────────────
const PAL = {
  white:    "FFFFFF",
  ink:      "0D1014",
  muted:    "5B6370",
  footer:   "70787F",
  blue1:    "06466D",   // primary navy
  blue2:    "1E6B9E",   // mid blue
  blue3:    "4A8FC0",   // light blue
  slate:    "6E8FAD",   // neutral blue-grey (replaces lavender)
  teal:     "247D6B",   // consulting green/teal
  amber:    "B8601F",   // muted amber
  positive: "217A52",   // upward/increase (green)
  negative: "B83232",   // downward/decrease (red)
  grid:     "E8EAED",
  // Chart series colours – 6 consulting-grade colours
  series: ["06466D", "1E6B9E", "4A8FC0", "247D6B", "6E8FAD", "B8601F"],
};

// ── coordinate helpers ────────────────────────────────────────────────────────
function fW(f) { return f * W; }
function fH(f) { return f * H; }

/** Resolve layout dimensions from a slide spec into absolute inches. */
function dims(s) {
  const ld = s.layout_dims || {};
  const hasRail  = s.has_rail;
  const hasPanel = s.has_panel;
  const M = 0.22;  // content margin inches

  const railW   = fW(ld.rail_w   || 0);
  const panelX  = fW(ld.panel_x  || (hasPanel ? 0.75 : 1.0));
  const panelW  = fW(ld.panel_w  || (hasPanel ? 0.25 : 0));
  const panelY  = fH(ld.panel_y  || 0.22);
  const panelH  = fH(ld.panel_h  || 0.68);
  const titleY  = fH(ld.title_y  || 0.05);
  const titleH  = Math.max(fH(ld.title_h || 0.06), 0.72);
  const subtY   = fH(ld.subtitle_y || (ld.title_y || 0.05) + (ld.title_h || 0.06));
  const subtH   = Math.max(fH(ld.subtitle_h || 0.06), 0.32);
  const cX      = fW(ld.content_x || (hasRail ? 0.133 : 0.0)) + M;
  const cY      = fH(ld.content_y || 0.17);
  const cW      = hasPanel ? (panelX - cX - M) : (W - cX - M);
  const cH      = fH(ld.content_h || 0.66);
  const footerY = fH(ld.footer_y || 0.88);
  const footerH = fH(ld.footer_h || 0.09);

  return { railW, panelX, panelW, panelY, panelH, titleY, titleH,
           subtY, subtH, cX, cY, cW, cH, footerY, footerH };
}

// ── shared drawing helpers ────────────────────────────────────────────────────
function txt(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace:  opts.font  || "Aptos",
    fontSize:  opts.size  || 11,
    color:     opts.color || PAL.ink,
    bold:      opts.bold  || false,
    align:     opts.align || "left",
    valign:    opts.valign|| "top",
    rotate:    opts.rotate || 0,
    margin:    opts.margin ?? 0,
    fit:       "shrink",
    wrap:      true,
    paraSpaceAfterPt: opts.paraSpace ?? 0,
  });
}

function rect(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(_ref.ShapeType.rect, {
    x, y, w, h,
    fill: { color: fill, transparency: opts.tp ?? 0 },
    line: opts.line ? { color: opts.line, width: opts.lw || 1 }
                    : { color: fill, transparency: 100 },
  });
}

function safeLine(slide, x1, y1, x2, y2, line) {
  const x = Math.min(x1, x2);
  const y = Math.min(y1, y2);
  const w = Math.abs(x2 - x1);
  const h = Math.abs(y2 - y1);
  const opts = { x, y, w, h, line };

  // PPTX extents cannot be negative. Upward left-to-right lines need a
  // positive bounding box plus flipV to preserve the visual direction.
  if ((x2 - x1) * (y2 - y1) < 0) opts.flipV = true;
  if ((x2 - x1) < 0) opts.flipH = true;
  slide.addShape(_ref.ShapeType.line, opts);
}

function drawRail(slide, s) {
  const ct = s.color_tokens || {};
  const d  = dims(s);
  const railColor = (ct.rail || "0B2C45").replace("#", "");
  const accentCol = (ct.divider || PAL.blue2).replace("#", "");

  // Slide background
  rect(slide, 0, 0, W, H, (ct.background || "FFFFFF").replace("#", ""));
  // Dark left rail
  rect(slide, 0, 0, d.railW, H, railColor);
  // Thin accent strip on rail edge
  rect(slide, d.railW, 0, 0.022, H, accentCol);

  // Section label (top of rail)
  const label = (s.content.rail_label || "").replace(/\\n/g, "\n");
  txt(slide, label, 0.16, 0.38, d.railW - 0.24, 0.72, {
    font: "Aptos Display", size: 13, color: "FFFFFF", bold: true,
  });
  // Thin rule below section label
  rect(slide, 0.16, 1.16, d.railW - 0.32, 0.012, "2A4A62");

  // Insight bullets — 3 items, generous spacing so nothing overlaps
  const bullets = s.content.panel_bullets || [];
  const bW    = d.railW - 0.34;
  const bStart = 1.28;
  const bStep  = (H - bStart - 0.55) / 3;   // divide remaining height evenly
  bullets.slice(0, 3).forEach((b, i) => {
    const by = bStart + i * bStep;
    rect(slide, 0.16, by + 0.06, 0.05, 0.05, accentCol);
    txt(slide, b.lead || "", 0.28, by, bW, 0.22, {
      size: 9, bold: true, color: "FFFFFF",
    });
    txt(slide, b.body || "", 0.28, by + 0.24, bW, bStep - 0.4, {
      size: 8, color: "9FB8CC",
    });
  });
}

function drawTitleStack(slide, s, titleW) {
  const d  = dims(s);
  const ct = s.color_tokens || {};
  const ink = (ct.text_primary || PAL.ink).replace("#", "");
  txt(slide, s.content.title, d.cX - 0.06, d.titleY, titleW || (W - d.cX - 0.1), d.titleH + 0.35, {
    font: "Aptos Display", size: 22, bold: true, color: ink,
  });
  if (s.content.subtitle) {
    txt(slide, s.content.subtitle, d.cX - 0.06, d.subtY + 0.35, titleW || (W - d.cX - 0.1), d.subtH, {
      size: 13, color: (ct.muted || PAL.muted).replace("#", ""),
    });
  }
}

function drawRightPanel(slide, s) {
  const d  = dims(s);
  const ct = s.color_tokens || {};
  const panelFill = (ct.panel || "D9DDE2").replace("#", "");
  const bullets   = s.content.panel_bullets || [];

  rect(slide, d.panelX, d.panelY, d.panelW, d.panelH, panelFill);

  const bx = d.panelX + 0.18;
  const bw = d.panelW - 0.26;
  let by = d.panelY + 0.18;
  const spacing = (d.panelH - 0.22) / Math.max(bullets.length, 1);

  bullets.forEach((b) => {
    rect(slide, bx - 0.13, by + 0.07, 0.05, 0.05, PAL.blue2);
    txt(slide, b.lead || "", bx, by, bw, 0.22, { size: 10, bold: true, color: PAL.ink });
    txt(slide, b.body || "", bx, by + 0.23, bw, spacing - 0.35, { size: 9, color: "3E454D" });
    by += spacing;
  });
}

function drawFooter(slide, s, note) {
  const d = dims(s);
  const deckTitle = (SPEC.deck.title || "").split("|")[0].trim();
  const footNote = note || "";
  // Separator only in content area (right of rail)
  rect(slide, d.cX - 0.06, d.footerY - 0.04, W - d.cX + 0.06, 0.016, "D1D5DB");
  txt(slide, footNote, d.cX - 0.06, d.footerY, W - d.cX - 3.6, 0.18, {
    size: 7, color: PAL.footer,
  });
  txt(slide, deckTitle, W * 0.42, d.footerY, W * 0.28, 0.18, {
    size: 7, color: PAL.footer, align: "center",
  });
  const n = s.slide_num || "";
  const total = SPEC.slides.length;
  txt(slide, `${n} / ${total}`, W - 0.72, d.footerY, 0.62, 0.18, {
    size: 7, color: PAL.footer, align: "right",
  });
}

function drawFullWidthFooter(slide, note, s) {
  const deckTitle = (SPEC.deck.title || "").split("|")[0].trim();
  rect(slide, 0, 7.32, W, 0.018, "D1D5DB");
  txt(slide, note || "", 0.55, 7.35, W - 5.8, 0.17, { size: 7, color: PAL.footer });
  txt(slide, deckTitle, W * 0.38, 7.35, W * 0.38, 0.17, { size: 7, color: PAL.footer, align: "center" });
  if (s) {
    const n = s.slide_num || "";
    const total = SPEC.slides.length;
    txt(slide, `${n} / ${total}`, W - 0.72, 7.35, 0.62, 0.17, { size: 7, color: PAL.footer, align: "right" });
  }
}

// ── background decorations (geometric watermark layer) ────────────────────────
function drawBgDecoration(pptx, slide, s) {
  if (!s || s.chart_type === "cover" || s.chart_type === "divider") return;
  const ct     = s.color_tokens || {};
  const accent = (ct.accent || ct.rail || PAL.blue1).replace("#", "");
  const type   = s.chart_type;
  const T      = 92;  // 92% transparent = 8% opacity — very faint watermark

  const shp = (shape, x, y, w, h, color, trans) =>
    slide.addShape(pptx.ShapeType[shape], {
      x, y, w, h,
      fill: { color: (color || accent).replace("#", ""), transparency: trans !== undefined ? trans : T },
      line: { color: "FFFFFF", transparency: 100 },
    });

  switch (type) {
    case "content":
    case "callout":
      shp("ellipse", 11.0, 3.0, 3.8, 3.8, accent);
      shp("ellipse", 10.1, 0.6, 2.6, 2.6, PAL.blue3, 94);
      break;
    case "bar":
      [[11.8, 2.0, 1.3, 0.46], [12.2, 2.62, 0.9, 0.46], [11.5, 3.24, 1.6, 0.46],
       [12.1, 3.86, 1.0, 0.46], [11.6, 4.48, 1.5, 0.46]].forEach(([x, y, w, h]) =>
        shp("rect", x, y, w, h, accent));
      break;
    case "waterfall":
      shp("ellipse", 10.8, 1.3, 2.8, 2.8, accent);
      shp("ellipse", 11.9, 4.8, 1.4, 1.4, PAL.teal, 91);
      break;
    case "bubble":
      [[11.4, 1.5, 0.55], [12.3, 2.5, 0.38], [11.0, 3.3, 0.6], [12.7, 3.8, 0.44],
       [11.6, 5.1, 0.5], [12.4, 5.7, 0.3]].forEach(([x, y, r]) =>
        shp("ellipse", x, y, r, r, accent, 91));
      break;
    case "heatmap":
      for (let c = 0; c < 4; c++) for (let r = 0; r < 5; r++)
        shp("ellipse", 11.1 + c * 0.52, 1.6 + r * 0.9, 0.2, 0.2, accent);
      break;
    case "matrix":
      [[10.7, 1.2], [12.0, 1.2], [10.7, 3.8], [12.0, 3.8]].forEach(([x, y], i) =>
        shp("ellipse", x, y, 1.15, 1.15, i < 2 ? PAL.teal : accent));
      break;
    case "slopegraph":
      for (let i = 0; i < 5; i++)
        shp("rect", 11.4 + i * 0.38, 1.1, 0.018, 5.9, accent, 88);
      break;
    case "area":
      [[10.9, 4.2, 3.2, 1.7], [11.7, 2.8, 2.4, 1.5], [12.2, 5.4, 1.5, 1.5]].forEach(([x, y, w, h]) =>
        shp("ellipse", x, y, w, h, PAL.teal, 91));
      break;
    case "metric_table":
      for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++)
        shp("rect", 11.1 + c * 0.52, 1.9 + r * 1.0, 0.34, 0.34, accent, 91);
      break;
    case "dualdoughnut":
    case "pie":
      shp("ellipse", 11.0, 1.9, 2.3, 2.3, accent);
      shp("ellipse", 11.6, 2.5, 1.1, 1.1, "FFFFFF", 0);
      break;
    case "stackedbar":
      [[11.7, 1.8, 1.5, 0.68], [11.3, 2.62, 1.9, 0.68], [11.5, 3.44, 1.7, 0.68],
       [11.9, 4.26, 1.3, 0.68]].forEach(([x, y, w, h], i) =>
        shp("rect", x, y, w, h, [accent, PAL.blue2, PAL.teal, PAL.slate][i]));
      break;
    case "line":
      shp("ellipse", 11.3, 1.7, 2.2, 2.2, accent);
      shp("ellipse", 12.0, 4.5, 1.3, 1.3, PAL.teal, 91);
      break;
    default:
      shp("ellipse", 11.2, 2.8, 2.6, 2.6, accent);
  }
}

// ── slide 1: content / 3 pillars ──────────────────────────────────────────────
function renderContentSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  const bg    = (ct.background || "FFFFFF").replace("#", "");
  slide.background = { color: bg };

  // Top accent bar
  const accent = (ct.accent || PAL.blue1).replace("#", "");
  rect(slide, 0, 0, W, 0.07, accent);

  // Title
  const titleX = 0.55, titleW = W - 1.1;
  txt(slide, s.content.title, titleX, 0.18, titleW, 0.76, {
    font: "Aptos Display", size: 22, bold: true, color: PAL.ink,
  });
  txt(slide, s.content.subtitle, titleX, 0.90, titleW, 0.46, {
    size: 12.5, color: PAL.muted,
  });

  // Thin separator
  rect(slide, titleX, 1.44, titleW, 0.02, "D1D5DB");

  // Pillar columns (3 or 4)
  const pillars = s.content.pillars || [];
  const nCols  = Math.max(pillars.length, 1);
  const gap    = nCols > 3 ? 0.14 : 0.2;
  const colW   = (W - 1.1 - gap * (nCols - 1)) / nCols;
  const blockH = nCols > 3 ? 0.60 : 0.72;
  pillars.forEach((p, i) => {
    const cx = 0.55 + i * (colW + gap);
    const cy = 1.6;
    const numW = nCols > 3 ? 0.38 : 0.62;
    rect(slide, cx, cy, colW, blockH, p.color || PAL.blue1);
    txt(slide, p.num, cx + 0.10, cy + 0.08, numW, blockH - 0.12, {
      size: nCols > 3 ? 24 : 30, bold: true, color: "FFFFFF", font: "Aptos Display",
    });
    txt(slide, p.title, cx + numW + 0.14, cy + (blockH * 0.18), colW - numW - 0.20, blockH - 0.18, {
      size: nCols > 3 ? 10.5 : 12, bold: true, color: "FFFFFF",
    });
    txt(slide, p.body || "", cx, cy + blockH + 0.12, colW, 3.7, {
      size: 11.5, color: PAL.ink, valign: "top",
    });
  });

  drawFullWidthFooter(slide, "", s);
}

// ── slide 2: scatter / bubble ─────────────────────────────────────────────────
function renderScatterSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  slide.background = { color: (s.color_tokens?.background || "F0F0F0").replace("#", "") };

  drawRail(slide, s);
  const d = dims(s);

  // Title
  const titleW = d.panelX - d.cX - 0.1;
  drawTitleStack(slide, s, titleW);

  // Chart
  const cd = s.chart_data;
  const chartX  = d.cX - 0.08;
  const subBot  = d.subtY + 0.35 + d.subtH + 0.08;
  const chartY  = Math.max(d.cY + 0.12, subBot);
  const chartW  = d.cW - 0.08;
  const chartH  = (d.cY + d.cH - 0.25) - chartY;

  slide.addChart(_ref.ChartType.bubble, [
    { name: "X", values: cd.x },
    { name: "Readiness", values: cd.y, sizes: cd.sizes },
  ], {
    x: chartX, y: chartY, w: chartW, h: chartH,
    showLegend: false, showTitle: false, showValue: false,
    catAxisTitle: cd.x_axis, valAxisTitle: cd.y_axis,
    catAxisTitleFontFace: "Aptos", valAxisTitleFontFace: "Aptos",
    catAxisTitleFontSize: 9.5, valAxisTitleFontSize: 9.5,
    catAxisLabelFontSize: 8.5, valAxisLabelFontSize: 8.5,
    catAxisMinVal: cd.x_min, catAxisMaxVal: cd.x_max,
    valAxisMinVal: cd.y_min, valAxisMaxVal: cd.y_max,
    valAxisMajorUnit: cd.y_major_unit || 20000, catAxisMajorUnit: cd.x_major_unit || 100,
    valGridLine: { color: "E5E7EB", transparency: 10 },
    chartColors: [PAL.blue1],
    chartColorsOpacity: 88,
    dataBorder: { pt: 0.5, color: PAL.blue1 },
  });

  // Country labels (key ones only)
  const annotate = cd.labels || [];
  annotate.forEach(([label, xv, yv]) => {
    const px = chartX + 0.52 + (xv / cd.x_max) * (chartW - 0.72);
    const py = chartY + (chartH - 0.35) - ((yv - cd.y_min) / (cd.y_max - cd.y_min)) * (chartH - 0.52);
    txt(slide, label, px + 0.07, py - 0.07, 1.1, 0.18, { size: 8.5, color: PAL.ink });
  });

  drawRightPanel(slide, s);
  drawFooter(slide, s, cd.source || "Note: Bubble size reflects estimated market scale.");
}

// ── slide 3: grouped bar ──────────────────────────────────────────────────────
function renderBarSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  slide.background = { color: (s.color_tokens?.background || "F0F0F0").replace("#", "") };

  drawRail(slide, s);
  const d = dims(s);

  const titleW = d.panelX - d.cX - 0.1;
  drawTitleStack(slide, s, titleW);

  const cd  = s.chart_data;
  const seriesData = cd.series.map((sr, i) => ({
    name:   sr.name,
    labels: cd.categories,
    values: sr.values,
  }));

  const subBot    = d.subtY + 0.35 + d.subtH + 0.08;
  const barChartY = Math.max(d.cY + 0.12, subBot);
  const barChartH = (d.cY + d.cH - 0.15) - barChartY;

  slide.addChart(_ref.ChartType.bar, seriesData, {
    x: d.cX - 0.06, y: barChartY, w: d.cW - 0.06, h: barChartH,
    barDir:       cd.bar_direction || "bar",
    barGrouping:  "clustered",
    barGapWidthPct: cd.gap_pct != null ? cd.gap_pct : 55,
    showLegend:   true,
    legendPos:    "b",
    legendFontSize: 9,
    showTitle:    false,
    showValue:    true,
    dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.##",
    dataLabelFontSize: 8.5,
    dataLabelColor: PAL.ink,
    catAxisTitle: "", catAxisTitleFontSize: 9,
    valAxisTitle: cd.x_axis,
    valAxisTitleFontFace: "Aptos",
    valAxisTitleFontSize: 9,
    catAxisLabelFontSize: 8.5,
    valAxisLabelFontSize: 8.5,
    valGridLine:  { color: "E5E7EB" },
    chartColors:  [PAL.blue1, PAL.blue2],
  });

  // CAGR callout for 2-bar vertical column charts
  if (cd.bar_direction === "col" && cd.growth_cagr) {
    const midX = d.cX + d.cW * 0.38;
    txt(slide, cd.growth_cagr, midX, barChartY + 0.22, 2.2, 0.4, {
      font: "Aptos Display", size: 16, bold: true, color: PAL.teal, align: "center",
    });
  }

  drawRightPanel(slide, s);
  drawFooter(slide, s, cd.source || "Note: Values are percentage of sector revenue; 2025 figures are management estimates.");
}

// ── slide 4: multi-series line ────────────────────────────────────────────────
function renderLineSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  const bg    = (ct.background || "FFFFFF").replace("#", "");
  slide.background = { color: bg };

  // Top accent bar
  rect(slide, 0, 0, W, 0.06, (ct.accent || PAL.blue1).replace("#", ""));

  const titleX = 0.55;
  txt(slide, s.content.title, titleX, 0.18, W - 1.1, 0.75, {
    font: "Aptos Display", size: 22, bold: true, color: PAL.ink,
  });
  txt(slide, s.content.subtitle, titleX, 0.90, W - 1.1, 0.44, {
    size: 13, color: PAL.muted,
  });

  const cd = s.chart_data;
  const seriesData = cd.series.map((sr, i) => ({
    name:   sr.name,
    labels: cd.categories,
    values: sr.values,
  }));

  slide.addChart(_ref.ChartType.line, seriesData, {
    x: 0.55, y: 1.45, w: W - 1.1, h: H - 2.0,
    showLegend:    true,
    legendPos:     "b",
    legendFontSize: 10,
    showTitle:     false,
    showValue:     false,
    catAxisTitle:  cd.x_axis,
    valAxisTitle:  cd.y_axis,
    catAxisTitleFontFace: "Aptos",
    valAxisTitleFontFace: "Aptos",
    catAxisTitleFontSize: 10,
    valAxisTitleFontSize: 10,
    catAxisLabelFontSize: 9.5,
    valAxisLabelFontSize: 9.5,
    valAxisMinVal: cd.y_min || 0,
    valAxisMaxVal: cd.y_max || 160,
    valAxisMajorUnit: 20,
    valGridLine:   { color: "E5E7EB" },
    chartColors:   [PAL.blue1, PAL.blue2, PAL.lavender],
    lineSize:      2.5,
    lineSmooth:    true,
    showMarker:    true,
    markerSize:    5,
  });

  drawFullWidthFooter(slide, cd.source || "", s);
}

// ── slide 5: pie ──────────────────────────────────────────────────────────────
function renderPieSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  const bg    = (ct.background || "FFFFFF").replace("#", "");
  slide.background = { color: bg };

  rect(slide, 0, 0, W, 0.06, (ct.accent || PAL.blue1).replace("#", ""));

  const titleX = 0.55;
  txt(slide, s.content.title, titleX, 0.18, W - 1.1, 0.72, {
    font: "Aptos Display", size: 22, bold: true, color: PAL.ink,
  });
  txt(slide, s.content.subtitle, titleX, 0.90, W - 1.1, 0.44, {
    size: 13, color: PAL.muted,
  });

  const cd = s.chart_data;
  slide.addChart(_ref.ChartType.doughnut, [{
    name:   "Allocation",
    labels: cd.labels,
    values: cd.values,
  }], {
    x: 0.9, y: 1.38, w: 11.5, h: 5.55,
    showLegend:     true,
    legendPos:      "r",
    legendFontSize: 10.5,
    showTitle:      false,
    showValue:      true,
    dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0\"%\"",
    dataLabelFontSize: 9.5,
    dataLabelFontBold: false,
    dataLabelColor: PAL.ink,
    chartColors:    PAL.series,
    holeSize:       45,
  });

  drawFullWidthFooter(slide, s.content.footer_note || cd.note || "", s);
}

// ── slide: stacked column (e.g. IoT connected devices) ───────────────────────
function renderStackedBarSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));

  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.72, {
    font: "Aptos Display", size: 22, bold: true, color: PAL.ink,
  });
  txt(slide, s.content.subtitle || "", 0.55, 0.90, W - 1.1, 0.44, {
    size: 13, color: PAL.muted,
  });

  const cd = s.chart_data;
  const seriesColors = ["06466D", "2D79A3", "5B9EC9", "A99BD1", "4A9B84", "D4895A"];
  const seriesData = cd.series.map((sr) => ({
    name: sr.name, labels: cd.categories, values: sr.values,
  }));

  const chartX = 0.55, chartY = 1.44, chartW = W - 1.1, chartH = 5.1;
  const axisMax = cd.axis_max || 32;

  slide.addChart(_ref.ChartType.bar, seriesData, {
    x: chartX, y: chartY, w: chartW, h: chartH,
    barDir:        "col",
    barGrouping:   "stacked",
    barGapWidthPct: 100,
    showLegend:    true,
    legendPos:     "b",
    legendFontSize: 9.5,
    showTitle:     false,
    showValue:     false,
    valAxisTitle:  cd.y_axis || "",
    valAxisTitleFontFace: "Aptos",
    valAxisTitleFontSize: 9.5,
    catAxisLabelFontSize: 11,
    valAxisLabelFontSize: 9,
    valAxisMaxVal: axisMax,
    valGridLine:   { color: "E5E7EB" },
    chartColors:   seriesColors,
  });

  // Total labels above each bar – estimate bar-top y positions
  if (cd.total_labels) {
    const plotH   = chartH - 0.75;            // legend ~0.75"
    const plotX   = chartX + 0.72;            // y-axis width ~0.72"
    const plotW   = chartW - 0.85;
    const entries = Object.entries(cd.total_labels);
    const nCats   = entries.length;
    entries.forEach(([cat, val], idx) => {
      const frac = (idx + 0.5) / nCats;
      const bx   = plotX + frac * plotW - 0.6;
      const barTopFrac = 1 - parseFloat(val) / axisMax;
      const by   = chartY + plotH * barTopFrac - 0.32;
      txt(slide, `${val} bn`, bx, by, 1.2, 0.26, {
        font: "Aptos Display", size: 12, bold: true, color: PAL.blue1, align: "center",
      });
    });
  }
  if (cd.growth_label) {
    txt(slide, cd.growth_label, chartX + chartW * 0.42, chartY + 0.28, 2.4, 0.38, {
      font: "Aptos Display", size: 15, bold: true, color: PAL.teal, align: "center",
    });
  }

  drawFullWidthFooter(slide, cd.source || "", s);
}

// ── slide: dual doughnut comparison (e.g. patent share 2006 vs 2016) ─────────
function renderDualDoughnutSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));

  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.72, {
    font: "Aptos Display", size: 22, bold: true, color: PAL.ink,
  });
  txt(slide, s.content.subtitle || "", 0.55, 0.90, W - 1.1, 0.38, {
    size: 13, color: PAL.muted,
  });

  const cd = s.chart_data;
  const chartColors = ["06466D", "2D79A3", "5B9EC9", "A99BD1", "4A9B84", "D4895A"];
  const dW = 5.55, dH = 4.7, dY = 1.52;
  const leftX = 0.45, rightX = W - dW - 0.45;

  // Center divider
  rect(slide, W / 2 - 0.012, 1.4, 0.024, dH + 0.6, "E5E7EB");

  // Year labels
  txt(slide, String(cd.left.year), leftX + dW * 0.32, 1.36, 1.3, 0.32, {
    font: "Aptos Display", size: 20, bold: true, color: PAL.blue1, align: "center",
  });
  txt(slide, String(cd.right.year), rightX + dW * 0.32, 1.36, 1.3, 0.32, {
    font: "Aptos Display", size: 20, bold: true, color: PAL.blue2, align: "center",
  });

  const doughnutOpts = () => ({
    showLegend: false, showTitle: false,
    showValue:  false,
    chartColors: chartColors,
    holeSize: 42,
  });

  slide.addChart(_ref.ChartType.doughnut,
    [{ name: String(cd.left.year),  labels: cd.left.labels,  values: cd.left.values  }],
    { x: leftX,  y: dY, w: dW, h: dH, ...doughnutOpts() });

  slide.addChart(_ref.ChartType.doughnut,
    [{ name: String(cd.right.year), labels: cd.right.labels, values: cd.right.values }],
    { x: rightX, y: dY, w: dW, h: dH, ...doughnutOpts() });

  // Legend split 3+3 under each chart to avoid the centre divider
  const legendY  = dY + dH + 0.1;
  const labels   = cd.left.labels;
  const half     = Math.ceil(labels.length / 2);
  const lItemW   = dW / half;
  const leftTot  = cd.left.values.reduce((a, b) => a + b, 0);
  const rightTot = cd.right.values.reduce((a, b) => a + b, 0);
  labels.forEach((lbl, i) => {
    const isRight = i >= half;
    const lx      = (isRight ? rightX : leftX) + (i - (isRight ? half : 0)) * lItemW;
    const lPct = (cd.left.values[i]  / leftTot  * 100).toFixed(1);
    const rPct = (cd.right.values[i] / rightTot * 100).toFixed(1);
    rect(slide, lx, legendY + 0.03, 0.15, 0.13, chartColors[i] || "888888");
    txt(slide, lbl, lx + 0.20, legendY, lItemW - 0.24, 0.17, {
      size: 8.5, bold: true, color: PAL.ink,
    });
    txt(slide, `${lPct}% → ${rPct}%`, lx + 0.20, legendY + 0.17, lItemW - 0.24, 0.16, {
      size: 8, color: PAL.muted,
    });
  });

  drawFullWidthFooter(slide, cd.source || "", s);
}

// ── slide: large-number callout boxes (e.g. IoT economic value) ──────────────
function renderCalloutSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));

  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.72, {
    font: "Aptos Display", size: 22, bold: true, color: PAL.ink,
  });
  txt(slide, s.content.subtitle || "", 0.55, 0.90, W - 1.1, 0.44, {
    size: 13, color: PAL.muted,
  });
  rect(slide, 0.55, 1.39, W - 1.1, 0.022, "D1D5DB");

  const cd       = s.chart_data;
  const boxes    = (cd.boxes || []).slice(0, 4);
  const gap      = 0.28;
  const colW     = (W - 1.1 - gap) / 2;
  const rowH     = (H - 1.78 - gap - 0.2) / 2;
  const boxAccents = [PAL.blue1, PAL.blue2, PAL.teal, PAL.amber];

  boxes.forEach((box, idx) => {
    const col  = idx % 2;
    const row  = Math.floor(idx / 2);
    const bx   = 0.55 + col * (colW + gap);
    const by   = 1.52 + row * (rowH + gap);
    const acct = boxAccents[idx] || PAL.blue1;

    // Box outline
    rect(slide, bx, by, colW, rowH, "F8FAFC", { line: "D1D5DB", lw: 1.2 });
    // Accent top strip with org name
    rect(slide, bx, by, colW, 0.32, acct);
    txt(slide, box.org || "", bx + 0.15, by + 0.07, colW - 0.22, 0.22, {
      size: 9.5, bold: true, color: "FFFFFF",
    });
    // Large value
    txt(slide, box.value || "", bx + 0.15, by + 0.38, colW - 0.2, 0.68, {
      font: "Aptos Display", size: 28, bold: true, color: acct,
    });
    // Description
    txt(slide, box.description || "", bx + 0.15, by + 1.06, colW - 0.22, rowH - 1.16, {
      size: 10.5, color: PAL.ink, valign: "top",
    });
  });

  drawFullWidthFooter(slide, cd.source || "", s);
}

// ── dispatch ──────────────────────────────────────────────────────────────────
function renderMetricTableSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));
  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.62, { font: "Aptos Display", size: 22, bold: true, color: PAL.ink });
  txt(slide, s.content.subtitle || "", 0.55, 0.86, W - 1.1, 0.35, { size: 11.5, color: PAL.muted });

  const cd = s.chart_data;
  const x = 0.55, y = 1.42, tableW = W - 1.1;
  const colW = [2.35, 1.15, 1.15, 1.05, tableW - 5.7];
  const rowH = 0.62;
  let cx = x;
  rect(slide, x, y, tableW, 0.38, PAL.blue1);
  cd.columns.forEach((h, i) => {
    txt(slide, h, cx + 0.08, y + 0.09, colW[i] - 0.12, 0.18, { size: 8.7, bold: true, color: "FFFFFF" });
    cx += colW[i];
  });
  cd.rows.forEach((row, r) => {
    const ry = y + 0.38 + r * rowH;
    rect(slide, x, ry, tableW, rowH, r % 2 ? "F4F6F8" : "FFFFFF", { line: "E3E6EA", lw: 0.4 });
    cx = x;
    row.forEach((cell, i) => {
      const isDelta = i === 3;
      txt(slide, String(cell), cx + 0.08, ry + 0.09, colW[i] - 0.12, rowH - 0.12, {
        size: i === 4 ? 8.5 : 9.2,
        bold: i === 0 || isDelta,
        color: isDelta ? PAL.teal : PAL.ink,
      });
      cx += colW[i];
    });
  });
  drawFullWidthFooter(slide, cd.source || "", s);
}

function renderWaterfallSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));
  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.62, { font: "Aptos Display", size: 22, bold: true, color: PAL.ink });
  txt(slide, s.content.subtitle || "", 0.55, 0.84, W - 1.1, 0.34, { size: 11.5, color: PAL.muted });

  const cd = s.chart_data;
  const items = cd.items;
  const chartX = 0.78, chartY = 1.55, chartW = 8.65, chartH = 4.72;
  const baseY = chartY + chartH;
  // Dynamic maxVal: find the highest running total across all items
  let _wfRun = 0, _wfPeak = 0;
  items.forEach(it => {
    if (it.kind === "total") _wfRun = it.value; else _wfRun += it.value;
    if (_wfRun > _wfPeak) _wfPeak = _wfRun;
  });
  const maxVal = Math.ceil(_wfPeak * 1.15 / 10) * 10;
  const barW = chartW / items.length * 0.62;
  const gap = chartW / items.length * 0.38;
  // Y-axis guide lines (3 ticks)
  [0.25, 0.5, 0.75].forEach(t => {
    const gy = baseY - t * chartH;
    slide.addShape(_ref.ShapeType.line, { x: chartX - 0.1, y: gy, w: chartW + 0.2, h: 0, line: { color: "E5E7EB", width: 0.5 } });
    txt(slide, String(Math.round(maxVal * t)), chartX - 0.64, gy - 0.1, 0.58, 0.2, { size: 7.6, color: PAL.muted, align: "right" });
  });
  let running = 0;
  items.forEach((it, i) => {
    const x = chartX + i * (barW + gap);
    let start = running;
    let end = running + it.value;
    if (it.kind === "total") { start = 0; end = it.value; running = it.value; }
    else { running = end; }
    const y0 = baseY - (Math.max(start, end) / maxVal) * chartH;
    const y1 = baseY - (Math.min(start, end) / maxVal) * chartH;
    const h = Math.max(0.08, y1 - y0);
    const color = it.kind === "decrease" ? PAL.amber : (it.kind === "total" ? PAL.blue1 : PAL.teal);
    rect(slide, x, y0, barW, h, color);
    txt(slide, `${it.value > 0 && it.kind !== "total" ? "+" : ""}${it.value}`, x - 0.08, y0 - 0.24, barW + 0.16, 0.18, { size: 8.5, bold: true, align: "center", color: PAL.ink });
    txt(slide, it.label, x - 0.16, baseY + 0.10, barW + 0.32, 0.42, { size: 7.6, align: "center", color: PAL.ink });
    if (i < items.length - 1) {
      const connY = baseY - (running / maxVal) * chartH;
      slide.addShape(_ref.ShapeType.line, { x: x + barW, y: connY, w: gap, h: 0, line: { color: "AEB4BC", width: 0.7, dash: "dash" } });
    }
  });
  slide.addShape(_ref.ShapeType.line, { x: chartX - 0.1, y: baseY, w: chartW + 0.2, h: 0, line: { color: "8A8F96", width: 0.8 } });
  txt(slide, cd.unit || "", chartX, chartY - 0.32, 1.2, 0.2, { size: 8.5, color: PAL.muted });
  (cd.callouts || []).forEach((c, i) => {
    const cy = 1.72 + i * 1.35;
    txt(slide, c.label, 9.8, cy, 2.6, 0.32, { font: "Aptos Display", size: 20, bold: true, color: PAL.teal });
    txt(slide, c.body, 9.8, cy + 0.38, 2.55, 0.52, { size: 10.2, color: PAL.ink });
  });
  drawFullWidthFooter(slide, cd.source || "", s);
}

function renderHeatmapSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));
  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.6, { font: "Aptos Display", size: 22, bold: true, color: PAL.ink });
  txt(slide, s.content.subtitle || "", 0.55, 0.82, W - 1.1, 0.34, { size: 11.5, color: PAL.muted });

  const cd = s.chart_data;
  const x = 0.55, y = 1.38, nameW = 2.5, noteW = 3.15, cellW = 0.88, rowH = 0.66;
  const colors = ["EFF3F6", "DDEBE7", "BBD9D1", "79B9A9", "1B8A8F"];
  txt(slide, "Use case", x, y, nameW, 0.22, { size: 8.8, bold: true, color: PAL.muted });
  cd.columns.forEach((h, i) => txt(slide, h, x + nameW + i * cellW, y, cellW, 0.22, { size: 8.3, bold: true, color: PAL.muted, align: "center" }));
  txt(slide, "Implication", x + nameW + cd.columns.length * cellW + 0.22, y, noteW, 0.22, { size: 8.8, bold: true, color: PAL.muted });
  cd.rows.forEach((r, ri) => {
    const ry = y + 0.36 + ri * rowH;
    rect(slide, x, ry, nameW + cd.columns.length * cellW + noteW + 0.38, rowH - 0.05, ri % 2 ? "F7F8FA" : "FFFFFF", { line: "E5E7EB", lw: 0.4 });
    txt(slide, r.name, x + 0.08, ry + 0.12, nameW - 0.15, 0.25, { size: 9, bold: true, color: PAL.ink });
    r.scores.forEach((score, ci) => {
      const px = x + nameW + ci * cellW;
      rect(slide, px + 0.07, ry + 0.10, cellW - 0.14, rowH - 0.25, colors[Math.max(0, Math.min(4, score - 1))], { line: "FFFFFF", lw: 0.5 });
      txt(slide, String(score), px, ry + 0.19, cellW, 0.18, { size: 9.3, bold: true, color: score >= 4 ? "FFFFFF" : PAL.ink, align: "center" });
    });
    txt(slide, r.note, x + nameW + cd.columns.length * cellW + 0.28, ry + 0.09, noteW - 0.05, 0.36, { size: 8.4, color: PAL.ink });
  });
  drawFullWidthFooter(slide, cd.source || "", s);
}

function renderMatrixSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));
  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.62, { font: "Aptos Display", size: 22, bold: true, color: PAL.ink });
  txt(slide, s.content.subtitle || "", 0.55, 0.84, W - 1.1, 0.34, { size: 11.5, color: PAL.muted });
  const cd = s.chart_data;
  const x = 1.05, y = 1.52, w = 8.9, h = 4.95;
  rect(slide, x, y, w / 2, h / 2, "E8F2EF");
  rect(slide, x + w / 2, y, w / 2, h / 2, "DCEDE8");
  rect(slide, x, y + h / 2, w / 2, h / 2, "F4F2EE");
  rect(slide, x + w / 2, y + h / 2, w / 2, h / 2, "EDF3F7");
  slide.addShape(_ref.ShapeType.line, { x: x + w / 2, y, w: 0, h, line: { color: "FFFFFF", width: 1.4 } });
  slide.addShape(_ref.ShapeType.line, { x, y: y + h / 2, w, h: 0, line: { color: "FFFFFF", width: 1.4 } });
  cd.quadrants.forEach((q, i) => {
    const qx = x + (i % 2) * w / 2 + 0.18;
    const qy = y + (i > 1 ? h / 2 : 0) + 0.15;
    txt(slide, q, qx, qy, 2.2, 0.25, { size: 10, bold: true, color: i === 0 ? PAL.teal : PAL.ink });
  });
  cd.items.forEach((it) => {
    const px = x + (it.x / 100) * w;
    const py = y + h - (it.y / 100) * h;
    const size = Math.max(0.22, it.size / 45);
    slide.addShape(_ref.ShapeType.ellipse, { x: px - size / 2, y: py - size / 2, w: size, h: size, fill: { color: PAL.blue1, transparency: 10 }, line: { color: "FFFFFF", width: 0.7 } });
    txt(slide, it.label, px + size / 2 + 0.04, py - 0.08, 1.25, 0.18, { size: 8.2, color: PAL.ink });
  });
  txt(slide, cd.x_axis, x + w * 0.36, y + h + 0.25, 2.4, 0.22, { size: 9.4, bold: true, align: "center" });
  txt(slide, cd.y_axis, 0.25, y + h * 0.42, 1.0, 0.4, { size: 9.4, bold: true, rotate: 270 });
  drawFullWidthFooter(slide, cd.source || "", s);
}

function renderSlopegraphSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));
  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.62, { font: "Aptos Display", size: 22, bold: true, color: PAL.ink });
  txt(slide, s.content.subtitle || "", 0.55, 0.84, W - 1.1, 0.34, { size: 11.5, color: PAL.muted });
  const cd = s.chart_data;
  const _allVals = cd.items.flatMap(it => [it.left, it.right]);
  const _sMax = Math.ceil(Math.max(..._allVals) * 1.10 / 5) * 5;
  const _sMin = Math.max(0, Math.floor(Math.min(..._allVals) * 0.85 / 5) * 5);
  const x1 = 2.2, x2 = 10.2, y = 1.55, h = 4.85, min = _sMin, max = _sMax;
  txt(slide, cd.left_label, x1 - 0.8, y - 0.28, 1.7, 0.2, { size: 9.5, bold: true, align: "center" });
  txt(slide, cd.right_label, x2 - 0.8, y - 0.28, 1.7, 0.2, { size: 9.5, bold: true, align: "center" });
  slide.addShape(_ref.ShapeType.line, { x: x1, y, w: 0, h, line: { color: "D2D6DB", width: 0.8 } });
  slide.addShape(_ref.ShapeType.line, { x: x2, y, w: 0, h, line: { color: "D2D6DB", width: 0.8 } });
  cd.items.forEach((it, i) => {
    const yL = y + h - ((it.left - min) / (max - min)) * h;
    const yR = y + h - ((it.right - min) / (max - min)) * h;
    const color = i < 3 ? PAL.teal : "7E8792";
    safeLine(slide, x1, yL, x2, yR, { color, width: i < 3 ? 1.9 : 1.1 });
    txt(slide, `${it.label} ${it.left}%`, x1 - 1.75, yL - 0.08, 1.55, 0.18, { size: 8.6, color: PAL.ink, align: "right" });
    txt(slide, `${it.right}%`, x2 + 0.12, yR - 0.08, 0.72, 0.18, { size: 8.6, bold: i < 3, color: PAL.ink });
  });
  drawFullWidthFooter(slide, cd.source || "", s);
}

function renderAreaSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct = s.color_tokens || {};
  slide.background = { color: (ct.background || "FFFFFF").replace("#", "") };
  rect(slide, 0, 0, W, 0.07, (ct.accent || PAL.blue1).replace("#", ""));
  txt(slide, s.content.title, 0.55, 0.18, W - 1.1, 0.62, { font: "Aptos Display", size: 22, bold: true, color: PAL.ink });
  txt(slide, s.content.subtitle || "", 0.55, 0.84, W - 1.1, 0.34, { size: 11.5, color: PAL.muted });
  const cd = s.chart_data;
  const seriesData = cd.series.map((sr) => ({ name: sr.name, labels: cd.categories, values: sr.values }));
  slide.addChart(_ref.ChartType.area, seriesData, {
    x: 0.75, y: 1.55, w: 9.4, h: 4.75,
    barGrouping: "stacked",
    showLegend: true, legendPos: "b", legendFontSize: 8.6,
    showTitle: false, showValue: false,
    valAxisTitle: cd.y_axis || "",
    valAxisMinVal: 0, valAxisMaxVal: cd.y_max || (() => { const peak = Math.max(...(cd.categories || []).map((_, ci) => cd.series.reduce((s, sr) => s + (sr.values[ci] || 0), 0))); return Math.ceil(peak * 1.15 / 5) * 5 || 70; })(), valAxisMajorUnit: 10,
    catAxisLabelFontSize: 8.5, valAxisLabelFontSize: 8.5,
    valGridLine: { color: "E5E7EB" },
    chartColors: [PAL.blue1, PAL.teal, PAL.blue3, PAL.lavender],
  });
  txt(slide, cd.callout || "", 10.45, 2.05, 2.1, 0.8, { font: "Aptos Display", size: 18, bold: true, color: PAL.teal });
  txt(slide, cd.callout_body || "", 10.45, 3.0, 2.15, 1.0, { size: 10, color: PAL.ink });
  drawFullWidthFooter(slide, cd.source || "", s);
}

// ── cover slide ───────────────────────────────────────────────────────────────
function renderCoverSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  const bg    = (ct.background || "06466D").replace("#", "");
  slide.background = { color: bg };

  // Full-bleed dark panel background
  // Top thin accent stripe
  rect(slide, 0, 0, W, 0.07, PAL.blue2);

  // Bottom branding strip
  rect(slide, 0, H - 0.52, W, 0.52, "082232");

  const cd = s.chart_data || {};
  // Firm name bottom-left
  txt(slide, SPEC.deck.firm || "Roland Berger", 0.6, H - 0.42, 3.5, 0.32, {
    font: "Aptos Display", size: 11, color: PAL.slate, bold: false,
  });
  // Date / confidentiality bottom-right
  txt(slide, cd.date || "", W - 3.2, H - 0.42, 2.9, 0.32, {
    size: 10, color: PAL.slate, align: "right",
  });

  // Main title — large, white, left-aligned
  txt(slide, s.content.title || "", 0.6, 1.55, 9.2, 2.4, {
    font: "Aptos Display", size: 38, bold: true, color: "FFFFFF",
  });

  // Subtitle below
  txt(slide, s.content.subtitle || "", 0.6, 4.05, 9.2, 0.8, {
    size: 16, color: "A8BFD0", bold: false,
  });

  // Thin rule between title and subtitle
  rect(slide, 0.6, 3.98, 4.5, 0.022, PAL.blue2);

  // Tag line
  if (cd.tag) {
    txt(slide, cd.tag, 0.6, 4.92, 9.2, 0.4, {
      size: 11.5, color: "7A9DB8",
    });
  }
}

// ── section divider ───────────────────────────────────────────────────────────
function renderDividerSlide(pptx, s) {
  const slide = pptx.addSlide();
  drawBgDecoration(pptx, slide, s);
  const ct    = s.color_tokens || {};
  slide.background = { color: "FFFFFF" };

  // Large left-side navy panel (40% width)
  const panW = W * 0.40;
  rect(slide, 0, 0, panW, H, (ct.rail || "06466D").replace("#", ""));
  rect(slide, panW, 0, 0.024, H, PAL.blue2);

  // Section number
  if (s.content.section_num) {
    txt(slide, String(s.content.section_num), 0.5, 2.1, panW - 0.7, 1.8, {
      font: "Aptos Display", size: 96, bold: true, color: "0C3D5C",
    });
  }

  // Section title (right panel)
  txt(slide, s.content.title || "", panW + 0.55, 2.5, W - panW - 0.8, 1.6, {
    font: "Aptos Display", size: 30, bold: true, color: PAL.ink,
  });

  // Section description
  txt(slide, s.content.subtitle || "", panW + 0.55, 4.2, W - panW - 0.8, 1.2, {
    size: 13, color: PAL.muted,
  });

  // Thin accent line left of section title
  rect(slide, panW + 0.28, 2.5, 0.055, 1.6, PAL.blue2);

  drawFullWidthFooter(slide, "", s);
}

const RENDERERS = {
  content:      renderContentSlide,
  cover:        renderCoverSlide,
  divider:      renderDividerSlide,
  bubble:       renderScatterSlide,
  bar:          renderBarSlide,
  line:         renderLineSlide,
  pie:          renderPieSlide,
  stackedbar:   renderStackedBarSlide,
  dualdoughnut: renderDualDoughnutSlide,
  callout:      renderCalloutSlide,
  metric_table: renderMetricTableSlide,
  waterfall:    renderWaterfallSlide,
  heatmap:      renderHeatmapSlide,
  matrix:       renderMatrixSlide,
  slopegraph:   renderSlopegraphSlide,
  area:         renderAreaSlide,
};

// ── build deck ────────────────────────────────────────────────────────────────
async function build() {
  const pptx = new pptxgen();
  pptx.defineLayout({ name: "WIDE", width: W, height: H });
  pptx.layout  = "WIDE";
  pptx.title   = SPEC.deck.title;
  pptx.author  = "ppt-dataset prototype";
  pptx.subject = "AI Investment Sample Deck";
  pptx.theme   = { headFontFace: "Aptos Display", bodyFontFace: "Aptos", lang: "en-US" };

  for (const s of SPEC.slides) {
    const render = RENDERERS[s.chart_type];
    if (!render) { console.error(`Unknown chart_type: ${s.chart_type}`); continue; }
    render(pptx, s);
    console.log(`  slide ${s.slide_num}: ${s.chart_type} (${s.recipe.split(" + ")[0]}...)`);
  }

  const outPath = SPEC.output_path;
  await pptx.writeFile({ fileName: outPath });
  console.log(`Written: ${outPath}`);
}

build().catch((err) => { console.error(err); process.exit(1); });
