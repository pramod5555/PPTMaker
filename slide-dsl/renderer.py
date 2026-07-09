"""
slide-dsl/renderer.py
Converts a slide DSL spec (dict or JSON string) into a complete 1280x720 HTML slide.

Usage:
    from renderer import render_slide
    html = render_slide(spec_dict)
    html = render_slide(json_string)

Slide types:   cover | chapter | content | cta
Layouts:       full | two-column | three-column | sidebar-right | sidebar-left
Block types:   bar-chart | line-chart | scatter-chart | donut-chart |
               kpi-grid | bullet-list | table | text-block |
               gantt-chart | waterfall-chart | process-flow
"""

import json
import math
import html as _html
import re

# ── Palette — Daimler Truck CI/CD brand colors ────────────────────────────────
# Source: daimler-truck-brand skill (internal CI doc)
PETROL      = "#00677F"   # DT primary accent
PETROL_DARK = "#004355"   # DT Petrol +40K — headers / dark surfaces
PETROL_MED  = "#007A93"   # DT Petrol 80%  — interactive accent
PETROL_LT   = "#5097AB"   # DT Petrol 60%  — tinted borders
PETROL_LTR  = "#79AEBF"   # DT Petrol 40%  — light tint
PETROL_LTST = "#A6CAD8"   # DT Petrol 20%  — very light tint / bg
GREY_BG     = "#EFF7FA"   # slide card background (petrol-tinted)
GREY_RULE   = "#DCE9ED"   # grid lines / dividers
GREY_TEXT   = "#1A1A1A"   # body text (near-black on white)
GREY_SUB    = "#707070"   # DT Light Grey +60K — secondary / axis text

# DT semantic / functional colours
YELLOW      = "#FFFF40"   # DT max-accent — ONE element per view, never series/bg/text
GREEN_PASS  = "#6EA046"   # DT green  — positive delta, success
ORANGE_WARN = "#E69123"   # DT orange — warning / caution
RED_FAIL    = "#C62828"   # DT-aligned dark red — negative delta, error (FF0000 too harsh at small sizes)

SERIES_COLORS = [PETROL, PETROL_LT, PETROL_LTR, PETROL_DARK, PETROL_MED, PETROL_LTST]

# ── DT brand SVG assets (fetched from daimlertruck.com, embedded inline) ──────
_SVG_DT_WORDMARK = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 318 24" width="318" height="24">'
    '<polygon points="198.48,0.43 198.48,3.53 204.53,3.53 204.53,23.56 208.1,23.56 208.1,3.53 214.21,3.53 214.21,0.43"/>'
    '<path d="M248.76,0.42v13.51c0,3.44,.14,4.41,.73,5.76c1.25,2.71,4.2,4.31,7.99,4.31c3.78,0,6.73-1.6,7.99-4.31'
    'c.59-1.32,.73-2.33,.73-5.76V0.42h-3.58v13.43c0,2.47-.07,3.26-.38,4.13c-.62,1.8-2.36,2.88-4.76,2.88'
    'c-2.18,0-3.89-.9-4.58-2.46c-.46-.97-.55-1.78-.55-4.55V0.42H248.76z"/>'
    '<path d="M292.3,7.22C291.82,2.59,288.95,0,284.4,0c-2.4,0-4.66,.86-6.36,2.4c-2.33,2.15-3.54,5.48-3.54,9.66'
    'c0,7.26,3.92,11.95,10.03,11.95c4.86,0,7.7-2.97,8.11-8.44l-3.25-.23c-.35,3.68-2.05,5.55-4.97,5.55'
    'c-3.82,0-6.18-3.41-6.18-8.85s2.36-8.89,6.11-8.89c2.6,0,4.24,1.46,4.79,4.31h.24L292.3,7.22z"/>'
    '<polygon points="313.08,0.43 305.53,9.7 304.13,9.7 304.13,0.43 300.55,0.43 300.55,23.56 304.13,23.56 304.13,12.8 305.27,12.8 313.32,23.56 318,23.56 308.26,11.25 317.27,0.43"/>'
    '<path d="M228.71,3.51c3.08,0,3.85,.11,4.82,.59c1.14,.55,1.8,1.7,1.8,3.15c0,1.7-.83,2.99-2.26,3.5'
    'c-.94,.35-1.7,.42-4.2,.42h-1.6V3.51H228.71z M223.72,23.56h3.58v-9.3h3.58l5.23,9.3h4.24l-5.69-9.88'
    'c2.92-1.18,4.4-3.36,4.4-6.38c0-2.67-1.32-4.88-3.5-5.93c-1.56-.73-3.01-.94-6.86-.94'
    'c-1.63,0-3.46-.04-4.96,.35v22.78H223.72z"/>'
    '<rect x="55.21" y="0.43" width="3.61" height="23.12"/>'
    '<polygon points="107.65,0.43 107.65,23.56 121.06,23.56 121.27,20.47 111.32,20.47 111.32,0.43"/>'
    '<polygon points="134.7,10.04 134.7,3.51 144.83,3.51 144.61,0.43 131.12,0.43 131.12,23.56 144.89,23.56 145.1,20.47 134.7,20.47 134.7,13.12 141.01,13.12 141.01,10.04"/>'
    '<path d="M38.46,15.05H31.9l3.26-10.4L38.46,15.05z M33.46,0.43l-7.91,23.12h3.68l1.74-5.41h8.44l1.7,5.41h3.71l-7.9-23.12H33.46z"/>'
    '<polygon points="72.54,0.44 71.17,23.54 74.47,23.54 75.61,5.31 82.44,23.54 84.28,23.54 91.14,5.31 92.28,23.54 95.58,23.54 94.21,0.44 89.57,0.44 83.36,16.79 77.21,0.44"/>'
    '<path d="M160.28,3.51c3.08,0,3.85,.11,4.82,.59c1.14,.55,1.8,1.7,1.8,3.15c0,1.7-.83,2.99-2.26,3.5'
    'c-.94,.35-1.7,.42-4.2,.42h-1.6V3.51H160.28z M155.29,23.56h3.58v-9.3h3.58l5.23,9.3h4.24l-5.69-9.88'
    'c2.92-1.18,4.4-3.36,4.4-6.38c0-2.67-1.32-4.88-3.5-5.93c-1.56-.73-3.01-.94-6.86-.94'
    'c-1.63,0-3.46-.04-4.96,.35v22.78H155.29z"/>'
    '<path d="M3.58,20.47V3.44h1.01c3.78,0,4.75,.14,6.14,1.01c2.11,1.32,3.22,4.08,3.22,7.51'
    's-1.03,6.13-2.98,7.41c-1.32,.86-2.5,1.12-5.52,1.12H3.58V20.47z M0,.78v22.78h4.2'
    'c4.82,0,6.41-.26,8.36-1.36c3.22-1.79,5.09-5.65,5.09-10.22c0-4.61-2-8.62-5.29-10.37'
    'C10.58,.66,8.6,.43,4.68,.43C3.35,.43,1.24,.44,0,.78z"/>'
    '</svg>'
)

_SVG_FL = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 110.6 54" width="110.6" height="54">'
    '<defs><clipPath id="clippath"><rect x="1.9" y="16" width="106.8" height="22" fill="none"/></clipPath></defs>'
    '<g clip-path="url(#clippath)">'
    '<path d="M54.1,37c41.1,0,42.8,0,46.8-1.8,2.6-1.2,4.3-3.8,4.3-6.9s-1-4.8-2.8-6.2c-2.8-2.1-6.7-3-25.2-4.2'
    '-3.8-.2-9.6-.6-16.7-.9-1.6,0-5.5-.2-6.4-.2s-4.8.1-6.4.2c-7.1.2-12.9.6-16.7.9-18.5,1.2-22.4,2.1-25.2,4.2'
    'c-1.8,1.4-2.8,3.9-2.8,6.2s1.7,5.7,4.3,6.9c4.1,1.8,5.7,1.8,46.8,1.8M54.1,18.6c11.7,0,34.8,1.6,40,2.9'
    ',3.2.8,5.4,3.4,5.4,6.6s-2.1,5.7-4.9,6.4c-3.7,1-24.7,1.1-40.4,1.1s-36.7,0-40.4-1.1c-2.8-.8-4.9-3.3-4.9-6.4'
    's2.1-5.8,5.4-6.6c5.2-1.3,28.3-2.9,40-2.9ZM56,22.8c0-.2,0-.4-.3-.4h-1c-.2,0-.5.2-.6.4l-1.2,3.3c0,.2-.3.4-.6.4'
    'h-2.3c-.2,0-.4-.2-.3-.4l1.2-3.3c0-.2,0-.4-.3-.4h-1c-.2,0-.5.2-.6.4l-3.1,8.8c0,.2,0,.4.3.4h1'
    'c.2,0,.5-.2.6-.4l1.1-3.2c0-.2.3-.4.6-.4h2.3c.2,0,.4.2.3.4l-1.1,3.2c0,.2,0,.4.3.4h1c.2,0,.5-.2.6-.4l3.1-8.8Z'
    'M67.3,31.6l.2-.6c0-.2,0-.4-.3-.4h-2.5c-.2,0-.4-.2-.3-.4l2.5-7.2c0-.2,0-.4-.3-.4h-1c-.2,0-.5.2-.6.4l-3,8.6'
    'c0,.2,0,.4.3.4h4.3c.2,0,.5-.2.6-.4h0ZM85.9,30.6h-2.6c-.2,0-.4-.2-.3-.4l.6-1.5c0-.2.3-.4.6-.4h1.9'
    'c.2,0,.5-.1.6-.4l.2-.5c0-.2,0-.4-.3-.4h-1.9c-.2,0-.4-.3-.3-.5l.4-1.2c0-.2.3-.4.6-.4l2.6.2c.2,0,.5-.2.6-.4'
    'l.2-.5c0-.2,0-.4-.3-.4l-4.4-.3c-.2,0-.5.2-.6.4l-2.7,7.9c0,.2,0,.4.3.4h4.5c.2,0,.5-.2.6-.4l.2-.6'
    'c0-.2,0-.4-.3-.4h0ZM32.3,30.6h-2.6c-.2,0-.4-.2-.3-.4l.6-1.7c0-.2.3-.4.6-.4h2c.2,0,.5-.2.6-.5l.2-.5'
    'c0-.2,0-.4-.3-.4h-2c-.2,0-.4-.2-.3-.4l.5-1.4c0-.2.3-.4.6-.4h2.6c.2,0,.5-.3.6-.5l.2-.6c0-.2,0-.4-.3-.4'
    'l-4.6.2c-.2,0-.5.2-.6.4l-2.9,8.2c0,.2,0,.4.3.4h4.6c.2,0,.5-.2.6-.4l.2-.6c0-.2,0-.4-.3-.4h0Z'
    'M15.1,31.6l.9-2.7c0-.2.3-.4.6-.4h1.8c.2,0,.5-.2.6-.4l.2-.6c0-.2,0-.4-.3-.4h-1.8c-.2,0-.4-.2-.3-.4l.3-.9'
    'c0-.2.3-.4.6-.4h2.3c.3-.2.5-.3.6-.6l.2-.7c0-.2,0-.4-.3-.4l-4.1.2c-.2,0-.5.2-.6.4l-2.5,7.4c0,.2,0,.4.3.4h1'
    'c.2,0,.5-.2.6-.4h0ZM59.4,24.3l-2.5,7.3c0,.2,0,.4.3.4h1c.2,0,.5-.2.6-.4l2.5-7.2c0-.2.3-.4.6-.4h1.4'
    'c.2,0,.5-.2.6-.4l.2-.6c0-.2,0-.4-.3-.4h-5.8c-.2,0-.5,0-.6.3l-.2.6c0,.2,0,.4.3.4h1.8c.2,0,.4.2.3.4Z'
    'M70.2,31.6l2.9-8.4c0-.2,0-.4-.3-.4h-.9c-.2,0-.5.1-.6.4l-2.9,8.4c0,.2,0,.4.3.4h1c.2,0,.5-.2.6-.4Z'
    'M35.8,31.6l3-8.5c0-.2,0-.4-.3-.4h-1c-.3,0-.5.2-.6.4l-2.9,8.5c0,.2,0,.4.3.4h1c.2,0,.5-.2.6-.4Z'
    'M25.5,28.3c1,0,1.5-.8,2-2.5.6-2.1-.1-2.7-1.4-2.6l-3.5.2c-.3,0-.5.2-.6.4l-2.7,7.8c0,.2,0,.4.3.4h1'
    'c.2,0,.5-.2.6-.4l1.1-3c.1-.3.2-.3.5-.3h.4c.3,0,.4,0,.4.3l.5,3c0,.2.3.4.5.4h.9c.2,0,.4-.2.3-.4l-.5-2.8'
    'c-.1-.4,0-.5.1-.5h0ZM24.6,26.8c.8,0,.9-.1,1.3-1,.4-.8.1-1-.6-1h-1.3c-.2,0-.5.3-.6.5l-.4,1.1c0,.2,0,.4.3.4h1.2,0Z'
    'M93.4,28.4c.8-.1,1.2-1.4,1.4-2.4.4-1.4-.3-2-1.5-2.1l-3-.2c-.3,0-.5.3-.6.5l-2.6,7.4c0,.2,0,.4.3.4h1'
    'c.2,0,.5-.2.6-.4l1.1-2.9c.1-.3.2-.3.5-.3h.4c.3,0,.4,0,.4.3l.9,2.9c0,.2.3.4.6.4h1c.2,0,.4-.2.3-.4l-.9-2.7'
    'c-.1-.4-.1-.4.2-.5h0ZM91.6,27.1c.8,0,.9,0,1.3-.9.3-.8.1-.9-.5-.9h-.9c-.2,0-.5.1-.6.4l-.4,1c0,.2,0,.4.3.4h.8Z'
    'M76.1,26.7l1,4.8c0,.2.2.4.4.4h1c.2,0,.5-.2.6-.4l2.8-8c0-.2,0-.4-.3-.4h-.9c-.2,0-.5.1-.6.4l-1.5,4.2'
    'c-.2.5-.4.5-.5,0l-.9-4.3c0-.3-.2-.4-.5-.4h-1.1c-.2,0-.5.1-.6.4l-2.9,8.3c0,.2,0,.4.3.4h1c.2,0,.5-.2.6-.4'
    'l1.7-4.9c.2-.5.4-.4.5,0h0ZM46.2,26.9c0-.2,0-.4-.3-.4h-2.7c-.2,0-.5.2-.6.4v.5c-.2.2,0,.4.2.4h.8'
    'c.2,0,.4.2.3.4l-.6,1.5c-.1.4-.6.7-1,.7h-2.1c-.4,0-.6-.3-.5-.7l1.9-5.6c0-.2.3-.4.6-.4h2.7c.2,0,.4.2.3.4'
    's0,.4.3.4h1c.2,0,.4-.3.5-.5.3-1-.2-1.6-1.1-1.7-.5,0-.6,0-2.1,0s-1.8,0-2.3.2c-.8.2-1.2.6-1.5,1.3'
    'l-2.1,6c-.4,1.2.3,2.1,1.4,2.1h3.5c.8,0,1.6-.6,1.9-1.4l1.4-3.7h0ZM106.2,20h.4c.3,0,.6,0,.6-.4s-.3-.4-.5-.4'
    'h-.5v.8h0ZM105.8,18.9h.9c.6,0,.8.2.8.7s-.3.6-.6.7l.7,1.1h-.4l-.7-1h-.4v1h-.4v-2.4Z'
    'M106.6,21.9c1,0,1.7-.8,1.7-1.8s-.7-1.7-1.7-1.7-1.7.8-1.7,1.7.7,1.8,1.7,1.8ZM106.6,18.1c1.1,0,2.1.9,2.1,2'
    's-.9,2.1-2.1,2.1-2.1-.9-2.1-2.1,1-2,2.1-2ZM54.1,38c-41.3,0-43.6-.2-47.5-2c-2.8-1.3-4.7-4.3-4.7-7.6'
    's1.4-5.6,3.3-7c2.8-2.1,6.3-3,26-4.4c3.3-.2,9-.6,16.7-.8c2.3,0,5.2-.2,6.3-.2s3.9,0,6.3.2'
    'c7.7.3,13.4.6,16.7.8c19.7,1.4,23.1,2.3,26,4.4c1.8,1.3,3.3,4,3.3,7s-1.8,6.3-4.7,7.6c-3.9,1.8-6.2,2.1-47.5,2h0Z"'
    ' fill-rule="evenodd"/>'
    '</g>'
    '<rect width="110.6" height="54" fill="none"/>'
    '</svg>'
)

