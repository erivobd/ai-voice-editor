
import os
import re
import json
import mimetypes
import difflib
import unicodedata
import subprocess
from pathlib import Path
from google import genai

WORK = Path(os.environ.get("WORK_DIR", "/tmp/voice_job"))
MODEL = "gemini-3.5-transcribe"
MAX_PAUSE = 3.0
EDGE_PADDING = 0.06


def run(cmd):
    p = subprocess.run(
        cmd, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )
    if p.returncode:
        raise RuntimeError(p.stderr[-2500:])
    return p


def one(pattern):
    found = sorted(WORK.glob(pattern))
    if len(found) != 1:
        raise RuntimeError(
            f"Expected exactly one {pattern}, found {len(found)}"
        )
    return found[0]


def probe(audio):
    p = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=sample_rate,channels",
        "-of", "json", str(audio)
    ])
    data = json.loads(p.stdout)
    stream = next(
        (s for s in data.get("streams", []) if "sample_rate" in s), {}
    )
    return (
        float(data["format"]["duration"]),
        int(stream.get("sample_rate", 48000)),
        int(stream.get("channels", 1))
    )


def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.replace("\u200c", "").replace("\u200d", "")
    text = text.lower()
    return re.findall(r"[\w]+", text, flags=re.UNICODE)


def read_script():
    path = WORK / "script.txt"
    if not path.exists():
        return [], []

    content = path.read_text(
        encoding="utf-8-sig", errors="replace"
    )

    lines = [
        x.strip() for x in
        re.split(r"(?<=[।!?])\s+|\n+", content)
        if x.strip()
    ]

    tokens = []
    for line in lines:
        tokens.extend(normalize(line))

    return lines, tokens


def seconds(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def get_attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def transcribe(audio):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    client = genai.Client(
        api_key=api_key,
        http_options={"api_version": "v1beta"}
    )

    uploaded = client.files.upload(file=str(audio))

    response = client.interactions.create(
        model=MODEL,
        input=[uploaded],
        generation_config={
            "transcription_config": {
                "language_codes": ["bn-BD"],
                "mode": {
                    "type": "verbatim",
                    "timestamp_granularities": ["word"]
                }
            }
        }
    )

    words = []

    for step in get_attr(response, "steps", []) or []:
        for content in get_attr(step, "content", []) or []:
            for annotation in get_attr(
                content, "annotations", []
            ) or []:

                if get_attr(annotation, "type") != "word_info":
                    continue

                word = get_attr(annotation, "text", "")
                start = seconds(
                    get_attr(annotation, "start_offset")
                )
                end = seconds(
                    get_attr(annotation, "end_offset")
                )

                if word and start is not None and end is not None:
                    if end > start:
                        words.append({
                            "text": str(word),
                            "start": round(start, 3),
                            "end": round(end, 3)
                        })

    words.sort(key=lambda x: x["start"])

    if not words:
        raise RuntimeError(
            "Gemini returned no word timestamps. "
            "No audio cuts will be created."
        )

    return words, get_attr(response, "output_text", "") or ""


def find_unmatched_cuts(script_tokens, words):
    if not script_tokens:
        return []

    spoken_tokens = []
    spoken_word_indexes = []

    for i, word in enumerate(words):
        tokens = normalize(word["text"])
        for token in tokens:
            spoken_tokens.append(token)
            spoken_word_indexes.append(i)

    matcher = difflib.SequenceMatcher(
        None, script_tokens, spoken_tokens, autojunk=False
    )

    unmatched = set()

    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            for index in range(b1, b2):
                unmatched.add(spoken_word_indexes[index])

    # Only remove clear multi-word unmatched passages.
    # A single uncertain word is preserved.
    groups = []
    for index in sorted(unmatched):
        if groups and index <= groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])

    cuts = []

    for group in groups:
        if len(group) < 2:
            continue

        first = words[group[0]]
        last = words[group[-1]]

        cuts.append({
            "start": max(0, first["start"] - EDGE_PADDING),
            "end": last["end"] + EDGE_PADDING,
            "reason": "script_mismatch_or_duplicate"
        })

    return cuts


