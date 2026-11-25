import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Set

try:
    from processor.sample_style_overlay import (
        create_callout_card_overlay,
        create_headline_overlay,
        create_motion_graphic_bg,
        create_stat_bars_overlay,
    )
    from processor.stock_fetcher import fetch_trimmed_stock_clip
except ImportError:
    from sample_style_overlay import (
        create_callout_card_overlay,
        create_headline_overlay,
        create_motion_graphic_bg,
        create_stat_bars_overlay,
    )
    from stock_fetcher import fetch_trimmed_stock_clip


def _render_scene_overlay(scene: Dict[str, Any], out_png: str, is_motion_bg: bool) -> str:
    style = scene.get("overlay_style", "headline")
    headline = scene.get("overlay_headline", "")
    subtext = scene.get("overlay_subtext", "")
    accent = scene.get("accent", "gold")

    if style == "stat_bars" and scene.get("stat_items"):
        return create_stat_bars_overlay(headline, scene["stat_items"], out_png)
    if style == "callout_card" or is_motion_bg:
        pos = "center" if is_motion_bg else ("bottom_left" if scene["scene_id"] % 2 == 0 else "bottom_right")
        return create_callout_card_overlay(headline, subtext, out_png, accent=accent, position=pos)
    return create_headline_overlay(headline, subtext, out_png, accent=accent)


def _compose_scene(
    scene: Dict[str, Any],
    temp_dir: str,
    used_media_ids: Set[str],
    blueprint_bg: str,
) -> str:
    sid = scene["scene_id"]
    dur = max(2.0, round(float(scene["end"]) - float(scene["start"]), 2))
    raw_clip = os.path.join(temp_dir, f"raw_{sid:03d}.mp4")
    ov_png = os.path.join(temp_dir, f"ov_{sid:03d}.png")
    final_clip = os.path.join(temp_dir, f"scene_{sid:03d}.mp4")

    use_stock = scene.get("type") == "stock_footage" and bool(scene.get("search_query"))
    got_stock = None
    if use_stock:
        got_stock = fetch_trimmed_stock_clip(
            query=scene["search_query"],
            needed_duration=dur,
            output_path=raw_clip,
            used_media_ids=used_media_ids,
        )

    is_motion_bg = got_stock is None
    _render_scene_overlay(scene, ov_png, is_motion_bg=is_motion_bg)

    fade_out_st = max(0.6, round(dur - 0.4, 2))
    overlay_chain = (
        f"[1:v]format=rgba,fade=t=in:st=0.15:d=0.35:alpha=1,"
        f"fade=t=out:st={fade_out_st}:d=0.35:alpha=1[ov];"
        f"[base][ov]overlay=0:0:shortest=1"
    )

    if not is_motion_bg:
        fc = (
            f"[0:v]scale=1344:756,crop=1280:720:(iw-1280)/2:(ih-720)/2,setsar=1[base];"
            f"{overlay_chain}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", got_stock,
            "-loop", "1", "-t", str(dur), "-i", ov_png,
            "-filter_complex", fc,
            "-t", str(dur),
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-an",
            final_clip,
        ]
    else:
        fc = f"[0:v]scale=1280:720,setsar=1[base];{overlay_chain}"
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(dur), "-i", blueprint_bg,
            "-loop", "1", "-t", str(dur), "-i", ov_png,
            "-filter_complex", fc,
            "-t", str(dur),
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-an",
            final_clip,
        ]

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Scene {sid} render failed: {res.stderr[-400:]}")

    for p in (raw_clip, ov_png):
        if os.path.exists(p):
            os.remove(p)

    return final_clip


def build_final_video(
    scenes: List[Dict[str, Any]],
    audio_path: str,
    output_path: str,
    enable_bg_music: bool = True,
) -> str:
    temp_dir = tempfile.mkdtemp(prefix="doc_build_")
    used_media_ids: Set[str] = set()
    blueprint_bg = os.path.join(temp_dir, "blueprint_bg.png")
    create_motion_graphic_bg(blueprint_bg)

    try:
        scene_files: List[str] = []
        total = len(scenes)
        for sc in scenes:
            print(f"[Builder] Rendering scene {sc['scene_id']}/{total} ({sc['type']} - {sc['overlay_style']})")
            clip = _compose_scene(sc, temp_dir, used_media_ids, blueprint_bg)
            scene_files.append(clip)

        concat_txt = os.path.join(temp_dir, "concat.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for sf in scene_files:
                f.write(f"file '{sf}'\n")

        silent_video = os.path.join(temp_dir, "silent_video.mp4")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_txt,
                "-c", "copy",
                silent_video,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        bg_music_file = None
        if enable_bg_music and os.path.isdir("assets/music"):
            for fn in sorted(os.listdir("assets/music")):
                if fn.lower().endswith((".mp3", ".wav", ".m4a")):
                    bg_music_file = os.path.join("assets/music", fn)
                    break

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        if bg_music_file:
            print(f"[Builder] Mixing voiceover + low-volume background music: {bg_music_file}")
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", silent_video,
                    "-i", audio_path,
                    "-stream_loop", "-1", "-i", bg_music_file,
                    "-filter_complex", "[2:a]volume=0.09[bg];[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                    "-map", "0:v:0", "-map", "[aout]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    output_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            print("[Builder] Muxing final video with voiceover audio...")
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", silent_video,
                    "-i", audio_path,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    output_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
