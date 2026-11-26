import html
import os
import re
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_STACK = "Hind Siliguri, Noto Sans Bengali, Noto Sans, sans-serif"

FONT_CANDIDATES = [
    REPO_ROOT / "assets" / "fonts" / "HindSiliguri-Bold.ttf",
    Path("/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansBengali-Bold.ttf"),
    Path("/usr/share/fonts/truetype/beng/kalpurush.ttf"),
]

THEME_PALETTES = {
    "crimson_noir": {
        "bg1": "#09090b", "bg2": "#1c060b", "accent": "#dc2626",
        "accent2": "#ffffff", "text": "#ffffff", "muted": "#e4e4e7",
        "card_bg": "#141418", "pill_bg": "#18181b", "is_light": False,
    },
    "cinematic_dark": {
        "bg1": "#08101c", "bg2": "#0f2035", "accent": "#facc15",
        "accent2": "#38bdf8", "text": "#f8fafc", "muted": "#cbd5e1",
        "card_bg": "#0f172a", "pill_bg": "#1e293b", "is_light": False,
    },
    "vox_colorful": {
        "bg1": "#fef08a", "bg2": "#fde047", "accent": "#dc2626",
        "accent2": "#111827", "text": "#111827", "muted": "#374151",
        "card_bg": "#ffffff", "pill_bg": "#111827", "is_light": True,
    },
    "editorial_paper": {
        "bg1": "#f6f1e7", "bg2": "#ebe2d2", "accent": "#d97706",
        "accent2": "#0f766e", "text": "#1c1917", "muted": "#57534e",
        "card_bg": "#fffdf9", "pill_bg": "#1c1917", "is_light": True,
    },
    "vibrant_gradient": {
        "bg1": "#1e1b4b", "bg2": "#4c1d95", "accent": "#22d3ee",
        "accent2": "#f472b6", "text": "#ffffff", "muted": "#e0e7ff",
        "card_bg": "#1e1b4b", "pill_bg": "#0f172a", "is_light": False,
    },
    "minimal_light": {
        "bg1": "#f8fafc", "bg2": "#e2e8f0", "accent": "#2563eb",
        "accent2": "#10b981", "text": "#0f172a", "muted": "#475569",
        "card_bg": "#ffffff", "pill_bg": "#0f172a", "is_light": True,
    },
}


