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


def _build_word_timings(seg, st: float, en: float):
    """Return Bengali-safe word-level timings (split only on whitespace)."""
    raw_words = seg.get("words") or []
    words = []
    for w in raw_words:
        if not isinstance(w, dict):
            continue
        wt = _bn(w.get("word") or w.get("text") or "")
        if not wt:
            continue
        ws = max(st, float(w.get("start", st)))
        we = min(en, max(ws + 0.04, float(w.get("end", ws + 0.15))))
        words.append({"start": round(ws, 3), "end": round(we, 3), "word": wt})
    if words:
        return words

    tokens = [tok for tok in _bn(seg.get("text", "")).split() if tok]
    if not tokens:
        return []
    span = max(0.1, en - st)
    step = span / len(tokens)
    return [
        {
            "start": round(st + i * step, 3),
            "end": round(en if i == len(tokens) - 1 else st + (i + 1) * step, 3),
            "word": tok,
        }
        for i, tok in enumerate(tokens)
    ]


def _keywords_for_range(scenes, st: float, en: float):
    kws = []
    for sc in scenes:
        sc_start = float(sc.get("start", 0.0))
        sc_end = float(sc.get("end", sc_start))
        if max(st, sc_start) < min(en, sc_end) + 0.05:
            for k in (sc.get("keywords") or []):
                clean_k = _bn(k)
                if clean_k and clean_k not in kws:
                    kws.append(clean_k)
    return kws[:4]


