import os
import subprocess
from pathlib import Path
from status import update_status
from audio_music import prepare_background_music

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
_ALLOWED_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"}
ENCODER_PRESET = os.environ.get("VIDEO_ENCODER_PRESET", "medium").strip().lower()
if ENCODER_PRESET not in _ALLOWED_PRESETS:
    ENCODER_PRESET = "medium"
SCENE_CRF = str(max(16, min(24, int(os.environ.get("VIDEO_SCENE_CRF", "19")))))
FINAL_CRF = str(max(16, min(24, int(os.environ.get("VIDEO_FINAL_CRF", "18")))))

GRADE_FILTERS = {
    "cinematic_teal": "eq=contrast=1.045:saturation=0.98:brightness=-0.008,colorbalance=bs=0.012:rs=-0.008,vignette=PI/7,unsharp=5:5:0.22:3:3:0.10",
    "warm_history": "eq=contrast=1.045:saturation=0.98:brightness=-0.005,colorbalance=rs=0.025:gs=0.008:bs=-0.018,vignette=PI/7",
    "cool_science": "eq=contrast=1.045:saturation=0.97,colorbalance=bs=0.025:gs=0.008:rs=-0.015,vignette=PI/7",
    "neutral_doc": "eq=contrast=1.025:saturation=0.99,vignette=PI/8"
}


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{proc.stderr[-2000:]}")
    return proc


def _camera_filter(scene):
    """Apply a subtle, deterministic documentary camera move to stock footage."""
    motion = str(scene.get("motion_effect") or "").lower()
    # Slight overscan gives the crop room to move without exposing empty edges.
    if motion in ("pan_left", "pan_right"):
        direction = "-" if motion == "pan_left" else "+"
        x_expr = f"(in_w-out_w)*(0.5{direction}0.32*sin(t*0.22))"
        return (
            "scale=2040:1148:force_original_aspect_ratio=increase,"
            f"crop=1920:1080:x='{x_expr}':y='(in_h-out_h)*0.5'"
        )
    if motion == "slow_zoom_out":
        return (
            "scale=2040:1148:force_original_aspect_ratio=increase,"
            "crop=1920:1080:x='(in_w-out_w)*(0.5+0.12*cos(t*0.18))':"
            "y='(in_h-out_h)*(0.5+0.12*cos(t*0.18))'"
        )
    # Default slow push-in / restrained documentary movement.
    return (
        "scale=2040:1148:force_original_aspect_ratio=increase,"
        "crop=1920:1080:x='(in_w-out_w)*(0.5+0.10*sin(t*0.16))':"
        "y='(in_h-out_h)*0.5'"
    )


def _fmt_srt_time(seconds):
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_subtitles_srt(transcript_data):
    srt_path = WORK / "subtitles.srt"
    blocks = []
    for idx, seg in enumerate(transcript_data.get("segments", []), start=1):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        blocks.append(f"{idx}\n{_fmt_srt_time(seg['start'])} --> {_fmt_srt_time(seg['end'])}\n{text}\n")
    srt_path.write_text("\n".join(blocks), encoding="utf-8")
    return srt_path


def _render_scene_clip(scene, out_clip, grade_filter):
    dur = max(1.0, float(scene.get("duration") or (float(scene.get("end", 5.0)) - float(scene.get("start", 0.0)))))
    # Documentary reference uses editorial hard cuts between shots. Avoid fading
    # every individual shot to black, which creates an unintended black flash.
    fade_d = 0.0
    fade_out_st = max(0.0, dur)

    footage_path = scene.get("footage_path")
    graphic_video_path = scene.get("graphic_video_path")
    graphic_path = scene.get("graphic_path")
    overlay_path = scene.get("overlay_path")

    if footage_path and Path(footage_path).exists():
        if overlay_path and Path(overlay_path).exists():
            ov_p = Path(overlay_path)
            fc = (
                f"[0:v]{_camera_filter(scene)},setsar=1,fps=30,format=yuv420p,{grade_filter}[base];"
                f"[1:v]fps=30,setsar=1,format=rgba[ov];"
                f"[base][ov]overlay=x=0:y=0:shortest=1,setsar=1,format=yuv420p[vout]"
            )
            ov_inputs = ["-i", str(ov_p)] if ov_p.suffix.lower() in (".mov", ".webm", ".mp4") else ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(ov_p)]
            run_ffmpeg([
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(footage_path),
                *ov_inputs,
                "-t", f"{dur:.3f}",
                "-an",
                "-filter_complex", fc,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", ENCODER_PRESET, "-crf", SCENE_CRF,
                "-video_track_timescale", "15360",
                "-pix_fmt", "yuv420p",
                str(out_clip)
            ])
        else:
            vf = (
                f"{_camera_filter(scene)},setsar=1,fps=30,format=yuv420p,"
                f"{grade_filter},setsar=1"
            )
            run_ffmpeg([
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(footage_path),
                "-t", f"{dur:.3f}",
                "-an",
                "-vf", vf,
                "-c:v", "libx264", "-preset", ENCODER_PRESET, "-crf", SCENE_CRF,
                "-video_track_timescale", "15360",
                "-pix_fmt", "yuv420p",
                str(out_clip)
            ])
        try:
            Path(footage_path).unlink()
        except OSError:
            pass

    elif graphic_video_path and Path(graphic_video_path).exists():
        vf = (
            f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,format=yuv420p"
        )
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(graphic_video_path),
            "-t", f"{dur:.3f}",
            "-an",
            "-vf", vf,
            "-c:v", "libx264", "-preset", ENCODER_PRESET, "-crf", SCENE_CRF,
            "-video_track_timescale", "15360",
            "-pix_fmt", "yuv420p",
            str(out_clip)
        ])
        try:
            Path(graphic_video_path).unlink()
        except OSError:
            pass

    elif graphic_path and Path(graphic_path).exists():
        frames = max(30, int(round(dur * 30)))
        vf = (
            f"scale=2040:1148,"
            f"zoompan=z='min(zoom+0.0005,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
            f"setsar=1,format=yuv420p"
        )
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(graphic_path),
            "-t", f"{dur:.3f}",
            "-an",
            "-vf", vf,
            "-c:v", "libx264", "-preset", ENCODER_PRESET, "-crf", SCENE_CRF,
            "-video_track_timescale", "15360",
            "-pix_fmt", "yuv420p",
            str(out_clip)
        ])
    else:
        raise RuntimeError(f"Scene {scene['scene_id']} has neither footage nor graphic.")


