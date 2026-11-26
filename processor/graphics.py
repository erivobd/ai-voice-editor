import html
import os
import re
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
FONT_STACK = "Hind Siliguri, Noto Sans Bengali, Noto Sans, sans-serif"

PALETTES = {
    "cinematic_teal": {"bg1": "#08101c", "bg2": "#0f2035", "accent": "#facc15", "accent2": "#38bdf8", "text": "#f8fafc", "muted": "#cbd5e1"},
    "warm_history": {"bg1": "#140e0a", "bg2": "#281b12", "accent": "#facc15", "accent2": "#ef4444", "text": "#fdf6ea", "muted": "#d6c5ad"},
    "cool_science": {"bg1": "#090f20", "bg2": "#132042", "accent": "#facc15", "accent2": "#38bdf8", "text": "#f1f5f9", "muted": "#a8bddb"},
    "neutral_doc": {"bg1": "#0b1120", "bg2": "#172033", "accent": "#facc15", "accent2": "#ef4444", "text": "#f8fafc", "muted": "#94a3b8"}
}


def _esc(text):
    return html.escape(str(text or ""))


def _wrap_text(text, max_chars=30):
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


def _render_svg_to_png(svg_content, png_path, transparent=False):
    svg_path = png_path.with_suffix(".svg")
    svg_path.write_text(svg_content, encoding="utf-8")

    if shutil.which("rsvg-convert"):
        proc = subprocess.run(
            ["rsvg-convert", "-w", "1920", "-h", "1080", str(svg_path), "-o", str(png_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if proc.returncode == 0 and png_path.exists():
            return png_path

    if transparent:
        img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    else:
        img = Image.new("RGB", (1920, 1080), (11, 17, 32))
        draw = ImageDraw.Draw(img)
        draw.rectangle([120, 480, 1800, 488], fill=(250, 204, 21))
    img.save(png_path)
    return png_path


def _build_stock_overlay_svg(scene, palette):
    """Sample-style transparent dark frosted glass callout card or top headline over stock footage."""
    g = scene.get("graphic") or {}
    heading = (g.get("heading") or scene.get("overlay_headline") or "").strip()
    subheading = (g.get("subheading") or scene.get("overlay_subtext") or "").strip()
    if not heading:
        return None

    accent = "#ef4444" if scene.get("accent") == "red" else palette["accent"]
    sid = int(scene.get("scene_id", 1))

    # Alternate between top headline banner and top-left frosted callout card (keeps bottom free for subtitles)
    if sid % 2 == 1:
        sub_svg = ""
        if subheading:
            sub_svg = (
                f'<text x="960" y="182" text-anchor="middle" fill="{accent}" '
                f'font-family="{FONT_STACK}" font-size="34" font-weight="600">{_esc(subheading[:54])}</text>'
            )
        box_h = 152 if subheading else 104
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect x="260" y="56" width="1400" height="{box_h}" rx="20" fill="#0b1120" fill-opacity="0.78" stroke="#ffffff" stroke-opacity="0.16" stroke-width="2"/>
  <rect x="900" y="56" width="120" height="6" rx="3" fill="{accent}"/>
  <text x="960" y="128" text-anchor="middle" fill="{palette["text"]}" font-family="{FONT_STACK}" font-size="52" font-weight="700">{_esc(heading[:42])}</text>
  {sub_svg}
</svg>"""
    else:
        sub_svg = ""
        if subheading:
            sub_svg = (
                f'<text x="128" y="182" fill="{accent}" '
                f'font-family="{FONT_STACK}" font-size="30" font-weight="600">{_esc(subheading[:48])}</text>'
            )
        box_h = 160 if subheading else 110
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect x="84" y="68" width="900" height="{box_h}" rx="18" fill="#0f172a" fill-opacity="0.84" stroke="#ffffff" stroke-opacity="0.18" stroke-width="2"/>
  <rect x="84" y="88" width="10" height="{box_h - 40}" rx="5" fill="{accent}"/>
  <text x="128" y="132" fill="{palette["text"]}" font-family="{FONT_STACK}" font-size="42" font-weight="700">{_esc(heading[:38])}</text>
  {sub_svg}
</svg>"""


def _build_svg_card(scene, palette):
    g = scene.get("graphic") or {}
    kind = g.get("kind", "title_card")
    heading = g.get("heading") or scene.get("overlay_headline") or "ডকুমেন্টারি তথ্য"
    subheading = g.get("subheading") or scene.get("overlay_subtext") or ""
    items = g.get("items") or []

    accent = "#ef4444" if scene.get("accent") == "red" else palette["accent"]
    accent2 = palette.get("accent2", "#38bdf8")

    h_lines = _wrap_text(heading, 28)
    sub_lines = _wrap_text(subheading, 48)

    body_svg = []
    if kind == "timeline" and items:
        body_svg.append(
            '<rect x="160" y="560" width="1600" height="330" rx="24" fill="#0f172a" fill-opacity="0.82" '
            'stroke="#ffffff" stroke-opacity="0.14" stroke-width="2"/>'
        )
        body_svg.append(f'<line x1="260" y1="700" x2="1660" y2="700" stroke="{accent}" stroke-width="6" opacity="0.85"/>')
        step = 1320 // max(1, len(items[:4]) - 1) if len(items[:4]) > 1 else 0
        for i, item in enumerate(items[:4]):
            cx = 300 + i * step if len(items[:4]) > 1 else 960
            body_svg.append(f'<circle cx="{cx}" cy="700" r="18" fill="{accent}"/>')
            body_svg.append(f'<circle cx="{cx}" cy="700" r="32" fill="none" stroke="{accent}" stroke-width="3" opacity="0.4"/>')
            body_svg.append(
                f'<text x="{cx}" y="785" text-anchor="middle" fill="{palette["text"]}" '
                f'font-family="{FONT_STACK}" font-size="32" font-weight="600">{_esc(str(item)[:26])}</text>'
            )
    elif kind == "map_marker":
        body_svg.append(f'<circle cx="1440" cy="540" r="245" fill="none" stroke="{accent2}" stroke-width="2" opacity="0.25"/>')
        body_svg.append(f'<circle cx="1440" cy="540" r="155" fill="none" stroke="{accent}" stroke-width="2.5" opacity="0.45"/>')
        body_svg.append(f'<circle cx="1440" cy="540" r="68" fill="{accent}" opacity="0.22"/>')
        body_svg.append(f'<circle cx="1440" cy="540" r="18" fill="{accent}"/>')
        body_svg.append(f'<line x1="1150" y1="540" x2="1730" y2="540" stroke="{accent2}" stroke-width="2" opacity="0.2"/>')
        body_svg.append(f'<line x1="1440" y1="250" x2="1440" y2="830" stroke="{accent2}" stroke-width="2" opacity="0.2"/>')
        if items:
            body_svg.append(
                '<rect x="160" y="620" width="900" height="260" rx="20" fill="#0f172a" fill-opacity="0.82" '
                'stroke="#ffffff" stroke-opacity="0.14" stroke-width="2"/>'
            )
            body_svg.append(f'<rect x="160" y="644" width="10" height="212" rx="5" fill="{accent}"/>')
            for i, it in enumerate(items[:3]):
                body_svg.append(
                    f'<text x="210" y="{695 + i * 66}" fill="{palette["text"]}" '
                    f'font-family="{FONT_STACK}" font-size="34" font-weight="600">● {_esc(it)}</text>'
                )
    elif kind == "stat_chart" and items:
        parsed = []
        for it in items[:4]:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(it))
            val = float(m.group(1)) if m else float((len(parsed) + 1) * 25)
            label = re.sub(r"[:\-]?\s*[0-9]+(?:\.[0-9]+)?%?", "", str(it)).strip() or str(it)
            parsed.append((label[:30], val))
        max_val = max(p[1] for p in parsed) or 1.0
        card_h = 80 + len(parsed) * 102
        body_svg.append(
            f'<rect x="160" y="530" width="1600" height="{card_h}" rx="24" fill="#0f172a" fill-opacity="0.86" '
            'stroke="#ffffff" stroke-opacity="0.16" stroke-width="2"/>'
        )
        body_svg.append(f'<rect x="160" y="556" width="10" height="{card_h - 52}" rx="5" fill="{accent}"/>')
        for i, (lbl, val) in enumerate(parsed):
            y = 595 + i * 96
            bar_w = max(140, int((val / max_val) * 1020))
            bar_col = accent if i == len(parsed) - 1 else accent2
            body_svg.append(
                f'<text x="215" y="{y}" fill="{palette["text"]}" '
                f'font-family="{FONT_STACK}" font-size="32" font-weight="600">{_esc(lbl)}</text>'
            )
            body_svg.append(f'<rect x="215" y="{y + 18}" width="1180" height="26" rx="13" fill="#ffffff" opacity="0.12"/>')
            body_svg.append(f'<rect x="215" y="{y + 18}" width="{bar_w}" height="26" rx="13" fill="{bar_col}"/>')
            body_svg.append(
                f'<text x="{215 + bar_w + 26}" y="{y + 42}" fill="{bar_col}" '
                f'font-family="{FONT_STACK}" font-size="32" font-weight="700">{val:g}</text>'
            )
    else:
        if items:
            card_h = 70 + len(items[:3]) * 70
            body_svg.append(
                f'<rect x="160" y="630" width="1360" height="{card_h}" rx="22" fill="#0f172a" fill-opacity="0.84" '
                'stroke="#ffffff" stroke-opacity="0.15" stroke-width="2"/>'
            )
            body_svg.append(f'<rect x="160" y="652" width="10" height="{card_h - 44}" rx="5" fill="{accent}"/>')
            for i, it in enumerate(items[:3]):
                body_svg.append(
                    f'<text x="210" y="{698 + i * 66}" fill="{palette["text"]}" '
                    f'font-family="{FONT_STACK}" font-size="34" font-weight="600">— {_esc(it)}</text>'
                )

    heading_svg = []
    for i, line in enumerate(h_lines):
        heading_svg.append(
            f'<text x="160" y="{310 + i * 94}" fill="{palette["text"]}" '
            f'font-family="{FONT_STACK}" font-size="76" font-weight="700">{_esc(line)}</text>'
        )

    sub_y = 310 + len(h_lines) * 94 + 22
    sub_svg = []
    for i, line in enumerate(sub_lines):
        sub_svg.append(
            f'<text x="160" y="{sub_y + i * 54}" fill="{accent}" '
            f'font-family="{FONT_STACK}" font-size="38" font-weight="600">{_esc(line)}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette["bg1"]}"/>
      <stop offset="100%" stop-color="{palette["bg2"]}"/>
    </linearGradient>
    <pattern id="grid" width="64" height="64" patternUnits="userSpaceOnUse">
      <path d="M 64 0 L 0 0 0 64" fill="none" stroke="#38bdf8" stroke-width="1" opacity="0.08"/>
    </pattern>
  </defs>
  <rect width="1920" height="1080" fill="url(#bg)"/>
  <rect width="1920" height="1080" fill="url(#grid)"/>
  <rect x="44" y="44" width="1832" height="992" rx="22" fill="none" stroke="#38bdf8" stroke-opacity="0.18" stroke-width="2"/>
  <rect x="160" y="195" width="120" height="8" rx="4" fill="{accent}"/>
  <text x="160" y="168" fill="{accent2}" font-family="{FONT_STACK}" font-size="24" letter-spacing="4" font-weight="700">DOCUMENTARY ANALYSIS</text>
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
            _render_svg_to_png(svg, png_path, transparent=False)
            scene["graphic_path"] = str(png_path)
            scene["overlay_path"] = None
            created += 1
        else:
            scene["graphic_path"] = None
            ov_svg = _build_stock_overlay_svg(scene, palette)
            if ov_svg:
                ov_path = gfx_dir / f"overlay_{scene['scene_id']:03d}.png"
                _render_svg_to_png(ov_svg, ov_path, transparent=True)
                scene["overlay_path"] = str(ov_path)
                created += 1
            else:
                scene["overlay_path"] = None

    update_status("creating_graphics", f"{created}টি ডকুমেন্টারি গ্রাফিক্স ও ওভারলে তৈরি সম্পন্ন।", percent=76)
    return scene_plan
