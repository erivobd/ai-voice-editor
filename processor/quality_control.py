"""Automated validation and visual storyboard export for the final documentary render."""
import base64
import html
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _run(command: List[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Quality check command failed: {proc.stderr[-1200:]}")
    return proc


def _rate(value: str) -> float:
    try:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else 0.0
    except (ValueError, AttributeError):
        return 0.0


def _fmt_tc(seconds: float) -> str:
    sec = max(0.0, float(seconds or 0.0))
    mins = int(sec // 60)
    rem = sec - mins * 60
    return f"{mins:02d}:{rem:05.2f}"


def validate_final_video(video_path: Path, expected_duration: float, report_path: Path) -> Dict[str, Any]:
    video_path = Path(video_path)
    if not video_path.exists() or video_path.stat().st_size < 100_000:
        raise RuntimeError("Final video is missing or unexpectedly small; export was not accepted.")

    probe = _run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height,avg_frame_rate,start_time,duration",
        "-of", "json", str(video_path)
    ])
    metadata = json.loads(probe.stdout or "{}")
    streams = metadata.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video_stream:
        raise RuntimeError("Final MP4 has no video stream.")
    if not audio_stream:
        raise RuntimeError("Final MP4 has no narration/audio stream.")

    actual_duration = float((metadata.get("format") or {}).get("duration") or 0.0)
    if actual_duration <= 0:
        actual_duration = float(video_stream.get("duration") or audio_stream.get("duration") or 0.0)
    expected_duration = float(expected_duration or 0.0)
    delta = abs(actual_duration - expected_duration)
    tolerance = max(2.5, expected_duration * 0.003)
    fps = _rate(video_stream.get("avg_frame_rate", "0/1"))
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)

    errors = []
    warnings = []
    if delta > tolerance:
        errors.append(f"Duration mismatch: audio={expected_duration:.3f}s, video={actual_duration:.3f}s (allowed {tolerance:.2f}s).")
    if (width, height) != (1920, 1080):
        errors.append(f"Unexpected resolution: {width}x{height}; expected 1920x1080.")
    if abs(fps - 30.0) > 0.15:
        errors.append(f"Unexpected frame rate: {fps:.3f} FPS; expected 30 FPS.")

    scan = _run([
        "ffmpeg", "-hide_banner", "-i", str(video_path),
        "-vf", "blackdetect=d=2.5:pix_th=0.10,freezedetect=n=-50dB:d=8",
        "-an", "-f", "null", "-"
    ])
    black_events = len(re.findall(r"black_start:", scan.stderr))
    freeze_events = len(re.findall(r"freeze_start:", scan.stderr))
    if black_events:
        warnings.append(f"Detected {black_events} possible extended black interval(s); review is automatic and report-only.")
    if freeze_events:
        warnings.append(f"Detected {freeze_events} possible frozen interval(s); still graphics may be intentional.")

    report = {
        "passed": not errors,
        "expected_duration_sec": round(expected_duration, 3),
        "actual_duration_sec": round(actual_duration, 3),
        "duration_delta_sec": round(delta, 3),
        "resolution": f"{width}x{height}",
        "fps": round(fps, 3),
        "has_video": True,
        "has_audio": True,
        "black_interval_count": black_events,
        "freeze_interval_count": freeze_events,
        "warnings": warnings,
        "errors": errors,
    }
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        raise RuntimeError("Final video quality validation failed: " + " ".join(errors))
    return report


