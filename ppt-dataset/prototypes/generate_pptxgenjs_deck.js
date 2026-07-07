const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const BASE_DIR = path.resolve(__dirname, "..");
const OUT_DIR = path.join(BASE_DIR, "prototypes", "output");
const DATASET_PATH = path.join(BASE_DIR, "dataset.json");
const DECK_PATH = path.join(OUT_DIR, "sample_deck_pptxgenjs_v03.pptx");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "ppt-dataset prototype";
pptx.subject = "Editable sample deck generated with pptxgenJS";
pptx.title = "Slide Dataset Prototype v0.3";
pptx.company = "Research prototype";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.margin = 0;

const C = {
  black: "111216",
  charcoal: "252A31",
  ink: "1F2328",
  muted: "6B7280",
  pale: "F7F6F2",
  paper: "FFFFFF",
  grid: "D8D4CC",
  teal: "1B8A8F",
  cyan: "35B6C7",
  plum: "6B3FA0",
  violet: "B100FF",
  green: "7BC06F",
  saffron: "F2A541",
  red: "D94F45",
};

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function countBy(slides, key) {
  const counts = new Map();
  for (const item of slides) {
    const value = item.label?.[key] || "unknown";
    counts.set(value, (counts.get(value) || 0) + 1);
  }
  return counts;
}

function topEntries(counts, n = 7) {
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace: opts.fontFace || "Aptos",
    fontSize: opts.fontSize || 12,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    fit: "shrink",
    breakLine: false,
    margin: opts.margin ?? 0,
    valign: opts.valign || "top",
    align: opts.align || "left",
    paraSpaceAfterPt: opts.paraSpaceAfterPt ?? 0,
  });
}

function addRect(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: fill, transparency: opts.transparency ?? 0 },
    line: opts.line ? { color: opts.line, width: opts.lineWidth || 1 } : { color: fill, transparency: 100 },
    radius: opts.radius || 0,
  });
}

function addRoundRect(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: opts.rectRadius ?? 0.08,
    fill: { color: fill, transparency: opts.transparency ?? 0 },
    line: opts.line ? { color: opts.line, width: opts.lineWidth || 1 } : { color: fill, transparency: 100 },
  });
}

function addRule(slide, x, y, w, color = C.teal) {
  addRect(slide, x, y, w, 0.035, color);
}

function addFooter(slide, n, totalLabels) {
  addText(slide, `Prototype deck from ${totalLabels} audited slide labels`, 0.55, 7.13, 4.6, 0.16, {
    fontSize: 7,
    color: C.muted,
  });
  addText(slide, String(n).padStart(2, "0"), 12.45, 7.1, 0.35, 0.16, {
    fontSize: 8,
    color: C.muted,
    align: "right",
  });
}

function addNativeBarChart(slide, title, entries, x, y, w, h, fillColor) {
  slide.addChart(
    pptx.ChartType.bar,
    [
      {
        name: title,
        labels: entries.map(([label]) => label.replaceAll("_", " ")),
        values: entries.map(([, value]) => value),
      },
    ],
    {
      x,
      y,
      w,
      h,
      catAxisLabelFontFace: "Aptos",
      catAxisLabelFontSize: 8,
      valAxisLabelFontSize: 8,
      valAxisMajorUnit: 50,
      showLegend: false,
      showTitle: false,
      showValue: false,
      showCatName: false,
      valGridLine: { color: "ECE8E0", transparency: 20 },
      chartColors: [fillColor],
      showValue: true,
      dataLabelPosition: "outEnd",
      dataLabelFontSize: 7,
      dataLabelColor: C.muted,
      valAxisMinVal: 0,
    }
  );
}

function addNativeColumnChart(slide, title, entries, x, y, w, h, colors = [C.teal]) {
  slide.addChart(
    pptx.ChartType.bar,
    [
      {
        name: title,
        labels: entries.map(([label]) => label),
        values: entries.map(([, value]) => value),
      },
    ],
    {
      x,
      y,
      w,
      h,
      barDir: "col",
      catAxisLabelFontSize: 8,
      valAxisLabelFontSize: 8,
      showLegend: false,
      showTitle: false,
      showValue: true,
      dataLabelPosition: "outEnd",
      dataLabelFontSize: 8,
      valGridLine: { color: "E9E5DE", transparency: 10 },
      chartColors: colors,
      valAxisMinVal: 0,
    }
  );
}

