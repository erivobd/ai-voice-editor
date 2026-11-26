import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Union
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

try:
    from status import update_status
except ImportError:
    def update_status(*args, **kwargs):
        pass


OPENROUTER_MODELS = [
    "google/gemini-2.5-flash:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/free",
]

VALID_GRADES = {"cinematic_teal", "warm_history", "cool_science", "neutral_doc"}
VALID_GRAPHIC_KINDS = {"title_card", "stat_chart", "timeline", "map_marker"}

BENGALI_VISUAL_LEXICON = [
    (["রাতের আকাশ", "অসংখ্য তারা", "নক্ষত্র", "আকাশের দিকে", "তারা দেখতে"], "রাতের আকাশের তারা", ["অসংখ্য নক্ষত্র", "অসীম মহাকাশ"], "night sky full of stars milky way timelapse"),
    (["পৃথিবী", "নীল গ্রহ"], "নীল গ্রহ পৃথিবী", ["মহাবিশ্বের বুকে", "জীবনের আবাস"], "earth from space blue planet view"),
    (["সূর্য", "সৌর", "নক্ষত্রের আলো"], "সূর্য ও সৌরজগৎ", ["তাপ ও আলোর উৎস", "মহাকর্ষীয় কেন্দ্র"], "sun surface solar flare space"),
    (["সমুদ্র", "সাগর", "মহাসাগর", "ঢেউ"], "গভীর সমুদ্রের রহস্য", ["বিশাল জলরাশি", "সামুদ্রিক জগৎ"], "deep blue ocean waves aerial view"),
    (["অরণ্য", "বন", "জঙ্গল", "গাছ"], "ঘন সবুজ অরণ্য", ["প্রকৃতির ফুসফুস", "বৈচিত্র্যময় প্রাণ"], "dense green forest canopy aerial"),
    (["পাহাড়", "পর্বত", "বরফ", "হিমালয়"], "বরফে ঢাকা পাহাড়", ["উচ্চ পর্বতমালা", "তুষারাবৃত চূড়া"], "snow covered mountain peaks landscape"),
    (["মঙ্গল", "লাল গ্রহ"], "মঙ্গল গ্রহ অভিযান", ["লাল গ্রহ মঙ্গল", "নতুন অনুসন্ধান"], "mars planet surface space exploration"),
    (["গ্যালাক্সি", "ছায়াপথ", "মহাকাশ", "মহাবিশ্ব"], "রহস্যময় মহাবিশ্ব", ["কোটি কোটি ছায়াপথ", "অজানা মহাকাশ"], "deep space galaxy nebula stars"),
    (["শহর", "প্রযুক্তি", "ভবিষ্যৎ", "বিজ্ঞান"], "আধুনিক বিজ্ঞান ও ভবিষ্যৎ", ["নতুন উদ্ভাবন", "দ্রুত পরিবর্তন"], "modern city skyline night lights aerial"),
]


