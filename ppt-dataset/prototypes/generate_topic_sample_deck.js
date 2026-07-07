const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const BASE_DIR = path.resolve(__dirname, "..");
const OUT_DIR = path.join(BASE_DIR, "prototypes", "output");
const DECK_PATH = path.join(OUT_DIR, "sample_prompt_genai_banking_deck.pptx");
const PROMPT_PATH = path.join(OUT_DIR, "sample_prompt_genai_banking.json");

const SAMPLE_PROMPT = {
  topic: "GenAI in Mid-Market Banking: 90-Day Value Capture Plan",
  audience: "COO, Chief Digital Officer, and transformation leadership team",
  request:
    "Create a consulting-style executive deck that recommends where a mid-market bank should focus GenAI pilots over the next 90 days. Include charts and graphs showing use-case value, adoption ramp, investment allocation, portfolio tradeoffs, and expected operating impact.",
  data_note: "All numbers are illustrative prototype data for deck-generation validation, not market facts.",
  style_anchor:
    "Use the labeled consulting-slide corpus for layout density and chart language; favor Roland Berger, BCG, and Accenture as visual anchors.",
};

const data = {
  useCases: [
    ["Contact center copilot", 88],
    ["Credit memo assistant", 76],
    ["KYC document review", 71],
    ["Collections next action", 63],
    ["Marketing personalization", 54],
  ],
  adoption: {
    labels: ["Month 0", "Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
    ops: [0, 8, 19, 33, 48, 61, 72],
    risk: [0, 5, 13, 24, 34, 43, 51],
  },
  allocation: [
    ["Platform + security", 34],
    ["Workflow build", 28],
    ["Change + training", 22],
    ["Measurement", 16],
  ],
  portfolio: {
    x: [72, 64, 58, 45, 68],
    y: [84, 77, 69, 61, 56],
    sizes: [28, 22, 20, 16, 14],
    labels: ["Contact center", "Credit memo", "KYC review", "Collections", "Marketing"],
  },
  impact: [
    ["Call handling time", -18],
    ["Manual review hours", -26],
    ["First-contact resolution", 12],
    ["Cycle time to decision", -21],
  ],
  roadmap: {
    labels: ["Weeks 1-2", "Weeks 3-6", "Weeks 7-10", "Weeks 11-13"],
    foundation: [80, 35, 15, 10],
    pilots: [20, 55, 45, 25],
    scale: [0, 10, 40, 65],
  },
};

const pptx = new pptxgen();
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.author = "ppt-dataset prototype";
pptx.company = "Research prototype";
pptx.subject = SAMPLE_PROMPT.topic;
pptx.title = "GenAI Banking Sample Prompt Deck";
pptx.lang = "en-US";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "en-US",
};

const C = {
  black: "111216",
  charcoal: "252A31",
  ink: "20242B",
  muted: "6C7480",
  pale: "F7F6F2",
  paper: "FFFFFF",
  grid: "E7E2DA",
  teal: "168C9B",
  cyan: "35B6C7",
  plum: "6B3FA0",
  violet: "A739D8",
  saffron: "F2A541",
  green: "6CBF84",
  red: "D75A4A",
};

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    margin: opts.margin ?? 0,
    fit: "shrink",
    fontFace: opts.fontFace || "Aptos",
    fontSize: opts.fontSize || 12,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    align: opts.align || "left",
    valign: opts.valign || "top",
    breakLine: false,
    paraSpaceAfterPt: 0,
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

function footer(slide, n) {
  addText(slide, "Illustrative prototype data | Generated from sample prompt", 0.55, 7.13, 4.8, 0.16, {
    fontSize: 7,
    color: C.muted,
  });
  addText(slide, String(n).padStart(2, "0"), 12.45, 7.1, 0.35, 0.16, {
    fontSize: 8,
    color: C.muted,
    align: "right",
  });
}

function barChart(slide, entries, x, y, w, h) {
  slide.addChart(
    pptx.ChartType.bar,
    [{ name: "Value index", labels: entries.map((d) => d[0]), values: entries.map((d) => d[1]) }],
    {
      x,
      y,
      w,
      h,
      showLegend: false,
      showTitle: false,
      showValue: true,
      dataLabelPosition: "outEnd",
      dataLabelFontSize: 8,
      dataLabelColor: C.muted,
      catAxisLabelFontSize: 9,
      valAxisLabelFontSize: 8,
      valAxisMinVal: 0,
      valAxisMaxVal: 100,
      valGridLine: { color: C.grid, transparency: 30 },
      chartColors: [C.plum],
    }
  );
}

