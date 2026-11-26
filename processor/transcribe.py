import json
import os
import re
import subprocess
from pathlib import Path
from status import update_status, download_original_audio, download_custom_srt

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")
AUDIO_LANGUAGE = (os.environ.get("AUDIO_LANGUAGE", "bn") or "bn").strip()


def run_cmd(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr[-1500:]}")
    return proc


def probe_audio(audio_path):
    proc = run_cmd([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=sample_rate,channels",
        "-of", "json",
        str(audio_path)
    ])
    data = json.loads(proc.stdout)
    duration = float(data.get("format", {}).get("duration", 0.0))
    if duration <= 0:
        raise RuntimeError("আপলোড করা অডিওর দৈর্ঘ্য সঠিক নয়।")
    stream = next((s for s in data.get("streams", []) if "sample_rate" in s), {})
    return duration, int(stream.get("sample_rate", 48000)), int(stream.get("channels", 1))


def sanitize_bengali_text(text: str) -> str:
    cleaned = re.sub(r"[\u0900-\u097F]+", "", str(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _parse_srt_timestamp(ts_str: str) -> float:
    ts_str = ts_str.strip().replace(",", ".")
    parts = ts_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600.0 + float(m) * 60.0 + float(s)
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60.0 + float(s)
    return float(ts_str)


def parse_srt_or_script(raw_text: str, total_duration: float):
    text = raw_text.replace("\r\n", "\n").strip()
    if not text:
        return []

    segments = []
    time_line_re = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)\s*-->\s*(\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)"
    )

    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        ts_idx = next((i for i, ln in enumerate(lines) if time_line_re.search(ln)), None)
        if ts_idx is not None:
            m = time_line_re.search(lines[ts_idx])
            start_s = max(0.0, _parse_srt_timestamp(m.group(1)))
            end_s = max(start_s + 0.8, _parse_srt_timestamp(m.group(2)))
            body = sanitize_bengali_text(" ".join(lines[ts_idx + 1 :]))
            if body:
                segments.append({
                    "id": len(segments),
                    "start": round(min(start_s, max(0.0, total_duration - 0.5)), 3),
                    "end": round(min(end_s, total_duration), 3),
                    "text": body,
                    "words": []
                })

    if segments:
        return segments

    non_index_lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s or s.isdigit():
            continue
        cleaned = sanitize_bengali_text(s)
        if cleaned:
            non_index_lines.append(cleaned)

    if not non_index_lines:
        return []

    step = total_duration / len(non_index_lines)
    for i, line_txt in enumerate(non_index_lines):
        st = round(i * step, 3)
        en = round(total_duration if i == len(non_index_lines) - 1 else (i + 1) * step, 3)
        segments.append({
            "id": i,
            "start": st,
            "end": max(st + 0.5, en),
            "text": line_txt,
            "words": []
        })
    return segments


def run_transcription():
    update_status("analyzing_voice", "আপনার রেডি ভয়েসওভার পরীক্ষা ও বিশ্লেষণ করা হচ্ছে...", percent=14)
    audio_path = download_original_audio()
    duration, sample_rate, channels = probe_audio(audio_path)

    custom_srt_path = download_custom_srt()
    if custom_srt_path and custom_srt_path.exists():
        update_status(
            "generating_transcript",
            "কাস্টম SRT/স্ক্রিপ্ট শনাক্ত হয়েছে — Whisper স্কিপ করে টাইমস্ট্যাম্প প্রস্তুত করা হচ্ছে...",
            percent=28
        )
        raw_srt = custom_srt_path.read_text(encoding="utf-8", errors="replace")
        segments = parse_srt_or_script(raw_srt, duration)
        if segments:
            full_text = " ".join(s["text"] for s in segments)
            transcript_data = {
                "job_id": os.environ.get("JOB_ID", ""),
                "audio_file": audio_path.name,
                "duration": round(duration, 3),
                "sample_rate": sample_rate,
                "channels": channels,
                "detected_language": AUDIO_LANGUAGE,
                "language_probability": 1.0,
                "source": "custom_srt",
                "voice_preserved": True,
                "full_text": full_text,
                "segments": segments
            }
            out_path = WORK / "transcript.json"
            out_path.write_text(json.dumps(transcript_data, ensure_ascii=False, indent=2), encoding="utf-8")
            update_status(
                "generating_transcript",
                f"কাস্টম SRT থেকে {len(segments)}টি অংশ লোড সম্পন্ন হয়েছে।",
                percent=34
            )
            return transcript_data, audio_path

    from faster_whisper import WhisperModel

    update_status(
        "generating_transcript",
        f"বাংলা (bn) Whisper দিয়ে নিখুঁত টাইমস্ট্যাম্প তৈরি হচ্ছে ({round(duration, 1)} সেকেন্ড)...",
        percent=22
    )

    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=AUDIO_LANGUAGE,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 450}
    )

    segments = []
    full_parts = []
    for seg in segments_iter:
        text = sanitize_bengali_text(seg.text or "")
        if not text:
            continue
        words = []
        for w in (seg.words or []):
            wt = sanitize_bengali_text(w.word or "")
            if wt:
                words.append({
                    "start": round(float(w.start), 3),
                    "end": round(float(w.end), 3),
                    "word": wt
                })
        segments.append({
            "id": len(segments),
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": text,
            "words": words
        })
        full_parts.append(text)

    if not segments:
        raise RuntimeError("অডিওতে কোনো স্পষ্ট বাংলা কথা শনাক্ত করা যায়নি।")

    transcript_data = {
        "job_id": os.environ.get("JOB_ID", ""),
        "audio_file": audio_path.name,
        "duration": round(duration, 3),
        "sample_rate": sample_rate,
        "channels": channels,
        "detected_language": AUDIO_LANGUAGE,
        "language_probability": round(float(getattr(info, "language_probability", 0.95)), 3),
        "source": "whisper_bn",
        "voice_preserved": True,
        "full_text": " ".join(full_parts),
        "segments": segments
    }

    out_path = WORK / "transcript.json"
    out_path.write_text(json.dumps(transcript_data, ensure_ascii=False, indent=2), encoding="utf-8")

    update_status(
        "generating_transcript",
        f"ট্রান্সক্রিপ্ট সম্পন্ন ({len(segments)}টি অংশ, ভাষা: {AUDIO_LANGUAGE})।",
        percent=34
    )
    return transcript_data, audio_path