def _build_music_volume_filter(scene_plan) -> str:
    """Build an FFmpeg volume filter that ducks or mutes music on dramatic scenes."""
    scenes = scene_plan.get("scenes") or []
    mute_ranges = []
    duck_ranges = []
    for sc in scenes:
        mode = str(sc.get("music_mode") or "normal").strip().lower()
        st = max(0.0, float(sc.get("start", 0.0)))
        en = max(st, float(sc.get("end", st)))
        if en - st < 0.2:
            continue
        if mode == "mute":
            mute_ranges.append((st, en))
        elif mode == "duck":
            duck_ranges.append((st, en))

    if not mute_ranges and not duck_ranges:
        return "volume=0.20"

    expr = "0.20"
    for st, en in reversed(duck_ranges[:16]):
        expr = f"if(between(t,{st:.2f},{en:.2f}),0.09,{expr})"
    for st, en in reversed(mute_ranges[:16]):
        expr = f"if(between(t,{st:.2f},{en:.2f}),0.0,{expr})"
    return f"volume='{expr}':eval=frame"


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
        if start > cursor:
            beats.append({
                "id": len(beats) + 1, "start": cursor, "end": start,
                "text": "", "headline": "", "tag": "",
                "storyBeat": "setup",
                "visualType": "motion_graphic", "mediaPreference": "video",
                "visualEffect": "none", "video": None,
                "zoom": 0.02, "cameraPreset": "CAM-DRIFT",
                "textPreset": "HDR-DROP", "transition": "TR-DISSOLVE",
                "transitionDuration": 0.35, "musicMode": "normal",
                "keywords": [],
                "grade": "neutral_doc",
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
        headline = _bn(graphic.get("heading") or scene.get("overlay_headline") or "")
        supporting = [_bn(x) for x in (graphic.get("items") or []) if _bn(x)][:3]
        keywords = [_bn(k) for k in (scene.get("keywords") or []) if _bn(k)][:2]
        beats.append({
            "id": len(beats) + 1, "start": start, "end": end,
            "text": _bn(scene.get("narration_text") or scene.get("text") or ""),
            "headline": headline, "tag": _bn(scene.get("overlay_subtext") or scene.get("tag") or ""),
            "storyBeat": str(scene.get("story_beat") or "rising"),
            "visualType": scene.get("visual_type", "motion_graphic"),
            "mediaPreference": str(scene.get("resolved_media_kind") or scene.get("media_preference") or "video"),
            "visualEffect": str(scene.get("visual_effect") or "none"),
            "video": video_src,
            "zoom": 0.035 if idx % 2 else 0.05,
            "cameraPreset": str(scene.get("camera_preset") or "CAM-PUSH"),
            "textPreset": str(scene.get("text_preset") or "HDR-DROP"),
            "transition": str(scene.get("transition") or "TR-CUT"),
            "transitionDuration": float(scene.get("transition_duration") or 0.35),
            "musicMode": str(scene.get("music_mode") or "normal"),
            "keywords": keywords,
            "grade": scene.get("color_grade") or scene_plan.get("color_grade", "neutral_doc"),
            "graphic": {"heading": headline, "items": supporting, "kind": graphic.get("kind", graphic.get("type", ""))},
            "position": scene.get("overlay_position") or ("right" if idx % 2 == 0 else "left"),
            "showOverlay": bool(scene.get("show_overlay", False)),
            "sfx": "audio/sfx_slide.mp3" if scene.get("show_overlay", False) else None
        })
        cursor = end
    if not beats:
        beats = [{
            "id": 1, "start": 0, "end": total_frames, "text": "",
            "storyBeat": "hook", "visualType": "motion_graphic",
            "mediaPreference": "video", "visualEffect": "none",
            "cameraPreset": "CAM-PUSH", "textPreset": "HDR-DROP",
            "transition": "TR-CUT", "transitionDuration": 0.35,
            "musicMode": "normal", "keywords": [],
            "graphic": {"heading": _bn(scene_plan.get("title"))}
        }]
    if beats[0]["start"] > 0:
        beats[0]["start"] = 0
    if beats[-1]["end"] < total_frames:
        beats[-1]["end"] = total_frames
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
            subtitles.append({
                "start": round(st, 3),
                "end": round(en, 3),
                "text": txt,
                "words": _build_word_timings(seg, st, en),
                "keywords": _keywords_for_range(scenes, st, en),
            })
    _copy_voice(audio_path)
    from video_render import build_subtitles_srt
    build_subtitles_srt(transcript_data)
    scene = {
        "fps": FPS, "width": 1920, "height": 1080, "duration": total_frames,
        "videoTheme": os.environ.get("VIDEO_THEME", "crimson_noir").strip(),
        "title": _bn(scene_plan.get("title", "ডকুমেন্টারি")),
        "voice": "audio/vo.wav", "beats": normalized, "subtitles": subtitles,
        "burnSubtitles": os.environ.get("BURN_SUBTITLES", "false").lower() == "true"
    }
    target = REMOTION / "src" / "scene.json"
    target.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    (WORK / "remotion_scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    return scene


def mix_final_audio(rendered_video: Path, original_audio_path: Path, scene_plan, duration: float, final_path: Path, enable_music: bool = True):
    """Master narration to YouTube -14 LUFS and mix optional background music with mute/duck support."""
    if enable_music:
        from audio_music import prepare_background_music
        bg = WORK / "bg_music.wav"
        prepare_background_music(scene_plan.get("mood", "documentary_ambient"), duration, bg)
        music_vol = _build_music_volume_filter(scene_plan)
        filter_graph = (
            "[1:a]aresample=48000,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,"
            "loudnorm=I=-14:TP=-1.0:LRA=11[v];"
            f"[2:a]aresample=48000,asetpts=PTS-STARTPTS,{music_vol}[m];"
            "[v][m]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.35:normalize=0,"
            "alimiter=limit=0.95[a]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(rendered_video), "-i", str(original_audio_path), "-i", str(bg),
            "-filter_complex", filter_graph, "-map", "0:v:0", "-map", "[a]"
        ]
    else:
        filter_graph = (
            "[1:a]aresample=48000,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,"
            "loudnorm=I=-14:TP=-1.0:LRA=11,alimiter=limit=0.95[a]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(rendered_video), "-i", str(original_audio_path),
            "-filter_complex", filter_graph, "-map", "0:v:0", "-map", "[a]"
        ]
    cmd += ["-t", f"{duration:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(final_path)]
    _run(cmd)
    return final_path


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
        update("rendering_final_video", "Remotion দিয়ে ভিডিও, ছবি, ইফেক্ট ও কারাওকে সাবটাইটেল রেন্ডার হচ্ছে...", percent=89)
    rendered = WORK / "remotion_video.mp4"
    _run(["npx", "remotion", "render", "src/index.ts", "Main", str(rendered),
          "--codec=h264", "--crf=18", "--concurrency=2", "--pixel-format=yuv420p"], cwd=REMOTION)
    final = WORK / "final_documentary.mp4"
    duration = float(transcript_data["duration"])
    enable_music = os.environ.get("ENABLE_BG_MUSIC", "true").lower() == "true"
    mix_final_audio(rendered, original_audio_path, scene_plan, duration, final, enable_music=enable_music)
    return final, WORK / "subtitles.srt"
