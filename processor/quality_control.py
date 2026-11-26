"""Automated validation for the final documentary render."""
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List


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

    # Visual anomaly scans are diagnostic rather than hard failures: dark scenes
    # and intentional still graphics can legitimately trigger these detectors.
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