def render_documentary(scene_plan, transcript_data, original_audio_path):
    update_status("editing_video", "প্রতিটি দৃশ্য সিনেম্যাটিক 1080p ফরম্যাটে সাজানো হচ্ছে...", percent=80)

    clips_dir = WORK / "scene_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    default_grade = scene_plan.get("color_grade", "cinematic_teal")

    clip_paths = []
    for scene in scene_plan.get("scenes", []):
        scene_grade = scene.get("color_grade") or default_grade
        grade_filter = GRADE_FILTERS.get(scene_grade, GRADE_FILTERS["cinematic_teal"])
        clip_path = clips_dir / f"clip_{scene['scene_id']:03d}.mp4"
        _render_scene_clip(scene, clip_path, grade_filter)
        clip_paths.append(clip_path)

    concat_list = WORK / "concat_list.txt"
    concat_lines = [f"file '{p.resolve()}'" for p in clip_paths]
    concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    merged_video = WORK / "merged_video.mp4"
    # Re-encode the concatenated CFR clips instead of stream-copying them.
    # Stream-copy concat can preserve per-clip timestamp/time-base quirks and
    # accumulate small timing discontinuities at every cut.
    run_ffmpeg([
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-an",
        "-vf", "setpts=PTS-STARTPTS,fps=30,setsar=1",
        "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", ENCODER_PRESET, "-crf", FINAL_CRF,
        "-pix_fmt", "yuv420p", "-r", "30",
        "-video_track_timescale", "15360",
        str(merged_video)
    ])

    for p in clip_paths:
        try:
            p.unlink()
        except OSError:
            pass

    srt_path = build_subtitles_srt(transcript_data)
    burn_subs = os.environ.get("BURN_SUBTITLES", "false").lower() == "true"
    enable_music = os.environ.get("ENABLE_BG_MUSIC", "true").lower() == "true"
    duration = float(transcript_data["duration"])

    update_status("rendering_final_video", f"আপনার মূল ভয়েসের সাথে চূড়ান্ত 1080p MP4 রেন্ডার হচ্ছে ({round(duration, 1)} সেকেন্ড)...", percent=92)

    final_mp4 = WORK / "final_documentary.mp4"

    inputs = ["-i", str(merged_video), "-i", str(original_audio_path)]
    if enable_music:
        bg_wav = WORK / "bg_music.wav"
        prepare_background_music(scene_plan.get("mood", "documentary_ambient"), duration, bg_wav)
        inputs.extend(["-i", str(bg_wav)])
        # Keep narration clearly in front; duck music gently under the voice.
        audio_filter = "[1:a]aresample=48000,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11[voice];[2:a]aresample=48000,asetpts=PTS-STARTPTS,volume=0.35[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.45:normalize=0,alimiter=limit=0.95,asetpts=PTS-STARTPTS[aout]"
        audio_map = ["-map", "[aout]"]
    else:
        audio_filter = None
        audio_map = ["-map", "1:a:0"]

    cmd = ["ffmpeg", "-y"] + inputs
    if burn_subs and srt_path.exists() and srt_path.stat().st_size > 0:
        escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
        sub_style = "FontName=Hind Siliguri,FontSize=21,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H64000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=36"
        vf = f"setpts=PTS-STARTPTS,fps=30,subtitles='{escaped_srt}':force_style='{sub_style}'"
        if audio_filter:
            cmd.extend(["-filter_complex", f"[0:v]{vf}[vout];{audio_filter}", "-map", "[vout]"] + audio_map)
        else:
            cmd.extend(["-vf", vf, "-map", "0:v:0"] + audio_map)
        cmd.extend(["-c:v", "libx264", "-preset", ENCODER_PRESET, "-crf", FINAL_CRF, "-pix_fmt", "yuv420p", "-r", "30"])
    else:
        # merged_video.mp4 is already timestamp-normalized, CFR 30 FPS and
        # 1920x1080. Stream-copy it to avoid a needless second video encode.
        cmd.extend(["-map", "0:v:0"] + audio_map)
        cmd.extend(["-c:v", "copy"])
        if audio_filter:
            cmd.extend(["-filter_complex", audio_filter])
        else:
            cmd.extend(["-af", "aresample=48000,asetpts=PTS-STARTPTS"])

    cmd.extend([
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{duration:.3f}",
        "-movflags", "+faststart",
        str(final_mp4)
    ])

    run_ffmpeg(cmd)
    return final_mp4, srt_path