function addImageIfExists(slide, fileName, x, y, w, h) {
  const imgPath = path.join(BASE_DIR, "slides", fileName);
  if (fs.existsSync(imgPath)) {
    slide.addImage({ path: imgPath, x, y, w, h, sizingCrop: true });
  } else {
    addRect(slide, x, y, w, h, "E9E5DE", { line: C.grid });
    addText(slide, "reference image missing", x + 0.15, y + h / 2 - 0.1, w - 0.3, 0.2, {
      fontSize: 10,
      color: C.muted,
      align: "center",
    });
  }
}

function sourceRows(counts) {
  return topEntries(counts, 6).map(([source, value]) => [source, value]);
}

function buildDeck() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const dataset = readJson(DATASET_PATH);
  const slides = dataset.slides || [];
  const total = slides.length;
  const source = countBy(slides, "source_company");
  const layout = countBy(slides, "layout_type");
  const chart = countBy(slides, "chart_type");
  const purpose = countBy(slides, "slide_purpose");
  const density = countBy(slides, "text_density");
  const labeledBatches = Math.ceil(total / 5);
  const totalPngs = 641;
  const remaining = Math.max(0, totalPngs - total);

  // Slide 1
  let slide = pptx.addSlide();
  slide.background = { color: C.black };
  addRect(slide, 0, 0, 2.35, 7.5, C.charcoal);
  [C.teal, C.saffron, C.plum].forEach((color, idx) => addRoundRect(slide, 0.62, 0.9 + idx * 0.78, 0.34, 0.34, color));
  addText(slide, "Slide Dataset\nPrototype v0.3", 3.02, 1.0, 5.75, 1.4, {
    fontSize: 40,
    color: C.paper,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "A complete labeled corpus with style-anchor controls for generation", 3.04, 2.72, 6.4, 0.3, {
    fontSize: 15,
    color: "CED7DE",
  });
  addRule(slide, 3.05, 3.32, 1.4, C.teal);
  addText(slide, `${total}`, 10.0, 1.17, 1.6, 0.55, { fontSize: 34, color: C.cyan, bold: true });
  addText(slide, "audited labels now available", 10.02, 1.82, 2.0, 0.34, { fontSize: 11, color: "C8D0D8" });
  addText(slide, `${remaining}`, 10.0, 2.72, 1.6, 0.55, { fontSize: 34, color: C.saffron, bold: true });
  addText(slide, "slides still queued", 10.02, 3.37, 2.0, 0.34, { fontSize: 11, color: "C8D0D8" });
  addText(slide, "Generated with pptxgenJS: editable text, editable shapes, native charts, and corpus thumbnails.", 3.05, 6.38, 6.8, 0.35, {
    fontSize: 11,
    color: "AEB7C2",
  });
  addText(slide, "v0.3 | 24 Jun 2026", 10.25, 6.96, 2.0, 0.2, { fontSize: 8, color: "9BA4B1" });

  // Slide 2
  slide = pptx.addSlide();
  slide.background = { color: C.pale };
  addText(slide, "The corpus is now fully labeled and ready for controlled generation", 0.65, 0.48, 9.4, 0.45, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "The final tranche completes coverage, while quality gating keeps report pages from steering style too much.", 0.66, 1.0, 9.1, 0.25, {
    fontSize: 11,
    color: C.muted,
  });
  addRule(slide, 0.66, 1.32, 1.25, C.teal);
  [
    [`${total}`, "labeled slides"],
    [`${labeledBatches}`, "labeled batches"],
    [`${source.get("Roland Berger") || 0}`, "Roland Berger anchors"],
    [`${Math.round((total / totalPngs) * 100)}%`, "corpus labeled"],
  ].forEach(([num, label], idx) => {
    const x = 0.78 + idx * 3.03;
    addText(slide, num, x, 1.72, 1.72, 0.62, { fontSize: 34, bold: true, color: idx === 3 ? C.teal : C.plum });
    addText(slide, label, x + 0.02, 2.36, 2.05, 0.2, { fontSize: 10.5, color: C.muted });
  });
  addNativeBarChart(slide, "Source", sourceRows(source), 0.78, 3.05, 5.45, 3.35, C.plum);
  addNativeColumnChart(slide, "Density", topEntries(density, 4), 7.05, 3.1, 4.85, 3.15, [C.teal, C.saffron, C.plum]);
  addFooter(slide, 2, total);

  // Slide 3
  slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addText(slide, "The best style anchors are still consulting-native", 0.7, 0.46, 8.4, 0.45, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "Use World Bank and IMF for robustness, but sample visual direction from Roland Berger, BCG, and Accenture.", 0.72, 0.98, 8.9, 0.25, {
    fontSize: 11,
    color: C.muted,
  });
  const refs = [
    ["Roland Berger", "roland_berger_trend_compendium_2050_technology_and_innovation_slide_008.png", "data evidence / scatter"],
    ["BCG", "bcg_how-cpg-retail-leaders-maximize-ai-roi_slide_005.png", "structured analysis"],
    ["Accenture", "accenture_Accenture-Banking-Top-10-Trends-2024_slide_005.png", "visual narrative"],
  ];
  refs.forEach(([name, file, tag], idx) => {
    const x = 0.74 + idx * 4.08;
    addImageIfExists(slide, file, x, 1.62, 3.45, 2.0);
    addText(slide, name, x, 3.88, 1.8, 0.22, { fontSize: 13, bold: true });
    addRule(slide, x, 4.2, 0.92, idx === 0 ? C.teal : idx === 1 ? C.green : C.violet);
    addText(slide, tag, x, 4.44, 2.6, 0.2, { fontSize: 10, color: C.muted });
    addText(slide, "Feed into prompt packs as style references, not copied content.", x, 4.9, 2.9, 0.45, {
      fontSize: 10,
      color: C.ink,
    });
  });
  addFooter(slide, 3, total);

  // Slide 4
  slide = pptx.addSlide();
  slide.background = { color: C.pale };
  addText(slide, "Layout labels are already expressive enough for retrieval", 0.65, 0.48, 8.5, 0.45, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "The next generator should branch by archetype before it writes slide text.", 0.66, 1.0, 6.2, 0.24, {
    fontSize: 11,
    color: C.muted,
  });
  const evidence =
    (layout.get("two_col_chart") || 0) +
    (layout.get("full_width_chart") || 0) +
    (layout.get("scatter_bubble_chart") || 0) +
    (layout.get("comparison_table") || 0);
  const frameworks = (layout.get("process_flow_timeline") || 0) + (layout.get("icon_grid") || 0) + (layout.get("mixed_layout") || 0);
  const narrative =
    (layout.get("title_slide") || 0) +
    (layout.get("section_divider") || 0) +
    (layout.get("three_col_text") || 0) +
    (layout.get("appendix") || 0);
  [
    ["Evidence", evidence, "charts, tables, callouts", C.teal],
    ["Framework", frameworks, "flows, icons, mixed layouts", C.plum],
    ["Narrative", narrative, "titles, text, appendix", C.saffron],
  ].forEach(([name, val, desc, color], idx) => {
    const x = 0.8 + idx * 4.05;
    addText(slide, String(val), x, 1.72, 1.55, 0.55, { fontSize: 34, bold: true, color });
    addText(slide, name, x, 2.42, 2.1, 0.24, { fontSize: 14, bold: true });
    addRule(slide, x, 2.77, 1.0, color);
    addText(slide, desc, x, 3.02, 2.6, 0.26, { fontSize: 10.5, color: C.muted });
  });
  addNativeBarChart(slide, "Layout", topEntries(layout, 8), 0.82, 3.75, 5.55, 2.6, C.teal);
  addNativeColumnChart(slide, "Chart type", topEntries(chart, 6), 7.1, 3.82, 4.75, 2.5, [C.plum, C.teal, C.saffron]);
  addFooter(slide, 4, total);

  // Slide 5
  slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addText(slide, "A practical generator starts with intent, then style memory", 0.7, 0.5, 8.6, 0.45, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  const steps = [
    ["1", "Brief", "topic, audience, decision, message"],
    ["2", "Retrieve", "layout + chart + density neighbors"],
    ["3", "Author", "editable pptxgenJS shapes and charts"],
    ["4", "Score", "QC labels, legibility, visual distance"],
  ];
  steps.forEach(([num, title, desc], idx) => {
    const y = 1.5 + idx * 1.08;
    addRoundRect(slide, 0.82, y, 0.44, 0.44, idx < 2 ? C.plum : C.teal);
    addText(slide, num, 0.96, y + 0.09, 0.18, 0.15, { fontSize: 10, color: C.paper, bold: true, align: "center" });
    addText(slide, title, 1.55, y - 0.02, 1.8, 0.24, { fontSize: 15, bold: true });
    addText(slide, desc, 1.55, y + 0.31, 4.9, 0.24, { fontSize: 10.5, color: C.muted });
    if (idx < 3) {
      slide.addShape(pptx.ShapeType.line, {
        x: 1.04,
        y: y + 0.55,
        w: 0,
        h: 0.42,
        line: { color: "CBC6BC", width: 1.2, beginArrowType: "none", endArrowType: "triangle" },
      });
    }
  });
  addRoundRect(slide, 8.05, 1.36, 3.25, 3.35, C.black, { rectRadius: 0.06 });
  addText(slide, "Prompt pack", 8.42, 1.82, 1.8, 0.25, { fontSize: 13, bold: true, color: C.paper });
  ["layout_type", "chart_type", "text_density", "palette", "references"].forEach((item, idx) => {
    addText(slide, item, 8.44, 2.35 + idx * 0.38, 1.8, 0.18, { fontSize: 10, color: "D7DEE6" });
    addRect(slide, 10.34, 2.42 + idx * 0.38, 0.58 + idx * 0.22, 0.045, idx % 2 ? C.saffron : C.teal);
  });
  addText(slide, "Output should be a real PPTX, not just an image. That is why pptxgenJS is the right next surface.", 8.36, 5.45, 3.25, 0.42, {
    fontSize: 11,
    color: C.ink,
  });
  addFooter(slide, 5, total);

  // Slide 6
  slide = pptx.addSlide();
  slide.background = { color: C.black };
  addText(slide, "Next sprint", 0.82, 0.62, 2.6, 0.45, { fontSize: 24, bold: true, color: C.paper });
  addText(slide, "Move from complete labels to ranked generated slide variants", 0.84, 1.13, 4.8, 0.24, { fontSize: 11, color: "BAC5CE" });
  const next = [
    ["Lock source weights", "Favor consulting-native slides for style; keep report pages as background data."],
    ["Add human audit marks", "Keep draft labels, but flag subjective layout calls before final training use."],
    ["Generate 3 variants per prompt", "Use retrieval packs and compare native chart structure."],
    ["Score presentation quality", "Combine schema checks, render checks, and manual preference."],
  ];
  next.forEach(([title, body], idx) => {
    const x = 0.92 + (idx % 2) * 5.95;
    const y = 2.0 + Math.floor(idx / 2) * 1.75;
    addRect(slide, x, y, 0.08, 0.85, idx % 2 ? C.saffron : C.teal);
    addText(slide, title, x + 0.26, y - 0.02, 4.6, 0.25, { fontSize: 14, color: C.paper, bold: true });
    addText(slide, body, x + 0.26, y + 0.38, 4.55, 0.45, { fontSize: 10.5, color: "C4CED7" });
  });
  addText(slide, "Decision: keep pptxgenJS for generated decks; use Python only for data prep and preview artifacts.", 0.9, 6.45, 7.5, 0.25, {
    fontSize: 11,
    color: C.paper,
    bold: true,
  });
  addText(slide, "06", 12.45, 7.1, 0.35, 0.16, { fontSize: 8, color: "9BA4B1", align: "right" });

  return pptx.writeFile({ fileName: DECK_PATH }).then(() => {
    console.log(`Wrote ${DECK_PATH}`);
  });
}

buildDeck().catch((err) => {
  console.error(err);
  process.exit(1);
});
