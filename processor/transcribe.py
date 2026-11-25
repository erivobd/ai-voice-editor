import json
import os
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel
from status import update_status, download_original_audio

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")
AUDIO_LANGUAGE = os.environ.get("AUDIO_LANGUAGE", "").strip() or None


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


def run_transcription():
    update_status("analyzing_voice", "আপনার রেডি ভয়েসওভার পরীক্ষা ও বিশ্লেষণ করা হচ্ছে...", percent=14)
    audio_path = download_original_audio()
    duration, sample_rate, channels = probe_audio(audio_path)

    update_status(
        "generating_transcript",
        f"বাক্যভিত্তিক নিখুঁত টাইমস্ট্যাম্প তৈরি হচ্ছে ({round(duration, 1)} সেকেন্ড)...",
        percent=22
    )

    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=AUDIO_LANGUAGE,
        beam_size=3,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500}
    )

    segments = []
    full_parts = []
    for idx, seg in enumerate(segments_iter):
        text = (seg.text or "").strip()
        if not text:
            continue
        words = []
        for w in (seg.words or []):
            wt = (w.word or "").strip()
            if wt:
                words.append({
                    "start": round(float(w.start), 3),
                    "end": round(float(w.end), 3),
                    "word": wt
                })
        segments.append({
            "id": idx,
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": text,
            "words": words
        })
        full_parts.append(text)

    if not segments:
        raise RuntimeError("অডিওতে কোনো স্পষ্ট কথা শনাক্ত করা যায়নি।")

    transcript_data = {
        "job_id": os.environ.get("JOB_ID", ""),
        "audio_file": audio_path.name,
        "duration": round(duration, 3),
        "sample_rate": sample_rate,
        "channels": channels,
        "detected_language": getattr(info, "language", AUDIO_LANGUAGE or "bn"),
        "language_probability": round(float(getattr(info, "language_probability", 0.0)), 3),
        "voice_preserved": True,
        "full_text": " ".join(full_parts),
        "segments": segments
    }

    out_path = WORK / "transcript.json"
    out_path.write_text(json.dumps(transcript_data, ensure_ascii=False, indent=2), encoding="utf-8")

    update_status(
        "generating_transcript",
        f"ট্রান্সক্রিপ্ট সম্পন্ন ({len(segments)}টি অংশ, ভাষা: {transcript_data['detected_language']})।",
        percent=32
    )
    return transcript_data, audio_path
