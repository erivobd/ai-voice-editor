import html
import os
import re
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))

PALETTES = {
    "cinematic_teal": {"bg1": "#08141f", "bg2": "#0e2a3b", "accent": "#38d9a9", "text": "#f1f7fc", "muted": "#9cb8cc"},
    "warm_history": {"bg1": "#1b140d", "bg2": "#332415", "accent": "#e8b059", "text": "#fdf6ea", "muted": "#c9b393"},
    "cool_science": {"bg1": "#0b1024", "bg2": "#18254a", "accent": "#5aa9ff", "text": "#eef5ff", "muted": "#9eb4d6"},
    "neutral_doc": {"bg1": "#11161f", "bg2": "#1f2937", "accent": "#43d3a2", "text": "#f3f6fa", "muted": "#a3b1c2"}
}


def _esc(text):
    return html.escape(str(text or ""))


def _wrap_text(text, max_chars=34):
    words = str(text or "").split()
    lines, cur = [], []
    length = 0
    for w in words:
        if length + len(w) + (1 if cur else 0) > max_chars and cur:
            lines.append(" ".join(cur))
            cur = [w]
            length = len(w)
        else:
            cur.append(w)
            length += len(w) + (1 if cur else 0)
    if cur:
        lines.append(" ".join(cur))
    return lines[:3]


