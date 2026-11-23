
import os
import re
import json
import math
import subprocess
import unicodedata

from pathlib import Path
from difflib import SequenceMatcher
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

WORK = Path(os.environ.get("WORK_DIR", "/tmp/voice_job"))

MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.5-transcribe"
)

MAX_PAUSE = 3.0
EDGE_PADDING = 0.06
MIN_MATCH_SCORE = 0.92
MAX_AUTO_CUT_RATIO = 0.40
MIN_KEEP_DURATION = 0.08


# ============================================================
# BASIC HELPERS
# ============================================================

def log(message):
    print(f"[AI Voice Editor] {message}", flush=True)


def normalize(word):
    word = unicodedata.normalize("NFKC", str(word)).lower()
    return re.sub(r"[^\w]", "", word, flags=re.UNICODE)


def tokens(text):
    result = []

    for item in re.findall(r"\S+", str(text)):
        value = normalize(item)

        if value:
            result.append(value)

    return result


def run(cmd):
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed:\n{result.stderr[-2500:]}"
        )

    return result


def get_audio_duration(audio):
    result = run([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio)
    ])

    duration = float(result.stdout.strip())

    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Could not determine audio duration.")

    return duration


def read_script():
    path = WORK / "script.txt"

    if not path.exists():
        log("No script.txt found. Duplicate-line detection disabled.")
        return []

    content = path.read_text(
        encoding="utf-8-sig"
    ).strip()

    lines = re.split(r"[\n।!?]+", content)

    return [
        line.strip()
        for line in lines
        if tokens(line)
    ]


def to_plain(value):
    """Convert SDK response objects into ordinary dictionaries."""

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(k): to_plain(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]

    if hasattr(value, "model_dump"):
        try:
            return to_plain(value.model_dump(exclude_none=True))
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            return to_plain(vars(value))
        except Exception:
            pass

    return str(value)


# ============================================================
# GEMINI TIMESTAMP HELPERS
# ============================================================

def to_seconds(value):
    if isinstance(value, (int, float)):
        result = float(value)

    else:
        text = str(value).strip()

        # Supports timestamps such as 1.25s.
        match = re.fullmatch(
            r"([0-9]+(?:\.[0-9]+)?)\s*s?",
            text
        )

        if not match:
            raise ValueError(
                f"Unsupported timestamp format: {value}"
            )

        result = float(match.group(1))

    if not math.isfinite(result):
        raise ValueError("Non-finite timestamp.")

    return result


def find_word_annotations(data):
    """Find word_info annotations anywhere in the SDK response."""

    found = []

    def walk(value):
        if isinstance(value, dict):

            annotation_type = value.get("type")

            if annotation_type == "word_info":
                found.append(value)

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)

    return found


# ============================================================
# GEMINI TRANSCRIPTION
# ============================================================

def transcribe(audio):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from environment variables."
        )

    client = genai.Client(
        api_key=api_key,
        http_options={
            "api_version": "v1beta"
        }
    )

    log("Uploading original audio to Gemini...")

    uploaded = client.files.upload(
        file=str(audio)
    )

    file_uri = getattr(uploaded, "uri", None)

    mime_type = (
        getattr(uploaded, "mime_type", None)
        or getattr(uploaded, "mimeType", None)
    )

    if not file_uri:
        raise RuntimeError(
            "Gemini file upload did not return a file URI."
        )

    if not mime_type:
        raise RuntimeError(
            "Gemini file upload did not return a MIME type."
        )

    log(f"Audio uploaded. MIME type: {mime_type}")
    log(f"Starting transcription with {MODEL}...")

    response = client.interactions.create(
        model=MODEL,

        input=[
            {
                "type": "audio",
                "uri": file_uri,
                "mime_type": mime_type
            }
        ],

        generation_config={
            "transcription_config": {
                "language_codes": ["bn-BD"],
                "mode": {
                    "type": "verbatim",
                    "timestamp_granularities": ["word"]
                }
            }
        },

        store=False
    )

    response_data = to_plain(response)

    if not isinstance(response_data, dict):
        raise RuntimeError(
            "Gemini returned an unexpected response format."
        )

    status = response_data.get("status")

    if status and status != "completed":
        raise RuntimeError(
            f"Gemini transcription did not complete. Status: {status}"
        )

    annotations = find_word_annotations(response_data)

    words = []

    for annotation in annotations:

        try:
            word = str(
                annotation.get("text")
                or annotation.get("word")
                or ""
            ).strip()

            start_value = (
                annotation.get("start_offset")
                or annotation.get("startOffset")
            )

            end_value = (
                annotation.get("end_offset")
                or annotation.get("endOffset")
            )

            start = to_seconds(start_value)
            end = to_seconds(end_value)

            if not word:
                continue

            if not (0 <= start < end):
                continue

            words.append({
                "word": word,
                "norm": normalize(word),
                "start": start,
                "end": end
            })

        except (TypeError, ValueError):
            continue

    words.sort(key=lambda item: item["start"])

    if not words:
        raise RuntimeError(
            "Gemini returned no usable word timestamps. "
            "Automatic editing stopped to protect the original recording."
        )

    # Get transcript text from the response if available.
    transcript = ""

    for key in ("output_text", "text"):
        value = response_data.get(key)

        if isinstance(value, str) and value.strip():
            transcript = value.strip()
            break

    if not transcript:
        transcript = " ".join(
            item["word"] for item in words
        )

    log(f"Transcription completed: {len(words)} words.")

    return transcript, words


