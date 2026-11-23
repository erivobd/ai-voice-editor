
import os
import json
import math
import subprocess
from pathlib import Path

WORK = Path(os.environ.get("WORK_DIR", "/tmp/voice_job"))
MIN_KEEP_SEGMENT = 0.08
MAX_CUT_RATIO = 0.60


def run(cmd):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if p.returncode:
        raise RuntimeError(f"FFmpeg failed: {p.stderr[-3000:]}")
    return p


def probe(path):
    p = run([
        "ffprobe", "-v", "error",
        "-show_entries",
        "format=duration:stream=sample_rate,channels",
        "-of", "json", str(path)
    ])

    data = json.loads(p.stdout)
    streams = data.get("streams", [])

    stream = next(
        (x for x in streams if "sample_rate" in x),
        None
    )

    if not stream:
        raise RuntimeError("Could not read audio stream information.")

    duration = float(data["format"]["duration"])
    sample_rate = int(stream["sample_rate"])
    channels = int(stream["channels"])

    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Invalid audio duration.")

    return duration, sample_rate, channels


def load_cuts(plan, duration):
    cuts = []

    for item in plan.get("approved_cuts", []):
        start = float(item["start"])
        end = float(item["end"])

        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end <= start
            or end > duration
        ):
            raise ValueError(
                f"Invalid cut interval: {start} - {end}"
            )

        cuts.append((start, end))

    cuts.sort()
    merged = []

    for start, end in cuts:
        if merged and start <= merged[-1][1] + 0.02:
            merged[-1] = (
                merged[-1][0],
                max(merged[-1][1], end)
            )
        else:
            merged.append((start, end))

    total_cut = sum(end - start for start, end in merged)

    if total_cut / duration > MAX_CUT_RATIO:
        raise ValueError(
            "Safety stop: the cut plan would remove more than "
            "60% of the original recording."
        )

    return merged


def build_keep_segments(cuts, duration):
    keep = []
    position = 0.0

    for start, end in cuts:
        if start - position >= MIN_KEEP_SEGMENT:
            keep.append((position, start))
        position = max(position, end)

    if duration - position >= MIN_KEEP_SEGMENT:
        keep.append((position, duration))

    if not keep:
        raise ValueError("The cut plan would remove the entire recording.")

    remaining = sum(end - start for start, end in keep)

    if remaining < max(1.0, duration * 0.05):
        raise ValueError("Too little audio would remain.")

    return keep


def render_audio(audio, keep, sample_rate, channels):
    filters = []
    labels = []

    for i, (start, end) in enumerate(keep):
        label = f"part{i}"
        labels.append(f"[{label}]")

        length = end - start
        fade = min(0.015, length / 4)

        filters.append(
            f"[0:a]"
            f"atrim=start={start:.6f}:end={end:.6f},"
            f"asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={fade:.5f},"
            f"afade=t=out:st={max(0, length-fade):.6f}:d={fade:.5f}"
            f"[{label}]"
        )

    filters.append(
        "".join(labels)
        + f"concat=n={len(keep)}:v=0:a=1[out]"
    )

    filter_complex = ";".join(filters)
    temp = WORK / "render_temp.wav"

    run([
        "ffmpeg", "-y",
        "-i", str(audio),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", "pcm_s24le",
        str(temp)
    ])

    # High-quality MP3 export.
    run([
        "ffmpeg", "-y",
        "-i", str(temp),
        "-c:a", "libmp3lame",
        "-b:a", "320k",
        str(WORK / "final_edited.mp3")
    ])

    # Keep the lossless WAV output.
    final_wav = WORK / "final_edited.wav"
    temp.replace(final_wav)

    return final_wav


def main():
    WORK.mkdir(parents=True, exist_ok=True)

    audio_files = sorted(WORK.glob("original_audio.*"))

    if len(audio_files) != 1:
        raise RuntimeError(
            f"Expected exactly one original audio file, found {len(audio_files)}"
        )

    audio = audio_files[0]
    plan_path = WORK / "approved_plan.json"

    if not plan_path.exists():
        raise RuntimeError("approved_plan.json is missing.")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    duration, sample_rate, channels = probe(audio)
    cuts = load_cuts(plan, duration)
    keep = build_keep_segments(cuts, duration)

    render_audio(audio, keep, sample_rate, channels)

    final_duration = sum(end - start for start, end in keep)
    saved = duration - final_duration

    report = {
        "original_duration_sec": round(duration, 3),
        "final_duration_sec": round(final_duration, 3),
        "time_saved_sec": round(saved, 3),
        "merged_cuts_count": len(cuts),
        "sample_rate": sample_rate,
        "channels": channels,
        "wav_codec": "pcm_s24le",
        "mp3_bitrate": "320k",
        "noise_reduction_applied": False,
        "voice_processing": "None",
        "note": (
            "No pitch shift, time stretch, voice conversion, "
            "voice generation, or noise reduction was applied."
        )
    }

    (WORK / "editing_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Rendering completed successfully.")
    print(f"Original: {duration:.2f} seconds")
    print(f"Final: {final_duration:.2f} seconds")
    print(f"Saved: {saved:.2f} seconds")


if __name__ == "__main__":
    main()
