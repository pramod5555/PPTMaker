const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const BASE_DIR = path.resolve(__dirname, "..");
const OUT_DIR = path.join(BASE_DIR, "prototypes", "output");
const DECK_PATH = path.join(OUT_DIR, "html_corpus_ai_banking_sample_deck.pptx");
const SPEC_PATH = path.join(OUT_DIR, "html_corpus_ai_banking_sample_spec.json");

const anchors = [
  "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_011.html",
  "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_012.html",
  "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_019.html",
  "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_024.html",
  "roland_berger_trend_compendium_2030___trend_5_dynamic_technology_and_innovation_slide_029.html",
];

const SPEC = {
  topic: "AI-native banking platforms: where value scales first",
  objective:
    "Generate a sample deck using newly processed HTML/CSS slide data as layout and infographic anchors.",
  source_corpus: anchors.map((name) => `html_slides/${name}`),
  data_note: "All figures are illustrative prototype data for design-system validation.",
  layouts_used: [
    "diffusion milestone ranked bars",
    "regional adoption comparison",
    "dual donut share shift",
    "digital evolution bubble timeline",
    "market value comparison",
  ],
};

const pptx = new pptxgen();
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.author = "ppt-dataset prototype";
pptx.company = "PPTMaker";
pptx.subject = SPEC.topic;
pptx.title = "HTML Corpus AI Banking Sample Deck";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Calibri Light",
  bodyFontFace: "Calibri",
  lang: "en-US",
};

const C = {
  black: "050505",
  ink: "111111",
  grey: "8D949B",
  paleGrey: "D9DDE2",
  rule: "000000",
  teal: "0AA8BD",
  teal2: "80C9D6",
  darkBlue: "166F9F",
  paper: "FFFFFF",
  panel: "F2F4F6",
  grid: "E1E5EA",
  purple: "5B2D8E",
  green: "3D8C74",
};

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    margin: opts.margin ?? 0,
    fit: opts.fit || "shrink",
    fontFace: opts.fontFace || "Calibri",
    fontSize: opts.fontSize || 12,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || "left",
    valign: opts.valign || "top",
    breakLine: false,
    paraSpaceAfterPt: 0,
    rotate: opts.rotate,
  });
}

function rect(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: fill, transparency: opts.transparency ?? 0 },
    line: opts.line ? { color: opts.line, width: opts.lineWidth || 1 } : { color: fill, transparency: 100 },
  });
}

function ellipse(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(pptx.ShapeType.ellipse, {
    x,
    y,
    w,
    h,
    fill: { color: fill, transparency: opts.transparency ?? 0 },
    line: opts.line ? { color: opts.line, width: opts.lineWidth || 1 } : { color: fill, transparency: 100 },
  });
}

function line(slide, x1, y1, x2, y2, color = C.rule, width = 1) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: { color, width, beginArrowType: "none", endArrowType: "none" },
  });
}

function brand(slide) {
  addText(slide, "Corpus\nsample", 11.58, 0.28, 0.72, 0.38, {
    fontSize: 10.5,
    align: "right",
    color: C.ink,
    fit: "resize",
  });
  addText(slide, "B", 12.36, 0.36, 0.42, 0.42, { fontSize: 30, bold: true, color: "A0A6AA" });
}

function rbHeader(slide, section, title, subtitle) {
  addText(slide, section, 1.0, 0.32, 8.6, 0.28, { fontSize: 12.5, bold: true, color: C.grey });
  brand(slide);
  addText(slide, title, 1.0, 0.88, 10.7, 0.82, {
    fontFace: "Calibri Light",
    fontSize: 26,
    color: C.black,
    fit: "shrink",
  });
  addText(slide, subtitle, 1.0, 2.03, 10.2, 0.44, {
    fontFace: "Calibri Light",
    fontSize: 19,
    color: C.grey,
    fit: "shrink",
  });
}

function footer(slide, n, anchor) {
  addText(slide, `Design anchor: ${anchor}`, 1.0, 7.1, 8.9, 0.14, { fontSize: 6.7, color: "444444" });
  addText(slide, `| ${String(n).padStart(2, "0")}`, 12.34, 7.1, 0.42, 0.14, {
    fontSize: 6.7,
    color: "777777",
    align: "right",
  });
}

