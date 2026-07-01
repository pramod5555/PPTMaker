"""
build_gallery.py — Generate a browsable HTML gallery of all converted slides.

Reads html_slides/ and dataset.json, groups slides by source company,
and writes slide_gallery.html to the pptmaker root directory.

Usage:
    python build_gallery.py
"""

import json
from pathlib import Path
from collections import defaultdict

ROOT      = Path(__file__).parent.parent          # pptmaker/
HTML_DIR  = ROOT / "html_slides"
DATASET   = Path(__file__).parent / "dataset.json"
OUT_FILE  = ROOT / "slide_gallery.html"

THUMB_W, THUMB_H = 640, 360   # displayed size (50% of 1280×720)
SCALE = 0.5

# Source display order and colors
SOURCE_META = {
    "Roland Berger": {"color": "#c0392b", "short": "RB"},
    "Deloitte":      {"color": "#006400", "short": "DLT"},
    "Bain":          {"color": "#1a237e", "short": "BAIN"},
    "Oliver Wyman":  {"color": "#e65100", "short": "OW"},
    "Strategy&":     {"color": "#4a148c", "short": "S&"},
    "BCG":           {"color": "#0d47a1", "short": "BCG"},
    "Accenture":     {"color": "#7b1fa2", "short": "ACC"},
    "World Bank":    {"color": "#1565c0", "short": "WB"},
    "Unknown":       {"color": "#546e7a", "short": "UNK"},
}