_SVG_TBB = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 107.8 54" width="107.8" height="54">'
    '<defs><clipPath id="clippath"><rect x="2.3" y="11.1" width="103.2" height="31.8" fill="none"/></clipPath></defs>'
    '<g clip-path="url(#clippath)">'
    '<path d="M3,42.9h97.2c.2-.2.4-.2.4-.5v-2.7c0-5.7.5-5.2-2-5.2H4.3c-1.9,0-1.9-.1-1.9,1.7v5.4c0,1,0,.9.5,1.2'
    'M73.1,24.9c-.8.2-2-1.6-4.9.4-2.9,2.1-2.7,6.2.9,7.8.8.4,1.8.5,2.7.2.7-.2,1.4-1.1,1.9.2h4.7v-.7'
    'c-1.7,0-1.3-1.8-1.3-3.3v-4.7c0-1.7,0-2.6-.9-3.8-.6-.8-1.9-1.3-3.3-1.4-1.6,0-5.1.7-5.4,1.5-.3.6.3,1.3.8,1.3'
    'c.4,0,4.8-2.3,4.9,0,0,.5.1,1.9,0,2.3h0ZM40.9,20.2c-1.7.3-3,1.3-3.7,2.3-1,1.4-.8,3.3-.7,5.2,0,.9-.1,1.9.2,2.7'
    'c.3.7.8,1.4,1.2,1.7c1,.9,2.5,1.8,4.5,1.5c1.7-.2,3-1.2,3.7-2.2c1-1.5.7-3.3.7-5.3s-.2-3.5-1.4-4.6'
    'c-.9-.9-2.7-1.7-4.5-1.4h0ZM88.1,39.4c0,.8.8,1,1.4,1s1.2-.3,1.2-.8-.3-.5-.8-.6l-1-.2c-.5,0-1.3-.3-1.3-1.1'
    's.6-1.3,1.8-1.3,1.8.3,1.8,1.3h-.6c-.1-.3-.3-.8-1.3-.8s-1,.2-1,.7,0,.5.7.6l1,.2c.4,0,1.4.2,1.4,1.1'
    's-1,1.4-1.9,1.4-2-.3-2-1.5h.6ZM79.1,36.5h3.6v.5h-2.9v1.3h2.8v.5h-2.8v1.5h2.9v.5h-3.6v-4.4Z'
    'M70.9,39.4c0,.8.7,1,1.4,1s1.2-.3,1.2-.8-.4-.5-.9-.6l-.9-.2c-.6,0-1.3-.3-1.3-1.1s.6-1.3,1.7-1.3'
    ',1.8.3,1.9,1.3h-.7c0-.3-.2-.8-1.3-.8s-1,.2-1,.7.2.5.7.6l1.1.2c.3,0,1.3.2,1.3,1.1s-1,1.4-1.9,1.4'
    's-2-.3-2-1.5h.7,0ZM61.3,36.5h.6v2.8c0,.7.6,1.1,1.4,1.1s1.3-.4,1.3-1.1v-2.8h.6v2.7c0,1.1-.6,1.7-1.9,1.7'
    's-2-.6-2-1.7v-2.7h0ZM53.3,40.3v-1.5h1.8c.6,0,.8.4.8.7s-.2.8-.9.8h-1.7ZM52.6,40.8h2.6c.9,0,1.4-.6,1.4-1.2'
    's-.3-1-.8-1.1c.3-.2.6-.4.6-.9c0-.7-.4-1.1-1.4-1.1h-2.4v4.4h0ZM53.3,38.3v-1.3h1.7c.5,0,.7.3.7.7s-.2.6-.7.6h-1.7Z'
    'M41.8,37h-1.6v-.5h4v.5h-1.6v3.8h-.7v-3.8h0ZM33.8,36.5h.6v3.8h2.6v.5h-3.2v-4.4ZM28.6,36.5h.6v4.4h-.6v-4.4Z'
    'M20,36.5h.7v2.8c0,.7.5,1.1,1.3,1.1s1.3-.4,1.3-1.1v-2.8h.7v2.7c0,1.1-.7,1.7-2,1.7s-2-.6-2-1.7v-2.7h0Z'
    'M12.5,40.3v-1.5h1.8c.6,0,.8.4.8.7s-.2.8-.9.8h-1.7ZM11.8,40.8h2.6c.9,0,1.3-.6,1.3-1.2s-.3-1-.8-1.1'
    'c.4-.2.7-.4.7-.9c0-.7-.5-1.1-1.4-1.1h-2.4v4.4h0ZM12.5,38.3v-1.3h1.7c.5,0,.7.3.7.7s-.2.6-.7.6h-1.7Z'
    'M79.9,28.6l-1.4.6,1.5,4.3h1.3c0-.3,0-.6.1-.8c.5,0,2.3.9,3.6.9c5,0,6.2-5.2,2.8-7.3c-.9-.6-2.1-1-3.1-1.5'
    'c-.9-.5-2.2-1.3-1.5-2.7c.8-1.6,2.9-1,4,1c.3.5.5,1.1.7,1.6c.4,0,1.3-.3,1.6-.5l-1.4-4.4h-1.4c0,.4,0,.6-.2.8'
    'c-.5,0-.8-1.1-3.2-1c-1.4,0-2.3.8-2.8,1.5c-1.5,1.8-1,4.5,1.1,6c1.1.8,5.3,2.1,3.4,4.3c-1.2,1.5-3.6-.2-4.6-1.9'
    'c-.1-.2-.2-.5-.4-.7h0ZM41.4,21.7c.4-.1.9.1,1.1.4c.3.3.2.8.2,1.3v6.2c0,1,.2,2.1-.7,2.3c-.5.1-.9-.1-1.1-.4'
    'c-.2-.3-.2-.9-.2-1.4v-6.2c0-1-.2-2,.8-2.3h0ZM71.2,27.2c1.2-.3,1.9.4,2,1.5c0,1.3.1,2.2-1,2.5c-.5.1-1,0-1.5-.2'
    'c-.4-.3-.5-.6-.5-1.3c0-1.3-.2-2.2,1-2.6ZM52.6,20.9c-.2-.2-.3-.3-.3-.7h-4.5c-.4,0-.4,0-.7.3c-.2.2,0,0-.2.2'
    'c.7.5,1.4.9,1.5,2.1c.1,1,0,2.5,0,3.5v5.4c0,1-.1.9-.6,1.2v.6h5.3v-.7c-1-.5-.8-.5-.8-2.4v-6.4'
    'c0-.7-.2-2,1.1-2.3c1.1-.2,1.4,1,1.4,1.8c0,2.6,0,5.6,0,8.2c0,.7-.2.7-.6,1v.6h5.1v-.7c-.8-.7-.7,0-.7-2.5v-6.5'
    'c0-.5,0-1.1.2-1.5c.5-.7,1.5-1,2-.1c.4.7.2,3.7.2,4.7v4.9c0,.8-.4.6-.6,1v.5h5.2s0-.5,0-.5'
    'c-.3-.4-.8,0-.8-1c0-.6,0-1.3,0-1.9v-7.6c-.1-1.8-3-4.1-5.7-1.6c-.4.3-.6.8-1.1.2c-.6-.7-1.3-1.2-2.6-1.2'
    'c-2.4,0-1.8,1-2.9,1h0ZM7,35.4c.6,0,80.6,0,88.1,0s1.8-.2,1.8,1.2v3c0,2.8.3,2.3-3.7,2.3H8.1'
    'c-2.1,0-1.8.4-1.8-4.3s-.3-2.2.7-2.3h0ZM103.9,42.9c-.9,0-1.6-.7-1.6-1.6s.7-1.6,1.6-1.6,1.6.7,1.6,1.6'
    '-.7,1.6-1.6,1.6ZM103.9,40c-.7,0-1.3.6-1.3,1.3s.6,1.3,1.3,1.3,1.3-.6,1.3-1.3-.6-1.3-1.3-1.3Z'
    'M104.3,42.2l-.3-.6c0,0,0-.2-.2-.2h-.2v.7h-.3v-1.7h.6c.1,0,.3,0,.4,0c.1,0,.2.2.2.4s-.1.4-.3.5h0s.4.7.4.7h-.4Z'
    'M104.2,40.8s-.1,0-.2,0h-.3v.4h.3c.2,0,.3,0,.3-.2s0-.1,0-.2Z'
    'M2.3,13.6v5.9s0,0,0,0h0c.3.5.7.4,1.5.4s1.5.2,1.7-.3c.2-.5-.1-1.2.2-1.8c.3-.5.7-.7,1.4-.7h6.1'
    'c.7,0,1.4,0,1.5.6c0,.6,0,12.2,0,14.1s-.3.9-.7,1.2v.5c0,0,5.6,0,5.6,0v-.5c-.9-.4-.8-.9-.8-1.9v-11.2'
    'c0-.7-.2-2.3.3-2.6c.4-.2,4.7-.1,5.5-.1v14.9c0,.8-.4.8-.7.9c-.3.1-.2,0-.2.3c0,.2,0,.2.5.2h5'
    'c0-.6,0-.3-.3-.5c-.2-.1-.3-.2-.4-.4c-.3-.5-.2-.9-.2-1.5v-6.7c0-.6,0-1,.3-1.4c.5-.8,1.6-.8,2.2-.2'
    'c.4.4.4.7.4,1.3c0,1,.2,7.9,0,8.4c-.3.9-.9.4-.7,1.1h5.3v-.5c-.9-.2-.9-.8-.9-1.8v-8.5'
    'c0-1.6-1.2-2.8-2.4-3.2c-1.1-.4-2.3.1-3.1.8c-.3.2-.4.6-.9.5c-.4-.2-.2-3.1-.2-3.6c.5,0,62.9,0,67.6,0'
    'c2.4,0,.6,2.6,2.1,2.8c.3,0,2.2,0,2.4,0c.6-.2.4-1.4.4-2.1c0-5.2.4-5-2.2-5H28.3c0-1.2,1.1-1.1,2.2-1'
    'l-.4-.8h-7.2l-.5.9c1.1,0,2.3-.2,2.3.9H4.5c-1.7,0-1.6-.2-2.2.6h0Z" fill-rule="evenodd"/>'
    '</g>'
    '<rect width="107.8" height="54" fill="none"/>'
    '</svg>'
)