function lineChart(slide, x, y, w, h) {
  slide.addChart(
    pptx.ChartType.line,
    [
      { name: "Operations", labels: data.adoption.labels, values: data.adoption.ops },
      { name: "Risk + compliance", labels: data.adoption.labels, values: data.adoption.risk },
    ],
    {
      x,
      y,
      w,
      h,
      showLegend: true,
      legendPos: "b",
      showTitle: false,
      catAxisLabelFontSize: 8,
      valAxisLabelFontSize: 8,
      valAxisMinVal: 0,
      valAxisMaxVal: 80,
      valAxisTitle: "% users active weekly",
      valAxisTitleFontSize: 8,
      valGridLine: { color: C.grid, transparency: 25 },
      chartColors: [C.teal, C.saffron],
      lineSize: 2.25,
      showValue: false,
    }
  );
}

function doughnutChart(slide, x, y, w, h) {
  slide.addChart(
    pptx.ChartType.doughnut,
    [{ name: "Allocation", labels: data.allocation.map((d) => d[0]), values: data.allocation.map((d) => d[1]) }],
    {
      x,
      y,
      w,
      h,
      holeSize: 62,
      showLegend: true,
      legendPos: "r",
      showValue: true,
      showPercent: false,
      dataLabelPosition: "bestFit",
      dataLabelFontSize: 8,
      chartColors: [C.teal, C.plum, C.saffron, C.green],
    }
  );
}

function bubbleChart(slide, x, y, w, h) {
  slide.addChart(
    pptx.ChartType.bubble,
    [
      { name: "Readiness", values: data.portfolio.x },
      { name: "Use-case portfolio", values: data.portfolio.y, sizes: data.portfolio.sizes },
    ],
    {
      x,
      y,
      w,
      h,
      showLegend: false,
      showTitle: false,
      showValue: false,
      catAxisTitle: "Readiness index",
      valAxisTitle: "Value index",
      catAxisTitleFontSize: 8,
      valAxisTitleFontSize: 8,
      catAxisLabelFontSize: 8,
      valAxisLabelFontSize: 8,
      catAxisMinVal: 35,
      catAxisMaxVal: 80,
      valAxisMinVal: 45,
      valAxisMaxVal: 90,
      valGridLine: { color: C.grid, transparency: 20 },
      chartColors: [C.teal],
      chartColorsOpacity: 72,
      lineSize: 0.7,
      showSerName: false,
    }
  );
}

function columnChart(slide, x, y, w, h) {
  slide.addChart(
    pptx.ChartType.bar,
    [
      { name: "Foundation", labels: data.roadmap.labels, values: data.roadmap.foundation },
      { name: "Pilots", labels: data.roadmap.labels, values: data.roadmap.pilots },
      { name: "Scale prep", labels: data.roadmap.labels, values: data.roadmap.scale },
    ],
    {
      x,
      y,
      w,
      h,
      barDir: "col",
      grouping: "stacked",
      showLegend: true,
      legendPos: "b",
      showTitle: false,
      catAxisLabelFontSize: 8,
      valAxisLabelFontSize: 8,
      valAxisMinVal: 0,
      valAxisMaxVal: 100,
      valAxisLabelFormatCode: "0'%'",
      valGridLine: { color: C.grid, transparency: 25 },
      chartColors: [C.charcoal, C.teal, C.saffron],
    }
  );
}

function addImpactRows(slide, x, y) {
  data.impact.forEach(([label, value], idx) => {
    const yy = y + idx * 0.52;
    const color = value < 0 ? C.teal : C.saffron;
    addText(slide, label, x, yy, 2.35, 0.2, { fontSize: 10.5, color: C.ink });
    addText(slide, `${value > 0 ? "+" : ""}${value}%`, x + 2.55, yy - 0.02, 0.75, 0.22, {
      fontSize: 15,
      bold: true,
      color,
      align: "right",
    });
    addRule(slide, x, yy + 0.31, 3.25, idx === 0 ? color : "D8D3CA");
  });
}

