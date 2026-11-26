import os
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
REPO_ROOT = Path(__file__).resolve().parent.parent

FONT_BOLD_CANDIDATES = [
    REPO_ROOT / "assets" / "fonts" / "HindSiliguri-Bold.ttf",
    Path("/usr/local/share/fonts/HindSiliguri-Bold.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansBengali-Bold.ttf"),
    Path("/usr/share/fonts/truetype/beng/kalpurush.ttf"),
]

FONT_REG_CANDIDATES = [
    REPO_ROOT / "assets" / "fonts" / "HindSiliguri-SemiBold.ttf",
    REPO_ROOT / "assets" / "fonts" / "HindSiliguri-Regular.ttf",
    Path("/usr/local/share/fonts/HindSiliguri-SemiBold.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"),
]

THEME_PALETTES = {
    "crimson_noir": {
        "bg1": (9, 9, 11), "bg2": (32, 6, 12), "accent": (220, 38, 38),
        "text": (255, 255, 255), "muted": (228, 228, 231),
        "card_bg": (18, 18, 22, 232), "pill_bg": (14, 14, 18, 238), "is_light": False,
    },
    "cinematic_dark": {
        "bg1": (8, 16, 28), "bg2": (15, 32, 53), "accent": (250, 204, 21),
        "text": (248, 250, 252), "muted": (203, 213, 225),
        "card_bg": (15, 23, 42, 232), "pill_bg": (15, 23, 42, 238), "is_light": False,
    },
    "vox_colorful": {
        "bg1": (254, 240, 138), "bg2": (253, 224, 71), "accent": (220, 38, 38),
        "text": (17, 24, 39), "muted": (55, 65, 81),
        "card_bg": (255, 255, 255, 238), "pill_bg": (17, 24, 39, 238), "is_light": True,
    },
    "editorial_paper": {
        "bg1": (246, 241, 231), "bg2": (235, 226, 210), "accent": (217, 119, 6),
        "text": (28, 25, 23), "muted": (87, 83, 78),
        "card_bg": (255, 253, 249, 238), "pill_bg": (28, 25, 23, 238), "is_light": True,
    },
    "vibrant_gradient": {
        "bg1": (30, 27, 75), "bg2": (76, 29, 149), "accent": (34, 211, 238),
        "text": (255, 255, 255), "muted": (224, 231, 255),
        "card_bg": (30, 27, 75, 232), "pill_bg": (15, 23, 42, 238), "is_light": False,
    },
    "minimal_light": {
        "bg1": (248, 250, 252), "bg2": (226, 232, 240), "accent": (37, 99, 235),
        "text": (15, 23, 42), "muted": (71, 85, 105),
        "card_bg": (255, 255, 255, 238), "pill_bg": (15, 23, 42, 238), "is_light": True,
    },
}