# ============================================================
# TIMESTAMP VALIDATION
# ============================================================

def validate_words(words, duration):

    previous_end = 0.0

    for item in words:

        start = item["start"]
        end = item["end"]

        if end > duration + 0.5:
            raise RuntimeError(
                "Gemini returned a timestamp beyond the audio duration."
            )

        if start < previous_end - 0.10:
            raise RuntimeError(
                "Gemini returned overlapping or inconsistent word timestamps. "
                "Automatic editing stopped."
            )

        if end <= start:
            raise RuntimeError(
                "Invalid word timestamp detected."
            )

        previous_end = end

    # Clip tiny timestamp overrun to the actual duration.
    for item in words:
        item["end"] = min(item["end"], duration)


# ============================================================
# SCRIPT LINE MATCHING
# ============================================================

def find_line_matches(line, words):

    target = tokens(line)

    if not target:
        return []

    count = len(target)

    # Only search around the expected sentence length.
    minimum = max(1, int(count * 0.90))
    maximum = max(minimum, int(count * 1.10))

    candidates = []

    for size in range(minimum, maximum + 1):

        for start_index in range(
            0,
            len(words) - size + 1
        ):

            chunk = [
                item["norm"]
                for item in words[start_index:start_index + size]
            ]

            if not all(chunk):
                continue

            score = SequenceMatcher(
                None,
                target,
                chunk,
                autojunk=False
            ).ratio()

            if score < MIN_MATCH_SCORE:
                continue

            candidates.append({
                "start_index": start_index,
                "end_index": start_index + size - 1,
                "start": words[start_index]["start"],
                "end": words[start_index + size - 1]["end"],
                "score": score,
                "word_count": size
            })

    # Highest score first.
    candidates.sort(
        key=lambda item: (
            -item["score"],
            abs(item["word_count"] - count),
            item["start"]
        )
    )

    unique = []

    for candidate in candidates:

        overlapping = False

        for old in unique:

            overlap = (
                min(candidate["end"], old["end"])
                - max(candidate["start"], old["start"])
            )

            shorter = min(
                candidate["end"] - candidate["start"],
                old["end"] - old["start"]
            )

            if shorter > 0 and overlap / shorter > 0.65:
                overlapping = True
                break

        if not overlapping:
            unique.append(candidate)

    return sorted(
        unique,
        key=lambda item: item["start"]
    )


# ============================================================
# DUPLICATE TAKE DETECTION
# ============================================================

def find_duplicate_take_cuts(lines, words, duration):

    cuts = []
    details = []

    for line_number, line in enumerate(lines, 1):

        matches = find_line_matches(
            line,
            words
        )

        if len(matches) < 2:
            continue

        matches.sort(
            key=lambda item: (
                -item["score"],
                abs(item["word_count"] - len(tokens(line))),
                item["start"]
            )
        )

        keep = matches[0]
        removed = []

        for item in matches[1:]:

            # Ignore any overlapping candidate.
            if (
                item["start"] < keep["end"]
                and item["end"] > keep["start"]
            ):
                continue

            start = max(
                0.0,
                item["start"] - EDGE_PADDING
            )

            end = min(
                duration,
                item["end"] + EDGE_PADDING
            )

            if end - start < MIN_KEEP_DURATION:
                continue

            cuts.append({
                "start": start,
                "end": end,
                "reason": "duplicate_script_line",
                "script_line": line_number,
                "match_score": round(item["score"], 3)
            })

            removed.append({
                "start": round(item["start"], 3),
                "end": round(item["end"], 3),
                "score": round(item["score"], 3)
            })

        details.append({
            "script_line": line_number,
            "matches_found": len(matches),
            "kept_start": round(keep["start"], 3),
            "kept_end": round(keep["end"], 3),
            "kept_score": round(keep["score"], 3),
            "removed_candidates": removed
        })

    return cuts, details


# ============================================================
# LONG PAUSE DETECTION
# ============================================================

def find_long_pause_cuts(words, duration):

    cuts = []

    for left, right in zip(words, words[1:]):

        gap = right["start"] - left["end"]

        if gap <= MAX_PAUSE:
            continue

        # Preserve a total gap of MAX_PAUSE seconds.
        remove_start = left["end"] + MAX_PAUSE / 2
        remove_end = right["start"] - MAX_PAUSE / 2

        remove_start = max(0.0, remove_start)
        remove_end = min(duration, remove_end)

        if remove_end > remove_start:

            cuts.append({
                "start": remove_start,
                "end": remove_end,
                "reason": "long_pause"
            })

    return cuts


# ============================================================
# CUT MERGING
# ============================================================