_SVG_WS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 91.8 54" width="91.8" height="54">'
    '<defs><clipPath id="clippath"><rect x="2" y="8" width="87.8" height="38" fill="none"/></clipPath></defs>'
    '<g clip-path="url(#clippath)">'
    '<path d="M77.6,38.5l-3.2,7.5h1.9l.5-1.1h3.6l.5,1.1h1.9l-3.2-7.5h-2.1ZM77.5,43.4l1.1-2.5h.2l1.1,2.5h-2.3,0Z" fill-rule="evenodd"/>'
    '<path d="M75.6,38.5h-7.2v1.6h2.7v5.8h1.8v-5.8h2.7v-1.6Z" fill-rule="evenodd"/>'
    '<path d="M54.8,43.3l-2.8-4.8h-2.1v7.5h1.8v-4.6l2.7,4.6h2.2v-7.5h-1.8v4.8Z" fill-rule="evenodd"/>'
    '<path d="M27.3,40.2h2.7v5.8h1.8v-5.8h2.7v-1.6h-7.2v1.6Z" fill-rule="evenodd"/>'
    '<path d="M20.5,39.2v3.2l.7.6h3.4v1l-.3.3h-3.7v1.6h5.1l.7-.6v-3.2l-.7-.6h-3.4v-1l.3-.3h3.7v-1.6h-5.1l-.7.6Z" fill-rule="evenodd"/>'
    '<path d="M61.7,39.2v3.2l.7.6h3.3v1l-.3.3h-3.7v1.6h5.1l.7-.6v-3.2l-.7-.6h-3.4v-1l.3-.3h3.7v-1.6h-5.1l-.7.6Z" fill-rule="evenodd"/>'
    '<path d="M13.8,46h5.8v-1.6h-4v-1.3h2.9v-1.6h-2.9v-1.4h4v-1.6h-5.8v7.5Z" fill-rule="evenodd"/>'
    '<path d="M35.4,46h5.8v-1.6h-4v-1.3h2.9v-1.6h-2.9v-1.4h4v-1.6h-5.8v7.5Z" fill-rule="evenodd"/>'
    '<path d="M9.8,42.7h-.1l-1.2-3.9v-.3h-1.8v.3c-.1,0-1.3,3.9-1.3,3.9h-.1l-1.3-4.2h-1.9l2.3,7.5h2l1.2-3.8h.1l1.2,3.8h2l2.3-7.5h-1.9l-1.3,4.2Z" fill-rule="evenodd"/>'
    '<path d="M48,43.4h0l.7-.6v-3.5l-.7-.6h-5.5v7.5h1.8v-2.6h1.4l1.3,2.6h1.9l-1.3-2.6h.4Z'
    'M46.8,41.5l-.3.3h-2.3v-1.6h2.3l.3.3v1Z" fill-rule="evenodd"/>'
    '<path d="M88.5,43.4h.4l.6-.6v-3.5l-.6-.6h-5.3v7.5h1.7v-2.6h1.4l1.3,2.6h1.9l-1.3-2.6h0Z'
    'M87.8,41.5l-.3.3h-2.2v-1.6h2.2l.3.3v1Z" fill-rule="evenodd"/>'
    '<path d="M74.5,8.6l-10.8,24.6c0,0-.1.1-.2.1h-13.8c0,0-.2,0-.2-.1l-3.5-7.8-3.6,7.8c0,0-.1.1-.2.1h-13.8'
    'c0,0-.2,0-.2-.1l-10.8-24.6c0,0,0-.1,0-.2c0,0,0,0,.2,0h11.4c0,0,.2,0,.2.1l5.6,12.8,2.4-5.1,1.1.8-2.6,5.5'
    'c0,0-.1.2-.2.2h-1.4c0,0-.2,0-.2-.2l-5.5-12.6c0,0-.1-.2-.2-.2h-8.6c0,0-.1,0,0,.2l9.7,22c0,0,.1.2.2.2h12'
    'c0,0,.2,0,.2-.1l3.5-7.6c0,0,.1-.2.2-.2h1.4c0,0,.2,0,.2.2l3.4,7.6c0,0,.1.2.2.2h12c0,0,.2,0,.2-.1l9.7-22'
    'c0,0,0-.2,0-.2h-8.6c0,0-.2,0-.2.2l-5.5,12.6c0,0-.1.2-.2.2h-1.4c0,0-.2,0-.2-.2l-2.6-5.5,1.1-.8,2.4,5.1'
    ',5.6-12.8c0,0,.1-.1.2-.1h11.4c0,0,.1,0,.2,0c0,0,0,.1,0,.2M40.9,8.5c0,0,.1-.1.2-.1h4.8l-.4,1.3h-3.5'
    'c0,0-.2,0-.2.1l-2.6,5.5h-1.5l3.3-6.9h0ZM50.8,8.4c0,0,.2,0,.2.1l3.3,6.9h-1.5l-2.6-5.5c0,0-.1-.2-.2-.2'
    'h-3.5l-.4-1.3h4.8ZM37.4,15.8h6.4l2-6v-.3c.1,0,.2.3.2.3l1.9,6h6.7l-5.4,3.9,2.1,6.3-5.4-3.9-5.4,3.9'
    ',2.1-6.3-4.1-3-1.1-.8h-.2c0-.1.2-.1.2-.1ZM43.5,19.4l-.2.5-1.3,4.1,3.5-2.5.5-.3.5.3,3.5,2.5-1.3-4.1'
    '-.2-.5.4-.3,3.5-2.6h-4.9l-.2-.5-1.3-4.1-1.3,4.1-.2.5h-4.9l3.5,2.6.4.3h0Z'
    'M74.8,8.2c0-.2-.3-.2-.5-.2h-11.4c-.2,0-.5.2-.6.4l-5.3,12-2.1-4.5.7-.5h-1l-3.4-7.1c0-.2-.3-.4-.6-.4h-9.7'
    'c-.2,0-.5.2-.6.4l-3.4,7.1h-1l.7.5-2.1,4.5-5.3-12c0-.2-.3-.4-.6-.4h-11.4c-.2,0-.4,0-.5.2'
    'c0,.2-.1.3,0,.5l10.8,24.6c0,.2.3.4.6.4h13.8c.2,0,.5-.2.6-.4l3.2-7,3.2,7c0,.2.3.4.6.4h13.8'
    'c.2,0,.5-.2.6-.4l10.8-24.6c0-.2,0-.4,0-.5h0Z" fill-rule="evenodd"/>'
    '</g>'
    '<rect width="91.8" height="54" fill="none"/>'
    '</svg>'
)

_SVG_MB = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 54 54" width="54" height="54">'
    '<defs><clipPath id="clippath"><rect x="2" y="2" width="50" height="50" fill="none"/></clipPath></defs>'
    '<g clip-path="url(#clippath)">'
    '<path d="M48.7,14.5c-2.2-3.8-5.3-7-9.2-9.2s-8.1-3.3-12.5-3.3-8.7,1.2-12.5,3.3c-3.8,2.2-7,5.4-9.2,9.2'
    'c-2.2,3.8-3.3,8.1-3.3,12.5s1.2,8.7,3.3,12.5c2.2,3.8,5.4,7,9.2,9.2c3.8,2.2,8.1,3.3,12.5,3.3'
    's8.7-1.2,12.5-3.3c3.8-2.2,7-5.4,9.2-9.2c2.2-3.8,3.3-8.1,3.3-12.5s-1.2-8.7-3.3-12.5'
    'M4.5,27c0-3.9,1-7.8,3-11.2c2-3.4,4.8-6.3,8.2-8.2c3.2-1.9,6.8-2.9,10.5-3l-2.9,20.4-16.3,12.7'
    'c-1.8-3.3-2.7-6.9-2.7-10.6h0ZM38.2,46.5c-3.4,2-7.3,3-11.2,3s-7.8-1-11.2-3c-3.2-1.9-5.9-4.5-7.9-7.6'
    'l19.1-7.7,19.1,7.7c-2,3.2-4.7,5.8-7.9,7.6h0ZM46.8,37.6l-16.3-12.7-2.9-20.4c3.7.1,7.3,1.1,10.6,3'
    'c3.4,2,6.3,4.8,8.2,8.2c2,3.4,3,7.3,3,11.2s-.9,7.4-2.7,10.6h0Z" fill-rule="evenodd"/>'
    '</g>'
    '<rect width="54" height="54" fill="none"/>'
    '</svg>'
)

_SVG_BB = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 91.5 54" width="91.5" height="54">'
    '<defs><clipPath id="clippath"><rect x="1.6" width="88.4" height="54" fill="none"/></clipPath></defs>'
    '<g clip-path="url(#clippath)">'
    '<path d="M45.8.6c11.9,0,21.6,8.5,21.6,19s-9.7,19-21.6,19-21.6-8.5-21.6-19S33.9.6,45.8.6'
    'M45.8,4.1c9.6,0,17.4,6.9,17.4,15.5s-7.8,15.5-17.4,15.5-17.4-6.9-17.4-15.5,7.8-15.5,17.4-15.5Z'
    'M45.8,3.5c10,0,18,7.2,18,16.1s-8.1,16.1-18,16.1-18-7.2-18-16.1S35.8,3.5,45.8,3.5Z'
    'M60.5,22.6h-4.5c-1.3,4.4-5.4,7.6-10.2,7.6s-8.9-3.2-10.2-7.6h-4.5c1.5,5.9,7.5,10.4,14.7,10.4s13.2-4.4,14.7-10.4Z'
    'M31.1,16.7h4.5c1.3-4.4,5.3-7.6,10.1-7.6s8.9,3.2,10.1,7.6h4.5c-1.5-5.9-7.5-10.4-14.7-10.4s-13.1,4.4-14.7,10.4Z'
    'M29.6,20.4v-.7c.3,0,1.1,0,1.4,0c.2,0,.4.1.4.3s-.3.3-.5.3c-.1,0-.3,0-.6,0h-.6Z'
    'M29.6,19.5v-.6c.3,0,1,0,1.3,0c.2,0,.3.1.3.3s-.2.2-.4.3c-.1,0-.5,0-.7,0h-.5Z'
    'M29.2,18.6v2h1.4c.3,0,.7,0,1-.1c.5-.2.6-.8-.3-.9c.2,0,.3-.1.4-.2c.2-.2.2-.3,0-.5c-.2-.2-.7-.2-1.1-.2h-1.4Z'
    'M34.9,18.6v.8h-1.9v-.8h-.5v2h.5v-.9h1.9v.9h.5v-2h-.5ZM37.2,19.2c0-.1.2-.3.2-.4c.1.3.4.7.6,1h-1.2l.4-.6Z'
    'M37.2,18.6l-1.4,2h.5l.4-.6h1.5l.4.6h.5l-1.5-2h-.5,0ZM40,18.8h1.2c.3,0,.5,0,.6,0c.2,0,.2.3,0,.4'
    'c-.2.1-.5.2-.8.2h-1v-.7h0ZM39.5,18.6v2h.5v-.9c.2,0,.7,0,.8,0c.3,0,.5.2.8.5l.5.4h.6l-.6-.5'
    'c-.2-.2-.4-.3-.7-.4c.3,0,.6,0,.8-.2c.3-.2.3-.4,0-.7c-.3-.2-.7-.2-1.1-.2h-1.6Z'
    'M44.2,19.2c0-.1.2-.3.2-.4c.1.3.4.7.6,1h-1.2l.4-.6ZM44.1,18.6l-1.4,2h.5l.4-.6h1.5l.4.6h.5l-1.5-2h-.5,0Z'
    'M45.8,18.6v.2h1.2v1.7h.5v-1.7h1.2v-.2h-2.9ZM52.8,18.6v2h2.8v-.3h-2v-.5h1.8v-.3h-1.8v-.4h2v-.3h-2.7Z'
    'M58.3,18.6v1.3l-1.5-1.3h-.7v2h.7v-1.3l1.5,1.3h.7v-2h-.7Z'
    'M59.7,18.6v.3h1.7l-1.9,1.3v.4h2.9v-.3h-2.1l2-1.3v-.3h-2.7Z'
    'M49.9,20.3v-.5h.6c.4,0,.7,0,.9.1c.2.1.1.4-.3.4c-.1,0-.4,0-.7,0h-.5,0ZM49.9,19h1c.1,0,.2,0,.3,0'
    'c.2,0,.2.3-.3.4h-1v-.4h0ZM50.6,18.6h-1.4v2c.5,0,1.7,0,2.1,0c.2,0,.4,0,.5,0c.6-.2.7-.8-.3-.9'
    'c.2,0,.3,0,.4-.2c.2-.1.2-.3,0-.5c-.3-.3-.7-.3-1.2-.3h-.2Z'
    'M64.4,54h0s0,0,0,0ZM2.9,53.4v-1.8c.8,0,3,0,3.7,0c.5,0,1,.3,1,.8s-.9.8-1.4.9c-.3,0-.9,0-1.6,0h-1.7,0Z'
    'M2.9,50.9v-1.6c.8,0,2.8,0,3.4,0c.4,0,.9.3.9.8s-.5.6-1,.7c-.4,0-1.2,0-2,0h-1.3Z'
    'M1.6,48.7v5.3h3.7c.9,0,1.9,0,2.6-.4c1.3-.5,1.6-2.1-.8-2.5c.5-.1.8-.3,1-.5c.5-.4.4-.9,0-1.3'
    'c-.7-.6-1.8-.7-2.8-.7H1.6h0ZM16.9,48.7v2.2h-5v-2.2h-1.3v5.3h1.3v-2.5h5v2.5h1.3v-5.3h-1.3Z'
    'M23,50.2c.2-.3.4-.7.5-1c.4.7,1.2,1.8,1.7,2.6h-3.3l1-1.6ZM22.8,48.7l-3.7,5.3h1.4l1.1-1.6h4l1.1,1.6h1.5'
    'l-3.9-5.3h-1.4ZM30.4,49.3h3.1c.7,0,1.2,0,1.6.3c.5.3.7.7.2,1.1c-.4.4-1.4.4-2.1.4h-2.7,0v-1.8h0Z'
    'M29.1,48.7v5.3h1.3v-2.4c.5,0,1.8,0,2.2,0c.8,0,1.4.6,2.1,1.2l1.3,1.1h1.6l-1.7-1.4c-.6-.5-1-.8-1.8-1'
    'c.9,0,1.6-.2,2.1-.5c.8-.5.9-1.2.3-1.8c-.7-.6-1.8-.7-3-.7h-4.3,0Z'
    'M41.5,50.2c.2-.3.4-.7.5-1c.4.7,1.2,1.8,1.7,2.6h-3.3l1.1-1.6ZM41.4,48.7l-3.7,5.3h1.3l1.1-1.6h4l1.1,1.6h1.5'
    'l-4-5.3h-1.4ZM46,48.7v.6h3.2v4.7h1.3v-4.7h3.2v-.6h-7.6Z'
    'M64.4,48.7v5.3h7.3v-.9h-5.4v-1.4h4.8v-.9h-4.8v-1.2h5.2v-.9h-7.2,0Z'
    'M79.2,48.7v3.6l-4-3.6h-1.9v5.3h1.8v-3.5l3.9,3.5h2v-5.3h-1.8Z'
    'M82.7,48.7v.9h4.5l-5.1,3.4v1h7.8v-.9h-5.5l5.3-3.6v-.8h-7.1Z'
    'M56.7,53.1v-1.4h1.6c1.1,0,1.9,0,2.3.3c.4.3.3,1-.8,1.1c-.3,0-1.1,0-1.8,0h-1.3Z'
    'M56.7,49.6h0s2.8,0,2.8,0c.3,0,.6,0,.7.2c.4.3.5.9-.8,1h-2.7s0-1.2,0-1.2Z'
    'M58.6,48.7h-3.9v5.3c1.4,0,4.5,0,5.6,0c.5,0,1-.1,1.3-.2c1.5-.6,1.8-2.2-.7-2.5c.4-.1.7-.3,1-.5'
    'c.5-.4.5-.9,0-1.3c-.7-.7-1.9-.7-3.1-.7h-.4,0Z" fill-rule="evenodd"/>'
    '</g>'
    '<rect width="91.5" height="54" fill="none"/>'
    '</svg>'
)