def _strip_chapter_and_hindi(text: str) -> str:
    s = re.sub(r"[\u0900-\u097F]+", "", str(text or ""))
    s = re.sub(r"^\s*অধ্যায়\s*[\d০-৯]+\s*(?://|[-–—:])?\s*", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def _load_font(size: int, bold: bool = True):
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REG_CANDIDATES + FONT_BOLD_CANDIDATES
    for p in candidates:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple:
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def _wrap_by_pixel(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 2) -> list:
    words = _strip_chapter_and_hindi(text).split()
    if not words:
        return []
    lines = []
    cur = []
    for w in words:
        trial = " ".join(cur + [w])
        tw, _ = _text_size(draw, trial, font)
        if tw <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(" ".join(cur))
    return lines[:max_lines]


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - ((1.0 - t) ** 3)


def _apply_alpha(rgba: tuple, mult: float) -> tuple:
    r, g, b = rgba[:3]
    a = rgba[3] if len(rgba) > 3 else 255
    return (r, g, b, max(0, min(255, int(round(a * mult)))))


def _draw_overlay_frame(
    heading: str,
    subheading: str,
    items: list,
    palette: dict,
    accent: tuple,
    t_sec: float,
    dur_sec: float,
) -> Image.Image:
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_head = _load_font(48, bold=True)
    font_sub = _load_font(30, bold=False)
    font_pill = _load_font(32, bold=True)

    fade_out = 1.0
    if dur_sec > 0.8 and t_sec > dur_sec - 0.35:
        fade_out = max(0.0, (dur_sec - t_sec) / 0.35)

    if heading:
        p_head = _ease_out_cubic((t_sec - 0.05) / 0.40) * fade_out
        if p_head > 0.01:
            slide_y = int(round((1.0 - _ease_out_cubic((t_sec - 0.05) / 0.40)) * 28))
            h_lines = _wrap_by_pixel(draw, heading, font_head, max_width=1360, max_lines=1)
            main_h = h_lines[0] if h_lines else heading[:28]
            hw, hh = _text_size(draw, main_h, font_head)
            sw, sh = (0, 0)
            sub_clean = subheading[:46] if subheading else ""
            if sub_clean:
                sw, sh = _text_size(draw, sub_clean, font_sub)

            content_w = max(hw, sw)
            box_w = max(560, min(1560, content_w + 130))
            box_h = (hh + sh + 64) if sub_clean else (hh + 52)
            box_x = (1920 - box_w) // 2
            box_y = 52 + slide_y

            border_col = _apply_alpha((255, 255, 255, 48) if not palette["is_light"] else (0, 0, 0, 48), p_head)
            draw.rounded_rectangle(
                [box_x, box_y, box_x + box_w, box_y + box_h],
                radius=22,
                fill=_apply_alpha(palette["card_bg"], p_head),
                outline=border_col,
                width=2,
            )
            draw.rounded_rectangle(
                [box_x + 26, box_y + 22, box_x + 38, box_y + box_h - 22],
                radius=6,
                fill=_apply_alpha(accent, p_head),
            )
            draw.text(
                (box_x + 60, box_y + 22),
                main_h,
                font=font_head,
                fill=_apply_alpha(palette["text"], p_head),
            )
            if sub_clean:
                draw.text(
                    (box_x + 60, box_y + 28 + hh),
                    sub_clean,
                    font=font_sub,
                    fill=_apply_alpha(accent, p_head),
                )

    if items:
        cur_x = 110
        base_pill_y = 885
        pill_h = 74
        for idx, it in enumerate(items[:3]):
            label = it[:24]
            if not label:
                continue
            pw_txt, ph_txt = _text_size(draw, label, font_pill)
            pill_w = max(250, min(560, pw_txt + 96))
            if cur_x + pill_w > 1810:
                break

            start_t = 0.28 + idx * 0.20
            prog = _ease_out_cubic((t_sec - start_t) / 0.35)
            alpha_m = prog * fade_out
            if alpha_m > 0.01:
                py = base_pill_y + int(round((1.0 - prog) * 32))
                draw.rounded_rectangle(
                    [cur_x, py, cur_x + pill_w, py + pill_h],
                    radius=37,
                    fill=_apply_alpha(palette["pill_bg"], alpha_m),
                    outline=_apply_alpha(accent, alpha_m),
                    width=3,
                )
                dot_r = 9
                dot_cx = cur_x + 32
                dot_cy = py + pill_h // 2
                draw.ellipse(
                    [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
                    fill=_apply_alpha(accent, alpha_m),
                )
                draw.text(
                    (cur_x + 56, py + (pill_h - ph_txt) // 2 - 3),
                    label,
                    font=font_pill,
                    fill=_apply_alpha((255, 255, 255), alpha_m),
                )
            cur_x += pill_w + 24

    return img


def _render_animated_overlay_mov(scene: dict, palette: dict, out_mov: Path, duration: float):
    if scene.get("rapid_cut"):
        return None
    g = scene.get("graphic") or {}
    heading = _strip_chapter_and_hindi(g.get("heading") or scene.get("overlay_headline") or "")
    subheading = _strip_chapter_and_hindi(g.get("subheading") or scene.get("overlay_subtext") or "")
    items = [_strip_chapter_and_hindi(x) for x in (g.get("items") or []) if _strip_chapter_and_hindi(x)][:3]

    if not heading and not items:
        return None

    accent = (220, 38, 38) if scene.get("accent") == "red" else palette["accent"]
    fps = 30
    total_frames = max(30, int(round(duration * fps)))

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", "1920x1080",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "png",
        "-pix_fmt", "rgba",
        str(out_mov),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    cached_static_bytes = None
    for f_idx in range(total_frames):
        t_sec = f_idx / float(fps)
        is_static_mid = (1.35 <= t_sec <= max(1.35, duration - 0.40))
        if is_static_mid and cached_static_bytes is not None:
            frame_bytes = cached_static_bytes
        else:
            frame_img = _draw_overlay_frame(heading, subheading, items, palette, accent, t_sec, duration)
            frame_bytes = frame_img.tobytes()
            if is_static_mid:
                cached_static_bytes = frame_bytes
        proc.stdin.write(frame_bytes)

    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    ret = proc.wait()
    if ret != 0 or not out_mov.exists():
        raise RuntimeError(f"Animated overlay render failed: {stderr_out[-800:]}")
    return out_mov


def _build_infographic_png(scene: dict, palette: dict, png_path: Path) -> Path:
    g = scene.get("graphic") or {}
    kind = g.get("kind") or "title_card"
    heading = _strip_chapter_and_hindi(g.get("heading") or scene.get("overlay_headline") or "মূল তথ্য")
    subheading = _strip_chapter_and_hindi(g.get("subheading") or scene.get("overlay_subtext") or "")
    items = [_strip_chapter_and_hindi(x) for x in (g.get("items") or []) if _strip_chapter_and_hindi(x)][:4]
    accent = (220, 38, 38) if scene.get("accent") == "red" else palette["accent"]

    img = Image.new("RGB", (1920, 1080), palette["bg1"])
    draw = ImageDraw.Draw(img)

    r1, g1, b1 = palette["bg1"]
    r2, g2, b2 = palette["bg2"]
    for y in range(0, 1080, 4):
        ratio = y / 1080.0
        col = (
            int(r1 + (r2 - r1) * ratio),
            int(g1 + (g2 - g1) * ratio),
            int(b1 + (b2 - b1) * ratio),
        )
        draw.rectangle([0, y, 1920, y + 4], fill=col)

    font_head = _load_font(68, bold=True)
    font_sub = _load_font(36, bold=False)
    font_pill = _load_font(34, bold=True)

    draw.rounded_rectangle([140, 165, 290, 176], radius=5, fill=accent)

    h_lines = _wrap_by_pixel(draw, heading, font_head, max_width=1580, max_lines=2)
    cur_y = 215
    for line in h_lines:
        draw.text((140, cur_y), line, font=font_head, fill=palette["text"])
        _, lh = _text_size(draw, line, font_head)
        cur_y += lh + 18

    if subheading:
        draw.text((140, cur_y + 6), subheading[:48], font=font_sub, fill=accent)
        _, sh = _text_size(draw, subheading[:48], font_sub)
        cur_y += sh + 48
    else:
        cur_y += 32

    if kind == "stat_chart" and items:
        for idx, raw_item in enumerate(items[:4]):
            parts = re.split(r"[:\-—]", raw_item, maxsplit=1)
            lbl = parts[0].strip()[:24] or f"তথ্য {idx + 1}"
            num_m = re.search(r"(\d+(?:\.\d+)?)", raw_item)
            pct = min(100.0, max(18.0, float(num_m.group(1)))) if num_m else min(95.0, 35.0 + idx * 18.0)
            val_txt = parts[1].strip()[:14] if len(parts) > 1 and parts[1].strip() else f"{int(pct)}%"
            ry = cur_y + idx * 116
            if ry > 930:
                break
            draw.text((140, ry), lbl, font=font_pill, fill=palette["text"])
            vw, _ = _text_size(draw, val_txt, font_pill)
            draw.text((1320 - vw, ry), val_txt, font=font_pill, fill=accent)
            draw.rounded_rectangle([140, ry + 48, 1320, ry + 78], radius=15, fill=palette["card_bg"][:3], outline=accent, width=2)
            bar_end = 140 + int((pct / 100.0) * 1180)
            draw.rounded_rectangle([140, ry + 48, bar_end, ry + 78], radius=15, fill=accent)
    elif items:
        px = 140
        py = cur_y + 10
        pill_h = 78
        for it in items[:4]:
            txt = it[:26]
            tw, th = _text_size(draw, txt, font_pill)
            pw = max(290, min(640, tw + 108))
            if px + pw > 1760:
                px = 140
                py += 98
            if py > 920:
                break
            draw.rounded_rectangle([px, py, px + pw, py + pill_h], radius=39, fill=palette["pill_bg"][:3], outline=accent, width=3)
            draw.ellipse([px + 26, py + pill_h // 2 - 10, px + 46, py + pill_h // 2 + 10], fill=accent)
            draw.text((px + 62, py + (pill_h - th) // 2 - 3), txt, font=font_pill, fill=(255, 255, 255))
            px += pw + 26

    img.save(png_path, format="PNG")
    return png_path


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
    update_status("creating_graphics", "FFmpeg + Pillow অ্যানিমেটেড ব্যাজ, হেডলাইন ও পিল তৈরি হচ্ছে...", percent=70)

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
            _build_infographic_png(scene, palette, card_png)
            _render_animated_infographic_mp4(card_png, out_mp4, dur, sid)
            scene["graphic_video_path"] = str(out_mp4)
            scene["graphic_path"] = str(card_png)
            graphic_count += 1
        else:
            ov_mov = gfx_dir / f"overlay_{sid:03d}.mov"
            res_mov = _render_animated_overlay_mov(scene, palette, ov_mov, dur)
            if res_mov and res_mov.exists():
                scene["overlay_path"] = str(res_mov)
                overlay_count += 1

    update_status(
        "creating_graphics",
        f"FFmpeg + Pillow এ {graphic_count}টি ইনফোগ্রাফিক ও {overlay_count}টি অ্যানিমেটেড পিল/ব্যাজ ওভারলে তৈরি সম্পন্ন।",
        percent=76,
    )
    return scene_plan
