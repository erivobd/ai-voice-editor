import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from google import genai
from google.genai import types
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))


def _build_prompt(transcript_data, doc_title):
    duration = transcript_data["duration"]
    lang = transcript_data.get("detected_language", "bn")
    lines = []
    for seg in transcript_data["segments"]:
        lines.append(f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")
    transcript_block = "\n".join(lines)

    return f"""You are an award-winning Cinematic Documentary Film Director and Visual Editor.
Analyze the following timestamped voiceover transcript (language: {lang}, total duration: {duration:.2f} seconds).
Optional documentary title: "{doc_title}"

Your job is to create a complete, seamless documentary scene plan from 0.0 seconds to {duration:.2f} seconds with NO gaps and NO overlapping timestamps.

Rules:
1. Divide the narration into dynamic documentary scenes (typically 5 to 12 seconds each; shorter for dramatic pacing).
2. The first scene MUST start at 0.0 and the last scene MUST end at {duration:.2f}. Every next scene's start MUST equal the previous scene's end.
3. Choose "visual_type":
   - Use "stock_footage" for ~75% of scenes (nature, cities, mountains, ocean, historical places, science, space, people, technology).
   - Use "motion_graphic" for ~25% of scenes (opening title card, maps/locations, timelines, statistics/charts, scientific concepts, key quotes).
4. For every scene, provide 3 SIMPLE, CONCRETE English stock footage search queries in "search_queries" (e.g., ["ancient river sunset aerial", "misty mountains landscape", "calm ocean waves"]). Never write poetic or non-English search queries.
5. For every scene, ALSO provide a "graphic" object so if stock footage is unavailable, the engine can seamlessly render a documentary graphic instead of repeating footage!
   - graphic.kind must be one of: "title_card", "map_marker", "timeline", "stat_chart", "quote_card"
   - graphic.heading: short crisp title in the narration's language (max 45 chars)
   - graphic.subheading: concise context (max 80 chars)
   - graphic.items: list of 2 to 4 short strings or "Label: Number" pairs (for timeline or stat_chart)
6. Set overall "mood" to one of: "documentary_ambient", "mystery", "science", "history", "inspiring".
7. Set overall "color_grade" to one of: "cinematic_teal", "warm_history", "cool_science", "neutral_doc".
8. Return ONLY valid JSON matching this exact structure:
{{
  "title": "Documentary Title",
  "mood": "documentary_ambient",
  "color_grade": "cinematic_teal",
  "scenes": [
    {{
      "scene_id": 1,
      "start": 0.0,
      "end": 6.5,
      "visual_type": "motion_graphic",
      "visual_description": "Opening cinematic title card introducing the topic",
      "search_queries": ["dramatic dark clouds timelapse", "earth from space sunrise", "cinematic mountain fog"],
      "transition": "fade",
      "graphic": {{
        "kind": "title_card",
        "heading": "Main Title",
        "subheading": "Documentary Subtitle",
        "items": []
      }}
    }}
  ]
}}

Timestamped Transcript:
{transcript_block}
"""


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _call_gemini_with_retry(api_key, prompt, max_retries=3):
    client = genai.Client(api_key=api_key)
    models_to_try = ["gemini-3.8-flash"]
    last_err = None

    for model_name in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4
                    )
                )
                return _extract_json(response.text)
            except Exception as e:
                last_err = e
                err_str = str(e)
                print(
                    f"[WARN] Gemini {model_name} attempt {attempt}/{max_retries} failed: {err_str}",
                    flush=True
                )
                is_transient = any(
                    code in err_str
                    for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED", "timeout")
                )
                if is_transient and attempt < max_retries:
                    wait_sec = 5 * (2 ** (attempt - 1))  # 5s, 10s
                    print(f"[INFO] Retrying Gemini in {wait_sec}s...", flush=True)
                    time.sleep(wait_sec)
                    continue
                break

    raise RuntimeError(f"Gemini failed: {last_err}")


def _call_groq_with_retry(api_key, prompt, max_retries=2):
    url = "https://api.groq.com/openai/v1/chat/completions"
    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    last_err = None

    for model_name in models_to_try:
        for attempt in range(1, max_retries + 1):
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a documentary film director. Always return ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.4,
                "response_format": {"type": "json_object"}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "AIDocumentaryMaker/1.0"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"]
                return _extract_json(content)
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                last_err = f"HTTP {e.code}: {err_body or e.reason}"
                print(
                    f"[WARN] Groq {model_name} attempt {attempt}/{max_retries} failed: {last_err}",
                    flush=True
                )
                if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(5 * attempt)
                    continue
                break
            except Exception as e:
                last_err = e
                print(
                    f"[WARN] Groq {model_name} attempt {attempt}/{max_retries} failed: {e}",
                    flush=True
                )
                if attempt < max_retries:
                    time.sleep(5 * attempt)
                    continue
                break

    raise RuntimeError(f"Groq failed: {last_err}")


