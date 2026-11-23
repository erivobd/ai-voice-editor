import os, re, json, glob, subprocess, difflib, unicodedata
from pathlib import Path
from faster_whisper import WhisperModel

WORK = Path(os.environ.get("WORK_DIR", "/tmp/voice_job"))
MODEL = os.environ.get("WHISPER_MODEL", "small")
LANGUAGE = "bn"

def run(cmd, check=True):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and p.returncode:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr[-2500:]}")
    return p

def one(pattern):
    found = sorted(WORK.glob(pattern))
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one {pattern}, found {len(found)}")
    return found[0]

def probe(audio):
    p = run(["ffprobe","-v","error","-show_entries","format=duration:stream=sample_rate,channels","-of","json",str(audio)])
    d = json.loads(p.stdout)
    stream = next((s for s in d.get("streams",[]) if "sample_rate" in s), {})
    return float(d["format"]["duration"]), int(stream.get("sample_rate",48000)), int(stream.get("channels",1))

def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).replace("\u200c","").replace("\u200d","")
    s = re.sub(r"[।!?.,;:()[\]{}\"'“”‘’\-—–]", " ", s)
    s = re.sub(r"\s+"," ",s).strip().lower()
    return s

def similarity(a,b):
    return difflib.SequenceMatcher(None,norm(a),norm(b)).ratio()

def read_script():
    p = WORK / "script.txt"
    if not p.exists(): return []
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    return [x.strip() for x in re.split(r"(?<=[।!?])\s+|\n+", text) if x.strip()]

def main():
    WORK.mkdir(parents=True, exist_ok=True)
    audio = one("original_audio.*")
    duration, sr, channels = probe(audio)
    script = read_script()

    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(str(audio), language=LANGUAGE, beam_size=3, word_timestamps=False, vad_filter=True)
    transcript = []
    for seg in segments_iter:
        transcript.append({"start": round(float(seg.start),3), "end": round(float(seg.end),3), "text": seg.text.strip()})

    suggestions = []
    matched = set()
    cursor = 0
    if script:
        for ti, seg in enumerate(transcript):
            candidates = []
            for si in range(cursor, min(len(script), cursor+5)):
                score = similarity(seg["text"], script[si])
                candidates.append((score,si))
            if candidates:
                score, idx = max(candidates)
                if score >= 0.42:
                    matched.add(idx)
                    cursor = max(cursor, idx+1)
                elif score < 0.22 and len(norm(seg["text"])) >= 8:
                    suggestions.append({
                        "edit_id": f"mismatch-{ti}", "type":"possible_mismatch",
                        "start": seg["start"], "end": seg["end"],
                        "duration": round(seg["end"]-seg["start"],2),
                        "confidence":"possible", "approved":False,
                        "reason":"এই অংশটি স্ক্রিপ্টের সঙ্গে স্পষ্টভাবে মেলেনি। ভুল বা অতিরিক্ত কথা কি না শুনে যাচাই করো।",
                        "transcript":seg["text"]
                    })

    # Detect long silence conservatively. Only suggest central portion, retaining padding.
    sil = run(["ffmpeg","-hide_banner","-i",str(audio),"-af","silencedetect=noise=-48dB:d=2.2","-f","null","-"], check=False)
    if sil.returncode not in (0, 1) and "silence_" not in sil.stderr:
        raise RuntimeError("FFmpeg silence detection failed: " + sil.stderr[-1200:])
    starts = []
    for line in sil.stderr.splitlines():
        m = re.search(r"silence_start:\s*([0-9.]+)",line)
        if m: starts.append(float(m.group(1)))
        m = re.search(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)",line)
        if m and starts:
            st = starts.pop(0); en = float(m.group(1))
            a, b = st+0.45, en-0.45
            if b-a >= 0.8:
                suggestions.append({
                    "edit_id":f"silence-{len(suggestions)}","type":"long_pause",
                    "start":round(a,3),"end":round(b,3),"duration":round(b-a,2),
                    "confidence":"possible","approved":False,
                    "reason":"দীর্ঘ নীরবতা শনাক্ত হয়েছে। নাটকীয় বিরতি বা শ্বাসের অংশ হলে কাটবে না।",
                    "transcript":""
                })

    suggestions.sort(key=lambda x:(x["start"],x["end"]))
    missing = [{"line_number":i+1,"script_text":line} for i,line in enumerate(script) if i not in matched]
    # Unmatched script lines are warnings, not cut recommendations.
    report = {
        "job_id":os.environ.get("JOB_ID",""),
        "duration":duration,"sample_rate":sr,"channels":channels,
        "transcript":transcript,"suggested_edits":suggestions,
        "missing_script_lines":missing,
        "summary":{"total_duration":duration,"total_suggestions":len(suggestions),
                   "transcript_segments":len(transcript),"script_lines":len(script),
                   "missing_lines":len(missing),"model":MODEL}
    }
    (WORK/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    run(["ffmpeg","-y","-ss","0","-i",str(audio),"-t","10","-af","afftdn=nf=-25","-c:a","pcm_s16le",str(WORK/"nr_preview.wav")],check=False)

if __name__ == "__main__": main()
