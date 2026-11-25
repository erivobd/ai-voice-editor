import json
import os
import subprocess
from typing import Dict, List, Tuple


def get_audio_duration(audio_path: str) -> float:
    """Return exact duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        audio_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {res.stderr}")
    data = json.loads(res.stdout)
    return float(data["format"]["duration"])


def transcribe_audio(audio_path: str) -> Tuple[str, float, List[Dict]]:
    """Transcribe audio with timestamps using faster-whisper."""
    duration = get_audio_duration(audio_path)
    model_size = os.environ.get("WHISPER_MODEL", "small")

    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_gen, _ = model.transcribe(audio_path, beam_size=3, vad_filter=True)

    segments: List[Dict] = []
    lines: List[str] = []
    for seg in segments_gen:
        text = seg.text.strip()
        if not text:
            continue
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": text,
        })
        lines.append(f"[{seg.start:.1f}s - {seg.end:.1f}s] {text}")

    transcript_text = "\n".join(lines) if lines else f"[0.0s - {duration:.1f}s] Documentary narration."
    return transcript_text, duration, segments