def _clean_bn(text: str) -> str:
    s = re.sub(r"[\u0900-\u097F]+", "", str(text or ""))
    s = re.sub(r"^\s*অধ্যায়\s*[\d০-৯]+\s*(?://|[-–—:])?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty LLM response")
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _build_prompt(transcript_text: str, total_duration: float, title: str = "") -> str:
    title_hint = f"Documentary Title: {title}\n" if title else ""
    return f"""
You are an elite documentary video director.
{title_hint}Create a tightly synchronized, visually accurate scene plan covering the ENTIRE {total_duration:.1f}s duration of this documentary from 0.0s to {total_duration:.1f}s:

TRANSCRIPT:
{transcript_text[:12000]}

STRICT VISUAL & TIMING RULES:
1. FULL DURATION COVERAGE (CRITICAL):
   - You MUST generate enough scenes to cover the ENTIRE timeline from 0.0s all the way to {total_duration:.1f}s with ZERO gaps and ZERO early cutoff.
   - Do NOT stop at the last transcript line if audio continues; continue matching thematic scenes up to {total_duration:.1f}s.
2. STRICT VISUAL-TRANSCRIPT LOCK:
   - Every single scene's "search_queries" and "graphic" MUST directly match the exact spoken subject, noun, place, or concept in the transcript at that exact timestamp.
   - Example: If the narrator says "রাতের আকাশের দিকে তাকালে আমরা অসংখ্য তারা দেখতে পাই", the query MUST be "night sky full of stars milky way" — NEVER ocean, whirlpool, or unrelated nature!
   - NEVER use generic engineering blueprints, circuit boards, or unrelated stock unless the transcript explicitly discusses engineering or code.
3. COHESIVE SCENE DURATION:
   - Keep each scene 3.5s to 7.0s (unless total_duration < 6.5s, in which case make 1 cohesive scene covering 0.0s to {total_duration:.1f}s).
   - Only split into rapid cuts (1.8s–2.8s) if the narrator explicitly enumerates 3+ separate objects in a list.
4. NEVER repeat the exact same search query across scenes. Provide 2 specific English visual queries per stock_footage scene.
5. Alternate with "motion_graphic" scenes (stat_chart, timeline, map_marker, title_card) on longer videos so no more than 2 stock_footage scenes appear back-to-back.
6. BENGALI ONLY FOR OVERLAYS & NO CHAPTER LABELS:
   - Every scene MUST include a "graphic" object with Bengali "heading" (<= 30 chars) and 2-3 punchy Bengali "items" (<= 22 chars each) so animated badges & pills always appear on screen.
   - NEVER write the word "অধ্যায়" or chapter numbers anywhere.
   - Zero Hindi/Devanagari characters.
7. Choose "color_grade" from: "cinematic_teal", "warm_history", "cool_science", "neutral_doc".

Return ONLY valid JSON with this schema:
{{
  "color_grade": "cinematic_teal",
  "mood": "documentary_ambient",
  "scenes": [
    {{
      "scene_id": 1,
      "start": 0.0,
      "end": 5.5,
      "visual_type": "stock_footage",
      "rapid_cut": false,
      "search_queries": ["night sky full of stars milky way", "starry night sky cosmos timelapse"],
      "accent": "red",
      "graphic": {{
        "kind": "title_card",
        "heading": "রাতের আকাশের তারা",
        "subheading": "অসীম মহাবিশ্বের ঝলক",
        "items": ["অসংখ্য নক্ষত্র", "রহস্যময় মহাকাশ"]
      }}
    }}
  ]
}}
""".strip()


