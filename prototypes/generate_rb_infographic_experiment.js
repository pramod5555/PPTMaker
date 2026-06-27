const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const BASE_DIR = path.resolve(__dirname, "..");
const OUT_DIR = path.join(BASE_DIR, "prototypes", "output");
const DECK_PATH = path.join(OUT_DIR, "rb_style_infographic_experiment.pptx");
const RECIPE_PATH = path.join(OUT_DIR, "rb_style_infographic_recipe.json");
const SOURCE_FEATURE_PATH = path.join(
  BASE_DIR,
  "fidelity",
  "roland_berger_trend_compendium_2050_technology_and_innovation_slide_008.json"
);

const C = {
  rail: "30343A",
  railMuted: "74787F",
  divider: "6B3FA0",
  ink: "111216",
  muted: "8A8F96",
  paper: "FFFFFF",
  panel: "D9DDE2",
  panelDark: "545B63",
  blue: "06466D",
  blue2: "2D79A3",
  lavender: "A99BD1",
  lightLavender: "C8BFDF",
  grid: "D8D8D8",
  footer: "4A4F56",
};

const benchmark = {
  x: [0.4, 0.7, 1.1, 1.2, 1.6, 1.8, 2.2, 2.5, 2.9, 3.1, 3.4, 4.0, 4.5, 1.4, 2.0, 2.8],
  y: [34, 39, 42, 46, 51, 55, 58, 54, 63, 60, 68, 66, 70, 48, 52, 57],
  sizes: [8, 9, 8, 9, 11, 11, 12, 11, 13, 12, 13, 12, 13, 10, 10, 11],
};

const highlightLabels = [
  ["US", 2.9, 63],
  ["Germany", 3.1, 60],
  ["Japan", 2.5, 54],
  ["South Korea", 4.0, 66],
  ["UK", 2.2, 58],
  ["Estonia", 1.4, 48],
  ["Lithuania", 1.1, 42],
];

function readRecipe() {
  if (!fs.existsSync(SOURCE_FEATURE_PATH)) return null;
  return JSON.parse(fs.readFileSync(SOURCE_FEATURE_PATH, "utf8"));
}

const pptx = new pptxgen();
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.author = "ppt-dataset prototype";
pptx.company = "Research prototype";
pptx.subject = "RB-style infographic experiment";
pptx.title = "RB-style Infographic Experiment";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};

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
    align: opts.align || "left",
    valign: opts.valign || "top",
    margin: opts.margin ?? 0,
    fit: "shrink",
    breakLine: false,
    paraSpaceAfterPt: 0,
    rotate: opts.rotate || 0,
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
  });
}

function addLine(slide, x, y, w, h, color, width = 1) {
  // OOXML requires non-negative ext cx/cy; use flipH/flipV for direction instead.
  const opts = { line: { color, width } };
  opts.x = w < 0 ? x + w : x;
  opts.y = h < 0 ? y + h : y;
  opts.w = Math.abs(w);
  opts.h = Math.abs(h);
  if (w < 0) opts.flipH = true;
  if (h < 0) opts.flipV = true;
  slide.addShape(pptx.ShapeType.line, opts);
}

function addHex(slide, x, y, w, h, fill, line, opts = {}) {
  slide.addShape(pptx.ShapeType.hexagon, {
    x,
    y,
    w,
    h,
    fill: { color: fill, transparency: opts.transparency ?? 0 },
    line: { color: line, width: opts.lineWidth || 2 },
  });
}

function addBullet(slide, y, boldLead, rest, height = 0.48) {
  addText(slide, ">", 9.85, y, 0.18, 0.18, { fontSize: 12, color: C.ink });
  addText(slide, boldLead, 10.1, y, 1.55, 0.2, { fontSize: 11.2, bold: true, color: C.ink });
  addText(slide, rest, 10.1, y + 0.2, 2.65, height, { fontSize: 10.2, color: C.ink });
}

function addScatter(slide) {
  slide.addChart(
    pptx.ChartType.bubble,
    [
      { name: "AI investment intensity", values: benchmark.x },
      { name: "Digital operating maturity", values: benchmark.y, sizes: benchmark.sizes },
    ],
    {
      x: 2.95,
      y: 2.14,
      w: 6.42,
      h: 4.0,
      showLegend: false,
      showTitle: false,
      showValue: false,
      catAxisTitle: "AI investment intensity as % of operating cost",
      valAxisTitle: "Digital operating maturity index",
      catAxisTitleFontFace: "Aptos",
      valAxisTitleFontFace: "Aptos",
      catAxisTitleFontSize: 10,
      valAxisTitleFontSize: 10,
      catAxisLabelFontSize: 9,
      valAxisLabelFontSize: 9,
      catAxisMinVal: 0,
      catAxisMaxVal: 5,
      valAxisMinVal: 30,
      valAxisMaxVal: 72,
      valAxisMajorUnit: 10,
      catAxisMajorUnit: 0.5,
      valGridLine: { color: "E3E3E3", transparency: 15 },
      chartColors: [C.blue],
      chartColorsOpacity: 92,
      lineSize: 0.55,
      showSerName: false,
      dataBorder: { pt: 0.5, color: C.blue },
    }
  );

  // Regression line overlay, aligned to chart plot area.
  addLine(slide, 3.35, 5.57, 5.45, -2.74, "55595E", 1.0);

  highlightLabels.forEach(([label, xv, yv]) => {
    const chartX = 2.95 + 0.42 + (xv / 5.0) * 5.48;
    const chartY = 2.14 + 3.52 - ((yv - 30) / 42) * 3.17;
    addText(slide, label, chartX + 0.05, chartY - 0.08, 0.8, 0.18, {
      fontSize: 9.6,
      color: C.ink,
    });
  });

  addText(slide, "R: 0.62", 3.07, 2.78, 0.65, 0.18, { fontSize: 11.5, color: C.ink });
}

