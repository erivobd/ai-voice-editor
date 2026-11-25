import subprocess
from pathlib import Path

MOOD_FREQS = {
    "documentary_ambient": (110.0, 164.81, 220.0),
    "mystery": (98.0, 146.83, 185.0),
    "science": (130.81, 196.0, 261.63),
    "history": (116.54, 174.61, 233.08),
    "inspiring": (146.83, 220.0, 293.66)
}


def prepare_background_music(mood, duration, out_wav):
    out_wav = Path(out_wav)
    repo_music_dir = Path(__file__).resolve().parent.parent / "assets" / "music"

    for ext in (".mp3", ".wav", ".m4a"):
        candidate = repo_music_dir / f"{mood}{ext}"
        if candidate.exists():
            cmd = [
                "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(candidate),
                "-t", f"{duration:.3f}",
                "-af", f"afade=t=in:st=0:d=2,afade=t=out:st={max(0, duration - 2.5):.3f}:d=2.5,volume=0.14",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return out_wav

    f1, f2, f3 = MOOD_FREQS.get(mood, MOOD_FREQS["documentary_ambient"])
    fade_out_start = max(0.0, duration - 2.5)
    expr = (
        f"aevalsrc="
        f"0.18*sin(2*PI*{f1}*t)+0.12*sin(2*PI*{f2}*t)+0.08*sin(2*PI*{f3}*t+0.4*sin(0.5*t))"
        f":s=48000:d={duration:.3f}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", expr,
        "-af", f"lowpass=f=650,afade=t=in:st=0:d=2.0,afade=t=out:st={fade_out_start:.3f}:d=2.5,volume=0.10",
        "-ac", "2", "-c:a", "pcm_s16le",
        str(out_wav)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_wav