def _validate_and_repair_plan(plan, duration, doc_title):
    valid_moods = {"documentary_ambient", "mystery", "science", "history", "inspiring"}
    valid_grades = {"cinematic_teal", "warm_history", "cool_science", "neutral_doc"}
    valid_kinds = {"title_card", "map_marker", "timeline", "stat_chart", "quote_card"}

    mood = plan.get("mood", "documentary_ambient")
    if mood not in valid_moods:
        mood = "documentary_ambient"

    grade = plan.get("color_grade", "cinematic_teal")
    if grade not in valid_grades:
        grade = "cinematic_teal"

    raw_scenes = plan.get("scenes") or []
    repaired = []
    cursor = 0.0

    for sc in raw_scenes:
        if cursor >= duration - 0.2:
            break
        try:
            end_t = float(sc.get("end", cursor + 6.0))
        except Exception:
            end_t = cursor + 6.0

        if end_t <= cursor + 1.5:
            end_t = min(duration, cursor + 5.0)
        if end_t > duration:
            end_t = duration

        vtype = sc.get("visual_type", "stock_footage")
        if vtype not in ("stock_footage", "motion_graphic"):
            vtype = "stock_footage"

        queries = [str(q).strip() for q in (sc.get("search_queries") or []) if str(q).strip()]
        if not queries:
            queries = ["cinematic nature landscape aerial", "documentary dark clouds sky", "abstract light particles"]

        g = sc.get("graphic") or {}
        g_kind = g.get("kind", "title_card")
        if g_kind not in valid_kinds:
            g_kind = "title_card"

        repaired.append({
            "scene_id": len(repaired) + 1,
            "start": round(cursor, 3),
            "end": round(end_t, 3),
            "duration": round(end_t - cursor, 3),
            "visual_type": vtype,
            "visual_description": str(sc.get("visual_description") or "Documentary visual scene"),
            "search_queries": queries[:4],
            "transition": sc.get("transition", "fade"),
            "graphic": {
                "kind": g_kind,
                "heading": str(g.get("heading") or doc_title or "Documentary")[:60],
                "subheading": str(g.get("subheading") or "")[:110],
                "items": [str(x)[:60] for x in (g.get("items") or [])[:5]]
            }
        })
        cursor = end_t

    if not repaired:
        seg_len = 8.0
        t = 0.0
        i = 1
        while t < duration - 0.1:
            nxt = min(duration, t + seg_len)
            repaired.append({
                "scene_id": i,
                "start": round(t, 3),
                "end": round(nxt, 3),
                "duration": round(nxt - t, 3),
                "visual_type": "motion_graphic" if i == 1 else "stock_footage",
                "visual_description": "Cinematic documentary scene",
                "search_queries": ["cinematic earth landscape aerial", "dramatic sky clouds", "ocean waves sunset"],
                "transition": "fade",
                "graphic": {
                    "kind": "title_card",
                    "heading": doc_title or "AI Documentary",
                    "subheading": f"Part {i}",
                    "items": []
                }
            })
            t = nxt
            i += 1
    else:
        repaired[-1]["end"] = round(duration, 3)
        repaired[-1]["duration"] = round(repaired[-1]["end"] - repaired[-1]["start"], 3)

    return {
        "title": str(plan.get("title") or doc_title or "AI Documentary")[:100],
        "mood": mood,
        "color_grade": grade,
        "total_duration": round(duration, 3),
        "scene_count": len(repaired),
        "scenes": repaired
    }


def create_scene_plan(transcript_data):
    update_status("creating_scene_plan", "AI ডকুমেন্টারি দৃশ্য ও স্টোরিবোর্ড তৈরি করছে...", percent=40)

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

    if not GEMINI_API_KEY and not GROQ_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY বা GROQ_API_KEY কোনোটিই পাওয়া যায়নি। GitHub Repository Secrets-এ অন্তত একটি API Key সেট করুন।"
        )

    doc_title = os.environ.get("DOC_TITLE", "").strip()
    prompt = _build_prompt(transcript_data, doc_title)

    raw_plan = None
    provider_used = None
    errors = []

    if GEMINI_API_KEY:
        try:
            raw_plan = _call_gemini_with_retry(GEMINI_API_KEY, prompt, max_retries=3)
            provider_used = "Gemini"
        except Exception as e:
            errors.append(str(e))
            print(f"[WARN] Gemini exhausted all retries: {e}", flush=True)

    if raw_plan is None and GROQ_API_KEY:
        update_status(
            "creating_scene_plan",
            "Gemini সার্ভার ব্যস্ত, ব্যাকআপ Groq AI দিয়ে দৃশ্য পরিকল্পনা তৈরি হচ্ছে...",
            percent=44
        )
        try:
            raw_plan = _call_groq_with_retry(GROQ_API_KEY, prompt, max_retries=2)
            provider_used = "Groq"
        except Exception as e:
            errors.append(str(e))
            print(f"[WARN] Groq fallback failed: {e}", flush=True)

    if raw_plan is None:
        raise RuntimeError(f"AI দৃশ্য পরিকল্পনা তৈরি করতে পারেনি: {' | '.join(errors)}")

    scene_plan = _validate_and_repair_plan(raw_plan, transcript_data["duration"], doc_title)
    out_path = WORK / "scene_plan.json"
    out_path.write_text(json.dumps(scene_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    update_status(
        "creating_scene_plan",
        f"দৃশ্য পরিকল্পনা তৈরি সম্পন্ন ({scene_plan['scene_count']}টি সিন, মুড: {scene_plan['mood']}, ইঞ্জিন: {provider_used})।",
        percent=48
    )
    return scene_plan