def merge_cuts(cuts, duration):

    valid = []

    for cut in cuts:

        try:
            start = float(cut["start"])
            end = float(cut["end"])

            if (
                math.isfinite(start)
                and math.isfinite(end)
                and 0 <= start < end <= duration
            ):
                valid.append({
                    **cut,
                    "start": start,
                    "end": end
                })

        except (KeyError, TypeError, ValueError):
            continue

    valid.sort(
        key=lambda item: item["start"]
    )

    merged = []

    for cut in valid:

        if (
            merged
            and cut["start"] <= merged[-1]["end"] + 0.02
        ):

            merged[-1]["end"] = max(
                merged[-1]["end"],
                cut["end"]
            )

            merged[-1]["reasons"].append(
                cut.get("reason", "unknown")
            )

        else:

            merged.append({
                "start": cut["start"],
                "end": cut["end"],
                "reasons": [
                    cut.get("reason", "unknown")
                ]
            })

    return merged


# ============================================================
# SUBTITLE GENERATION
# ============================================================

def write_srt(words):

    def stamp(value):

        milliseconds = int(round(value * 1000))

        hours, milliseconds = divmod(
            milliseconds,
            3600000
        )

        minutes, milliseconds = divmod(
            milliseconds,
            60000
        )

        seconds, milliseconds = divmod(
            milliseconds,
            1000
        )

        return (
            f"{hours:02}:"
            f"{minutes:02}:"
            f"{seconds:02},"
            f"{milliseconds:03}"
        )

    output = []

    for index, item in enumerate(words, 1):

        output.extend([
            str(index),

            (
                f"{stamp(item['start'])}"
                f" --> "
                f"{stamp(item['end'])}"
            ),

            item["word"],
            ""
        ])

    (WORK / "transcript.srt").write_text(
        "\n".join(output),
        encoding="utf-8"
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def main():

    WORK.mkdir(
        parents=True,
        exist_ok=True
    )

    log("Starting audio analysis...")

    audio_files = sorted(
        WORK.glob("original_audio.*")
    )

    if len(audio_files) != 1:
        raise RuntimeError(
            f"Expected exactly one original_audio file, "
            f"found {len(audio_files)}"
        )

    audio = audio_files[0]

    duration = get_audio_duration(audio)

    log(f"Original audio duration: {duration:.2f} seconds")

    script_lines = read_script()

    log(f"Script lines loaded: {len(script_lines)}")

    transcript, words = transcribe(audio)

    validate_words(
        words,
        duration
    )

    # Detect repeated complete script lines.
    duplicate_cuts, duplicate_details = (
        find_duplicate_take_cuts(
            script_lines,
            words,
            duration
        )
    )

    # Detect gaps longer than three seconds.
    pause_cuts = find_long_pause_cuts(
        words,
        duration
    )

    # Combine all proposed cuts.
    all_cuts = merge_cuts(
        duplicate_cuts + pause_cuts,
        duration
    )

    total_cut = sum(
        item["end"] - item["start"]
        for item in all_cuts
    )

    # Safety limit.
    if total_cut / duration > MAX_AUTO_CUT_RATIO:

        log(
            "Safety limit reached. "
            "Duplicate-line cuts have been disabled."
        )

        all_cuts = merge_cuts(
            pause_cuts,
            duration
        )

        duplicate_cuts = []

        safety_note = (
            "Duplicate cuts were skipped because the proposed "
            "total cut duration exceeded the safety limit."
        )

    else:

        safety_note = (
            "Only high-confidence repeated script-line candidates "
            "and pauses longer than three seconds were considered."
        )

    approved = []

    for item in all_cuts:

        approved.append({
            "start": round(item["start"], 3),
            "end": round(item["end"], 3),
            "reason": ", ".join(item["reasons"])
        })

    # Render plan.
    plan = {
        "approved_cuts": approved,

        "noise_reduction": "original",

        "automatic_speech_mismatch_cuts": False,

        "automatic_duplicate_take_cuts": bool(
            duplicate_cuts
        ),

        "max_pause_seconds": MAX_PAUSE,

        "safety_mode": "conservative"
    }

    # Analysis report.
    report = {
        "model": MODEL,

        "original_audio": audio.name,

        "original_duration_sec": round(
            duration,
            3
        ),

        "transcript": transcript,

        "script_lines": len(script_lines),

        "transcribed_word_count": len(words),

        "duplicate_take_candidates": duplicate_details,

        "long_pause_candidates": len(pause_cuts),

        "approved_cuts": approved,

        "total_cut_seconds": round(
            sum(
                item["end"] - item["start"]
                for item in approved
            ),
            3
        ),

        "safety_note": safety_note,

        "unmatched_speech_policy": (
            "Unmatched speech is reported only. "
            "It is not automatically removed."
        ),

        "voice_preservation": (
            "No pitch shift, speed change, time stretch, "
            "voice conversion or voice generation."
        )
    }

    (WORK / "approved_plan.json").write_text(
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    (WORK / "report.json").write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    write_srt(words)

    log("Analysis completed successfully.")

    log(f"Words transcribed: {len(words)}")

    log(f"Approved cuts: {len(approved)}")

    log("Generated report.json")

    log("Generated approved_plan.json")

    log("Generated transcript.srt")


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        log(f"ANALYSIS FAILED: {error}")

        raise