def _strip_chapter_and_hindi(text: str) -> str:
    s = re.sub(r"[\u0900-\u097F]+", "", str(text or ""))
    s = re.sub(r"^\s*অধ্যায়\s*[\d০-৯]+\s*(?://|[-–—:])?\s*", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def _esc(text: str) -> str:
    return html.escape(_strip_chapter_and_hindi(text))


def _wrap_text(text: str, max_chars=26):
    cleaned = _strip_chapter_and_hindi(text)
    words = cleaned.split()
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


def _find_font_path():
    for p in FONT_CANDIDATES:
        if p.exists():
            return str(p)
    return None


def _render_svg_to_png(svg_content: str, png_path: Path, transparent: bool = False) -> Path:
    svg_path = png_path.with_suffix(".svg")
    svg_path.write_text(svg_content, encoding="utf-8")

    if shutil.which("rsvg-convert"):
        proc = subprocess.run(
            ["rsvg-convert", "-w", "1920", "-h", "1080", str(svg_path), "-o", str(png_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if proc.returncode == 0 and png_path.exists() and png_path.stat().st_size > 500:
            return png_path

    if transparent:
        img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    else:
        img = Image.new("RGB", (1920, 1080), (12, 12, 16))
        draw = ImageDraw.Draw(img)
        font_path = _find_font_path()
        font = ImageFont.truetype(font_path, 56) if font_path else ImageFont.load_default()
        draw.rectangle([140, 260, 280, 270], fill=(220, 38, 38))
        draw.text((140, 310), "ডকুমেন্টারি তথ্য", fill=(255, 255, 255), font=font)
    img.save(png_path)
    return png_path


def _build_stock_overlay_svg(scene: dict, palette: dict):
    if scene.get("rapid_cut"):
        return None
    g = scene.get("graphic") or {}
    heading = _strip_chapter_and_hindi(g.get("heading") or scene.get("overlay_headline") or "")
    subheading = _strip_chapter_and_hindi(g.get("subheading") or scene.get("overlay_subtext") or "")
    items = [_strip_chapter_and_hindi(x) for x in (g.get("items") or []) if _strip_chapter_and_hindi(x)][:3]

    if not heading and not items:
        return None

    accent = "#dc2626" if scene.get("accent") == "red" or palette == THEME_PALETTES["crimson_noir"] else palette["accent"]
    box_fill = palette["card_bg"]
    pill_bg = palette["pill_bg"]
    stroke_col = "#000000" if palette["is_light"] else "#ffffff"

    parts = []

    if heading:
        h_lines = _wrap_text(heading, 28)
        main_h = h_lines[0]
        box_w = max(560, min(1480, len(main_h) * 34 + 140))
        box_x = (1920 - box_w) // 2
        box_h = 148 if subheading else 104
        parts.append(
            f'<rect x="{box_x}" y="48" width="{box_w}" height="{box_h}" rx="20" '
            f'fill="{box_fill}" fill-opacity="0.90" stroke="{stroke_col}" stroke-opacity="0.18" stroke-width="2"/>'
        )
        parts.append(
            f'<rect x="{box_x + 26}" y="72" width="10" height="{box_h - 48}" rx="5" fill="{accent}"/>'
        )
        parts.append(
            f'<text x="{box_x + 56}" y="114" fill="{palette["text"]}" '
            f'font-family="{FONT_STACK}" font-size="44" font-weight="700">{_esc(main_h)}</text>'
        )
        if subheading:
            parts.append(
                f'<text x="{box_x + 56}" y="144" fill="{accent}" '
                f'font-family="{FONT_STACK}" font-size="28" font-weight="600">{_esc(subheading[:44])}</text>'
            )

    if items:
        cur_x = 110
        pill_y = 890
        pill_h = 68
        for it in items:
            label = it[:24]
            pill_w = max(230, min(520, len(label) * 26 + 92))
            if cur_x + pill_w > 1810:
                break
            parts.append(
                f'<rect x="{cur_x}" y="{pill_y}" width="{pill_w}" height="{pill_h}" rx="34" '
                f'fill="{pill_bg}" fill-opacity="0.92" stroke="{accent}" stroke-width="2.5"/>'
            )
            parts.append(
                f'<circle cx="{cur_x + 30}" cy="{pill_y + pill_h // 2}" r="8" fill="{accent}"/>'
            )
            parts.append(
                f'<text x="{cur_x + 52}" y="{pill_y + 44}" fill="#ffffff" '
                f'font-family="{FONT_STACK}" font-size="30" font-weight="700">{_esc(label)}</text>'
            )
            cur_x += pill_w + 22

    if not parts:
        return None

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">\n'
        f'  {"".join(parts)}\n'
        f'</svg>'
    )


def _build_infographic_svg(scene: dict, palette: dict) -> str:
    g = scene.get("graphic") or {}
    kind = g.get("kind") or "title_card"
    heading = _strip_chapter_and_hindi(g.get("heading") or scene.get("overlay_headline") or "মূল তথ্য")
    subheading = _strip_chapter_and_hindi(g.get("subheading") or scene.get("overlay_subtext") or "")
    items = [_strip_chapter_and_hindi(x) for x in (g.get("items") or []) if _strip_chapter_and_hindi(x)][:4]
    accent = "#dc2626" if scene.get("accent") == "red" or palette == THEME_PALETTES["crimson_noir"] else palette["accent"]

    h_lines = _wrap_text(heading, 24)
    heading_svg = "".join(
        f'<text x="140" y="{250 + i * 86}" fill="{palette["text"]}" '
        f'font-family="{FONT_STACK}" font-size="68" font-weight="700">{_esc(line)}</text>'
        for i, line in enumerate(h_lines)
    )
    next_y = 250 + len(h_lines) * 86 + 18
    sub_svg = ""
    if subheading:
        sub_svg = (
            f'<text x="140" y="{next_y}" fill="{accent}" '
            f'font-family="{FONT_STACK}" font-size="36" font-weight="600">{_esc(subheading[:48])}</text>'
        )
        next_y += 64

    body_svg = ""
    if kind == "stat_chart" and items:
        rows = []
        for idx, raw_item in enumerate(items[:4]):
            parts = re.split(r"[:\-—]", raw_item, maxsplit=1)
            lbl = parts[0].strip()[:24] or f"তথ্য {idx + 1}"
            num_m = re.search(r"(\d+(?:\.\d+)?)", raw_item)
            pct = min(100.0, max(18.0, float(num_m.group(1)))) if num_m else min(95.0, 35.0 + idx * 18.0)
            val_txt = parts[1].strip()[:14] if len(parts) > 1 and parts[1].strip() else f"{int(pct)}%"
            ry = next_y + 16 + idx * 112
            bar_w = int((pct / 100.0) * 1150)
            rows.append(
                f'<text x="140" y="{ry}" fill="{palette["text"]}" font-family="{FONT_STACK}" font-size="32" font-weight="700">{_esc(lbl)}</text>'
                f'<text x="1310" y="{ry}" text-anchor="end" fill="{accent}" font-family="{FONT_STACK}" font-size="32" font-weight="700">{_esc(val_txt)}</text>'
                f'<rect x="140" y="{ry + 14}" width="1170" height="28" rx="14" fill="{palette["card_bg"]}" stroke="{accent}" stroke-opacity="0.35" stroke-width="2"/>'
                f'<rect x="140" y="{ry + 14}" width="{bar_w}" height="28" rx="14" fill="{accent}"/>'
            )
        body_svg = "".join(rows)
    elif items:
        pills_svg = []
        px = 140
        py = next_y + 20
        for it in items[:4]:
            txt = it[:26]
            pw = max(280, min(620, len(txt) * 28 + 110))
            if px + pw > 1760:
                px = 140
                py += 92
            if py > 920:
                break
            pills_svg.append(
                f'<rect x="{px}" y="{py}" width="{pw}" height="72" rx="36" '
                f'fill="{palette["pill_bg"]}" stroke="{accent}" stroke-width="2.5"/>'
                f'<circle cx="{px + 34}" cy="{py + 36}" r="10" fill="{accent}"/>'
                f'<text x="{px + 58}" y="{py + 47}" fill="#ffffff" font-family="{FONT_STACK}" font-size="32" font-weight="700">{_esc(txt)}</text>'
            )
            px += pw + 24
        body_svg = "".join(pills_svg)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette["bg1"]}"/>
      <stop offset="100%" stop-color="{palette["bg2"]}"/>
    </linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#bgGrad)"/>
  <rect x="140" y="165" width="140" height="9" rx="4.5" fill="{accent}"/>
  {heading_svg}
  {sub_svg}
  {body_svg}
</svg>"""


def _render_animated_infographic_mp4(png_path: Path, out_mp4: Path, duration: float, scene_id: int) -> Path:
    dur = max(1.5, float(duration))
    frames = max(45, int(round(dur * 30)))
    if scene_id % 2 == 1:
        zp = f"zoompan=z='min(zoom+0.0005,1.07)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
    else:
        zp = f"zoompan=z='zoom+0.0004':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(png_path),
        "-t", f"{dur:.3f}",
        "-an",
        "-vf", f"{zp},format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_mp4)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0 or not out_mp4.exists():
        raise RuntimeError(f"Infographic video render failed: {proc.stderr[-800:]}")
    return out_mp4


def create_motion_graphics(scene_plan: dict) -> dict:
    update_status("creating_graphics", "FFmpeg + Pillow অ্যানিমেটেড ইনফোগ্রাফিক্স ও পিল ওভারলে তৈরি হচ্ছে...", percent=70)

    gfx_dir = WORK / "graphics"
    gfx_dir.mkdir(parents=True, exist_ok=True)
    video_theme = (
        os.environ.get("VIDEO_THEME", "").strip()
        or scene_plan.get("video_theme", "")
        or "crimson_noir"
    )
    if video_theme not in THEME_PALETTES:
        video_theme = "crimson_noir"
    palette = THEME_PALETTES[video_theme]

    graphic_count = 0
    overlay_count = 0

    for scene in scene_plan.get("scenes", []):
        sid = int(scene["scene_id"])
        scene["graphic_video_path"] = None
        scene["graphic_path"] = None
        scene["overlay_path"] = None
        dur = max(1.5, float(scene.get("duration") or (float(scene.get("end", 5.0)) - float(scene.get("start", 0.0)))))

        if scene.get("visual_type") == "motion_graphic" or not scene.get("footage_path"):
            card_png = gfx_dir / f"infographic_{sid:03d}.png"
            out_mp4 = gfx_dir / f"graphic_{sid:03d}.mp4"
            svg = _build_infographic_svg(scene, palette)
            _render_svg_to_png(svg, card_png, transparent=False)
            _render_animated_infographic_mp4(card_png, out_mp4, dur, sid)
            scene["graphic_video_path"] = str(out_mp4)
            scene["graphic_path"] = str(card_png)
            graphic_count += 1
        else:
            ov_svg = _build_stock_overlay_svg(scene, palette)
            if ov_svg:
                ov_path = gfx_dir / f"overlay_{sid:03d}.png"
                _render_svg_to_png(ov_svg, ov_path, transparent=True)
                scene["overlay_path"] = str(ov_path)
                overlay_count += 1

    update_status(
        "creating_graphics",
        f"FFmpeg + Pillow এ {graphic_count}টি ইনফোগ্রাফিক ও {overlay_count}টি পিল/ব্যাজ ওভারলে তৈরি সম্পন্ন।",
        percent=76,
    )
    return scene_plan