_SVG_SE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 109.5 54" width="109.5" height="54">'
    '<defs><clipPath id="clippath"><rect x="2.4" y="16" width="104.7" height="22" fill="none"/></clipPath></defs>'
    '<g clip-path="url(#clippath)">'
    '<path d="M28.4,29c2.4,0,2.5-1.2,2.6-1.6c0-.6-.3-1.6-2.5-1.6h-4.4v-1.1h6.6c0,0,.1,0,.1-.1v-1'
    'c0,0,0-.1-.1-.1h-8.4c-2.3,0-2.5,1.2-2.5,1.6c0,.6.3,1.6,2.5,1.6h4.4v1.1h-6.6c0,0-.1,0-.1.1v1'
    'c0,0,0,.1.1.1h8.4ZM106.4,18.5c0,.4-1.6,6.5-3.2,10.5c-.7,1.7-1.2,2.9-1.4,3.2c-.4.8-1.1,1.3-2,1.4'
    'c-11.8,1.9-63.5,3.7-88.5,3.8c-1,0-2.3,0-3.2-.5c-.8-.4-1.1-1.5-1.2-1.8l-3.8-13.9c-.4-1.5-.2-2.7.6-3.5'
    'c.9-1,1.9-1,5.4-1h95.6c.6,0,1.1.3,1.4.8c.2.3.3.7.2,1.1h0ZM104.8,17.3c.4,0,.7.2.8.4c.1.2.2.4.1.6'
    'c-.1.5-1.6,6.4-3.1,10.3c-.7,1.7-1.2,2.9-1.3,3.2c-.3.6-.8.9-1.5,1c-12.1,1.9-66,3.7-88.4,3.8'
    'c-.9,0-2.1,0-2.9-.4c-.4-.2-.7-.9-.8-1.4l-3.7-14c-.5-1.9.2-2.6.4-2.9c.7-.8,1.6-.8,5-.8h95.6,0Z'
    'M83.6,24.7c0,0,.2,0,.2.2v1.7h-2.6v-1.7c0,0,0-.2.2-.2h2.3Z'
    'M72.8,29c-.5-.5-1.3-1.2-1.6-1.5h-.1c0-.1.2-.2.2-.2c.7-.2,1.3-.9,1.3-1.8v-.3c0-1.2-1-1.9-1.9-1.9h-8.1'
    'c0,0-.1,0-.1.1v5.4c0,0,0,.1.1.1h3.6c0,0,.1,0,.1-.1v-1.4h.8l1.5,1.5h4.2,0ZM66.3,26.5h0v-1.8h2.1'
    'c.4,0,.8.3.8.8v.3c0,.5-.4.8-.8.8h-2Z'
    'M58.7,24.6v-1c0,0,0-.1-.1-.1h-10.8c0,0-.1,0-.1.1v1c0,0,0,.1.1.1h3.5v4.3c0,0,0,.1.1.1h3.6'
    'c0,0,.1,0,.1-.1v-4.2h3.5c0,0,.1,0,.1-.1h0Z'
    'M44.2,25.8h-5.3v-1.1h5.3c0,0,.1,0,.1-.1v-1c0,0,0-.1-.1-.1h-9c0,0-.1,0-.1.1v5.4c0,0,0,.1.1.1h9'
    'c0,0,.1,0,.1-.1v-1c0,0,0-.1-.1-.1h-5.3v-1.1h5.3c0,0,.1,0,.1-.1v-.8c0,0,0-.1-.1-.1h0Z'
    'M87.6,28.9v-3.6c0-1.1-.9-1.9-1.9-1.9h-6.4c-1.1,0-1.9.9-1.9,1.9v3.6c0,0,0,.1.1.1h3.6'
    'c0,0,.1,0,.1-.1v-1.4h2.6v1.4c0,0,0,.1.1.1h3.6c0,0,.1,0,.1-.1h0Z'
    'M106.8,17.1c-.4-.7-1.1-1.1-1.9-1.1H9.2c-3.5,0-4.7,0-5.9,1.2c-.6.7-1.3,1.9-.7,4.1l3.7,13.9'
    'c.1.5.5,1.7,1.5,2.2c.5.2,1.3.6,3.5.5c23.7-.1,76.6-1.9,88.6-3.8c1.1-.2,2-.8,2.5-1.7c.2-.4.7-1.6,1.4-3.3'
    'c1.6-4.1,3.1-10.2,3.2-10.6c0-.5,0-1-.3-1.5h0Z" fill-rule="evenodd"/>'
    '</g>'
    '<rect width="109.5" height="54" fill="none"/>'
    '</svg>'
)

# Ordered list matching the DT brand page strip
_BRAND_LOGO_SVGS = [_SVG_FL, _SVG_TBB, _SVG_WS, _SVG_MB, _SVG_BB, _SVG_SE]
# Scaled widths at target height 28px  (origW / 54 * 28, rounded)
_LOGO_H  = 28
_LOGO_WS = [57, 56, 48, 28, 47, 57]
_LOGO_XS = [374, 479, 583, 679, 755, 850]   # centered in 1280px strip


def _brand_logo(svg_str: str, uid: int, w: int, h: int) -> str:
    """Fix clipPath IDs and scale a brand logo SVG for inline embedding."""
    svg = svg_str.replace('id="clippath"', f'id="cp_{uid}"')
    svg = svg.replace('clip-path="url(#clippath)"', f'clip-path="url(#cp_{uid})"')
    svg = re.sub(r'\bwidth="\d+(?:\.\d+)?"', f'width="{w}"', svg, count=1)
    svg = re.sub(r'\bheight="\d+(?:\.\d+)?"', f'height="{h}"', svg, count=1)
    return svg


def _dt_footer(f: dict, dark: bool = False) -> list:
    """Standard DT footer: thin rule + 'DAIMLER TRUCK' label + source + page."""
    sep  = "rgba(255,255,255,.15)" if dark else GREY_RULE
    dt_c = "rgba(255,255,255,.40)" if dark else "#999"
    src_c= "rgba(255,255,255,.30)" if dark else "#aaa"
    pg_c = "rgba(255,255,255,.45)" if dark else "#888"
    out  = [_d(M_L, FOOTER_Y - 7, SLIDE_W - M_L - M_R, 1, f"background:{sep};")]
    out.append(_d(M_L, FOOTER_Y, 140, 16,
        f"font-size:9px;font-weight:600;letter-spacing:.7px;color:{dt_c};"
        "text-transform:uppercase;overflow:hidden;white-space:nowrap;", "Daimler Truck"))
    if f.get("source"):
        out.append(_d(M_L + 150, FOOTER_Y, SLIDE_W - M_L - M_R - 210, 16,
            f"font-size:9px;color:{src_c};overflow:hidden;white-space:nowrap;",
            _e(f["source"])))
    if f.get("page") is not None:
        out.append(_d(SLIDE_W - M_R - 50, FOOTER_Y, 50, 16,
            f"font-size:10px;color:{pg_c};text-align:right;", str(f["page"])))
    return out


# ── Fixed slide geometry (1280x720) ────────────────────────────────────────────
SLIDE_W  = 1280
SLIDE_H  = 720
M_L      = 64
M_R      = 64
CON_X    = M_L
CON_Y    = 110    # content top — below header zone
CON_W    = SLIDE_W - M_L - M_R   # 1152
CON_H    = SLIDE_H - CON_Y - 34  # 576
FOOTER_Y = 686

# Column definitions: (x-offset from CON_X, width)
_COLS = {
    "full":          [{"dx": 0,   "w": 1152}],
    "two-column":    [{"dx": 0,   "w": 550},  {"dx": 602, "w": 550}],
    "three-column":  [{"dx": 0,   "w": 360},  {"dx": 396, "w": 360}, {"dx": 792, "w": 360}],
    "sidebar-right": [{"dx": 0,   "w": 720},  {"dx": 772, "w": 380}],
    "sidebar-left":  [{"dx": 0,   "w": 380},  {"dx": 432, "w": 720}],
}
_KEYS = {
    "full":          ["main"],
    "two-column":    ["left", "right"],
    "three-column":  ["left", "center", "right"],
    "sidebar-right": ["main", "sidebar"],
    "sidebar-left":  ["sidebar", "main"],
}

# ── HTML shell ─────────────────────────────────────────────────────────────────
_BASE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:1280px;height:720px;overflow:hidden;background:#fff;}}
.slide{{position:relative;width:1280px;height:720px;background:#fff;
        font-family:Arial,Helvetica,sans-serif;overflow:hidden;}}