function cover() {
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  rect(slide, 0, 0, 0.18, 7.5, C.teal);
  rect(slide, 0.18, 0, 0.04, 7.5, C.purple);
  addText(slide, "HTML/CSS corpus sample", 0.95, 0.65, 4.2, 0.28, { fontSize: 14, bold: true, color: C.grey });
  addText(slide, "AI-native banking platforms", 0.95, 1.18, 8.5, 0.56, {
    fontFace: "Calibri Light",
    fontSize: 34,
    color: C.black,
  });
  addText(slide, "where value scales first", 0.95, 1.78, 6.2, 0.48, {
    fontFace: "Calibri Light",
    fontSize: 30,
    color: C.black,
  });
  addText(
    slide,
    "A generated sample deck using the newly processed Roland Berger HTML/CSS slide conversions as layout memory",
    0.98,
    2.62,
    7.1,
    0.52,
    { fontSize: 16, color: C.grey, fit: "shrink" }
  );
  line(slide, 0.98, 3.42, 3.3, 3.42, C.rule, 4);

  const items = [
    ["011", "diffusion bars"],
    ["012", "regional comparison"],
    ["019", "dual donut shift"],
    ["024", "bubble timeline"],
    ["029", "market value comparison"],
  ];
  items.forEach(([num, label], i) => {
    const x = 7.7 + (i % 2) * 2.15;
    const y = 4.2 + Math.floor(i / 2) * 0.58;
    addText(slide, num, x, y, 0.42, 0.24, { fontSize: 15, bold: true, color: C.teal });
    addText(slide, label, x + 0.5, y + 0.02, 1.5, 0.18, { fontSize: 9.5, color: C.grey });
  });
  brand(slide);
  footer(slide, 1, "html_slides/*priority Roland Berger conversions");
}

function diffusionBars() {
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  rbHeader(
    slide,
    "1. Adoption velocity - From pilots to institutional workflows",
    "AI platforms are reaching diffusion thresholds faster",
    "Time from first deployment to 25% weekly active workflow coverage [months]"
  );
  const rows = [
    ["Core analytics dashboards", 46],
    ["RPA workflow scripts", 35],
    ["Cloud data lake", 31],
    ["Document AI", 26],
    ["GenAI knowledge assistant", 16],
    ["Credit memo copilot", 13],
    ["Service AI copilot", 7],
    ["Agentic queue orchestration", 4],
  ];
  line(slide, 3.4, 3.0, 3.4, 6.7, C.rule, 1);
  rows.forEach(([label, value], i) => {
    const y = 3.1 + i * 0.47;
    addText(slide, label, 1.0, y + 0.02, 2.2, 0.2, { fontSize: 11.5, color: C.black });
    rect(slide, 3.42, y, (value / 46) * 7.0, 0.27, C.teal);
    addText(slide, String(value), 3.55 + (value / 46) * 7.0, y + 0.03, 0.42, 0.16, {
      fontSize: 11.5,
      bold: true,
      color: C.black,
    });
  });
  addText(slide, "Read: platformized AI is moving from experimentation to institutional workflow coverage on a compressed timeline.", 8.1, 6.35, 3.2, 0.38, {
    fontSize: 10.5,
    color: C.grey,
  });
  footer(slide, 2, anchors[0]);
}

function regionalReadiness() {
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  rbHeader(
    slide,
    "2. Deployment footprint - Readiness is uneven by market",
    "AI readiness is uneven by market",
    "Indexed AI banking platform readiness by region [0-100]"
  );
  const regions = [
    ["North America", 76, 86],
    ["Europe", 63, 78],
    ["Asia-Pacific", 68, 84],
    ["Middle East", 52, 70],
    ["Latin America", 45, 61],
  ];
  addText(slide, "2024", 1.05, 3.0, 0.7, 0.24, { fontSize: 17, bold: true });
  line(slide, 1.85, 3.18, 6.0, 3.18, C.rule, 4);
  addText(slide, "2028 target", 7.2, 3.0, 1.6, 0.24, { fontSize: 17, bold: true });
  line(slide, 8.55, 3.18, 12.3, 3.18, C.rule, 4);
  regions.forEach(([label, now, target], i) => {
    const y = 3.62 + i * 0.53;
    addText(slide, label, 1.05, y + 0.02, 1.5, 0.18, { fontSize: 10.8 });
    rect(slide, 2.65, y, now / 18, 0.18, C.teal2);
    addText(slide, String(now), 2.76 + now / 18, y, 0.35, 0.16, { fontSize: 9.5, bold: true });
    addText(slide, label, 7.2, y + 0.02, 1.5, 0.18, { fontSize: 10.8 });
    rect(slide, 8.8, y, target / 18, 0.18, C.teal);
    addText(slide, String(target), 8.92 + target / 18, y, 0.35, 0.16, { fontSize: 9.5, bold: true });
  });
  addText(slide, "Implication", 1.05, 6.35, 1.1, 0.2, { fontSize: 12, bold: true, color: C.teal });
  addText(slide, "Scale plays should separate workflow maturity from country-level regulatory readiness.", 2.0, 6.35, 6.0, 0.22, {
    fontSize: 10.5,
    color: C.grey,
  });
  footer(slide, 3, anchors[1]);
}