def find_long_pause_cuts(words, duration):
    cuts = []

    for previous, current in zip(words, words[1:]):
        gap = current["start"] - previous["end"]

        if gap > MAX_PAUSE:
            start = previous["end"] + MAX_PAUSE / 2
            end = current["start"] - MAX_PAUSE / 2

            if end > start:
                cuts.append({
                    "start": start,
                    "end": end,
                    "reason": "pause_over_3_seconds"
                })

    return cuts


def merge_cuts(cuts, duration):
    valid = []

    for cut in cuts:
        start = max(0.0, float(cut["start"]))
        end = min(duration, float(cut["end"]))

        if end > start:
            valid.append((start, end, cut["reason"]))

    valid.sort(key=lambda x: x[0])

    merged = []

    for start, end, reason in valid:
        if merged and start <= merged[-1]["end"] + 0.02:
            merged[-1]["end"] = max(merged[-1]["end"], end)
            merged[-1]["reasons"].add(reason)
        else:
            merged.append({
                "start": start,
                "end": end,
                "reasons": {reason}
            })

    return [
        {
            "start": round(x["start"], 3),
            "end": round(x["end"], 3),
            "reason": ", ".join(sorted(x["reasons"]))
        }
        for x in merged
    ]


def write_srt(words):
    lines = []
    group_size = 7

    for i in range(0, len(words), group_size):
        group = words[i:i + group_size]
        start = group[0]["start"]
        end = group[-1]["end"]

        def stamp(value):
            ms = int(round(value * 1000))
            h, ms = divmod(ms, 3600000)
            m, ms = divmod(ms, 60000)
            s, ms = divmod(ms, 1000)
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        text = " ".join(x["text"] for x in group)

        lines.extend([
            str(i // group_size + 1),
            f"{stamp(start)} --> {stamp(end)}",
            text,
            ""
        ])

    (WORK / "transcript.srt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main():
    WORK.mkdir(parents=True, exist_ok=True)

    audio = one("original_audio.*")
    duration, sample_rate, channels = probe(audio)

    script_lines, script_tokens = read_script()

    print("Uploading audio to Gemini...")
    words, full_text = transcribe(audio)

    print(f"Gemini recognized {len(words)} words.")

    mismatch_cuts = find_unmatched_cuts(
        script_tokens, words
    )

    pause_cuts = find_long_pause_cuts(
        words, duration
    )

    all_cuts = merge_cuts(
        mismatch_cuts + pause_cuts, duration
    )

    approved_plan = {
        "approved_cuts": all_cuts,
        "noise_reduction": "original",
        "max_pause_seconds": MAX_PAUSE,
        "preserve_original_voice": True
    }

    (WORK / "approved_plan.json").write_text(
        json.dumps(
            approved_plan, ensure_ascii=False, indent=2
        ),
        encoding="utf-8"
    )

    report = {
        "job_id": os.environ.get("JOB_ID", ""),
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "model": MODEL,
        "transcript_text": full_text,
        "transcript": words,
        "script_lines": script_lines,
        "summary": {
            "recognized_words": len(words),
            "script_words": len(script_tokens),
            "mismatch_cut_groups": len(mismatch_cuts),
            "long_pause_cuts": len(pause_cuts),
            "total_cut_intervals": len(all_cuts),
            "max_pause_seconds": MAX_PAUSE
        },
        "note": (
            "Original voice is preserved. "
            "No voice generation, pitch shift, "
            "or speed change is applied. "
            "Single uncertain mismatched words are preserved."
        )
    }

    (WORK / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    write_srt(words)

    print("Analysis completed.")
    print(f"Cut intervals: {len(all_cuts)}")


if __name__ == "__main__":
    main()
