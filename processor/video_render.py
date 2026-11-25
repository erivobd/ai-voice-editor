import os
import subprocess
from pathlib import Path
from status import update_status
from audio_music import prepare_background_music

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))

GRADE_FILTERS = {
    "cinematic_teal": "eq=contrast=1.06:saturation=1.08:brightness=-0.02,colorbalance=bs=0.05:rs=-0.03",
    "warm_history": "eq=contrast=1.05:saturation=0.92:brightness=-0.01,colorbalance=rs=0.06:gs=0.02:bs=-0.05",
    "cool_science": "eq=contrast=1.07:saturation=1.05,colorbalance=bs=0.07:gs=0.02:rs=-0.04",
    "neutral_doc": "eq=contrast=1.04:saturation=1.03"
}


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{proc.stderr[-2000:]}")
    return proc


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
    dur = max(1.0, float(scene["duration"]))
    fade_d = min(0.35, dur / 5.0)
    fade_out_st = max(0.0, dur - fade_d)

    footage_path = scene.get("footage_path")
    graphic_path = scene.get("graphic_path")

    if footage_path and Path(footage_path).exists():
        vf = (
            f"scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,fps=30,format=yuv420p,"
            f"{grade_filter},"
            f"fade=t=in:st=0:d={fade_d:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_d:.3f}"
        )
        run_ffmpeg([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(footage_path),
            "-t", f"{dur:.3f}",
            "-an",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p",
            str(out_clip)
        ])
        try:
            Path(footage_path).unlink()
        except OSError:
            pass
    elif graphic_path and Path(graphic_path).exists():
        frames = max(30, int(round(dur * 30)))
        vf = (
            f"scale=2040:1148,"
            f"zoompan=z='min(zoom+0.0005,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
            f"format=yuv420p,"
            f"fade=t=in:st=0:d={fade_d:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_d:.3f}"
        )
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(graphic_path),
            "-t", f"{dur:.3f}",
            "-an",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(out_clip)
        ])
    else:
        raise RuntimeError(f"Scene {scene['scene_id']} has neither footage nor graphic.")


def render_documentary(scene_plan, transcript_data, original_audio_path):
    update_status("editing_video", "প্রতিটি দৃশ্য সিনেম্যাটিক 1080p ফরম্যাটে সাজানো হচ্ছে...", percent=80)

    clips_dir = WORK / "scene_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    grade_filter = GRADE_FILTERS.get(scene_plan.get("color_grade", "cinematic_teal"), GRADE_FILTERS["cinematic_teal"])

    clip_paths = []
    for scene in scene_plan.get("scenes", []):
        clip_path = clips_dir / f"clip_{scene['scene_id']:03d}.mp4"
        _render_scene_clip(scene, clip_path, grade_filter)
        clip_paths.append(clip_path)

    concat_list = WORK / "concat_list.txt"
    concat_lines = [f"file '{p.resolve()}'" for p in clip_paths]
    concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    merged_video = WORK / "merged_video.mp4"
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(merged_video)
    ])

    for p in clip_paths:
        try:
            p.unlink()
        except OSError:
            pass

    srt_path = build_subtitles_srt(transcript_data)
    burn_subs = os.environ.get("BURN_SUBTITLES", "true").lower() == "true"
    enable_music = os.environ.get("ENABLE_BG_MUSIC", "true").lower() == "true"
    duration = float(transcript_data["duration"])

    update_status("rendering_final_video", "আপনার মূল ভয়েসের সাথে চূড়ান্ত 1080p MP4 রেন্ডার হচ্ছে...", percent=92)

    final_mp4 = WORK / "final_documentary.mp4"

    inputs = ["-i", str(merged_video), "-i", str(original_audio_path)]
    if enable_music:
        bg_wav = WORK / "bg_music.wav"
        prepare_background_music(scene_plan.get("mood", "documentary_ambient"), duration, bg_wav)
        inputs.extend(["-i", str(bg_wav)])
        audio_filter = "[1:a]aresample=48000,aformat=channel_layouts=stereo[voice];[2:a]volume=0.85[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
        audio_map = ["-map", "[aout]"]
    else:
        audio_filter = None
        audio_map = ["-map", "1:a:0"]

    cmd = ["ffmpeg", "-y"] + inputs
    if burn_subs and srt_path.exists() and srt_path.stat().st_size > 0:
        escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
        sub_style = "FontName=Noto Sans Bengali,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H64000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=36"
        vf = f"subtitles='{escaped_srt}':force_style='{sub_style}'"
        if audio_filter:
            cmd.extend(["-filter_complex", f"[0:v]{vf}[vout];{audio_filter}", "-map", "[vout]"] + audio_map)
        else:
            cmd.extend(["-vf", vf, "-map", "0:v:0"] + audio_map)
        cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"])
    else:
        if audio_filter:
            cmd.extend(["-filter_complex", audio_filter, "-map", "0:v:0"] + audio_map)
        else:
            cmd.extend(["-map", "0:v:0"] + audio_map)
        cmd.extend(["-c:v", "copy"])

    cmd.extend([
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        str(final_mp4)
    ])

    run_ffmpeg(cmd)
    return final_mp4, srt_path