function valueMix() {
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  rbHeader(
    slide,
    "3. Value pools - Economics shift as platforms mature",
    "Value pools shift as platforms mature",
    "Illustrative banking AI value pool split [% of total]"
  );
  slide.addChart(
    pptx.ChartType.doughnut,
    [
      {
        name: "2024",
        labels: ["Efficiency", "Risk controls", "Revenue growth", "New propositions"],
        values: [58, 18, 16, 8],
      },
    ],
    {
      x: 1.05,
      y: 3.25,
      w: 4.5,
      h: 2.65,
      holeSize: 58,
      showLegend: false,
      showValue: true,
      dataLabelFontSize: 9,
      chartColors: [C.teal, C.teal2, C.paleGrey, C.darkBlue],
    }
  );
  slide.addChart(
    pptx.ChartType.doughnut,
    [
      {
        name: "2028",
        labels: ["Efficiency", "Risk controls", "Revenue growth", "New propositions"],
        values: [34, 24, 28, 14],
      },
    ],
    {
      x: 7.0,
      y: 3.25,
      w: 4.5,
      h: 2.65,
      holeSize: 58,
      showLegend: false,
      showValue: true,
      dataLabelFontSize: 9,
      chartColors: [C.teal, C.teal2, C.paleGrey, C.darkBlue],
    }
  );
  addText(slide, "2024", 0.95, 3.05, 0.8, 0.26, { fontSize: 20, bold: true });
  addText(slide, "2028", 6.9, 3.05, 0.8, 0.26, { fontSize: 20, bold: true });
  [["Efficiency", C.teal], ["Risk controls", C.teal2], ["Revenue growth", C.paleGrey], ["New propositions", C.darkBlue]].forEach(
    ([label, color], i) => {
      const x = 3.0 + i * 1.75;
      rect(slide, x, 6.32, 0.13, 0.13, color);
      addText(slide, label, x + 0.18, 6.29, 1.3, 0.14, { fontSize: 8.3 });
    }
  );
  footer(slide, 4, anchors[2]);
}

function evolutionTimeline() {
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  rbHeader(
    slide,
    "4. Platform evolution - The operating system gets broader",
    "The operating system gets broader",
    "Milestones in AI-native banking platform evolution"
  );
  line(slide, 1.2, 6.52, 12.35, 6.52, C.teal, 2);
  [2024, 2025, 2026, 2027, 2028, 2029].forEach((year, i) => {
    const x = 1.2 + i * 2.0;
    line(slide, x, 6.43, x, 6.62, C.teal, 1);
    addText(slide, String(year), x - 0.25, 6.72, 0.55, 0.18, { fontSize: 10.5, bold: true });
  });
  const bubbles = [
    ["Service copilot", 2.0, 5.75, 0.45],
    ["Document AI", 3.25, 5.35, 0.7],
    ["Credit assistant", 4.65, 4.95, 0.92],
    ["Risk controls", 6.15, 4.35, 1.15],
    ["Customer 360", 7.55, 3.55, 1.42],
    ["Agentic queueing", 9.2, 2.65, 1.88],
    ["Smart operating model", 10.6, 1.48, 2.65],
  ];
  bubbles.forEach(([label, x, y, s]) => {
    ellipse(slide, x, y, s, s, C.teal, { transparency: 58 });
    addText(slide, label, x + s * 0.22, y + s * 0.48, s * 0.78, 0.22, { fontSize: 7.8, color: C.black, fit: "shrink" });
  });
  addText(slide, "Copilot layer", 1.0, 3.9, 1.4, 0.22, { fontSize: 13, bold: true });
  addText(slide, "Decision layer", 5.55, 3.55, 1.5, 0.22, { fontSize: 13, bold: true });
  addText(slide, "Orchestration layer", 9.95, 3.1, 1.8, 0.22, { fontSize: 13, bold: true });
  footer(slide, 5, anchors[3]);
}

