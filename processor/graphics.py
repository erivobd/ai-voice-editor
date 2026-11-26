import html
import json
import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
REPO_ROOT = Path(__file__).resolve().parent.parent
REMOTION_SCRIPT = REPO_ROOT / "remotion" / "render_scenes.mjs"
FONT_STACK = "Hind Siliguri, Noto Sans Bengali, Noto Sans, sans-serif"

THEME_PALETTES = {
    "cinematic_dark": {
        "bg1": "#08101c", "bg2": "#0f2035", "accent": "#facc15",
        "accent2": "#38bdf8", "text": "#f8fafc", "muted": "#cbd5e1",
        "card_bg": "#0f172a", "is_light": False,
    },
    "vox_colorful": {
        "bg1": "#fef08a", "bg2": "#fde047", "accent": "#dc2626",
        "accent2": "#111827", "text": "#111827", "muted": "#374151",
        "card_bg": "#ffffff", "is_light": True,
    },
    "editorial_paper": {
        "bg1": "#f6f1e7", "bg2": "#ebe2d2", "accent": "#d97706",
        "accent2": "#0f766e", "text": "#1c1917", "muted": "#57534e",
        "card_bg": "#fffdf9", "is_light": True,
    },
    "vibrant_gradient": {
        "bg1": "#1e1b4b", "bg2": "#4c1d95", "accent": "#22d3ee",
        "accent2": "#f472b6", "text": "#ffffff", "muted": "#e0e7ff",
        "card_bg": "#1e1b4b", "is_light": False,
    },
    "minimal_light": {
        "bg1": "#f8fafc", "bg2": "#e2e8f0", "accent": "#2563eb",
        "accent2": "#10b981", "text": "#0f172a", "muted": "#475569",
        "card_bg": "#ffffff", "is_light": True,
    },
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
    g = scene.get("graphic") or {}
    heading = (g.get("heading") or scene.get("overlay_headline") or "").strip()
    subheading = (g.get("subheading") or scene.get("overlay_subtext") or "").strip()
    if not heading or scene.get("rapid_cut"):
        return None

    accent = "#ef4444" if scene.get("accent") == "red" else palette["accent"]
    box_fill = palette["card_bg"]
    stroke_col = "#000000" if palette["is_light"] else "#ffffff"
    sid = int(scene.get("scene_id", 1))

    if sid % 2 == 1:
        sub_svg = ""
        if subheading:
            sub_svg = (
                f'<text x="960" y="182" text-anchor="middle" fill="{accent}" '
                f'font-family="{FONT_STACK}" font-size="34" font-weight="600">{_esc(subheading[:54])}</text>'
            )
        box_h = 152 if subheading else 104
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect x="260" y="56" width="1400" height="{box_h}" rx="20" fill="{box_fill}" fill-opacity="0.88" stroke="{stroke_col}" stroke-opacity="0.16" stroke-width="2"/>
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
  <rect x="84" y="68" width="900" height="{box_h}" rx="18" fill="{box_fill}" fill-opacity="0.90" stroke="{stroke_col}" stroke-opacity="0.18" stroke-width="2"/>
  <rect x="84" y="88" width="10" height="{box_h - 40}" rx="5" fill="{accent}"/>
  <text x="128" y="132" fill="{palette["text"]}" font-family="{FONT_STACK}" font-size="42" font-weight="700">{_esc(heading[:38])}</text>
  {sub_svg}
</svg>"""


def _build_fallback_svg_card(scene, palette):
    g = scene.get("graphic") or {}
    heading = g.get("heading") or scene.get("overlay_headline") or "ডকুমেন্টারি তথ্য"
    subheading = g.get("subheading") or scene.get("overlay_subtext") or ""
    accent = "#ef4444" if scene.get("accent") == "red" else palette["accent"]
    h_lines = _wrap_text(heading, 28)
    sub_lines = _wrap_text(subheading, 48)

    heading_svg = [
        f'<text x="160" y="{340 + i * 94}" fill="{palette["text"]}" font-family="{FONT_STACK}" font-size="76" font-weight="700">{_esc(line)}</text>'
        for i, line in enumerate(h_lines)
    ]
    sub_y = 340 + len(h_lines) * 94 + 24
    sub_svg = [
        f'<text x="160" y="{sub_y + i * 54}" fill="{accent}" font-family="{FONT_STACK}" font-size="38" font-weight="600">{_esc(line)}</text>'
        for i, line in enumerate(sub_lines)
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="{palette["bg1"]}"/>
  <rect x="160" y="210" width="120" height="8" rx="4" fill="{accent}"/>
  {"".join(heading_svg)}
  {"".join(sub_svg)}
</svg>"""


def create_motion_graphics(scene_plan):
    update_status("creating_graphics", "Remotion অ্যানিমেটেড মোশন গ্রাফিক্স ও ওভারলে তৈরি হচ্ছে...", percent=70)

    gfx_dir = WORK / "graphics"
    gfx_dir.mkdir(parents=True, exist_ok=True)
    color_grade = scene_plan.get("color_grade", "cinematic_teal")
    video_theme = (
        os.environ.get("VIDEO_THEME", "").strip()
        or scene_plan.get("video_theme", "")
        or "cinematic_dark"
    )
    if video_theme not in THEME_PALETTES:
        video_theme = "cinematic_dark"
    palette = THEME_PALETTES[video_theme]

    remotion_jobs = []
    job_scene_map = {}
    overlay_count = 0

    for scene in scene_plan.get("scenes", []):
        sid = int(scene["scene_id"])
        scene["graphic_video_path"] = None
        scene["graphic_path"] = None
        scene["overlay_path"] = None

        if scene.get("visual_type") == "motion_graphic" or not scene.get("footage_path"):
            g = scene.get("graphic") or {}
            out_mp4 = gfx_dir / f"remotion_{sid:03d}.mp4"
            dur = max(1.5, float(scene.get("duration") or (float(scene.get("end", 5.0)) - float(scene.get("start", 0.0)))))
            remotion_jobs.append({
                "scene_id": sid,
                "kind": g.get("kind", "title_card"),
                "heading": g.get("heading") or scene.get("overlay_headline") or f"অধ্যায় {sid}",
                "subheading": g.get("subheading") or scene.get("overlay_subtext") or "",
                "items": g.get("items") or [],
                "accent": scene.get("accent", "gold"),
                "color_grade": color_grade,
                "video_theme": video_theme,
                "duration": round(dur, 2),
                "output_path": str(out_mp4),
            })
            job_scene_map[sid] = (scene, out_mp4)
        else:
            ov_svg = _build_stock_overlay_svg(scene, palette)
            if ov_svg:
                ov_path = gfx_dir / f"overlay_{sid:03d}.png"
                _render_svg_to_png(ov_svg, ov_path, transparent=True)
                scene["overlay_path"] = str(ov_path)
                overlay_count += 1

    remotion_ok = 0
    if remotion_jobs and REMOTION_SCRIPT.exists() and shutil.which("node"):
        jobs_json = gfx_dir / "remotion_jobs.json"
        jobs_json.write_text(json.dumps(remotion_jobs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Graphics] Launching Remotion ({video_theme}) for {len(remotion_jobs)} animated scenes...", flush=True)
        proc = subprocess.run(
            ["node", str(REMOTION_SCRIPT), str(jobs_json)],
            cwd=str(REPO_ROOT / "remotion"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        print(proc.stdout[-4000:], flush=True)
        if proc.returncode != 0:
            print(f"[ERROR] Remotion failed with exit code {proc.returncode}", flush=True)
    else:
        print(f"[WARN] Remotion skipped: script_exists={REMOTION_SCRIPT.exists()}, node={shutil.which('node')}", flush=True)

    fallback_count = 0
    for sid, (scene, out_mp4) in job_scene_map.items():
        if out_mp4.exists() and out_mp4.stat().st_size > 15_000:
            scene["graphic_video_path"] = str(out_mp4)
            remotion_ok += 1
        else:
            png_path = gfx_dir / f"graphic_{sid:03d}.png"
            svg = _build_fallback_svg_card(scene, palette)
            _render_svg_to_png(svg, png_path, transparent=False)
            scene["graphic_path"] = str(png_path)
            fallback_count += 1

    update_status(
        "creating_graphics",
        f"{remotion_ok}টি Remotion অ্যানিমেটেড গ্রাফিক্স (ফলব্যাক: {fallback_count}) ও {overlay_count}টি ওভারলে তৈরি সম্পন্ন।",
        percent=76,
    )
    return scene_plan