def _render_svg_to_png(svg_content, png_path):
    svg_path = png_path.with_suffix(".svg")
    svg_path.write_text(svg_content, encoding="utf-8")

    if shutil.which("rsvg-convert"):
        proc = subprocess.run(
            ["rsvg-convert", "-w", "1920", "-h", "1080", str(svg_path), "-o", str(png_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if proc.returncode == 0 and png_path.exists():
            return png_path

    img = Image.new("RGB", (1920, 1080), (14, 24, 38))
    draw = ImageDraw.Draw(img)
    draw.rectangle([120, 480, 1800, 488], fill=(67, 211, 162))
    img.save(png_path)
    return png_path


def _build_svg_card(scene, palette):
    g = scene.get("graphic") or {}
    kind = g.get("kind", "title_card")
    heading = g.get("heading") or "Documentary"
    subheading = g.get("subheading") or ""
    items = g.get("items") or []

    h_lines = _wrap_text(heading, 30)
    sub_lines = _wrap_text(subheading, 54)

    body_svg = []
    if kind == "timeline" and items:
        body_svg.append(f'<line x1="220" y1="680" x2="1700" y2="680" stroke="{palette["accent"]}" stroke-width="6" opacity="0.8"/>')
        step = 1360 // max(1, len(items) - 1) if len(items) > 1 else 0
        for i, item in enumerate(items[:4]):
            cx = 280 + i * step if len(items) > 1 else 960
            body_svg.append(f'<circle cx="{cx}" cy="680" r="18" fill="{palette["accent"]}"/>')
            body_svg.append(f'<circle cx="{cx}" cy="680" r="30" fill="none" stroke="{palette["accent"]}" stroke-width="3" opacity="0.45"/>')
            body_svg.append(
                f'<text x="{cx}" y="760" text-anchor="middle" fill="{palette["text"]}" '
                f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="32" font-weight="600">{_esc(item[:28])}</text>'
            )
    elif kind == "map_marker":
        body_svg.append(f'<circle cx="1420" cy="540" r="240" fill="none" stroke="{palette["accent"]}" stroke-width="2" opacity="0.25"/>')
        body_svg.append(f'<circle cx="1420" cy="540" r="150" fill="none" stroke="{palette["accent"]}" stroke-width="2" opacity="0.4"/>')
        body_svg.append(f'<circle cx="1420" cy="540" r="65" fill="{palette["accent"]}" opacity="0.22"/>')
        body_svg.append(f'<circle cx="1420" cy="540" r="18" fill="{palette["accent"]}"/>')
        body_svg.append(f'<line x1="1140" y1="540" x2="1700" y2="540" stroke="{palette["accent"]}" stroke-width="2" opacity="0.2"/>')
        body_svg.append(f'<line x1="1420" y1="260" x2="1420" y2="820" stroke="{palette["accent"]}" stroke-width="2" opacity="0.2"/>')
        for i, it in enumerate(items[:3]):
            body_svg.append(
                f'<text x="180" y="{680 + i * 58}" fill="{palette["accent"]}" '
                f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="34">● {_esc(it)}</text>'
            )
    elif kind == "stat_chart" and items:
        parsed = []
        for it in items[:4]:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(it))
            val = float(m.group(1)) if m else float((len(parsed) + 1) * 25)
            label = re.sub(r"[:\-]?\s*[0-9]+(?:\.[0-9]+)?%?", "", str(it)).strip() or str(it)
            parsed.append((label[:34], val))
        max_val = max(p[1] for p in parsed) or 1.0
        for i, (lbl, val) in enumerate(parsed):
            y = 580 + i * 95
            bar_w = max(140, int((val / max_val) * 950))
            body_svg.append(
                f'<text x="180" y="{y}" fill="{palette["text"]}" '
                f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="32">{_esc(lbl)}</text>'
            )
            body_svg.append(f'<rect x="180" y="{y + 16}" width="1100" height="28" rx="14" fill="#ffffff" opacity="0.1"/>')
            body_svg.append(f'<rect x="180" y="{y + 16}" width="{bar_w}" height="28" rx="14" fill="{palette["accent"]}"/>')
            body_svg.append(
                f'<text x="{180 + bar_w + 24}" y="{y + 40}" fill="{palette["accent"]}" '
                f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="30" font-weight="700">{val:g}</text>'
            )
    else:
        for i, it in enumerate(items[:3]):
            body_svg.append(
                f'<text x="180" y="{700 + i * 58}" fill="{palette["muted"]}" '
                f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="34">— {_esc(it)}</text>'
            )

    heading_svg = []
    for i, line in enumerate(h_lines):
        heading_svg.append(
            f'<text x="180" y="{330 + i * 90}" fill="{palette["text"]}" '
            f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="72" font-weight="700">{_esc(line)}</text>'
        )

    sub_y = 330 + len(h_lines) * 90 + 25
    sub_svg = []
    for i, line in enumerate(sub_lines):
        sub_svg.append(
            f'<text x="180" y="{sub_y + i * 52}" fill="{palette["muted"]}" '
            f'font-family="Noto Sans Bengali, Noto Sans, sans-serif" font-size="38">{_esc(line)}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette["bg1"]}"/>
      <stop offset="100%" stop-color="{palette["bg2"]}"/>
    </linearGradient>
    <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
      <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.04"/>
    </pattern>
  </defs>
  <rect width="1920" height="1080" fill="url(#bg)"/>
  <rect width="1920" height="1080" fill="url(#grid)"/>
  <rect x="180" y="210" width="110" height="8" rx="4" fill="{palette["accent"]}"/>
  <text x="180" y="185" fill="{palette["accent"]}" font-family="Noto Sans, sans-serif" font-size="24" letter-spacing="4" font-weight="700">DOCUMENTARY BRIEFING</text>
  {"".join(heading_svg)}
  {"".join(sub_svg)}
  {"".join(body_svg)}
</svg>"""


def create_motion_graphics(scene_plan):
    update_status("creating_graphics", "ইনফোগ্রাফিক্স, ম্যাপ ও মোশন গ্রাফিক্স তৈরি হচ্ছে...", percent=70)

    gfx_dir = WORK / "graphics"
    gfx_dir.mkdir(parents=True, exist_ok=True)
    palette = PALETTES.get(scene_plan.get("color_grade", "cinematic_teal"), PALETTES["cinematic_teal"])

    created = 0
    for scene in scene_plan.get("scenes", []):
        if scene.get("visual_type") == "motion_graphic" or not scene.get("footage_path"):
            png_path = gfx_dir / f"graphic_{scene['scene_id']:03d}.png"
            svg = _build_svg_card(scene, palette)
            _render_svg_to_png(svg, png_path)
            scene["graphic_path"] = str(png_path)
            created += 1
        else:
            scene["graphic_path"] = None

    update_status("creating_graphics", f"{created}টি ডকুমেন্টারি গ্রাফিক্স ও ইনফোগ্রাফিক তৈরি সম্পন্ন।", percent=76)
    return scene_plan
