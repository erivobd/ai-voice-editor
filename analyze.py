
import os
import re
import json
import math
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from google import genai
from google.genai import types

WORK = Path(os.environ.get("WORK_DIR", "/tmp/voice_job"))
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-transcribe")
MAX_PAUSE = 3.0
EDGE_PADDING = 0.06
MIN_MATCH_SCORE = 0.88
MAX_AUTO_CUT_RATIO = 0.40


def normalize(word):
    word = unicodedata.normalize("NFKC", str(word)).lower()
    return re.sub(r"[^\w]", "", word, flags=re.UNICODE)


def tokens(text):
    return [normalize(x) for x in re.findall(r"\S+", text) if normalize(x)]


def read_script():
    path = WORK / "script.txt"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig").strip()
    return [line.strip() for line in re.split(r"[\n।!?]+", text) if tokens(line)]


def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


def transcribe(audio):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    client = genai.Client(api_key=api_key)
    uploaded = client.files.upload(file=str(audio))

    prompt = """
Listen to the complete Bengali audio carefully.
Return ONLY valid JSON with this exact structure:
{
  "transcript": "complete verbatim transcript",
  "words": [
    {"word": "spoken word", "start": 0.0, "end": 0.4}
  ]
}
Requirements:
- Bengali script where appropriate.
- Include every audible spoken word, in original order.
- Give start and end timestamps in seconds for EACH word.
- Timestamps must refer to the original audio timeline.
- Do not invent words or timestamps.
- Do not rewrite, correct, or summarize the speaker.
- Include repetitions, mistakes, fillers and incomplete phrases.
- If a word timestamp is uncertain, do not guess it.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0
        )
    )

    data = parse_json(response.text)
    words = []

    for item in data.get("words", []):
        try:
            word = str(item["word"]).strip()
            start = float(item["start"])
            end = float(item["end"])
            if word and math.isfinite(start) and math.isfinite(end) and 0 <= start < end:
                words.append({
                    "word": word,
                    "norm": normalize(word),
                    "start": start,
                    "end": end
                })
        except (KeyError, TypeError, ValueError):
            continue

    words.sort(key=lambda x: x["start"])
    return str(data.get("transcript", "")), words


def find_line_matches(line, words):
    target = tokens(line)
    if not target:
        return []

    n = len(target)
    low = max(1, int(n * 0.70))
    high = max(low, int(n * 1.35))
    found = []

    for size in range(low, high + 1):
        for start in range(0, len(words) - size + 1):
            chunk = [w["norm"] for w in words[start:start + size]]
            if not all(chunk):
                continue

            score = SequenceMatcher(None, target, chunk, autojunk=False).ratio()
            if score >= MIN_MATCH_SCORE:
                found.append({
                    "start_index": start,
                    "end_index": start + size - 1,
                    "start": words[start]["start"],
                    "end": words[start + size - 1]["end"],
                    "score": score,
                    "word_count": size
                })

    # Remove near-identical overlapping windows.
    found.sort(key=lambda x: (-x["score"], abs(x["word_count"] - n)))
    unique = []

    for candidate in found:
        duplicate = False
        for old in unique:
            overlap = min(candidate["end"], old["end"]) - max(candidate["start"], old["start"])
            shorter = min(
                candidate["end"] - candidate["start"],
                old["end"] - old["start"]
            )
            if shorter > 0 and overlap / shorter > 0.65:
                duplicate = True
                break
        if not duplicate:
            unique.append(candidate)

    return sorted(unique, key=lambda x: x["start"])


def find_duplicate_take_cuts(lines, words):
    cuts = []
    details = []

    for line_number, line in enumerate(lines, 1):
        matches = find_line_matches(line, words)

        if len(matches) < 2:
            continue

        # Keep the most complete/highest matching occurrence.
        # If scores tie, keep the earlier take.
        matches.sort(key=lambda x: (-x["score"], x["start"]))
        keep = matches[0]

        for item in matches[1:]:
            if item["start"] >= keep["end"] or item["end"] <= keep["start"]:
                cuts.append({
                    "start": max(0, item["start"] - EDGE_PADDING),
                    "end": item["end"] + EDGE_PADDING,
                    "reason": "duplicate_script_line",
                    "script_line": line_number,
                    "match_score": round(item["score"], 3)
                })

        details.append({
            "script_line": line_number,
            "matches_found": len(matches),
            "kept_start": round(keep["start"], 3),
            "kept_end": round(keep["end"], 3),
            "kept_score": round(keep["score"], 3)
        })

    return cuts, details


def find_long_pause_cuts(words):
    cuts = []

    for left, right in zip(words, words[1:]):
        gap = right["start"] - left["end"]

        if gap > MAX_PAUSE:
            # Leave a total of MAX_PAUSE seconds between the spoken lines.
            remove_start = left["end"] + MAX_PAUSE / 2
            remove_end = right["start"] - MAX_PAUSE / 2

            if remove_end > remove_start:
                cuts.append({
                    "start": remove_start,
                    "end": remove_end,
                    "reason": "long_pause"
                })

    return cuts


def merge_cuts(cuts):
    valid = []
    for cut in cuts:
        try:
            a, b = float(cut["start"]), float(cut["end"])
            if math.isfinite(a) and math.isfinite(b) and b > a >= 0:
                valid.append({**cut, "start": a, "end": b})
        except (KeyError, TypeError, ValueError):
            pass

    valid.sort(key=lambda x: x["start"])
    merged = []

    for cut in valid:
        if merged and cut["start"] <= merged[-1]["end"] + 0.02:
            merged[-1]["end"] = max(merged[-1]["end"], cut["end"])
            merged[-1]["reasons"].append(cut.get("reason", "unknown"))
        else:
            merged.append({
                "start": cut["start"],
                "end": cut["end"],
                "reasons": [cut.get("reason", "unknown")]
            })

    return merged


def write_srt(words):
    def stamp(value):
        ms = int(round(value * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    lines = []
    for i, word in enumerate(words, 1):
        lines.extend([
            str(i),
            f"{stamp(word['start'])} --> {stamp(word['end'])}",
            word["word"],
            ""
        ])

    (WORK / "transcript.srt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    audio_files = sorted(WORK.glob("original_audio.*"))

    if len(audio_files) != 1:
        raise RuntimeError(
            f"Expected exactly one original_audio file, found {len(audio_files)}"
        )

    audio = audio_files[0]
    script_lines = read_script()
    transcript, words = transcribe(audio)

    if not words:
        raise RuntimeError(
            "Gemini did not return reliable word timestamps. "
            "No automatic cuts were made."
        )

    # Reject invalid or suspicious timestamps.
    previous_end = 0.0
    for word in words:
        if word["end"] <= word["start"]:
            raise RuntimeError("Invalid word timestamp received.")
        if word["start"] < previous_end - 0.15:
            raise RuntimeError("Overlapping or inconsistent word timestamps.")
        previous_end = word["end"]

    duplicate_cuts, duplicate_details = (
        find_duplicate_take_cuts(script_lines, words)
    )
    pause_cuts = find_long_pause_cuts(words)

    all_cuts = merge_cuts(duplicate_cuts + pause_cuts)

    # Never allow the automatic plan to remove too much audio.
    total_cut = sum(x["end"] - x["start"] for x in all_cuts)

    # Use a conservative duration estimate from the final word.
    estimated_duration = max(x["end"] for x in words)

    if estimated_duration > 0 and total_cut / estimated_duration > MAX_AUTO_CUT_RATIO:
        all_cuts = merge_cuts(pause_cuts)
        duplicate_cuts = []
        safety_note = (
            "Duplicate-take cuts were skipped because the proposed "
            "total cut duration exceeded the safety limit."
        )
    else:
        safety_note = (
            "Unmatched speech was reported but not automatically removed."
        )

    approved = []
    for cut in all_cuts:
        approved.append({
            "start": round(cut["start"], 3),
            "end": round(cut["end"], 3),
            "reason": ", ".join(cut["reasons"])
        })

    plan = {
        "approved_cuts": approved,
        "noise_reduction": "original",
        "automatic_speech_mismatch_cuts": False,
        "automatic_duplicate_take_cuts": bool(duplicate_cuts),
        "max_pause_seconds": MAX_PAUSE,
        "safety_mode": "conservative"
    }

    report = {
        "model": MODEL,
        "transcript": transcript,
        "script_lines": len(script_lines),
        "transcribed_word_count": len(words),
        "duplicate_take_candidates": duplicate_details,
        "long_pause_cuts": len(pause_cuts),
        "approved_cuts": approved,
        "safety_note": safety_note,
        "unmatched_speech_policy": "Report only; do not cut automatically."
    }

    (WORK / "approved_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (WORK / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    write_srt(words)

    print("Analysis completed.")
    print(f"Words transcribed: {len(words)}")
    print(f"Approved cuts: {len(approved)}")


if __name__ == "__main__":
    main()
