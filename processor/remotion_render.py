"""Build and render the documentary with the in-app Remotion engine."""
import json
import os
import shutil
import subprocess
import unicodedata
from pathlib import Path

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
ROOT = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
FPS = 30


def _run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    if p.returncode:
        raise RuntimeError("Remotion render failed:\n" + (p.stdout or "")[-9000:])
    return p.stdout


def _bn(value):
    return unicodedata.normalize("NFC", str(value or "")).strip()


def _copy_voice(audio_path):
    audio_dir = REMOTION / "public" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    target = audio_dir / "vo.wav"
    _run(["ffmpeg", "-y", "-i", str(audio_path), "-vn", "-ac", "1", "-ar", "24000",
          "-c:a", "pcm_s16le", str(target)])
    return target


def _build_scene(scene_plan, transcript_data, audio_path):
    duration = float(transcript_data["duration"])
    total_frames = max(1, round(duration * FPS))
    public_video = REMOTION / "public" / "video"
    public_video.mkdir(parents=True, exist_ok=True)
    beats = []
    scenes = sorted(scene_plan.get("scenes", []), key=lambda x: float(x.get("start", 0)))
    cursor = 0
    for idx, scene in enumerate(scenes, 1):
        start = max(cursor, min(total_frames, round(float(scene.get("start", 0)) * FPS)))
        end = max(start, min(total_frames, round(float(scene.get("end", duration)) * FPS)))
        if end <= start:
            continue
        # Never stretch a stock clip over an unplanned gap: create a designed
        # graphic bridge instead, preventing frozen final frames.
        if start > cursor:
            beats.append({
                "id": len(beats) + 1, "start": cursor, "end": start,
                "text": "", "headline": "", "tag": "",
                "visualType": "motion_graphic", "video": None,
                "zoom": 0.02, "grade": "neutral_doc",
                "graphic": {"heading": _bn(scene_plan.get("title", "")), "items": []},
                "position": "center", "showOverlay": True
            })
        video_src = None
        source = scene.get("footage_path")
        if source and Path(source).is_file():
            suffix = Path(source).suffix.lower() or ".mp4"
            dest = public_video / f"scene_{idx:04d}{suffix}"
            shutil.copy2(source, dest)
            video_src = f"video/{dest.name}"
        graphic = scene.get("graphic") or {}
        queries = scene.get("search_queries") or []
        if isinstance(queries, str):
            queries = [queries]
        headline = _bn(graphic.get("heading") or scene.get("overlay_headline") or "")
        supporting = [_bn(x) for x in (graphic.get("items") or []) if _bn(x)][:3]
        beats.append({
            "id": len(beats) + 1, "start": start, "end": end,
            "text": _bn(scene.get("narration_text") or scene.get("text") or ""),
            "headline": headline, "tag": _bn(scene.get("overlay_subtext") or scene.get("tag") or ""),
            "visualType": scene.get("visual_type", "motion_graphic"),
            "video": video_src,
            "zoom": 0.035 if idx % 2 else 0.05,
            "grade": scene.get("color_grade") or scene_plan.get("color_grade", "neutral_doc"),
            "graphic": {"heading": headline, "items": supporting, "kind": graphic.get("kind", graphic.get("type", ""))},
            "position": scene.get("overlay_position") or ("right" if idx % 2 == 0 else "left"),
            "showOverlay": bool(scene.get("show_overlay", False)),
            "sfx": "audio/sfx_slide.mp3" if scene.get("show_overlay", False) else None
        })
        cursor = end
    if not beats:
        beats = [{"id": 1, "start": 0, "end": total_frames, "text": "", "visualType": "motion_graphic", "graphic": {"heading": _bn(scene_plan.get("title"))}}]
    if beats[0]["start"] > 0:
        beats[0]["start"] = 0
    if beats[-1]["end"] < total_frames:
        beats[-1]["end"] = total_frames
    # Normalize boundaries so every frame belongs to exactly one beat.
    normalized = []
    cursor = 0
    for beat in beats:
        end = max(cursor + 1, min(total_frames, int(beat["end"])))
        beat["start"], beat["end"] = cursor, end
        normalized.append(beat)
        cursor = end
        if cursor >= total_frames:
            break
    if normalized[-1]["end"] != total_frames:
        normalized[-1]["end"] = total_frames

    subtitles = []
    for seg in transcript_data.get("segments", []):
        st = max(0.0, float(seg.get("start", 0)))
        en = min(duration, float(seg.get("end", st)))
        txt = _bn(seg.get("text", ""))
        if txt and en > st:
            subtitles.append({"start": st, "end": en, "text": txt})
    voice = _copy_voice(audio_path)
    from video_render import build_subtitles_srt
    build_subtitles_srt(transcript_data)
    scene = {
        "fps": FPS, "width": 1920, "height": 1080, "duration": total_frames,
        "title": _bn(scene_plan.get("title", "ডকুমেন্টারি")),
        "voice": "audio/vo.wav", "beats": normalized, "subtitles": subtitles,
        "burnSubtitles": os.environ.get("BURN_SUBTITLES", "false").lower() == "true"
    }
    target = REMOTION / "src" / "scene.json"
    target.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    (WORK / "remotion_scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    return scene


def render_remotion_documentary(scene_plan, transcript_data, original_audio_path):
    if not (REMOTION / "node_modules" / "@remotion" / "cli").exists():
        raise RuntimeError("Remotion dependencies are not installed. Run npm ci in the remotion directory.")
    WORK.mkdir(parents=True, exist_ok=True)
    _build_scene(scene_plan, transcript_data, original_audio_path)
    update = None
    try:
        from status import update_status as update
    except Exception:
        pass
    if update:
        update("rendering_final_video", "Remotion দিয়ে প্রতিটি দৃশ্য, অ্যানিমেশন ও ভয়েস একসঙ্গে রেন্ডার হচ্ছে...", percent=89)
    rendered = WORK / "remotion_video.mp4"
    _run(["npx", "remotion", "render", "src/index.ts", "Main", str(rendered),
          "--codec=h264", "--crf=18", "--concurrency=2", "--pixel-format=yuv420p"], cwd=REMOTION)
    final = WORK / "final_documentary.mp4"
    duration = float(transcript_data["duration"])
    enable_music = os.environ.get("ENABLE_BG_MUSIC", "true").lower() == "true"
    if enable_music:
        from audio_music import prepare_background_music
        bg = WORK / "bg_music.wav"
        prepare_background_music(scene_plan.get("mood", "documentary_ambient"), duration, bg)
        cmd = ["ffmpeg", "-y", "-i", str(rendered), "-i", str(original_audio_path), "-i", str(bg),
               "-filter_complex", "[1:a]aresample=48000,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11[v];[2:a]aresample=48000,asetpts=PTS-STARTPTS,volume=0.22[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.35:normalize=0,alimiter=limit=0.95[a]",
               "-map", "0:v:0", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(rendered), "-i", str(original_audio_path), "-map", "0:v:0", "-map", "1:a:0"]
    cmd += ["-t", f"{duration:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(final)]
    _run(cmd)
    return final, WORK / "subtitles.srt"
