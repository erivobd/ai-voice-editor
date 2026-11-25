import os
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "assets/fonts/HindSiliguri-Bold.ttf"
FONT_SEMI = "assets/fonts/HindSiliguri-SemiBold.ttf"
FONT_REG = "assets/fonts/HindSiliguri-Regular.ttf"

COLOR_WHITE = (248, 250, 252, 255)
COLOR_GOLD = (250, 204, 21, 255)
COLOR_RED = (239, 68, 68, 255)
COLOR_SKY = (56, 189, 248, 255)
COLOR_GLASS = (15, 23, 42, 222)
COLOR_BORDER = (255, 255, 255, 48)
COLOR_BG_DARK = (11, 17, 32, 255)
COLOR_GRID = (30, 41, 59, 130)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if not os.path.exists(path):
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(path, size)


def create_motion_graphic_bg(out_png: str, size: Tuple[int, int] = (1280, 720)) -> str:
    """Creates a sleek dark engineering/documentary blueprint grid background."""
    w, h = size
    img = Image.new("RGBA", (w, h), COLOR_BG_DARK)
    draw = ImageDraw.Draw(img)

    step = 48
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=COLOR_GRID, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=COLOR_GRID, width=1)

    draw.rectangle([28, 28, w - 28, h - 28], outline=(56, 189, 248, 55), width=2)
    img.convert("RGB").save(out_png)
    return out_png


def create_headline_overlay(
    headline: str,
    subtext: str,
    out_png: str,
    accent: str = "gold",
    size: Tuple[int, int] = (1280, 720),
) -> str:
    """Sample style: Bold centered top title + warm gold/red subtitle."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    accent_col = COLOR_RED if accent == "red" else COLOR_GOLD
    f_head = _load_font(FONT_BOLD, 54)
    f_sub = _load_font(FONT_SEMI, 28)

    if headline:
        bbox = draw.textbbox((0, 0), headline, font=f_head)
        tw = bbox[2] - bbox[0]
        x = max(40, (w - tw) // 2)
        y = 58
        draw.rounded_rectangle(
            [x - 28, y - 14, x + tw + 28, y + (bbox[3] - bbox[1]) + 22],
            radius=12,
            fill=(15, 23, 42, 165),
        )
        draw.text((x + 2, y + 2), headline, font=f_head, fill=(0, 0, 0, 180))
        draw.text((x, y), headline, font=f_head, fill=COLOR_WHITE)

    if subtext:
        sb = draw.textbbox((0, 0), subtext, font=f_sub)
        sw = sb[2] - sb[0]
        sx = max(40, (w - sw) // 2)
        sy = 148
        draw.text((sx + 2, sy + 2), subtext, font=f_sub, fill=(0, 0, 0, 190))
        draw.text((sx, sy), subtext, font=f_sub, fill=accent_col)

    img.save(out_png)
    return out_png


def create_callout_card_overlay(
    headline: str,
    subtext: str,
    out_png: str,
    accent: str = "gold",
    position: str = "bottom_left",
    size: Tuple[int, int] = (1280, 720),
) -> str:
    """Sample style: Dark frosted glass card with accent left bar."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    accent_color = COLOR_RED if accent == "red" else COLOR_GOLD
    f_head = _load_font(FONT_BOLD, 34)
    f_sub = _load_font(FONT_SEMI, 22)

    card_w, card_h = 520, 134
    if position == "top_left":
        x0, y0 = 64, 72
    elif position == "center":
        x0, y0 = (w - card_w) // 2, (h - card_h) // 2
    elif position == "bottom_right":
        x0, y0 = w - card_w - 64, h - card_h - 72
    else:
        x0, y0 = 64, h - card_h - 72

    draw.rounded_rectangle(
        [x0, y0, x0 + card_w, y0 + card_h],
        radius=14,
        fill=COLOR_GLASS,
        outline=COLOR_BORDER,
        width=2,
    )
    draw.rounded_rectangle(
        [x0, y0 + 14, x0 + 8, y0 + card_h - 14],
        radius=4,
        fill=accent_color,
    )

    draw.text((x0 + 28, y0 + 20), headline or "মূল তথ্য", font=f_head, fill=COLOR_WHITE)
    if subtext:
        draw.text((x0 + 28, y0 + 76), subtext, font=f_sub, fill=accent_color)

    img.save(out_png)
    return out_png


def create_stat_bars_overlay(
    title: str,
    items: List[Tuple[str, float]],
    out_png: str,
    size: Tuple[int, int] = (1280, 720),
) -> str:
    """Sample style: Right-side dark data card with progressive horizontal bars."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    card_w, card_h = 520, 350
    x0, y0 = w - card_w - 60, (h - card_h) // 2

    draw.rounded_rectangle(
        [x0, y0, x0 + card_w, y0 + card_h],
        radius=16,
        fill=COLOR_GLASS,
        outline=COLOR_BORDER,
        width=2,
    )

    f_title = _load_font(FONT_BOLD, 28)
    f_lbl = _load_font(FONT_SEMI, 20)
    draw.text((x0 + 26, y0 + 22), title or "তথ্য তুলনা", font=f_title, fill=COLOR_GOLD)

    parsed: List[Tuple[str, float]] = []
    for it in items[:5]:
        try:
            parsed.append((str(it[0]), float(it[1])))
        except Exception:
            continue
    if not parsed:
        parsed = [("ধাপ ১", 40.0), ("ধাপ ২", 75.0), ("ধাপ ৩", 100.0)]

    max_val = max((v for _, v in parsed), default=1.0) or 1.0
    bar_max_w = 290
    start_y = y0 + 88

    for idx, (label, val) in enumerate(parsed):
        ry = start_y + idx * 50
        bar_w = max(16, int((val / max_val) * bar_max_w))
        draw.rounded_rectangle(
            [x0 + 26, ry + 10, x0 + 26 + bar_max_w, ry + 22],
            radius=6,
            fill=(75, 85, 99, 165),
        )
        bar_col = COLOR_GOLD if idx == len(parsed) - 1 else COLOR_SKY
        draw.rounded_rectangle(
            [x0 + 26, ry + 10, x0 + 26 + bar_w, ry + 22],
            radius=6,
            fill=bar_col,
        )
        draw.text((x0 + 26 + bar_max_w + 18, ry + 2), label[:16], font=f_lbl, fill=COLOR_WHITE)

    img.save(out_png)
    return out_png