function build() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(PROMPT_PATH, JSON.stringify(SAMPLE_PROMPT, null, 2), "utf8");

  // 1. Cover
  let slide = pptx.addSlide();
  slide.background = { color: C.black };
  addRect(slide, 0, 0, 2.2, 7.5, C.charcoal);
  addText(slide, "90", 0.68, 0.78, 1.1, 0.65, { fontSize: 42, bold: true, color: C.cyan, align: "center" });
  addText(slide, "days", 0.72, 1.48, 1.0, 0.2, { fontSize: 13, color: "BFC9D4", align: "center" });
  addText(slide, "GenAI in\nMid-Market\nBanking", 3.0, 1.0, 5.4, 1.85, {
    fontSize: 39,
    bold: true,
    color: C.paper,
    fontFace: "Aptos Display",
  });
  addText(slide, "Value capture plan for service, risk, and credit workflows", 3.04, 3.23, 6.5, 0.34, {
    fontSize: 15,
    color: "CBD5DD",
  });
  addRule(slide, 3.05, 3.82, 1.35, C.teal);
  addText(slide, "Sample prompt deck", 3.05, 6.45, 2.2, 0.2, { fontSize: 10.5, color: "AEB7C2" });
  addText(slide, "Illustrative data", 10.8, 6.96, 1.3, 0.18, { fontSize: 8, color: "9BA4B1", align: "right" });

  // 2. Recommendation
  slide = pptx.addSlide();
  slide.background = { color: C.pale };
  addText(slide, "Prioritize customer-service and credit workflows first", 0.65, 0.48, 8.2, 0.45, {
    fontSize: 25,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "They combine visible P&L impact, manageable controls, and enough repeat volume for fast learning.", 0.66, 1.03, 8.6, 0.25, {
    fontSize: 11,
    color: C.muted,
  });
  addRule(slide, 0.66, 1.35, 1.1, C.teal);
  barChart(slide, data.useCases, 0.82, 1.85, 6.3, 4.55);
  addText(slide, "The first wave should prove three things", 8.0, 1.92, 3.2, 0.28, { fontSize: 16, bold: true });
  [
    ["Impact", "Measurable reduction in manual effort or cycle time"],
    ["Control", "Human review and audit trail from day one"],
    ["Repeatability", "Reusable workflow patterns across products"],
  ].forEach(([title, body], idx) => {
    const y = 2.58 + idx * 1.0;
    addRect(slide, 8.02, y, 0.08, 0.54, idx === 1 ? C.saffron : C.teal);
    addText(slide, title, 8.28, y - 0.03, 1.4, 0.2, { fontSize: 12.5, bold: true });
    addText(slide, body, 8.28, y + 0.3, 3.2, 0.3, { fontSize: 9.6, color: C.muted });
  });
  footer(slide, 2);

  // 3. Adoption graph
  slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addText(slide, "Adoption becomes real when pilots are embedded into weekly work", 0.7, 0.5, 9.0, 0.42, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "Training alone does not move usage; workflow integration does.", 0.72, 1.0, 5.5, 0.24, {
    fontSize: 11,
    color: C.muted,
  });
  lineChart(slide, 0.82, 1.62, 8.05, 4.9);
  addText(slide, "72%", 9.65, 2.0, 1.4, 0.5, { fontSize: 36, bold: true, color: C.teal });
  addText(slide, "weekly active users in operations by month 6", 9.68, 2.65, 2.4, 0.38, { fontSize: 10.5, color: C.muted });
  addText(slide, "Design implication", 9.68, 4.05, 1.9, 0.2, { fontSize: 12.5, bold: true });
  addText(slide, "The pilot plan needs embedded queue triggers, manager coaching, and visible throughput dashboards.", 9.68, 4.42, 2.55, 0.68, { fontSize: 10.2, color: C.ink });
  footer(slide, 3);

  // 4. Investment allocation
  slide = pptx.addSlide();
  slide.background = { color: C.pale };
  addText(slide, "The 90-day budget should over-invest in controls and workflow fit", 0.65, 0.48, 9.0, 0.42, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "A flashy model demo is the easy part; adoption depends on security, task design, and measurement.", 0.66, 1.0, 8.8, 0.25, {
    fontSize: 11,
    color: C.muted,
  });
  doughnutChart(slide, 0.98, 1.75, 5.1, 3.85);
  addText(slide, "Illustrative 90-day allocation", 1.1, 5.82, 3.2, 0.22, { fontSize: 11, color: C.muted });
  addImpactRows(slide, 7.0, 2.05);
  addText(slide, "Expected operating movement", 7.0, 1.55, 3.2, 0.24, { fontSize: 15, bold: true });
  addText(slide, "Target metrics should be tracked weekly and reviewed before any scale decision.", 7.0, 4.55, 3.9, 0.42, {
    fontSize: 10.5,
    color: C.muted,
  });
  footer(slide, 4);

  // 5. Portfolio graph
  slide = pptx.addSlide();
  slide.background = { color: C.paper };
  addText(slide, "A portfolio lens prevents the pilot list from becoming a wish list", 0.7, 0.5, 8.9, 0.42, {
    fontSize: 24,
    bold: true,
    fontFace: "Aptos Display",
  });
  addText(slide, "Start with high-readiness, high-value use cases; defer anything that needs unresolved policy change.", 0.72, 1.0, 8.8, 0.24, {
    fontSize: 11,
    color: C.muted,
  });
  bubbleChart(slide, 0.82, 1.62, 7.2, 4.95);
  addText(slide, "Use-case legend", 8.55, 1.68, 1.8, 0.22, { fontSize: 13, bold: true });
  data.portfolio.labels.forEach((label, idx) => {
    const y = 2.14 + idx * 0.55;
    addRoundRect(slide, 8.58, y, 0.18, 0.18, idx < 2 ? C.teal : idx === 2 ? C.saffron : C.plum);
    addText(slide, label, 8.9, y - 0.02, 2.0, 0.18, { fontSize: 10.5, color: C.ink });
  });
  addText(slide, "Bubble size indicates relative 90-day benefit pool.", 8.58, 5.35, 2.8, 0.36, { fontSize: 10, color: C.muted });
  footer(slide, 5);

  // 6. Roadmap
  slide = pptx.addSlide();
  slide.background = { color: C.black };
  addText(slide, "The operating model shifts from foundation to scale by week 10", 0.75, 0.58, 9.1, 0.42, {
    fontSize: 24,
    bold: true,
    color: C.paper,
    fontFace: "Aptos Display",
  });
  addText(slide, "The final three weeks should decide scale/no-scale, not discover basic blockers.", 0.77, 1.1, 7.3, 0.24, {
    fontSize: 11,
    color: "BAC5CE",
  });
  columnChart(slide, 0.95, 1.72, 7.1, 4.85);
  addText(slide, "Decision gates", 8.75, 1.9, 2.0, 0.24, { fontSize: 15, color: C.paper, bold: true });
  [
    ["Gate 1", "security pattern approved"],
    ["Gate 2", "two workflows live"],
    ["Gate 3", "weekly benefit signal visible"],
    ["Gate 4", "scale backlog funded"],
  ].forEach(([gate, body], idx) => {
    const y = 2.42 + idx * 0.75;
    addRect(slide, 8.78, y, 0.08, 0.42, idx < 2 ? C.teal : C.saffron);
    addText(slide, gate, 9.02, y - 0.02, 0.8, 0.18, { fontSize: 10.5, color: C.paper, bold: true });
    addText(slide, body, 9.85, y - 0.02, 2.1, 0.2, { fontSize: 10, color: "C6CFD8" });
  });
  addText(slide, "Recommendation: fund a controlled 90-day wave, but block broad rollout until adoption and control metrics are proven.", 0.95, 6.65, 8.8, 0.28, {
    fontSize: 11,
    color: C.paper,
    bold: true,
  });
  addText(slide, "06", 12.45, 7.1, 0.35, 0.16, { fontSize: 8, color: "9BA4B1", align: "right" });

  return pptx.writeFile({ fileName: DECK_PATH }).then(() => {
    console.log(`Wrote ${DECK_PATH}`);
    console.log(`Wrote ${PROMPT_PATH}`);
  });
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