def main():
    # Load dataset for metadata
    with open(DATASET, encoding="utf-8") as f:
        data = json.load(f)
    meta = {s["slide_id"]: s.get("label", {}) for s in data["slides"]}

    # Collect available HTML files
    html_files = sorted(HTML_DIR.glob("*.html"))
    if not html_files:
        print("No HTML files found in html_slides/")
        return

    # Group by source_company
    groups = defaultdict(list)
    for hf in html_files:
        sid = hf.stem
        lbl = meta.get(sid, {})
        src = lbl.get("source_company", "Unknown")
        groups[src].append({
            "sid": sid,
            "path": f"html_slides/{hf.name}",
            "layout": lbl.get("layout_type", "unknown"),
            "purpose": lbl.get("slide_purpose", "unknown"),
            "quality": lbl.get("estimated_quality_score", 0),
        })

    # Sort sources by priority order
    order = list(SOURCE_META.keys())
    sorted_groups = sorted(groups.items(), key=lambda x: order.index(x[0]) if x[0] in order else 99)

    total = len(html_files)
    source_list = [{"src": src, "count": len(slides), **SOURCE_META.get(src, {"color": "#546e7a", "short": src[:3].upper()})}
                   for src, slides in sorted_groups]

    # Build filter buttons JS
    filter_btns = "\n".join(
        f'<button class="filter-btn" data-src="{src}" style="--c:{SOURCE_META.get(src,{}).get("color","#555")}" onclick="filterSrc(this)">'
        f'{src} <span class="cnt">{len(slides)}</span></button>'
        for src, slides in sorted_groups
    )

    # Build slide cards per group
    sections_html = ""
    for src, slides in sorted_groups:
        color = SOURCE_META.get(src, {}).get("color", "#555")
        short = SOURCE_META.get(src, {}).get("short", src[:3])
        cards = ""
        for s in slides:
            label_txt = f"{s['layout']} · {s['purpose']}"
            cards += f"""
        <div class="card" data-src="{src}" onclick="openModal('{s['path']}','{s['sid']}')">
          <div class="thumb-wrap">
            <iframe src="{s['path']}" scrolling="no" loading="lazy"
                    style="width:1280px;height:720px;transform:scale({SCALE});transform-origin:top left;border:none;pointer-events:none;"></iframe>
          </div>
          <div class="card-foot">
            <span class="badge" style="background:{color}">{short}</span>
            <span class="label-txt">{label_txt}</span>
            <span class="q-score">★{s['quality']}</span>
          </div>
        </div>"""

        sections_html += f"""
      <section class="src-group" data-src="{src}" id="src-{src.replace(' ','_').replace('&','and')}">
        <h2 class="src-heading" style="border-left:4px solid {color}">
          {src} <span class="src-count">{len(slides)} slides</span>
        </h2>
        <div class="card-grid">{cards}
        </div>
      </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Slide Gallery — {total} slides</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: Arial, Helvetica, sans-serif;
  background: #1a1a1a;
  color: #eee;
  min-height: 100vh;
}}

/* ── Header ─────────────────────────── */
.header {{
  position: sticky; top: 0; z-index: 200;
  background: #111;
  padding: 14px 28px;
  border-bottom: 1px solid #333;
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
}}
.header h1 {{ font-size: 20px; font-weight: 600; color: #fff; white-space: nowrap; }}
.header .total {{ font-size: 13px; color: #888; }}
.filters {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.filter-btn {{
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.15);
  color: #ccc;
  padding: 5px 12px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: background 0.15s;
}}
.filter-btn:hover, .filter-btn.active {{
  background: var(--c);
  border-color: var(--c);
  color: #fff;
}}
.filter-btn .cnt {{ opacity: 0.75; font-size: 11px; }}
.filter-all {{
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.25);
  color: #fff;
  padding: 5px 14px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
}}
.filter-all.active {{ background: #fff; color: #111; }}

/* ── Main ───────────────────────────── */
.main {{ padding: 28px; }}
.src-group {{ margin-bottom: 40px; }}
.src-group.hidden {{ display: none; }}
.src-heading {{
  font-size: 18px; font-weight: 600; color: #fff;
  padding-left: 12px; margin-bottom: 16px;
}}
.src-count {{ font-size: 14px; color: #888; font-weight: 400; margin-left: 8px; }}

/* ── Card grid ──────────────────────── */
.card-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax({THUMB_W}px, 1fr));
  gap: 16px;
}}
.card {{
  background: #252525;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s, transform 0.15s;
}}
.card:hover {{ border-color: #555; transform: translateY(-2px); }}
.thumb-wrap {{
  width: {THUMB_W}px;
  height: {THUMB_H}px;
  overflow: hidden;
  position: relative;
  background: #f0f0f0;
}}
.card-foot {{
  padding: 8px 10px;
  display: flex; align-items: center; gap: 8px;
  background: #1e1e1e;
}}
.badge {{
  font-size: 10px; font-weight: 700; color: #fff;
  padding: 2px 7px; border-radius: 10px; white-space: nowrap;
}}
.label-txt {{ font-size: 12px; color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.q-score {{ font-size: 11px; color: #f0c040; white-space: nowrap; }}

/* ── Modal ──────────────────────────── */
.modal-bg {{
  display: none;
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.88);
  align-items: center; justify-content: center;
}}
.modal-bg.open {{ display: flex; }}
.modal-box {{
  position: relative;
  width: 1280px; height: 720px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.6);
}}
.modal-box iframe {{
  width: 1280px; height: 720px; border: none;
}}
.modal-close {{
  position: absolute;
  top: -36px; right: 0;
  background: none; border: none;
  color: #fff; font-size: 28px; cursor: pointer; line-height: 1;
}}
.modal-id {{
  position: absolute;
  bottom: -28px; left: 0;
  font-size: 12px; color: #888;
}}
</style>
</head>
<body>

<div class="header">
  <h1>Slide Gallery</h1>
  <span class="total">{total} slides converted</span>
  <div class="filters">
    <button class="filter-all active" onclick="filterAll(this)">All</button>
    {filter_btns}
  </div>
</div>

<div class="main">
  {sections_html}
</div>

<!-- Modal -->
<div class="modal-bg" id="modal" onclick="closeModal(event)">
  <div class="modal-box" id="modal-box">
    <button class="modal-close" onclick="closeModal()">&#x2715;</button>
    <iframe id="modal-frame" src="" loading="lazy"></iframe>
    <div class="modal-id" id="modal-id"></div>
  </div>
</div>

<script>
function filterSrc(btn) {{
  const src = btn.dataset.src;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.filter-all').classList.remove('active');
  btn.classList.add('active');
  document.querySelectorAll('.src-group').forEach(g => {{
    g.classList.toggle('hidden', g.dataset.src !== src);
  }});
}}
function filterAll(btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.src-group').forEach(g => g.classList.remove('hidden'));
}}
function openModal(path, sid) {{
  document.getElementById('modal-frame').src = path;
  document.getElementById('modal-id').textContent = sid;
  document.getElementById('modal').classList.add('open');
}}
function closeModal(e) {{
  if (e && e.target !== document.getElementById('modal')) return;
  document.getElementById('modal').classList.remove('open');
  document.getElementById('modal-frame').src = '';
}}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});
</script>
</body>
</html>"""

    OUT_FILE.write_text(html, encoding="utf-8")
    print(f"Gallery written: {OUT_FILE}")
    print(f"Total slides   : {total}")
    for src, slides in sorted_groups:
        print(f"  {src:<20} {len(slides)}")

if __name__ == "__main__":
    main()