function build() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const sourceRecipe = readRecipe();
  fs.writeFileSync(
    RECIPE_PATH,
    JSON.stringify(
      {
        source_anchor: sourceRecipe
          ? {
              slide_id: sourceRecipe.slide_id,
              design_recipe: sourceRecipe.fidelity.design_recipe,
              regions: sourceRecipe.fidelity.regions,
              note: "Used only as structural reference; generated slide uses original topic, data, and text.",
            }
          : null,
        target_recipe:
          "left_nav_rail + title_stack + scatter_evidence_field + right_insight_panel + source_footer",
        generated_slide: path.relative(BASE_DIR, DECK_PATH).replaceAll("\\", "/"),
      },
      null,
      2
    ),
    "utf8"
  );

  const slide = pptx.addSlide();
  slide.background = { color: C.paper };

  // Left navigation rail.
  addRect(slide, 0, 0, 1.78, 7.5, C.rail);
  addRect(slide, 1.78, 0, 0.035, 7.5, C.divider);
  addText(slide, "Digital\nOperations", 0.13, 0.48, 1.3, 0.6, {
    fontSize: 18,
    bold: true,
    color: C.paper,
    fontFace: "Aptos Display",
  });
  [
    ["1", "Value\nof AI", C.blue2, "FFFFFF", 1.45],
    ["2", "Control\nmodel", "777B82", "C1C5CA", 2.75],
    ["3", "Scale\nplan", "8B8F96", "E5E7EA", 4.05],
  ].forEach(([num, label, fill, line, y]) => {
    addHex(slide, 0.12, y, 0.78, 0.62, fill, line, { lineWidth: 2.2, transparency: num === "1" ? 0 : 45 });
    addText(slide, num, 0.96, y + 0.03, 0.3, 0.25, {
      fontSize: 23,
      bold: true,
      color: num === "1" ? C.lavender : C.railMuted,
      align: "center",
    });
    addText(slide, label, 1.16, y + 0.15, 0.58, 0.32, {
      fontSize: 8.9,
      bold: num === "1",
      color: num === "1" ? C.lavender : C.railMuted,
    });
  });
  addText(slide, "9", 0.12, 7.2, 0.18, 0.14, { fontSize: 8.5, color: C.paper });
  addText(slide, "AI", 0.68, 6.42, 0.55, 0.34, { fontSize: 26, bold: true, color: "6F747B", align: "center" });

  // Title stack.
  addText(
    slide,
    "... as AI investment intensity emerges as a decisive factor\nfor scalable productivity gains",
    2.16,
    0.48,
    8.95,
    0.72,
    { fontSize: 23.5, bold: true, color: C.ink, fontFace: "Aptos Display" }
  );
  addText(
    slide,
    "Illustrative banking benchmark plotted against AI investment intensity",
    2.17,
    1.46,
    8.6,
    0.28,
    { fontSize: 17.2, color: C.muted }
  );

  // Main evidence field.
  addScatter(slide);

  addText(slide, "Emerging banks", 3.28, 2.18, 1.0, 0.18, { fontSize: 9.4, color: C.ink });
  addHex(slide, 3.05, 2.18, 0.12, 0.1, C.lightLavender, C.lightLavender, { lineWidth: 0.2 });
  addText(slide, "Advanced digital leaders", 3.28, 2.43, 1.55, 0.18, { fontSize: 9.4, color: C.ink });
  addHex(slide, 3.05, 2.43, 0.12, 0.1, C.blue, C.blue, { lineWidth: 0.2 });

  // Right insight panel.
  addRect(slide, 9.7, 1.9, 3.45, 5.12, C.panel);
  addBullet(slide, 2.08, "Funding AI operations", "must connect to repeatable frontline workflows", 0.42);
  addBullet(slide, 3.0, "Productivity processes", "need controls for adoption, data quality, and auditability", 0.5);
  addBullet(slide, 4.02, "Higher investment intensity", "correlates with maturity, but execution quality explains dispersion", 0.58);
  addBullet(slide, 5.52, "At the operating level", "investment signals confidence in redesign and scaled learning", 0.58);

  // Footer.
  addText(slide, "1) Prototype benchmark created for slide-generation research; values are illustrative", 2.17, 7.08, 5.5, 0.14, {
    fontSize: 7.2,
    color: C.footer,
  });
  addText(slide, "Sources: synthetic benchmark set; ppt-dataset fidelity extractor", 2.17, 7.25, 4.8, 0.14, {
    fontSize: 7.2,
    color: C.footer,
  });
  addText(slide, "Prototype", 12.18, 7.2, 0.75, 0.16, { fontSize: 7.2, color: C.footer, align: "right" });

  return pptx.writeFile({ fileName: DECK_PATH }).then(() => {
    console.log(`Wrote ${DECK_PATH}`);
    console.log(`Wrote ${RECIPE_PATH}`);
  });
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