</style>
</head>
<body><div class="slide">
{body}
</div></body></html>"""


# ── Utility helpers ────────────────────────────────────────────────────────────
def _e(s):
    return _html.escape(str(s))

def _d(left, top, w, h, style="", inner=""):
    return (f'<div style="position:absolute;left:{left}px;top:{top}px;'
            f'width:{w}px;height:{h}px;{style}">{inner}</div>')

def _nice_max(v, n=5):
    """Return the tightest axis ceiling >= v that divides into n nice intervals."""
    if v <= 0: return 10
    raw = v / n
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    # Walk up nice factors until the resulting max covers v
    for f in (1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10):
        candidate = f * mag * n
        if candidate >= v:
            return candidate
    return 10 * mag * n

def _fmt(v, mode="auto"):
    if mode == "percent":  return f"{v:.0f}%"
    if mode == "currency":
        a = abs(v)
        if a == 0:        return "$0"
        if a < 1:         return f"${v:.2f}"
        if a < 10:        return f"${v:.1f}"
        if a < 1_000:     return f"${v:,.0f}"
        if a < 1_000_000: return f"${v/1_000:.1f}K"
        if a < 1_000_000_000: return f"${v/1_000_000:.1f}M"
        return f"${v/1_000_000_000:.1f}B"
    if mode == "decimal":  return f"{v:.1f}"
    if v >= 1_000_000:     return f"{v/1_000_000:.1f}M"
    if v >= 1_000:         return f"{v:,.0f}"
    if v == int(v):        return str(int(v))
    return f"{v:.2f}"

def _svg(w, h, inner, overflow="visible"):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'style="overflow:{overflow};">{inner}</svg>')

def _txt(x, y, text, size=11, weight=400, fill=GREY_TEXT,
         anchor="start", font="Arial,Helvetica,sans-serif"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'font-family="{font}">{_e(str(text))}</text>')


# ── Entry point ────────────────────────────────────────────────────────────────
def render_slide(spec) -> str:
    if isinstance(spec, str):
        spec = json.loads(spec)
    accent = spec.get("theme", {}).get("accent", PETROL)
    stype  = spec.get("slide_type", "content")
    if stype == "cover":
        body = _cover(spec, accent)
    elif stype == "chapter":
        body = _chapter(spec, accent)
    elif stype == "cta":
        body = _cta(spec, accent)
    else:
        body = _content(spec, accent)
    return _BASE.format(body=body)


# ── Cover ──────────────────────────────────────────────────────────────────────
def _cover(spec, accent):
    h = spec.get("header", {})
    p = []

    # Full-bleed iridescent swirl (pure CSS — iframe sandbox bars JS)
    SWIRL = (
        "radial-gradient(ellipse 47% 43% at 50% 50%,"
        "white 0%,rgba(255,255,255,.93) 16%,rgba(255,255,255,.6) 36%,transparent 58%),"
        "repeating-conic-gradient(from 0deg at 50% 50%,"
        "rgba(255,255,255,.45) 0deg 1.5deg,transparent 1.5deg 3deg),"
        "repeating-conic-gradient(from 27deg at 48% 52%,"
        "rgba(255,255,255,.25) 0deg 2deg,transparent 2deg 4deg),"
        "conic-gradient(from 12deg at 50% 50%,"
        "#F8C6D5 0%,#C6EDD6 22%,#C0D8F4 44%,#F8EEC0 66%,#DCC6F2 88%,#F8C6D5 100%)"
    )
    p.append(_d(0, 0, SLIDE_W, SLIDE_H, f"background:{SWIRL};"))

    # DT Wordmark SVG — centered, scaled to 540×41px
    WM_W, WM_H = 540, 41
    wm_svg = re.sub(r'\bwidth="\d+(?:\.\d+)?(?:px)?"', f'width="{WM_W}"',
                    _SVG_DT_WORDMARK, count=1)
    wm_svg = re.sub(r'\bheight="\d+(?:\.\d+)?(?:px)?"', f'height="{WM_H}"',
                    wm_svg, count=1)
    p.append(_d((SLIDE_W - WM_W) // 2, 180, WM_W, WM_H, "", wm_svg))

    # Thin separator rule below wordmark
    p.append(_d((SLIDE_W - 360) // 2, 233, 360, 1, "background:rgba(0,0,0,.16);"))

    # Headline / kicker / sub — vertically stacked below rule
    oy = 250
    if h.get("kicker"):
        p.append(_d(0, oy, SLIDE_W, 20,
            "font-size:11px;font-weight:700;color:#1A1A1A;text-transform:uppercase;"
            "letter-spacing:2.5px;text-align:center;overflow:hidden;white-space:nowrap;",
            _e(h["kicker"])))
        oy += 30

    if h.get("headline"):
        hl  = h["headline"]
        fs  = 36 if len(hl) <= 50 else (28 if len(hl) <= 80 else 22)
        cpl = max(1, (SLIDE_W - 280) / (fs * 0.54))
        nln = max(1, math.ceil(len(hl) / cpl))
        hl_h = min(max(int(nln * fs * 1.35 + 8), 44), 640 - oy - 50)
        p.append(_d(140, oy, SLIDE_W - 280, hl_h,
            f"font-size:{fs}px;font-weight:700;color:#1A1A1A;"
            "text-align:center;line-height:1.35;overflow:hidden;",
            _e(hl)))
        oy += hl_h + 14

    if h.get("sub"):
        sub_y = min(oy, 618)
        p.append(_d(180, sub_y, SLIDE_W - 360, 40,
            "font-size:14px;color:#444;text-align:center;overflow:hidden;",
            _e(h["sub"])))

    # Brand logos strip (bottom 70px, white/translucent)
    STRIP_H = 70
    STRIP_Y = SLIDE_H - STRIP_H  # 650
    p.append(_d(0, STRIP_Y, SLIDE_W, STRIP_H,
        "background:rgba(255,255,255,.92);border-top:1px solid rgba(0,0,0,.05);"))
    LOGO_Y = STRIP_Y + (STRIP_H - _LOGO_H) // 2
    for i, (svg_str, lw, lx) in enumerate(zip(_BRAND_LOGO_SVGS, _LOGO_WS, _LOGO_XS)):
        p.append(_d(lx, LOGO_Y, lw, _LOGO_H, "",
                    _brand_logo(svg_str, i, lw, _LOGO_H)))

    return "\n".join(p)


# ── Chapter divider ────────────────────────────────────────────────────────────
def _chapter(spec, accent):
    h = spec.get("header", {})
    f = spec.get("footer", {})
    bg = spec.get("theme", {}).get("bg", PETROL_DARK)
    p = []
    p.append(_d(0, 0, SLIDE_W, SLIDE_H, f"background:{bg};"))
    if h.get("kicker"):
        p.append(_d(M_L, 230, 300, 20,
            "font-size:13px;font-weight:700;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:2px;",
            _e(h["kicker"])))
    p.append(_d(M_L, 252, 70, 3, f"background:{accent};"))
    if h.get("headline"):
        text = _e(h["headline"]).replace("\n", "<br>")
        p.append(_d(M_L, 262, 900, 160,
            "font-size:42px;font-weight:700;color:#fff;line-height:1.2;", text))
    p.extend(_dt_footer(f, dark=True))
    return "\n".join(p)


# ── CTA / closing ──────────────────────────────────────────────────────────────
def _cta(spec, accent):
    h = spec.get("header", {})
    f = spec.get("footer", {})
    bg = spec.get("theme", {}).get("bg", "#002E3D")
    p = []
    p.append(_d(0, 0, SLIDE_W, SLIDE_H, f"background:{bg};"))
    oy_cta = 270
    if h.get("headline"):
        hl = h["headline"]
        cpl_cta = max(1, 1000 / (34 * 0.54))
        n_lines_cta = max(1, math.ceil(len(hl) / cpl_cta))
        hl_h_cta = max(80, int(n_lines_cta * 34 * 1.35))
        p.append(_d(M_L, oy_cta, 1000, hl_h_cta,
            "font-size:34px;font-weight:700;color:#fff;line-height:1.35;overflow:hidden;",
            _e(hl)))
        oy_cta += hl_h_cta + 20
    if h.get("sub"):
        p.append(_d(M_L, oy_cta, 850, 50,
            "font-size:15px;color:rgba(255,255,255,0.65);overflow:hidden;", _e(h["sub"])))
    for i, item in enumerate(spec.get("content", {}).get("items", [])):
        p.append(_d(M_L, 450 + i * 28, 650, 24,
            "font-size:13px;color:rgba(255,255,255,0.8);", _e(item)))
    p.extend(_dt_footer(f, dark=True))
    return "\n".join(p)


# ── Content slide ──────────────────────────────────────────────────────────────
def _content(spec, accent):
    h       = spec.get("header", {})
    f       = spec.get("footer", {})
    layout  = spec.get("layout", "full")
    content = spec.get("content", {})
    p = []

    # Header zone (no accent bar — clean DT template style)
    oy_hdr = 4
    if h.get("kicker"):
        p.append(_d(M_L, oy_hdr + 12, CON_W, 16,
            f"font-size:10px;font-weight:700;color:{accent};text-transform:uppercase;"
            "letter-spacing:1px;overflow:hidden;white-space:nowrap;",
            _e(h["kicker"])))
        oy_hdr += 28
    else:
        oy_hdr += 16
    if h.get("headline"):
        hl = h["headline"]
        # Smaller font for long headlines so they fit in 2 lines comfortably
        fs = 20 if len(hl) <= 70 else (18 if len(hl) <= 95 else 16)
        p.append(_d(M_L, oy_hdr, CON_W, 42,
            f"font-size:{fs}px;font-weight:700;color:#1A1A1A;line-height:1.25;"
            "overflow:hidden;",
            _e(hl)))
        oy_hdr += 46
    # Divider rule
    p.append(_d(M_L, oy_hdr, CON_W, 1, f"background:{GREY_RULE};"))
    oy_hdr += 6
    if h.get("sub"):
        p.append(_d(M_L, oy_hdr, CON_W, 22,
            "font-size:12px;color:#666;overflow:hidden;white-space:nowrap;",
            _e(h["sub"])))

    # Column layout
    cols = _COLS.get(layout, _COLS["full"])
    keys = _KEYS.get(layout, ["main"])
    for col, key in zip(cols, keys):
        block = content.get(key)
        if not block:
            continue
        bx = CON_X + col["dx"]
        p.append(render_block(block, bx, CON_Y, col["w"], CON_H, accent))

    p.extend(_dt_footer(f, dark=False))
    return "\n".join(p)


# ── Block dispatcher ───────────────────────────────────────────────────────────
def render_block(block: dict, x: int, y: int, w: int, h: int,
                 accent: str = PETROL) -> str:
    btype = block.get("type", "text-block")
    fn = {
        "bar-chart":       render_bar_chart,
        "line-chart":      render_line_chart,
        "scatter-chart":   render_scatter_chart,
        "donut-chart":     render_donut_chart,
        "kpi-grid":        render_kpi_grid,
        "bullet-list":     render_bullet_list,
        "table":           render_table,
        "text-block":      render_text_block,
        "gantt-chart":        render_gantt,
        "waterfall-chart":    render_waterfall,
        "process-flow":       render_process_flow,
        "comparison-matrix":  render_comparison_matrix,
    }.get(btype)
    if fn:
        return fn(block, x, y, w, h, accent)
    return _d(x, y, w, 40, "border:1px dashed #ccc;color:#999;font-size:11px;"
              "display:flex;align-items:center;justify-content:center;",
              f"[unsupported: {btype}]")


# ══════════════════════════════════════════════════════════════════════════════
# Chart renderers
# ══════════════════════════════════════════════════════════════════════════════

# ── Bar chart ──────────────────────────────────────────────────────────────────
def render_bar_chart(block, x, y, w, h, accent=PETROL):
    """
    orientation: "vertical" (default) | "horizontal"
    Single-series:  series: [{label, value}]
    Multi-series:   series: [{name, values:[...]}], labels: [...]
    stacked: bool
    fmt: "auto"|"percent"|"currency"|"decimal"
    show_values: bool (default True)
    title: str
    """
    if block.get("orientation") == "horizontal":
        return _bar_h(block, x, y, w, h, accent)
    return _bar_v(block, x, y, w, h, accent)


def _series_mode(block):
    s = block.get("series", [])
    if not s:
        return "single", []
    if isinstance(s[0].get("values"), list):
        lbls = block.get("labels", [str(i) for i in range(len(s[0]["values"]))])
        return "multi", lbls, s
    return "single", s


def _bar_v(block, x, y, w, h, accent):
    title     = block.get("title", "")
    fmt       = block.get("fmt", "auto")
    show_vals = block.get("show_values", True)
    stacked   = block.get("stacked", False)

    T = 22 if title else 4
    L, R = 48, 6

    # Pre-compute legend rows to set B before cw/ch
    _slist = [s for s in block.get("series", []) if isinstance(s, dict) and "values" in s and s.get("name")]
    if len(_slist) > 1:
        _est_lbl = max((len(s["name"]) for s in _slist), default=8)
        _est_w   = max(_est_lbl * 6 + 22, 80)
        _est_ipr = max(1, (w - L - R) // _est_w)
        _n_rows  = math.ceil(len(_slist) / _est_ipr)
        B = 30 + _n_rows * 14
    else:
        B = 38

    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    mode, *rest = _series_mode(block)
    if mode == "single":
        s_raw  = rest[0]
        labels = [s["label"] for s in s_raw]
        # "highlight": true on one bar → renders that bar in YELLOW (DT max-accent rule: 1 per view)
        hl_flags = [bool(s.get("highlight")) for s in s_raw]
        series = [{"name": "", "values": [s["value"] for s in s_raw],
                   "color": accent, "_hl": hl_flags}]
    else:
        labels, s_raw = rest
        hl_flags = []
        series = [{"name": s.get("name", ""), "values": s["values"],
                   "color": SERIES_COLORS[i % len(SERIES_COLORS)]}
                  for i, s in enumerate(s_raw)]

    n, ns = len(labels), len(series)
    all_v = [v for s in series for v in s["values"]]
    if stacked:
        col_sums = [sum(s["values"][i] for s in series) for i in range(n)]
        y_max = _nice_max(max(col_sums))
    else:
        y_max = _nice_max(max(all_v)) if all_v else 10
    y_min = 0

    def vy(v): return cy + ch - (v - y_min) / (y_max - y_min) * ch

    slot = cw / n
    if stacked or ns == 1:
        bw = slot * 0.72
        def bx_fn(i, si): return cx + i * slot + (slot - bw) / 2
    else:
        bw = slot * 0.72 / ns
        def bx_fn(i, si): return cx + i * slot + (slot - bw * ns) / 2 + si * bw

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(6):
        gv = y_min + k * (y_max - y_min) / 5
        gy = vy(gv)
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(cx - 4, gy + 4, _fmt(gv, fmt), 9, 400, GREY_SUB, "end"))

    ln.append(f'<line x1="{cx}" y1="{vy(0):.1f}" x2="{cx+cw}" y2="{vy(0):.1f}" stroke="#999" stroke-width="1.5"/>')

    inside_labels = stacked and ns <= 2

    stack = [0] * n
    for si, s in enumerate(series):
        _bar_hl = s.get("_hl", [])
        for i, v in enumerate(s["values"][:n]):
            bx = bx_fn(i, si)
            if stacked:
                bot, top = vy(stack[i]), vy(stack[i] + v)
                stack[i] += v
            else:
                bot, top = vy(0), vy(v)
            bh = bot - top
            bar_color = YELLOW if (not stacked and _bar_hl and _bar_hl[i]) else s["color"]
            ln.append(f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(bh, 1):.1f}" fill="{bar_color}" rx="1"/>')
            if show_vals and v > 0:
                if inside_labels:
                    if bh >= 16:
                        lbl_y = top + bh / 2 + 4
                        lbl_c = "#fff" if si == 0 else "rgba(255,255,255,0.85)"
                        ln.append(_txt(bx + bw / 2, lbl_y, _fmt(v, fmt), 9, 700, lbl_c, "middle"))
                elif not stacked:
                    ln.append(_txt(bx + bw / 2, top - 3, _fmt(v, fmt), 9, 400, GREY_TEXT, "middle"))

    # For stacked bars with 3+ series: total above each bar
    if stacked and ns >= 3 and show_vals:
        for i in range(n):
            total = sum(s["values"][i] for s in series if i < len(s["values"]))
            if total > 0:
                bx    = bx_fn(i, 0)
                top_y = vy(total)
                ln.append(_txt(bx + bw / 2, top_y - 5, _fmt(total, fmt), 9, 700, GREY_TEXT, "middle"))

    for i, lbl in enumerate(labels):
        lx = cx + i * slot + slot / 2
        ln.append(_txt(lx, cy + ch + 14, lbl, 10, 400, GREY_SUB, "middle"))

    if ns > 1:
        max_lbl_len = max((len(s["name"]) for s in series if s["name"]), default=8)
        item_w      = max(max_lbl_len * 6 + 22, 80)
        items_per_row = max(1, cw // item_w)
        leg_y_base  = cy + ch + 26
        for si, s in enumerate(series):
            if not s["name"]: continue
            row = si // items_per_row
            col = si % items_per_row
            lx  = cx + col * item_w
            ly  = leg_y_base + row * 14
            ln.append(f'<rect x="{lx}" y="{ly}" width="10" height="10" fill="{s["color"]}"/>')
            ln.append(_txt(lx + 13, ly + 9, s["name"], 9, 400, GREY_SUB))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


def _bar_h(block, x, y, w, h, accent):
    title     = block.get("title", "")
    fmt       = block.get("fmt", "auto")
    show_vals = block.get("show_values", True)

    mode, *rest = _series_mode(block)
    if mode == "single":
        items = rest[0]
    else:
        lbls, s_raw = rest
        items = [{"label": l, "value": s_raw[0]["values"][i]}
                 for i, l in enumerate(lbls)]

    T, B, L, R = (22 if title else 4), 28, 120, 55
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T  # bars start from top — no vertical centring

    n   = len(items)
    all_v = [s["value"] for s in items]
    x_max = _nice_max(max(all_v)) if all_v else 10

    slot = ch / n               # distribute evenly across available height
    bh   = min(slot * 0.60, 40) # cap bar height so thick columns stay slim

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(5):
        gx = cx + k * cw / 4
        ln.append(f'<line x1="{gx:.1f}" y1="{cy}" x2="{gx:.1f}" y2="{cy+ch}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(gx, cy + ch + 14, _fmt(k * x_max / 4, fmt), 9, 400, GREY_SUB, "middle"))

    for i, s in enumerate(items):
        by = cy + i * slot + (slot - bh) / 2
        bw_px = s["value"] / x_max * cw
        color = YELLOW if s.get("highlight") else SERIES_COLORS[i % len(SERIES_COLORS)]

        ln.append(f'<rect x="{cx}" y="{by:.1f}" width="{max(bw_px, 1):.1f}" height="{bh:.1f}" fill="{color}" rx="2"/>')
        ln.append(_txt(cx - 6, by + bh / 2 + 4, s["label"], 10, 400, GREY_TEXT, "end"))
        if show_vals:
            ln.append(_txt(cx + bw_px + 4, by + bh / 2 + 4,
                           _fmt(s["value"], fmt), 10, 700, color))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Line chart ─────────────────────────────────────────────────────────────────
def render_line_chart(block, x, y, w, h, accent=PETROL):
    """
    labels: ["Q1 2020", ...]
    series: [{name, values:[...]}]
    fmt: str
    show_points: bool (default True)
    title: str
    area: bool — fill area under line (default False)
    """
    labels      = block.get("labels", [])
    series_raw  = block.get("series", [])
    fmt         = block.get("fmt", "auto")
    show_pts    = block.get("show_points", True)
    title       = block.get("title", "")
    area        = block.get("area", False)

    T  = 22 if title else 8
    L, R = 48, 8

    # Pre-compute legend row count to set B before cw/ch
    ns_est = len(series_raw)
    if ns_est > 1:
        est_max_lbl = max((len(s.get("name", "")) for s in series_raw if s.get("name")), default=8)
        est_item_w  = max(est_max_lbl * 6 + 28, 90)
        est_ipr     = max(1, (w - L - R) // est_item_w)
        n_leg_rows  = math.ceil(ns_est / est_ipr)
        B = 28 + n_leg_rows * 16   # 28px clears x-axis labels; 16px per legend row
    else:
        B = 24

    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    series = [{"name": s.get("name", ""), "values": s["values"],
               "color": SERIES_COLORS[i % len(SERIES_COLORS)]}
              for i, s in enumerate(series_raw)]

    all_v = [v for s in series for v in s["values"] if v is not None]
    y_max = _nice_max(max(all_v)) if all_v else 10
    y_min = min(0, min(all_v)) if all_v else 0
    n     = max(len(labels), 1)

    def _pt(i, v):
        px_x = cx + i * cw / (n - 1) if n > 1 else cx + cw / 2
        px_y = cy + ch - (v - y_min) / (y_max - y_min) * ch
        return px_x, px_y

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(6):
        gv = y_min + k * (y_max - y_min) / 5
        gy = cy + ch - k * ch / 5
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(cx - 4, gy + 4, _fmt(gv, fmt), 9, 400, GREY_SUB, "end"))

    for s in series:
        # Build path with gaps (M/L) around None values
        raw_pts = [(_pt(i, v) if v is not None else None)
                   for i, v in enumerate(s["values"][:n])]
        segs, cur = [], []
        for pt in raw_pts:
            if pt is None:
                if cur: segs.append(cur); cur = []
            else:
                cur.append(pt)
        if cur: segs.append(cur)

        for seg in segs:
            path = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in seg)
            if area and len(seg) > 1:
                close = f" L {seg[-1][0]:.1f},{cy+ch} L {seg[0][0]:.1f},{cy+ch} Z"
                ln.append(f'<path d="{path}{close}" fill="{s["color"]}" opacity="0.12"/>')
            ln.append(f'<path d="{path}" stroke="{s["color"]}" stroke-width="2.5" fill="none"/>')

        if show_pts:
            for pt in raw_pts:
                if pt is not None:
                    ln.append(f'<circle cx="{pt[0]:.1f}" cy="{pt[1]:.1f}" r="4" fill="{s["color"]}" stroke="#fff" stroke-width="1.5"/>')

    for i, lbl in enumerate(labels):
        lx, _ = _pt(i, 0)
        ln.append(_txt(lx, cy + ch + 14, lbl, 10, 400, GREY_SUB, "middle"))

    if len(series) > 1:
        max_lbl_len = max((len(s["name"]) for s in series if s["name"]), default=8)
        item_w      = max(max_lbl_len * 6 + 28, 90)
        items_per_row = max(1, cw // item_w)
        leg_y_base  = cy + ch + 28   # 28px clears x-axis label text
        for si, s in enumerate(series):
            if not s["name"]: continue
            row = si // items_per_row
            col = si % items_per_row
            lx  = cx + col * item_w
            ly  = leg_y_base + row * 16
            ln.append(f'<rect x="{lx}" y="{ly}" width="20" height="3" fill="{s["color"]}"/>')
            ln.append(_txt(lx + 25, ly + 6, s["name"], 9, 400, GREY_SUB))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Scatter / bubble chart ─────────────────────────────────────────────────────
def render_scatter_chart(block, x, y, w, h, accent=PETROL):
    """
    points: [{label, x, y, size: float, color: hex}]
    x_label / y_label: axis labels
    x_range / y_range: [min, max]
    quadrant_labels: [TL, TR, BL, BR]
    title: str
    """
    points   = block.get("points", [])
    x_label  = block.get("x_label", "")
    y_label  = block.get("y_label", "")
    x_range  = block.get("x_range")
    y_range  = block.get("y_range")
    qlabels  = block.get("quadrant_labels")
    title    = block.get("title", "")

    T, B, L, R = (22 if title else 8), 36, 48, 8
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    x_min, x_max = (x_range or [min(xs, default=0), _nice_max(max(xs, default=10))])
    y_min, y_max = (y_range or [0, _nice_max(max(ys, default=10))])

    def to_px(px_v, py_v):
        return (cx + (px_v - x_min) / (x_max - x_min) * cw,
                cy + ch - (py_v - y_min) / (y_max - y_min) * ch)

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(5):
        gy = cy + k * ch / 4
        gx = cx + k * cw / 4
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(f'<line x1="{gx:.1f}" y1="{cy}" x2="{gx:.1f}" y2="{cy+ch}" stroke="{GREY_RULE}" stroke-width="1"/>')

    if qlabels:
        mx, my = to_px((x_min + x_max) / 2, (y_min + y_max) / 2)
        ln.append(f'<line x1="{mx:.1f}" y1="{cy}" x2="{mx:.1f}" y2="{cy+ch}" stroke="#aaa" stroke-width="1" stroke-dasharray="4 3"/>')
        ln.append(f'<line x1="{cx}" y1="{my:.1f}" x2="{cx+cw}" y2="{my:.1f}" stroke="#aaa" stroke-width="1" stroke-dasharray="4 3"/>')
        # Place quadrant labels at the mid-top and mid-bottom of each quadrant
        # so they stay clear of extreme-corner bubbles and the center boundary
        tl_cx = (cx + mx) / 2
        tr_cx = (mx + cx + cw) / 2
        ql_positions = [
            (tl_cx, cy + 14,      "middle"),   # TL: mid-top of top-left quadrant
            (tr_cx, cy + 14,      "middle"),   # TR: mid-top of top-right quadrant
            (tl_cx, cy + ch - 8,  "middle"),   # BL: mid-bottom of bottom-left quadrant
            (tr_cx, cy + ch - 8,  "middle"),   # BR: mid-bottom of bottom-right quadrant
        ]
        for ql, (qx, qy, anchor) in zip(qlabels, ql_positions):
            ln.append(_txt(qx, qy, ql, 9, 400, GREY_SUB, anchor))

    for p in points:
        px2, py2 = to_px(p["x"], p["y"])
        r     = p.get("size", 6)
        # "highlight": true → YELLOW ring + filled (DT max-accent, 1 point per view)
        if p.get("highlight"):
            color = YELLOW
            ln.append(f'<circle cx="{px2:.1f}" cy="{py2:.1f}" r="{r+3}" fill="none" stroke="{YELLOW}" stroke-width="2" opacity="0.6"/>')
        else:
            color = p.get("color") or accent
        ln.append(f'<circle cx="{px2:.1f}" cy="{py2:.1f}" r="{r}" fill="{color}" opacity="0.85"/>')
        if p.get("label"):
            ln.append(_txt(px2 + r + 3, py2 + 4, p["label"], 9, 400, GREY_TEXT))

    ln.append(f'<line x1="{cx}" y1="{cy+ch}" x2="{cx+cw}" y2="{cy+ch}" stroke="#999" stroke-width="1.5"/>')
    ln.append(f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+ch}" stroke="#999" stroke-width="1.5"/>')

    if x_label:
        ln.append(_txt(cx + cw / 2, cy + ch + 28, x_label, 10, 400, GREY_SUB, "middle"))
    if y_label:
        mid = cy + ch / 2
        ln.append(f'<text x="12" y="{mid:.1f}" text-anchor="middle" font-size="10" fill="{GREY_SUB}" '
                  f'transform="rotate(-90,12,{mid:.1f})" font-family="Arial,Helvetica,sans-serif">{_e(y_label)}</text>')

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Donut chart ────────────────────────────────────────────────────────────────
def render_donut_chart(block, x, y, w, h, accent=PETROL):
    """
    segments: [{label, value, color: hex}]
    center_text / center_label: text shown in donut hole
    show_legend: bool (default True)
    fmt: "percent"|"auto"
    """
    segs         = block.get("segments", [])
    center_text  = block.get("center_text", "")
    center_label = block.get("center_label", "")
    show_leg     = block.get("show_legend", True)
    fmt          = block.get("fmt", "percent")

    if not segs:
        return ""

    leg_w = 200 if show_leg else 0
    chart_w = w - leg_w
    r_out = min(chart_w, h) // 2 - 10
    r_in  = int(r_out * 0.58)
    cx2   = chart_w // 2
    cy2   = h // 2

    total = sum(s.get("value", 0) for s in segs)
    if total == 0: return ""

    # Assign colors so no two adjacent segments (including last→first wrap) share a color
    _ext_palette = list(SERIES_COLORS) + [YELLOW]
    _seg_colors: list = []
    for _i, _s in enumerate(segs):
        if _s.get("color"):
            _seg_colors.append(_s["color"])
        else:
            _prev  = _seg_colors[-1] if _seg_colors else None
            _first = _seg_colors[0]  if (_i == len(segs) - 1 and _seg_colors) else None
            _chosen = next((c for c in _ext_palette if c != _prev and c != _first), YELLOW)
            _seg_colors.append(_chosen)

    ln    = []
    start = -math.pi / 2

    for i, seg in enumerate(segs):
        v     = seg.get("value", 0)
        color = _seg_colors[i]
        sweep = (v / total) * 2 * math.pi
        end   = start + sweep

        x1, y1 = cx2 + r_out * math.cos(start), cy2 + r_out * math.sin(start)
        x2, y2 = cx2 + r_out * math.cos(end),   cy2 + r_out * math.sin(end)
        ix1, iy1 = cx2 + r_in * math.cos(end),  cy2 + r_in * math.sin(end)
        ix2, iy2 = cx2 + r_in * math.cos(start), cy2 + r_in * math.sin(start)

        large = 1 if sweep > math.pi else 0
        d = (f"M {x1:.1f} {y1:.1f} A {r_out} {r_out} 0 {large} 1 {x2:.1f} {y2:.1f} "
             f"L {ix1:.1f} {iy1:.1f} A {r_in} {r_in} 0 {large} 0 {ix2:.1f} {iy2:.1f} Z")
        ln.append(f'<path d="{d}" fill="{color}"/>')

        if sweep > 0.3:
            mid  = start + sweep / 2
            lr   = (r_out + r_in) / 2
            lx   = cx2 + lr * math.cos(mid)
            ly   = cy2 + lr * math.sin(mid)
            pct  = f"{v / total * 100:.0f}%"
            ln.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="middle" font-size="11" '
                      f'font-weight="700" fill="#fff" font-family="Arial,Helvetica,sans-serif">{pct}</text>')
        start = end

    if center_text:
        ln.append(f'<text x="{cx2}" y="{cy2-2}" text-anchor="middle" font-size="20" font-weight="700" '
                  f'fill="{accent}" font-family="Arial,Helvetica,sans-serif">{_e(center_text)}</text>')
    if center_label:
        ln.append(f'<text x="{cx2}" y="{cy2+16}" text-anchor="middle" font-size="9" fill="{GREY_SUB}" '
                  f'font-family="Arial,Helvetica,sans-serif">{_e(center_label)}</text>')

    if show_leg:
        lx0     = chart_w + 10
        txt_w   = leg_w - 28          # available width for label text
        cpl_leg = max(1, txt_w / 6.0) # ~10px font ≈ 6px/char
        # Pre-compute per-item heights so we can vertically center the block
        def _leg_item_h(seg):
            lbl = seg.get("label", "")
            return 44 if len(lbl) > cpl_leg else 30
        total_leg_h = sum(_leg_item_h(s) for s in segs)
        ly = max(h // 2 - total_leg_h // 2, 6)

        for i, seg in enumerate(segs):
            if ly > h - 20: break
            color = _seg_colors[i]
            ln.append(f'<rect x="{lx0}" y="{ly}" width="12" height="12" fill="{color}" rx="2"/>')
            label = seg.get("label", "")
            v   = seg.get("value", 0)
            pct = f"{v / total * 100:.1f}%"
            if len(label) > cpl_leg:
                # split at last word boundary before cpl_leg
                sp = label.rfind(" ", 0, int(cpl_leg))
                sp = sp if sp > 0 else int(cpl_leg)
                ln.append(_txt(lx0 + 16, ly + 10, label[:sp],       10, 400, GREY_TEXT))
                ln.append(_txt(lx0 + 16, ly + 22, label[sp+1:],     10, 400, GREY_TEXT))
                ln.append(_txt(lx0 + 16, ly + 36, pct,               9, 400, GREY_SUB))
                ly += 46
            else:
                ln.append(_txt(lx0 + 16, ly + 10, label, 10, 400, GREY_TEXT))
                ln.append(_txt(lx0 + 16, ly + 22, pct,    9, 400, GREY_SUB))
                ly += 32

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── KPI / stat callout grid ────────────────────────────────────────────────────
def render_kpi_grid(block, x, y, w, h, accent=PETROL):
    """
    columns: 1-4 (default 2)
    style: "default" | "accent" | "compact" | "borderless"
    items: [{stat, label, delta, positive: True|False|None, icon: str}]
    """
    items  = block.get("items", [])
    n_cols = min(block.get("columns", 2), 4)
    n_rows = math.ceil(len(items) / n_cols) if items else 1
    style  = block.get("style", "default")

    gap    = 12
    card_w = (w - gap * (n_cols - 1)) // n_cols
    card_h = (h - gap * (n_rows - 1)) // n_rows

    # Accent cards have fixed content height; cap and center vertically so they
    # don't stretch to fill the full column with empty whitespace.
    if style == "accent":
        eff_card_h = min(card_h, 160)
        total_grid_h = n_rows * eff_card_h + gap * (n_rows - 1)
        y_start = y + max(0, (h - total_grid_h) // 2)
    else:
        eff_card_h = card_h
        y_start = y

    stat_fs = min(38, max(20, eff_card_h // 5))

    p = []
    for i, item in enumerate(items):
        col, row = i % n_cols, i // n_cols
        cx2 = x + col * (card_w + gap)
        cy2 = y_start + row * (eff_card_h + gap)

        stat  = _e(str(item.get("stat", "")))
        label = _e(str(item.get("label", "")))
        delta = item.get("delta", "")
        pos   = item.get("positive", None)
        icon  = _e(str(item.get("icon", "")))

        if style == "accent":
            # Colored stat band + tight white body; card shrinks to its content
            hdr_h   = max(14, int(eff_card_h * 0.55))
            label_h = 22
            body_pad = 10  # top+bottom padding inside white section
            vis_h = hdr_h + body_pad + label_h + (18 if delta else 0) + body_pad
            # full card bg (white, sized to content)
            p.append(_d(cx2, cy2, card_w, vis_h,
                f"background:#fff;border-radius:6px;border:1px solid {GREY_RULE};overflow:hidden;"))
            # accent header band
            p.append(_d(cx2, cy2, card_w, hdr_h,
                f"background:{accent};border-radius:6px 6px 0 0;"))
            # stat — vertically centered in header band
            stat_y = cy2 + (hdr_h - stat_fs) // 2
            p.append(_d(cx2 + 12, stat_y, card_w - 24, stat_fs + 2,
                f"font-size:{stat_fs}px;font-weight:700;color:#fff;line-height:1;", stat))
            # label
            body_y = cy2 + hdr_h + body_pad
            p.append(_d(cx2 + 12, body_y, card_w - 24, label_h,
                "font-size:11px;color:#444;line-height:1.3;overflow:hidden;", label))
            # delta sits immediately below label
            if delta:
                dc = (GREEN_PASS if pos else RED_FAIL) if pos is not None else GREY_SUB
                p.append(_d(cx2 + 12, body_y + label_h + 4, card_w - 24, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

        elif style == "compact":
            # Left accent bar, no card background — just a clean row
            p.append(_d(cx2, cy2 + 4, 3, card_h - 8, f"background:{accent};border-radius:2px;"))
            p.append(_d(cx2 + 14, cy2, card_w - 14, int(card_h * 0.5),
                f"font-size:{min(stat_fs, 28)}px;font-weight:700;color:{accent};line-height:1;", stat))
            p.append(_d(cx2 + 14, cy2 + int(card_h * 0.52), card_w - 14, int(card_h * 0.3),
                "font-size:11px;color:#555;line-height:1.4;", label))
            if delta:
                dc = (GREEN_PASS if pos else RED_FAIL) if pos is not None else GREY_SUB
                p.append(_d(cx2 + 14, cy2 + int(card_h * 0.82), card_w - 14, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

        elif style == "borderless":
            # No card chrome — just stat + label floating on slide background
            p.append(_d(cx2, cy2, card_w, int(card_h * 0.48),
                f"font-size:{stat_fs}px;font-weight:700;color:{accent};line-height:1;", stat))
            p.append(_d(cx2, cy2 + int(card_h * 0.50), card_w, int(card_h * 0.35),
                "font-size:11px;color:#666;line-height:1.4;", label))
            p.append(_d(cx2, cy2 + card_h - 2, card_w, 1, f"background:{GREY_RULE};"))
            if delta:
                dc = (GREEN_PASS if pos else RED_FAIL) if pos is not None else GREY_SUB
                p.append(_d(cx2, cy2 + int(card_h * 0.86), card_w, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

        else:  # default
            p.append(_d(cx2, cy2, card_w, card_h,
                f"background:{GREY_BG};border-radius:6px;"))
            p.append(_d(cx2, cy2, card_w, 3,
                f"background:{accent};border-radius:6px 6px 0 0;"))
            if icon:
                p.append(_d(cx2 + card_w - 36, cy2 + 8, 28, 16,
                    f"font-size:9px;font-weight:700;color:{accent};background:#fff;"
                    f"border-radius:3px;text-align:center;padding:2px 4px;", icon))
            stat_top  = max(14, int(card_h * 0.12))
            label_top = max(stat_top + stat_fs + 8, int(card_h * 0.48))
            delta_top = int(card_h * 0.82)
            p.append(_d(cx2 + 14, cy2 + stat_top, card_w - 28, int(card_h * 0.36),
                f"font-size:{stat_fs}px;font-weight:700;color:{accent};line-height:1;", stat))
            p.append(_d(cx2 + 14, cy2 + label_top, card_w - 28, int(card_h * 0.30),
                "font-size:11px;color:#555;line-height:1.4;", label))
            if delta:
                dc = (GREEN_PASS if pos else RED_FAIL) if pos is not None else GREY_SUB
                p.append(_d(cx2 + 14, cy2 + delta_top, card_w - 28, 14,
                    f"font-size:10px;font-weight:700;color:{dc};", _e(str(delta))))

    return "\n".join(p)


# ── Bullet list ────────────────────────────────────────────────────────────────
def render_bullet_list(block, x, y, w, h, accent=PETROL):
    """
    title: str (optional section title)
    items: [{text, sub}] or ["plain string", ...]
    spacing: int (px between items, default 10)
    """
    title   = block.get("title", "")
    items   = block.get("items", [])
    spacing = block.get("spacing", 10)

    p  = []
    text_w   = max(w - 16, 1)
    cpl_main = max(1, text_w / 7.5)
    cpl_sub  = max(1, text_w / 6.3)

    # Pre-compute total content height to vertically center the list
    title_h = 28 if title else 0
    def _item_h(item):
        t = item if isinstance(item, str) else item.get("text", "")
        s = "" if isinstance(item, str) else item.get("sub", "")
        mh = max(20, int(max(1, math.ceil(len(t) / cpl_main)) * 20)) + 2
        sh = (max(18, int(max(1, math.ceil(len(s) / cpl_sub)) * 17)) + 4) if s else 0
        return mh + sh + spacing

    total_content_h = title_h + sum(_item_h(it) for it in items)
    top_pad = max(0, (h - total_content_h) // 2)
    oy = y + top_pad

    if title:
        p.append(_d(x, oy, w, 20,
            f"font-size:13px;font-weight:700;color:{accent};", _e(title)))
        oy += 28

    for item in items:
        if isinstance(item, str):
            text, sub = item, ""
        else:
            text = item.get("text", "")
            sub  = item.get("sub", "")

        main_lines = max(1, math.ceil(len(text) / cpl_main))
        main_h     = max(20, int(main_lines * 20))

        p.append(_d(x, oy + 6, 7, 7, f"background:{accent};border-radius:50%;"))
        p.append(_d(x + 16, oy, text_w, main_h,
            "font-size:13px;color:#1A1A1A;font-weight:600;line-height:1.5;overflow:hidden;",
            _e(text)))
        oy += main_h + 2

        if sub:
            sub_lines = max(1, math.ceil(len(sub) / cpl_sub))
            sub_h     = max(18, int(sub_lines * 17))
            p.append(_d(x + 16, oy, text_w, sub_h,
                "font-size:11px;color:#666;line-height:1.55;overflow:hidden;", _e(sub)))
            oy += sub_h + 4
        oy += spacing

        if oy > y + h - 20:
            break

    return "\n".join(p)


# ── Table ──────────────────────────────────────────────────────────────────────
def render_table(block, x, y, w, h, accent=PETROL):
    """
    headers: ["Col A", "Col B", ...]
    rows: [[v1, v2, ...], ...]
    col_widths: [int, ...] — optional, overrides equal distribution
    highlight_col: int — column index to accent
    """
    headers     = block.get("headers", [])
    rows        = block.get("rows", [])
    hl_col      = block.get("highlight_col")
    col_widths  = block.get("col_widths")

    n_cols = len(headers)
    if n_cols == 0: return ""

    if col_widths:
        cws = col_widths
    else:
        # Give the first (label) column 20% of width; split rest evenly
        label_w = max(60, int(w * 0.20))
        data_w  = (w - label_w) // max(n_cols - 1, 1)
        cws = [label_w] + [data_w] * (n_cols - 1)

    # Fewer columns → more room per header → use full label; many columns → shrink
    hdr_fs  = max(9, 11 - max(0, n_cols - 5))

    # Dynamically size hdr_h based on how many lines the longest header needs
    max_hdr_lines = 1
    for ci, hdr in enumerate(headers):
        col_w = cws[ci] if ci < len(cws) else (w // max(n_cols, 1))
        chars_per_line = max(1, (col_w - 8) / (hdr_fs * 0.55))
        lines = max(1, math.ceil(len(str(hdr)) / chars_per_line))
        max_hdr_lines = max(max_hdr_lines, lines)
    hdr_h = max(28, min(62, max_hdr_lines * (hdr_fs + 5) + 8))

    # Fill available height — cap per-row at 52px so it doesn't look too tall
    row_h  = min(52, max(28, (h - hdr_h) // max(len(rows), 1)))
    # Scale font with row height
    cell_fs = 11 if row_h <= 32 else (12 if row_h <= 42 else 13)

    p = []
    for ci, hdr in enumerate(headers):
        hx  = x + sum(cws[:ci])
        bg  = accent if ci == hl_col else PETROL_DARK
        p.append(_d(hx, y, cws[ci] - 1, hdr_h, f"background:{bg};"))
        p.append(_d(hx + 4, y + 4, cws[ci] - 8, hdr_h - 8,
            f"font-size:{hdr_fs}px;font-weight:700;color:#fff;overflow:hidden;line-height:1.35;",
            _e(str(hdr))))

    for ri, row in enumerate(rows):
        ry   = y + hdr_h + ri * row_h
        if ry + row_h > y + h: break
        rbg  = GREY_BG if ri % 2 == 0 else "#fff"
        for ci, val in enumerate(row[:n_cols]):
            cx2 = x + sum(cws[:ci])
            bg  = rbg
            ts  = f"font-size:{cell_fs}px;color:#333;"
            if ci == hl_col:
                bg = "#EFF7FA"
                ts = f"font-size:{cell_fs}px;font-weight:700;color:{accent};"
            p.append(_d(cx2, ry, cws[ci] - 1, row_h,
                f"background:{bg};border-bottom:1px solid {GREY_RULE};"))
            pad_t = max(4, (row_h - cell_fs * 2 - 4) // 2)
            p.append(_d(cx2 + 6, ry + pad_t, cws[ci] - 12, row_h - pad_t,
                ts + "overflow:hidden;line-height:1.4;", _e(str(val))))

    return "\n".join(p)


# ── Text block ─────────────────────────────────────────────────────────────────
def render_text_block(block, x, y, w, h, accent=PETROL):
    """
    title: str
    body: str (paragraph text)
    size: font-size in px (default 13)
    style: "default" | "callout" | "pull-quote"
    """
    title = block.get("title", "")
    body  = block.get("body", block.get("text", ""))
    size  = block.get("size", 13)
    style = block.get("style", "default")
    p     = []
    oy    = y

    if style == "callout":
        # Tinted box with left accent bar
        p.append(_d(x, y, w, h, f"background:{GREY_BG};border-radius:6px;border-left:4px solid {accent};"))
        x, w = x + 16, w - 24
        oy = y + 14

    elif style == "pull-quote":
        # Large opening quote mark + italic body
        p.append(_d(x, y - 8, 32, 40,
            f"font-size:52px;font-weight:900;color:{PETROL_LTST};line-height:1;", "“"))
        x, oy = x + 8, y + 28

    if title:
        p.append(_d(x, oy, w, 22,
            f"font-size:14px;font-weight:700;color:{accent};", _e(title)))
        oy += 30

    if body:
        fs   = size if style == "default" else size
        clr  = "#333" if style != "pull-quote" else "#444"
        p.append(_d(x, oy, w, h - (oy - y) - (14 if style == "callout" else 0),
            f"font-size:{fs}px;color:{clr};line-height:1.65;", _e(body)))

    return "\n".join(p)


# ── Comparison matrix ──────────────────────────────────────────────────────────
def render_comparison_matrix(block, x, y, w, h, accent=PETROL):
    """
    Side-by-side labeled comparison rows — the "2-column matrix" pattern.

    Schema:
      { "type": "comparison-matrix",
        "columns": ["Option A", "Option B"],
        "rows": [
          { "label": "Cost",  "values": ["Low", "High"] },
          { "label": "Speed", "values": ["Fast", "Slow"], "highlight": 0 }
        ],
        "style": "default | zebra | bordered"
      }
    highlight: 0-based index of winning/preferred column per row
    """
    cols  = block.get("columns", [])
    rows  = block.get("rows", [])
    style = block.get("style", "zebra")
    title = block.get("title", "")

    if not cols or not rows:
        return ""

    n_cols = len(cols)
    p      = []
    oy     = y

    if title:
        p.append(_d(x, oy, w, 20,
            f"font-size:13px;font-weight:700;color:{accent};", _e(title)))
        oy += 26

    label_w = max(130, w // (n_cols + 2))
    col_w   = (w - label_w) // n_cols
    hdr_h   = 30
    avail_h = h - (oy - y) - hdr_h
    # Fill height but cap rows at 90px so short-content rows don't look hollow
    row_h   = max(36, min(90, avail_h // max(len(rows), 1)))
    text_h  = row_h - 12

    # ── Column headers ──
    p.append(_d(x, oy, w, hdr_h, f"background:{accent};border-radius:4px 4px 0 0;"))
    for ci, ch in enumerate(cols):
        cx2 = x + label_w + ci * col_w
        p.append(_d(cx2, oy + 6, col_w - 8, hdr_h - 12,
            "font-size:11px;font-weight:700;color:#fff;text-align:center;", _e(str(ch))))
    oy += hdr_h

    # ── Rows ──
    for ri, row in enumerate(rows):
        ry        = oy + ri * row_h
        highlight = row.get("highlight", None)
        values    = row.get("values", [])

        # Row background
        if style == "zebra":
            row_bg = GREY_BG if ri % 2 == 0 else "#fff"
        else:
            row_bg = "#fff"
        p.append(_d(x, ry, w, row_h, f"background:{row_bg};"))
        # Row separator
        p.append(_d(x, ry + row_h - 1, w, 1, f"background:{GREY_RULE};"))

        # Row label (bold, left column)
        p.append(_d(x + 10, ry + 6, label_w - 14, text_h,
            "font-size:11px;font-weight:600;color:#1A1A1A;line-height:1.4;"
            "overflow:hidden;", _e(str(row.get("label", "")))))

        # Value cells
        for ci, val in enumerate(values[:n_cols]):
            cx2   = x + label_w + ci * col_w
            is_hl = (ci == highlight)
            if is_hl:
                # Light accent tint background + accent bold text
                p.append(_d(cx2 + 2, ry + 1, col_w - 4, row_h - 2,
                    f"background:{accent}18;border-radius:3px;"))
                clr, fw = accent, "700"
            else:
                clr, fw = "#444", "400"
            p.append(_d(cx2 + 8, ry + 6, col_w - 16, text_h,
                f"font-size:10.5px;font-weight:{fw};color:{clr};"
                f"line-height:1.4;overflow:hidden;", _e(str(val))))

    return "\n".join(p)


# ── Gantt chart ────────────────────────────────────────────────────────────────
def render_gantt(block, x, y, w, h, accent=PETROL):
    """
    x_labels: ["Q1", "Q2", ...] — time columns
    rows: [{label, start: float, end: float, bar_label: str, color: hex}]
    milestones: [{label, at: float}]
    title: str
    """
    title      = block.get("title", "")
    x_labels   = block.get("x_labels", [])
    rows       = block.get("rows", [])
    milestones = block.get("milestones", [])

    n_col = len(x_labels)
    n_row = len(rows)
    if n_col == 0 or n_row == 0: return ""

    T, B, L = (22 if title else 4), 10, 130
    hdr_h   = 22
    ms_h    = 20 if milestones else 0   # space for milestone labels at bottom
    cx, cy  = L, T + hdr_h
    cw      = w - L - 6
    ch      = h - T - hdr_h - B - ms_h
    row_h   = ch / n_row                # fill available height — no cap
    col_w   = cw / n_col

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    # Throttle x-axis labels when too many columns to avoid crowding
    label_step = 1 if n_col <= 8 else (2 if n_col <= 14 else 3)

    # Column headers + vertical rules
    for i, lbl in enumerate(x_labels):
        gx = cx + i * col_w
        ln.append(f'<line x1="{gx:.1f}" y1="{cy}" x2="{gx:.1f}" y2="{cy + n_row * row_h}" stroke="{GREY_RULE}" stroke-width="1"/>')
        if i % label_step == 0:
            hx = cx + i * col_w + col_w / 2
            ln.append(_txt(hx, T + hdr_h - 6, lbl, 9, 700, GREY_TEXT, "middle"))

    # Row bars — start/end are 0–1 fractions of the FULL timeline width
    for ri, row in enumerate(rows):
        ry    = cy + ri * row_h
        bar_y = ry + row_h * 0.22
        bar_h = row_h * 0.56

        ln.append(_txt(cx - 6, ry + row_h / 2 + 4, row.get("label", ""), 9, 400, GREY_TEXT, "end"))

        if ri % 2 == 0:
            ln.append(f'<rect x="{cx}" y="{ry}" width="{cw}" height="{row_h}" fill="{GREY_BG}"/>')

        s, e  = row.get("start", 0), row.get("end", 1)
        color = row.get("color") or SERIES_COLORS[ri % len(SERIES_COLORS)]
        bx_r  = cx + s * cw           # fraction of full chart width
        bw_r  = (e - s) * cw
        ln.append(f'<rect x="{bx_r:.1f}" y="{bar_y:.1f}" width="{max(bw_r, 2):.1f}" height="{bar_h:.1f}" fill="{color}" rx="3"/>')

        if row.get("bar_label"):
            ln.append(_txt(bx_r + bw_r / 2, bar_y + bar_h / 2 + 4,
                           row["bar_label"], 9, 700, "#fff", "middle"))

    # Milestones — small diamonds sitting on the chart top boundary
    for ms in milestones:
        mx  = cx + ms["at"] * cw      # fraction of full chart width
        my0 = cy
        r   = 4           # half-size (was 5/6 — smaller so header stays clear)
        ln.append(f'<polygon points="{mx},{my0-r} {mx+r},{my0} {mx},{my0+r} {mx-r},{my0}" fill="{accent}"/>')
        if ms.get("label"):
            ln.append(_txt(mx, cy + n_row * row_h + 14, ms["label"], 9, 400, accent, "middle"))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Waterfall chart ────────────────────────────────────────────────────────────
def render_waterfall(block, x, y, w, h, accent=PETROL):
    """
    bars: [{label, value, type: "start"|"positive"|"negative"|"total"}]
    fmt: str
    show_values: bool
    title: str
    """
    bars      = block.get("bars", [])
    fmt       = block.get("fmt", "auto")
    show_vals = block.get("show_values", True)
    title     = block.get("title", "")

    n_bars = len(bars)
    B = 80 if n_bars >= 8 else 38   # extra room for rotated labels
    T, L, R = (22 if title else 4), 50, 8
    cw, ch = w - L - R, h - T - B
    cx, cy = L, T

    running  = 0
    computed = []
    all_y    = []
    for b in bars:
        v     = b.get("value", 0)
        btype = b.get("type", "positive" if v >= 0 else "negative")
        if btype == "start":
            sy, ey = 0, v
            running = v
        elif btype == "total":
            sy, ey = 0, v
        else:
            sy, ey = running, running + v
            running = ey
        computed.append({"label": b.get("label", ""), "value": v,
                         "type": btype, "sy": sy, "ey": ey})
        all_y.extend([sy, ey])

    y_max = _nice_max(max(all_y)) if all_y else 10

    # Smart y-axis floor: if all non-zero running values sit above 15% of y_max,
    # zoom in so the bridge bars are visible instead of tiny slivers at the top.
    running_vals = [b["ey"] for b in computed]
    running_vals += [b["sy"] for b in computed if b["sy"] > 0]
    running_min = min(running_vals) if running_vals else 0
    if running_min > 0.15 * y_max:
        raw_floor = running_min * 0.92
        mag = 10 ** math.floor(math.log10(raw_floor)) if raw_floor > 0 else 1
        y_min = math.floor(raw_floor / mag) * mag
    else:
        y_min = min(0, min(all_y)) if all_y else 0

    def vy(v): return cy + ch - (v - y_min) / (y_max - y_min) * ch

    n    = len(computed)
    slot = cw / n
    bw   = slot * 0.6

    ln = []
    if title:
        ln.append(_txt(w / 2, 15, title, 11, 700, GREY_TEXT, "middle"))

    for k in range(5):
        gv = y_min + k * (y_max - y_min) / 4
        gy = vy(gv)
        ln.append(f'<line x1="{cx}" y1="{gy:.1f}" x2="{cx+cw}" y2="{gy:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')
        ln.append(_txt(cx - 4, gy + 4, _fmt(gv, fmt), 9, 400, GREY_SUB, "end"))

    # Zero baseline only if 0 is visible in the y range
    if y_min <= 0 <= y_max:
        ln.append(f'<line x1="{cx}" y1="{vy(0):.1f}" x2="{cx+cw}" y2="{vy(0):.1f}" stroke="#999" stroke-width="1.5"/>')
    # Always show the chart floor axis
    ln.append(f'<line x1="{cx}" y1="{cy+ch:.1f}" x2="{cx+cw}" y2="{cy+ch:.1f}" stroke="{GREY_RULE}" stroke-width="1"/>')

    prev_ey = None
    for i, b in enumerate(computed):
        bx  = cx + i * slot + (slot - bw) / 2
        # Start/total bars draw from the chart floor (y_min) when axis is zoomed
        sy_draw = y_min if (b["type"] in ("start", "total") and y_min > 0) else b["sy"]
        top = vy(max(sy_draw, b["ey"]))
        bot = vy(min(sy_draw, b["ey"]))
        bh  = max(bot - top, 2)

        color = (PETROL_DARK if b["type"] == "total" else
                 PETROL_MED  if b["type"] == "start"  else
                 PETROL_LT   if b["value"] >= 0        else "#C62828")

        if prev_ey is not None and b["type"] not in ("start", "total"):
            ln.append(f'<line x1="{bx - (slot-bw)/2:.1f}" y1="{prev_ey:.1f}" '
                      f'x2="{bx:.1f}" y2="{prev_ey:.1f}" stroke="#aaa" stroke-width="1" stroke-dasharray="3 2"/>')

        ln.append(f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}"/>')

        if b["type"] not in ("start", "total"):
            prev_ey = vy(b["ey"])

        if show_vals:
            sign = "+" if b["value"] > 0 and b["type"] not in ("start", "total") else ""
            ln.append(_txt(bx + bw / 2, top - 4, f"{sign}{_fmt(b['value'], fmt)}", 9, 400, GREY_TEXT, "middle"))

        lx_lbl = bx + bw / 2
        ly_lbl = cy + ch + 12
        if n_bars >= 8:
            ln.append(f'<text x="{lx_lbl:.1f}" y="{ly_lbl}" '
                      f'transform="rotate(-40 {lx_lbl:.1f} {ly_lbl})" '
                      f'font-size="8" fill="{GREY_SUB}" text-anchor="end">'
                      f'{_e(b["label"])}</text>')
        else:
            ln.append(_txt(lx_lbl, ly_lbl + 4, b["label"], 9, 400, GREY_SUB, "middle"))

    return _d(x, y, w, h, "", _svg(w, h, "\n".join(ln)))


# ── Process flow ───────────────────────────────────────────────────────────────
def render_process_flow(block, x, y, w, h, accent=PETROL):
    """
    steps: [{icon, label, sub}]
    direction: "horizontal" (default) | "vertical"
    """
    steps = block.get("steps", [])
    if not steps: return ""

    direction = block.get("direction", "horizontal")
    n = len(steps)
    p = []

    if direction == "horizontal":
        # Timeline layout: horizontal connector line + badges + text below
        step_w   = w // n
        badge_r  = 20           # badge radius
        badge_d  = badge_r * 2
        line_y   = y + badge_r  # vertical position of the timeline line
        text_y   = line_y + badge_r + 18  # text starts below badges

        # Full-width connector line (behind badges)
        p.append(_d(x, line_y - 1, w, 2, f"background:{accent};opacity:0.25;"))

        for i, step in enumerate(steps):
            cx_step = x + i * step_w + step_w // 2  # center x of this step
            bx      = cx_step - badge_r
            col_w2  = step_w - 16

            # Connector segment — solid line from this badge to next
            if i < n - 1:
                line_start = cx_step + badge_r
                line_end   = x + (i + 1) * step_w + step_w // 2 - badge_r
                p.append(_d(line_start, line_y - 1, line_end - line_start, 2,
                    f"background:{accent};opacity:0.5;"))
                # Arrowhead at midpoint
                mid = (line_start + line_end) // 2
                p.append(_d(mid - 5, line_y - 6, 0, 0,
                    f"border-top:6px solid transparent;border-bottom:6px solid transparent;"
                    f"border-left:9px solid {accent};width:0;height:0;opacity:0.6;"))

            # Badge circle
            p.append(_d(bx, line_y - badge_r, badge_d, badge_d,
                f"background:{accent};border-radius:50%;font-size:13px;font-weight:700;"
                f"color:#fff;text-align:center;line-height:{badge_d}px;",
                _e(step.get("icon", str(i + 1)))))

            # Label — centered under badge
            lx = x + i * step_w + 8
            p.append(_d(lx, text_y, col_w2, 34,
                "font-size:12px;font-weight:700;color:#1A1A1A;line-height:1.3;"
                "text-align:center;",
                _e(step.get("label", ""))))

            # Sub text — centered, flows for remaining space
            if step.get("sub"):
                sub_y = text_y + 38
                sub_h = max(60, h - (sub_y - y) - 8)
                p.append(_d(lx, sub_y, col_w2, sub_h,
                    "font-size:10.5px;color:#555;line-height:1.55;overflow:hidden;"
                    "text-align:center;",
                    _e(step["sub"])))
    else:
        step_h = min((h - 10) // n, 110)
        for i, step in enumerate(steps):
            sy2 = y + i * step_h + 5
            sx2 = x
            p.append(_d(sx2, sy2, w, step_h - 6,
                f"background:{GREY_BG};border-radius:6px;border-left:4px solid {accent};"))
            p.append(_d(sx2 + 12, sy2 + 8, 28, 28,
                f"background:{accent};border-radius:50%;font-size:13px;font-weight:700;"
                f"color:#fff;text-align:center;line-height:28px;",
                _e(step.get("icon", str(i + 1)))))
            p.append(_d(sx2 + 50, sy2 + 8, w - 70, 22,
                "font-size:12px;font-weight:700;color:#1A1A1A;", _e(step.get("label", ""))))
            if step.get("sub"):
                p.append(_d(sx2 + 50, sy2 + 30, w - 70, 50,
                    "font-size:11px;color:#666;line-height:1.4;", _e(step["sub"])))

    return "\n".join(p)