def generate_storyboard(
    video_path: Path,
    scene_plan: Dict[str, Any],
    output_dir: Path,
    qc_report: Optional[Dict[str, Any]] = None,
) -> Path:
    """Extract mid-scene thumbnails and build a self-contained Bengali storyboard.html for visual QC."""
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    thumbs_dir = output_dir / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    scenes = scene_plan.get("scenes") or []
    title = html.escape(str(scene_plan.get("title") or "ডকুমেন্টারি স্টোরিবোর্ড"))
    total_dur = float(scene_plan.get("total_duration") or 0.0)
    cards_html = []

    for idx, sc in enumerate(scenes, start=1):
        st = float(sc.get("start", 0.0))
        en = float(sc.get("end", st + 1.0))
        mid = max(0.0, (st + en) / 2.0)
        thumb_path = thumbs_dir / f"scene_{idx:03d}.jpg"
        img_tag = '<div class="thumb-placeholder">থাম্বনেইল পাওয়া যায়নি</div>'
        if video_path.exists():
            proc = subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", f"{mid:.2f}", "-i", str(video_path),
                    "-frames:v", "1", "-vf", "scale=480:270:force_original_aspect_ratio=decrease",
                    "-q:v", "5", str(thumb_path)
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if proc.returncode == 0 and thumb_path.exists() and thumb_path.stat().st_size > 0:
                b64 = base64.b64encode(thumb_path.read_bytes()).decode("ascii")
                img_tag = f'<img src="data:image/jpeg;base64,{b64}" alt="দৃশ্য {idx}" loading="lazy" />'

        beat = html.escape(str(sc.get("story_beat") or "scene"))
        cam = html.escape(str(sc.get("camera_preset") or sc.get("motion_effect") or "CAM-PUSH"))
        txt_preset = html.escape(str(sc.get("text_preset") or "HDR-DROP"))
        tr = html.escape(str(sc.get("transition") or "TR-CUT"))
        music = html.escape(str(sc.get("music_mode") or "normal"))
        fx = html.escape(str(sc.get("visual_effect") or "none"))
        vtype = str(sc.get("visual_type") or "stock_footage")
        media_kind = str(sc.get("resolved_media_kind") or sc.get("media_preference") or "video")
        media_label = "গ্রাফিক" if vtype == "motion_graphic" else ("ছবি (Ken Burns)" if media_kind == "photo" else "HD ভিডিও")
        voice = html.escape(str(sc.get("narration_text") or (sc.get("graphic") or {}).get("heading") or ""))
        kws = ", ".join(html.escape(str(k)) for k in (sc.get("keywords") or []))

        cards_html.append(f"""
        <article class="card">
          <div class="thumb">{img_tag}<span class="badge">দৃশ্য {idx:02d} · {beat}</span>{f'<span class="fx-badge">{fx}</span>' if fx != 'none' else ''}</div>
          <div class="body">
            <div class="tc">{_fmt_tc(st)} – {_fmt_tc(en)} <span class="vtype">{html.escape(media_label)}</span></div>
            <p class="voice">{voice or "—"}</p>
            <div class="meta">
              <span><b>ক্যামেরা:</b> {cam}</span>
              <span><b>টেক্সট:</b> {txt_preset}</span>
              <span><b>ট্রানজিশন:</b> {tr}</span>
              <span><b>ইফেক্ট:</b> {fx}</span>
              <span><b>মিউজিক:</b> {music}</span>
            </div>
            {f'<div class="kws">কিওয়ার্ড: {kws}</div>' if kws else ''}
          </div>
        </article>
        """.strip())

    qc_status = "পাস" if (qc_report or {}).get("passed", True) else "সতর্কতা"
    qc_res = html.escape(str((qc_report or {}).get("resolution") or "1920x1080"))
    qc_fps = html.escape(str((qc_report or {}).get("fps") or "30"))
    html_doc = f"""<!doctype html>
<html lang="bn">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} — স্টোরিবোর্ড</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Hind Siliguri", "Noto Sans Bengali", system-ui, sans-serif; background: #0b0d12; color: #f3f4f6; line-height: 1.45; }}
    header {{ padding: 24px 28px; border-bottom: 1px solid #1f2937; background: #111827; }}
    header h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px; color: #cbd5e1; }}
    .summary span {{ background: #1e293b; padding: 4px 10px; border-radius: 6px; }}
    main {{ padding: 24px 28px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }}
    .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }}
    .thumb {{ position: relative; aspect-ratio: 16 / 9; background: #030712; overflow: hidden; }}
    .thumb img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .thumb-placeholder {{ display: flex; align-items: center; justify-content: center; height: 100%; color: #64748b; font-size: 13px; }}
    .badge {{ position: absolute; left: 10px; top: 10px; background: rgba(220, 38, 38, 0.92); color: #fff; font-size: 12px; font-weight: 700; padding: 3px 9px; border-radius: 999px; }}
    .fx-badge {{ position: absolute; right: 10px; top: 10px; background: rgba(245, 158, 11, 0.92); color: #111827; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 999px; }}
    .body {{ padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; flex: 1; }}
    .tc {{ display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8; font-weight: 600; }}
    .vtype {{ color: #38bdf8; }}
    .voice {{ margin: 0; font-size: 15px; color: #f8fafc; }}
    .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 10px; font-size: 12px; color: #cbd5e1; background: #0f172a; padding: 8px 10px; border-radius: 8px; }}
    .kws {{ font-size: 12px; color: #facc15; }}
  </style>
</head>
<body>
  <header>
    <h1>{title} — ভিজ্যুয়াল স্টোরিবোর্ড ও QC</h1>
    <div class="summary">
      <span>দৃশ্য সংখ্যা: {len(scenes)}</span>
      <span>মোট দৈর্ঘ্য: {_fmt_tc(total_dur)}</span>
      <span>রেজোলিউশন: {qc_res} @ {qc_fps} FPS</span>
      <span>QC: {qc_status}</span>
    </div>
  </header>
  <main>
    {''.join(cards_html)}
  </main>
</body>
</html>
"""
    out_html = output_dir / "storyboard.html"
    out_html.write_text(html_doc, encoding="utf-8")
    return out_html