function marketValue() {
  const slide = pptx.addSlide();
  slide.background = { color: C.paper };
  rbHeader(
    slide,
    "5. Economic prize - Platform value scales across three benefit pools",
    "Platform value scales across benefit pools",
    "Illustrative annualized value creation potential [INR bn]"
  );
  const groups = [
    ["Efficiency", [["Service", 18, C.teal], ["Ops", 12, C.teal]]],
    ["Risk + credit", [["Credit", 21, C.paleGrey], ["Fraud", 15, C.paleGrey]]],
    ["Growth", [["Next best action", 14, C.teal2], ["Pricing", 9, C.teal2]]],
  ];
  groups.forEach(([group, entries], gi) => {
    const gx = 1.1 + gi * 3.85;
    addText(slide, group, gx, 3.0, 2.2, 0.3, { fontSize: 19, bold: true });
    line(slide, gx, 3.45, gx + 2.95, 3.45, C.rule, 4);
    entries.forEach(([label, val, color], i) => {
      const h = val / 28 * 1.72;
      const x = gx + 0.25 + i * 1.18;
      rect(slide, x, 5.45 - h, 0.72, h, color);
      addText(slide, String(val), x + 0.2, 5.12 - h, 0.35, 0.18, { fontSize: 12, bold: true });
      addText(slide, label, x - 0.05, 5.68, 1.0, 0.28, { fontSize: 9.2, bold: true, align: "center" });
    });
  });
  addText(slide, "89", 11.35, 3.55, 0.72, 0.44, { fontSize: 30, bold: true, color: C.teal });
  addText(slide, "total illustrative annualized value pool across selected workflows", 11.35, 4.12, 1.35, 0.72, {
    fontSize: 10.2,
    color: C.grey,
  });
  footer(slide, 6, anchors[4]);
}

function close() {
  const slide = pptx.addSlide();
  slide.background = { color: C.black };
  rect(slide, 0, 0, 0.16, 7.5, C.teal);
  addText(slide, "What the new HTML/CSS corpus adds", 0.9, 0.85, 6.8, 0.52, {
    fontFace: "Calibri Light",
    fontSize: 32,
    color: C.paper,
  });
  addText(
    slide,
    "The generator can now retrieve concrete infographic structures, not just generic chart labels.",
    0.92,
    1.65,
    6.2,
    0.35,
    { fontSize: 15, color: "C7D0D8" }
  );
  const points = [
    ["Layout memory", "fixed 1280x720 object positions"],
    ["Chart grammar", "bars, donuts, timelines, market comparisons"],
    ["Density cues", "where titles, captions, values, and footers sit"],
    ["Next bridge", "convert HTML patterns into reusable PPTX recipes"],
  ];
  points.forEach(([title, body], i) => {
    const y = 2.62 + i * 0.8;
    rect(slide, 0.95, y, 0.09, 0.42, i < 2 ? C.teal : C.purple);
    addText(slide, title, 1.22, y - 0.03, 1.9, 0.2, { fontSize: 13, bold: true, color: C.paper });
    addText(slide, body, 3.22, y - 0.03, 4.3, 0.22, { fontSize: 12, color: "C7D0D8" });
  });
  addText(slide, "HTML corpus deck", 10.9, 6.85, 1.2, 0.14, { fontSize: 7.5, color: "9BA4B1", align: "right" });
  addText(slide, "| 07", 12.35, 6.85, 0.42, 0.14, { fontSize: 7.5, color: "9BA4B1", align: "right" });
}

async function build() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(SPEC_PATH, JSON.stringify(SPEC, null, 2), "utf8");
  cover();
  diffusionBars();
  regionalReadiness();
  valueMix();
  evolutionTimeline();
  marketValue();
  close();
  await pptx.writeFile({ fileName: DECK_PATH });
  console.log(`Wrote ${DECK_PATH}`);
  console.log(`Wrote ${SPEC_PATH}`);
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