def _call_openrouter(prompt: str, api_key: str) -> Dict[str, Any]:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Documentary Video Maker",
    }
    payload = {
        "models": OPENROUTER_MODELS[:3],
        "messages": [
            {"role": "system", "content": "Return ONLY valid JSON. No markdown prose."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    req = urlrequest.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=75) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return _extract_json(content)
    except (HTTPError, URLError, KeyError, IndexError, ValueError, json.JSONDecodeError):
        pass

    for model_name in OPENROUTER_MODELS[3:]:
        single_payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON. No markdown prose."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        req = urlrequest.Request(
            url, data=json.dumps(single_payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urlrequest.urlopen(req, timeout=75) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"]
                return _extract_json(content)
        except Exception:
            continue

    raise RuntimeError("All OpenRouter fallback models failed")


def _call_groq(prompt: str, api_key: str) -> Dict[str, Any]:
    from groq import Groq

    client = Groq(api_key=api_key)
    models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
    last_err = None
    for m in models:
        try:
            completion = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            return _extract_json(completion.choices[0].message.content or "")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Groq failed: {last_err}")


def _call_gemini(prompt: str, api_key: str) -> Dict[str, Any]:
    from google import genai

    client = genai.Client(api_key=api_key)
    models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    last_err = None
    for m in models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
            )
            return _extract_json(response.text or "")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Gemini failed: {last_err}")


def _derive_topic_from_transcript(transcript_text: str, idx: int, title: str = "") -> Dict[str, Any]:
    lower_t = (transcript_text or "").lower()
    for keys, h, pills, q in BENGALI_VISUAL_LEXICON:
        if any(k in transcript_text or k in lower_t for k in keys):
            return {"heading": h, "items": pills, "query": q, "matched": True}

    clean_words = [w for w in re.findall(r"[\u0980-\u09FF]+", transcript_text or "") if len(w) >= 2]
    if clean_words:
        heading = " ".join(clean_words[:3])[:30]
        pills = clean_words[3:6] if len(clean_words) >= 6 else clean_words[:2]
        return {"heading": heading, "items": pills[:3], "query": "night sky stars cosmos wide view", "matched": False}

    base_h = _clean_bn(title) or "মূল অনুসন্ধান"
    return {"heading": base_h[:30], "items": ["গুরুত্বপূর্ণ তথ্য", "বিস্তারিত বিশ্লেষণ"], "query": "night sky stars cosmos wide view", "matched": False}


def _normalize_graphic(sc: Dict[str, Any], idx: int, transcript_text: str = "", title: str = "") -> Dict[str, Any]:
    derived = _derive_topic_from_transcript(transcript_text, idx, title=title)
    g = sc.get("graphic") if isinstance(sc.get("graphic"), dict) else {}
    kind = g.get("kind") or ""
    if kind not in VALID_GRAPHIC_KINDS:
        ov_style = sc.get("overlay_style", "")
        kind = "stat_chart" if ov_style == "stat_bars" else ["title_card", "stat_chart", "timeline", "map_marker"][idx % 4]

    raw_heading = g.get("heading") or sc.get("overlay_headline") or derived["heading"]
    heading = _clean_bn(raw_heading)[:30] or derived["heading"]

    raw_sub = g.get("subheading") or sc.get("overlay_subtext") or ""
    subheading = _clean_bn(raw_sub)[:46]

    items_raw = g.get("items") or sc.get("stat_items") or derived["items"]
    items: List[str] = []
    for it in items_raw[:4]:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            k_clean = _clean_bn(it[0])[:20]
            v_clean = _clean_bn(it[1])[:14]
            if k_clean and v_clean:
                items.append(f"{k_clean}: {v_clean}")
        else:
            c = _clean_bn(it)[:24]
            if c and c not in items:
                items.append(c)

    if not items:
        items = derived["items"][:2]

    return {
        "kind": kind,
        "heading": heading,
        "subheading": subheading,
        "items": items,
    }


def _find_segment_text_for_range(segments: List[Dict[str, Any]], start: float, end: float, fallback_full: str) -> str:
    if not segments:
        return fallback_full
    matched = []
    for s in segments:
        s_start = float(s.get("start", 0.0))
        s_end = float(s.get("end", s_start))
        if max(start, s_start) < min(end, s_end) + 0.05:
            txt = str(s.get("text") or "").strip()
            if txt:
                matched.append(txt)
    return " ".join(matched) if matched else fallback_full


def _enforce_variety_and_pacing(
    raw_scenes: List[Dict[str, Any]],
    total_duration: float,
    segments: Optional[List[Dict[str, Any]]] = None,
    fallback_full: str = "",
    title: str = "",
) -> List[Dict[str, Any]]:
    total_duration = max(float(total_duration or 0.0), 1.5)
    segments = segments or []
    motions = ["slow_zoom_in", "pan_left", "slow_zoom_out", "pan_right"]
    fallback_queries = [
        "night sky full of stars milky way timelapse",
        "earth from space blue planet view",
        "deep space galaxy nebula stars",
        "deep blue ocean waves aerial view",
        "dense green forest canopy aerial",
        "snow covered mountain peaks landscape",
        "mars planet surface space exploration",
        "sun surface solar flare space",
        "aurora borealis night sky stars",
        "modern city skyline night lights aerial",
    ]

    if total_duration < 6.5:
        derived = _derive_topic_from_transcript(fallback_full, 0, title=title)
        first_raw = raw_scenes[0] if raw_scenes else {}
        raw_qs = first_raw.get("search_queries") if isinstance(first_raw.get("search_queries"), list) else []
        queries = [derived["query"]]
        for q in raw_qs:
            qs = str(q or "").strip()
            if qs and qs.lower() != derived["query"].lower():
                queries.append(qs)
                break
        graphic = _normalize_graphic(first_raw, 0, transcript_text=fallback_full, title=title)
        return [{
            "scene_id": 1,
            "start": 0.0,
            "end": round(total_duration, 2),
            "duration": round(total_duration, 2),
            "visual_type": "stock_footage",
            "type": "stock_footage",
            "rapid_cut": False,
            "search_queries": queries[:2],
            "search_query": queries[0],
            "accent": "red",
            "motion_effect": "slow_zoom_in",
            "graphic": graphic,
            "overlay_headline": graphic["heading"],
            "overlay_subtext": graphic["subheading"],
        }]

    if not raw_scenes:
        step = 5.5
        count = max(1, int(total_duration // step))
        raw_scenes = []
        for i in range(count):
            st = round(i * step, 2)
            en = round(min((i + 1) * step, total_duration), 2)
            seg_txt = _find_segment_text_for_range(segments, st, en, fallback_full)
            derived = _derive_topic_from_transcript(seg_txt, i, title=title)
            raw_scenes.append({
                "scene_id": i + 1,
                "start": st,
                "end": en,
                "visual_type": "motion_graphic" if i % 3 == 2 else "stock_footage",
                "rapid_cut": False,
                "search_queries": [derived["query"], fallback_queries[i % len(fallback_queries)]],
                "accent": "red" if i % 2 == 0 else "gold",
                "graphic": {
                    "kind": "title_card",
                    "heading": derived["heading"],
                    "subheading": "",
                    "items": derived["items"],
                },
            })

    seen_queries: Set[str] = set()
    consecutive_normal_stock = 0
    consecutive_rapid_stock = 0
    cleaned: List[Dict[str, Any]] = []
    cursor = 0.0

    for idx, sc in enumerate(raw_scenes):
        if cursor >= total_duration - 0.15:
            break

        orig_start = float(sc.get("start", cursor))
        orig_end = float(sc.get("end", orig_start + 5.0))
        orig_dur = float(sc.get("duration") or (orig_end - orig_start if orig_end > orig_start else 5.0))

        is_rapid = bool(sc.get("rapid_cut")) and orig_dur < 3.0
        if is_rapid:
            dur = max(1.6, min(3.0, orig_dur))
        else:
            dur = max(3.5, min(7.5, orig_dur))

        start = round(cursor, 2)
        end = round(min(total_duration, start + dur), 2)
        if total_duration - end < 1.5:
            end = round(total_duration, 2)
        actual_dur = round(max(1.5, end - start), 2)

        vtype = sc.get("visual_type") or sc.get("type") or "stock_footage"
        if vtype not in ("stock_footage", "motion_graphic"):
            vtype = "stock_footage" if is_rapid else ("motion_graphic" if idx % 3 == 2 else "stock_footage")

        if is_rapid:
            if consecutive_rapid_stock >= 4:
                vtype = "motion_graphic"
                consecutive_rapid_stock = 0
                consecutive_normal_stock = 0
            else:
                vtype = "stock_footage"
                consecutive_rapid_stock += 1
                consecutive_normal_stock = 0
        else:
            consecutive_rapid_stock = 0
            if vtype == "stock_footage":
                if consecutive_normal_stock >= 2:
                    vtype = "motion_graphic"
                    consecutive_normal_stock = 0
                else:
                    consecutive_normal_stock += 1
            else:
                consecutive_normal_stock = 0

        seg_txt = _find_segment_text_for_range(segments, start, end, fallback_full)
        derived = _derive_topic_from_transcript(seg_txt, len(cleaned), title=title)

        raw_qs = sc.get("search_queries")
        if isinstance(raw_qs, str):
            raw_qs = [raw_qs]
        elif not isinstance(raw_qs, list):
            single_q = sc.get("search_query")
            raw_qs = [single_q] if single_q else []

        candidate_qs = ([derived["query"]] if derived.get("matched") else []) + [
            str(q or "").strip() for q in raw_qs if str(q or "").strip()
        ]
        if not derived.get("matched"):
            candidate_qs.append(derived["query"])

        queries: List[str] = []
        if vtype == "stock_footage":
            for q_str in candidate_qs:
                low = q_str.lower()
                if any(bad in low for bad in ("blueprint", "circuit", "code screen", "whirlpool", "vortex")):
                    continue
                if low not in seen_queries:
                    queries.append(q_str)
                    seen_queries.add(low)
                if len(queries) >= 2:
                    break

            if not queries:
                for fq in fallback_queries:
                    if fq.lower() not in seen_queries:
                        queries.append(fq)
                        seen_queries.add(fq.lower())
                        break
                if not queries:
                    queries.append(f"{fallback_queries[idx % len(fallback_queries)]} wide")

        graphic = _normalize_graphic(sc, len(cleaned), transcript_text=seg_txt, title=title)
        accent = "red" if sc.get("accent") == "red" or idx % 2 == 0 else "gold"

        cleaned.append({
            "scene_id": len(cleaned) + 1,
            "start": start,
            "end": end,
            "duration": actual_dur,
            "visual_type": vtype,
            "type": vtype,
            "rapid_cut": is_rapid,
            "search_queries": queries,
            "search_query": queries[0] if queries else "",
            "accent": accent,
            "motion_effect": sc.get("motion_effect") or motions[idx % len(motions)],
            "graphic": graphic,
            "overlay_headline": graphic["heading"],
            "overlay_subtext": graphic["subheading"],
        })
        cursor = end

    # Extend seamlessly up to the FULL audio duration (total_duration) so video never stops at 4 seconds!
    if cleaned and cleaned[-1]["end"] < total_duration:
        gap = round(total_duration - cleaned[-1]["end"], 2)
        if gap <= 3.5:
            cleaned[-1]["end"] = round(total_duration, 2)
            cleaned[-1]["duration"] = round(cleaned[-1]["end"] - cleaned[-1]["start"], 2)
        else:
            while cursor < total_duration - 0.15:
                s_idx = len(cleaned)
                start = round(cursor, 2)
                end = round(min(total_duration, start + 5.5), 2)
                if total_duration - end < 1.5:
                    end = round(total_duration, 2)
                dur = round(max(1.5, end - start), 2)
                vtype = "motion_graphic" if s_idx % 3 == 2 else "stock_footage"
                seg_txt = _find_segment_text_for_range(segments, start, end, fallback_full)
                derived = _derive_topic_from_transcript(seg_txt, s_idx, title=title)
                fq = fallback_queries[s_idx % len(fallback_queries)]
                if derived.get("matched") and derived["query"].lower() not in seen_queries:
                    fq = derived["query"]
                seen_queries.add(fq.lower())

                cleaned.append({
                    "scene_id": s_idx + 1,
                    "start": start,
                    "end": end,
                    "duration": dur,
                    "visual_type": vtype,
                    "type": vtype,
                    "rapid_cut": False,
                    "search_queries": [fq] if vtype == "stock_footage" else [],
                    "search_query": fq if vtype == "stock_footage" else "",
                    "accent": "red" if s_idx % 2 == 0 else "gold",
                    "motion_effect": motions[s_idx % len(motions)],
                    "graphic": {
                        "kind": ["title_card", "stat_chart", "timeline", "map_marker"][s_idx % 4],
                        "heading": derived["heading"],
                        "subheading": "",
                        "items": derived["items"],
                    },
                    "overlay_headline": derived["heading"],
                    "overlay_subtext": "",
                })
                cursor = end

    return cleaned


def plan_scenes(
    transcript_text: str,
    total_duration: float,
    title: str = "",
    segments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    update_status("creating_scene_plan", f"AI ডিরেক্টর সম্পূর্ণ {round(total_duration, 1)} সেকেন্ডের দৃশ্য পরিকল্পনা তৈরি করছে...", percent=42)
    prompt = _build_prompt(transcript_text, total_duration, title=title)
    plan: Dict[str, Any] = {}

    providers = [
        ("gemini", os.environ.get("GEMINI_API_KEY", "").strip(), _call_gemini),
        ("groq", os.environ.get("GROQ_API_KEY", "").strip(), _call_groq),
        ("openrouter", os.environ.get("OPENROUTER_API_KEY", "").strip(), _call_openrouter),
    ]

    for name, api_key, fn in providers:
        if not api_key:
            continue
        try:
            print(f"[Director] Trying provider: {name}", flush=True)
            plan = fn(prompt, api_key)
            if isinstance(plan, dict) and isinstance(plan.get("scenes"), list) and plan["scenes"]:
                print(f"[Director] Scene plan generated via {name} ({len(plan['scenes'])} scenes)", flush=True)
                break
        except Exception as e:
            print(f"[Director] {name} failed: {e}", flush=True)
            continue

    raw_scenes = plan.get("scenes") if isinstance(plan, dict) else []
    color_grade = plan.get("color_grade") if isinstance(plan, dict) else "cinematic_teal"
    if color_grade not in VALID_GRADES:
        color_grade = "cinematic_teal"
    mood = (plan.get("mood") if isinstance(plan, dict) else None) or "documentary_ambient"

    scenes = _enforce_variety_and_pacing(
        raw_scenes or [],
        total_duration,
        segments=segments,
        fallback_full=transcript_text,
        title=title,
    )
    update_status("creating_scene_plan", f"{len(scenes)}টি ডাইনামিক দৃশ্য পরিকল্পনা প্রস্তুত হয়েছে ({round(total_duration, 1)} সেকেন্ড)।", percent=50)

    return {
        "title": title or os.environ.get("DOC_TITLE", "").strip() or "Documentary",
        "color_grade": color_grade,
        "mood": mood,
        "scene_count": len(scenes),
        "total_duration": round(float(total_duration), 2),
        "scenes": scenes,
    }


def create_scene_plan(
    transcript: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    duration: Optional[float] = None,
    title: str = "",
    *args: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    explicit_duration = duration or kwargs.get("total_duration") or kwargs.get("audio_duration")
    doc_title = title or kwargs.get("doc_title") or os.environ.get("DOC_TITLE", "").strip()
    segments: List[Dict[str, Any]] = []
    audio_duration: Optional[float] = float(explicit_duration) if explicit_duration else None
    max_seg_end = 0.0

    if isinstance(transcript, dict):
        if transcript.get("duration"):
            probe_dur = float(transcript["duration"])
            audio_duration = max(audio_duration or 0.0, probe_dur)
        segments = transcript.get("segments") or []
        if segments:
            transcript_text = "\n".join(
                f"[{float(s.get('start', 0)):.1f}s - {float(s.get('end', 0)):.1f}s] {str(s.get('text', '')).strip()}"
                for s in segments
                if str(s.get("text", "")).strip()
            )
            max_seg_end = max((float(s.get("end", 0)) for s in segments), default=0.0)
        else:
            transcript_text = str(transcript.get("text") or transcript.get("full_text") or "")
    elif isinstance(transcript, list):
        segments = [s for s in transcript if isinstance(s, dict)]
        transcript_text = "\n".join(
            f"[{float(s.get('start', 0)):.1f}s - {float(s.get('end', 0)):.1f}s] {str(s.get('text', '')).strip()}"
            for s in segments
            if str(s.get("text", "")).strip()
        )
        max_seg_end = max((float(s.get("end", 0)) for s in segments), default=0.0)
    else:
        transcript_text = str(transcript or "")

    # Always use the full audio duration (never truncate to the first 4-second segment!)
    total_duration = max(audio_duration or 0.0, max_seg_end, 4.0)
    return plan_scenes(transcript_text, total_duration, title=doc_title, segments=segments)
