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


# Dynamic OpenRouter free-model router. It selects from currently available
# free endpoints rather than relying on model IDs that may be retired.
OPENROUTER_MODELS = ["openrouter/free"]

VALID_GRADES = {"cinematic_teal", "warm_history", "cool_science", "neutral_doc"}
VALID_GRAPHIC_KINDS = {"title_card", "stat_chart", "timeline", "map_marker"}


def _scene_grade_for_text(text: str, requested: str = "") -> str:
    """Choose a restrained scene-specific grade from the spoken topic."""
    if requested in VALID_GRADES:
        return requested
    t = (text or "").lower()
    if any(k in t for k in ("ইতিহাস", "প্রাচীন", "যুদ্ধ", "ঔপনিবেশ", "ঐতিহাসিক", "সভ্যতা")):
        return "warm_history"
    if any(k in t for k in ("বিজ্ঞান", "প্রযুক্তি", "মহাকাশ", "গবেষণা", "রোবট", "কম্পিউটার")):
        return "cool_science"
    if any(k in t for k in ("অর্থনীতি", "বাণিজ্য", "শিল্প", "রাজনীতি", "সরকার", "নির্বাচন", "চীন", "বাংলাদেশ")):
        return "cinematic_teal"
    return "neutral_doc"

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


def _build_prompt(
    transcript_text: str,
    total_duration: float,
    title: str = "",
    window_start: float = 0.0,
    window_end: Optional[float] = None,
) -> str:
    window_end = float(total_duration if window_end is None else window_end)
    window_start = max(0.0, float(window_start))
    window_duration = max(0.0, window_end - window_start)
    title_hint = f"Documentary Title: {title}\n" if title else ""
    return f"""
You are an elite documentary video director.
{title_hint}Create a tightly synchronized scene plan for the narration window from {window_start:.1f}s to {window_end:.1f}s. The complete documentary duration is {total_duration:.1f}s.

TRANSCRIPT FOR THIS WINDOW (use every timestamped line; do not invent events):
{transcript_text}

STRICT VISUAL & TIMING RULES:
1. COVER THIS WINDOW COMPLETELY:
   - Cover the absolute timeline from {window_start:.1f}s through {window_end:.1f}s with no intentional gaps.
   - Scene start/end values are ABSOLUTE timestamps on the original narration timeline, not offsets from this window.
   - Never retime, compress, stretch, or evenly redistribute timestamps.
   - Place each visual change where its spoken subject begins, using timestamped transcript lines as authority.
2. STRICT VISUAL-TRANSCRIPT LOCK:
   - Every scene's search_queries and graphic MUST directly match the exact spoken subject, noun, place, or concept at that timestamp.
   - Example: If the narrator says "রাতের আকাশের দিকে তাকালে আমরা অসংখ্য তারা দেখতে পাই", the query MUST be "night sky full of stars milky way" — NEVER ocean, whirlpool, or unrelated nature.
   - NEVER use generic engineering blueprints, circuit boards, or unrelated stock unless the transcript explicitly discusses engineering or code.
3. COHESIVE SCENE DURATION:
   - Keep each scene 3.5s to 7.0s. Only use one scene if this window is shorter than 6.5s.
   - Only split into rapid cuts (1.8s–2.8s) if the narrator explicitly enumerates 3+ separate objects in a list.
4. NEVER repeat the exact same search query across scenes. Provide 2 specific English visual queries per stock_footage scene.
5. MODERN YOUTUBE DOCUMENTARY EDITING:
   - Stock footage is the MAIN visual layer. Aim for about 75-85% relevant footage and 15-25% purposeful explainer graphics, not alternating slides.
   - Never force a graphic just because two footage scenes appeared. Use full-screen motion_graphic only for a real explanation: a location, timeline, process, comparison, or meaningful statistic.
   - Use editorial overlays on footage sparingly (roughly one in every 3-4 scenes). Do not put a title, badges, or pills on every shot.
   - Prefer visual variety: wide establishing shots, close details, aerials, archival-style images, maps, and short punch-in shots that match the narration.
6. BENGALI ONLY FOR ON-SCREEN WORDS:
   - Keep on-screen wording concise and factual. Do not invent statistics, dates, locations, or claims absent from the transcript.
   - Use a heading and 1-3 supporting labels only when they add explanatory value.
   - NEVER write the word "অধ্যায়" or chapter numbers anywhere. Zero Hindi/Devanagari characters.
7. Choose a documentary color grade: cinematic_teal, warm_history, cool_science, or neutral_doc.
8. Choose subtle camera movement: slow_zoom_in, slow_zoom_out, pan_left, or pan_right.
9. Use clean editorial cuts by default; reserve transitions and graphic emphasis for story beats.

Return ONLY valid JSON with this schema:
{{
  "color_grade": "cinematic_teal",
  "mood": "documentary_ambient",
  "scenes": [
    {{
      "scene_id": 1,
      "start": {window_start:.1f},
      "end": {min(window_start + 5.5, window_end):.1f},
      "visual_type": "stock_footage",
      "rapid_cut": false,
      "search_queries": ["night sky full of stars milky way", "starry night sky cosmos timelapse"],
      "motion_effect": "slow_zoom_in",
      "color_grade": "cool_science",
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
    last_error = None
    for model_name in OPENROUTER_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Return ONLY valid JSON. No markdown prose."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        req = urlrequest.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"]
                return _extract_json(content)
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"OpenRouter free-model router failed: {last_error}")


def _call_groq(prompt: str, api_key: str) -> Dict[str, Any]:
    from groq import Groq

    client = Groq(api_key=api_key)
    models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
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
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
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
        queries = []
        for q in raw_qs:
            qs = str(q or "").strip()
            if qs and qs.lower() != derived["query"].lower():
                queries.append(qs)
                break
        fallback_type = first_raw.get("visual_type", "motion_graphic") if first_raw else "motion_graphic"
        if fallback_type not in ("stock_footage", "motion_graphic"):
            fallback_type = "motion_graphic"
        if fallback_type == "stock_footage" and not queries:
            queries = [derived["query"]]
        graphic = _normalize_graphic(first_raw, 0, transcript_text=fallback_full, title=title)
        return [{
            "scene_id": 1,
            "start": 0.0,
            "end": round(total_duration, 2),
            "duration": round(total_duration, 2),
            "visual_type": fallback_type,
            "type": fallback_type,
            "rapid_cut": False,
            "search_queries": queries[:2],
            "search_query": queries[0] if queries else "",
            "accent": "red",
            "motion_effect": "slow_zoom_in",
            "graphic": graphic,
            "show_overlay": bool(first_raw.get("show_overlay", False)),
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
                "visual_type": "motion_graphic",
                "rapid_cut": False,
                "search_queries": [],
                "accent": "red" if i % 2 == 0 else "gold",
                "graphic": {
                    "kind": "title_card",
                    "heading": derived["heading"],
                    "subheading": "",
                    "items": derived["items"],
                },
            })

    # Process scenes chronologically and honor absolute narration timestamps.
    # Gaps are filled by extending the previous shot (or a generated opener),
    # while overlaps are trimmed at the current cursor. Never move a later
    # scene earlier just to make the timeline contiguous.
    raw_scenes = sorted(
        raw_scenes,
        key=lambda item: float(item.get("start", 0.0)) if isinstance(item, dict) else 0.0,
    )

    seen_queries: Set[str] = set()
    consecutive_normal_stock = 0
    consecutive_rapid_stock = 0
    cleaned: List[Dict[str, Any]] = []
    cursor = 0.0

    for idx, sc in enumerate(raw_scenes):
        if not isinstance(sc, dict) or cursor >= total_duration - 0.15:
            continue

        orig_start = max(0.0, float(sc.get("start", cursor)))
        orig_end = float(sc.get("end", orig_start + 5.0))
        orig_dur = float(sc.get("duration") or (orig_end - orig_start if orig_end > orig_start else 5.0))
        requested_start = min(total_duration, max(cursor, orig_start))

        # Do not stretch one unrelated shot across a long transcript gap.
        # Small gaps can hold the previous shot; larger gaps become concise,
        # transcript-led motion graphics until the next timestamped scene.
        if requested_start > cursor + 0.20:
            gap_duration = requested_start - cursor
            if cleaned and gap_duration <= 7.5:
                cleaned[-1]["end"] = round(requested_start, 3)
                cleaned[-1]["duration"] = round(cleaned[-1]["end"] - cleaned[-1]["start"], 3)
            else:
                gap_cursor = cursor
                while gap_cursor < requested_start - 0.15:
                    gap_end = min(requested_start, gap_cursor + 5.5)
                    gap_text = _find_segment_text_for_range(segments, gap_cursor, gap_end, fallback_full)
                    gap_topic = _derive_topic_from_transcript(gap_text, len(cleaned), title=title)
                    graphic = {
                        "kind": "title_card", "heading": gap_topic["heading"],
                        "subheading": "", "items": gap_topic["items"]
                    }
                    cleaned.append({
                        "scene_id": len(cleaned) + 1,
                        "start": round(gap_cursor, 3), "end": round(gap_end, 3),
                        "duration": round(gap_end - gap_cursor, 3),
                        "visual_type": "motion_graphic", "type": "motion_graphic",
                        "rapid_cut": False, "search_queries": [], "search_query": "",
                        "accent": "red" if len(cleaned) % 2 == 0 else "gold",
                        "motion_effect": motions[len(cleaned) % len(motions)],
                        "color_grade": _scene_grade_for_text(gap_text),
                        "graphic": graphic, "show_overlay": False,
                        "overlay_headline": graphic["heading"], "overlay_subtext": ""
                    })
                    gap_cursor = gap_end
            cursor = requested_start

        start = round(cursor, 3)
        is_rapid = bool(sc.get("rapid_cut")) and orig_dur < 3.0
        target_end = orig_end if orig_end > start + 0.25 else max(orig_start + orig_dur, start + 1.0)
        end = round(min(total_duration, max(start + 0.5, target_end)), 3)
        if total_duration - end < 0.25:
            end = round(total_duration, 3)
        actual_dur = round(end - start, 3)
        if actual_dur <= 0:
            continue

        vtype = sc.get("visual_type") or sc.get("type") or "stock_footage"
        if vtype not in ("stock_footage", "motion_graphic"):
            vtype = "stock_footage"

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
            "color_grade": _scene_grade_for_text(seg_txt, str(sc.get("color_grade") or "")),
            "graphic": graphic,
            "show_overlay": bool(sc.get("show_overlay", idx % 4 == 1)) and not is_rapid,
            "overlay_headline": graphic["heading"],
            "overlay_subtext": graphic["subheading"],
        })
        cursor = end

    # Fill the remaining narration tail without shortening the audio timeline.
    if cleaned and cleaned[-1]["end"] < total_duration:
        gap = round(total_duration - cleaned[-1]["end"], 3)
        if gap <= 3.5:
            cleaned[-1]["end"] = round(total_duration, 3)
            cleaned[-1]["duration"] = round(cleaned[-1]["end"] - cleaned[-1]["start"], 3)
        else:
            while cursor < total_duration - 0.15:
                s_idx = len(cleaned)
                start = round(cursor, 3)
                end = round(min(total_duration, start + 5.5), 3)
                seg_txt = _find_segment_text_for_range(segments, start, end, fallback_full)
                derived = _derive_topic_from_transcript(seg_txt, s_idx, title=title)
                query = derived["query"]
                cleaned.append({
                    "scene_id": s_idx + 1, "start": start, "end": end,
                    "duration": round(end - start, 3), "visual_type": "motion_graphic",
                    "type": "motion_graphic", "rapid_cut": False,
                    "search_queries": [], "search_query": "",
                    "accent": "red" if s_idx % 2 == 0 else "gold",
                    "motion_effect": motions[s_idx % len(motions)],
                    "color_grade": _scene_grade_for_text(seg_txt),
                    "graphic": {"kind": "title_card", "heading": derived["heading"],
                                "subheading": "", "items": derived["items"]},
                    "show_overlay": False, "overlay_headline": derived["heading"], "overlay_subtext": ""
                })
                cursor = end

    return cleaned



def _is_valid_provider_plan(
    plan: Any,
    total_duration: float,
    window_start: float = 0.0,
    window_end: Optional[float] = None,
) -> bool:
    if not isinstance(plan, dict) or not isinstance(plan.get("scenes"), list) or not plan["scenes"]:
        return False
    window_end = float(total_duration if window_end is None else window_end)
    valid_count = 0
    for scene in plan["scenes"]:
        if not isinstance(scene, dict):
            continue
        try:
            start = float(scene.get("start"))
            end = float(scene.get("end"))
        except (TypeError, ValueError):
            continue
        if start < max(0.0, window_start - 0.5) or end <= start or start >= window_end or end > window_end + 1.5:
            continue
        queries = scene.get("search_queries", scene.get("search_query", []))
        if isinstance(queries, str):
            queries = [queries]
        if scene.get("visual_type") == "stock_footage" and not queries:
            continue
        valid_count += 1
    return valid_count >= max(1, min(3, len(plan["scenes"]) // 3))


def _local_graphic_scenes(
    segments: List[Dict[str, Any]],
    window_start: float,
    window_end: float,
    fallback_full: str,
    title: str,
) -> List[Dict[str, Any]]:
    scenes: List[Dict[str, Any]] = []
    cursor = float(window_start)
    while cursor < window_end - 0.15:
        end = min(float(window_end), cursor + 5.5)
        segment_text = _find_segment_text_for_range(segments, cursor, end, fallback_full)
        derived = _derive_topic_from_transcript(segment_text, len(scenes), title=title)
        scenes.append({
            "scene_id": len(scenes) + 1,
            "start": round(cursor, 3),
            "end": round(end, 3),
            "duration": round(end - cursor, 3),
            "visual_type": "motion_graphic",
            "rapid_cut": False,
            "search_queries": [],
            "accent": "red" if len(scenes) % 2 == 0 else "gold",
            "graphic": {
                "kind": "title_card",
                "heading": derived["heading"],
                "subheading": "",
                "items": derived["items"],
            },
        })
        cursor = end
    return scenes


def plan_scenes(
    transcript_text: str,
    total_duration: float,
    title: str = "",
    segments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    segments = segments or []
    chunk_seconds = max(90, min(180, int(os.environ.get("AI_SCENE_CHUNK_SECONDS", "120"))))
    use_chunks = bool(segments) and total_duration > 180
    windows = []
    if use_chunks:
        cursor = 0.0
        while cursor < total_duration - 0.15:
            window_end = min(total_duration, cursor + chunk_seconds)
            windows.append((cursor, window_end))
            cursor = window_end
    else:
        windows = [(0.0, total_duration)]

    providers = [
        ("gemini", os.environ.get("GEMINI_API_KEY", "").strip(), _call_gemini),
        ("groq", os.environ.get("GROQ_API_KEY", "").strip(), _call_groq),
        ("openrouter", os.environ.get("OPENROUTER_API_KEY", "").strip(), _call_openrouter),
    ]

    raw_scenes: List[Dict[str, Any]] = []
    providers_used: List[str] = []
    fallback_used = False
    color_grade = "cinematic_teal"
    mood = "documentary_ambient"

    for chunk_index, (window_start, window_end) in enumerate(windows, start=1):
        chunk_segments = [
            seg for seg in segments
            if float(seg.get("start", 0.0)) < window_end and float(seg.get("end", seg.get("start", 0.0))) > window_start
        ]
        if chunk_segments:
            chunk_text = "\n".join(
                f"[{float(seg.get('start', 0.0)):.1f}s - {float(seg.get('end', 0.0)):.1f}s] {str(seg.get('text', '')).strip()}"
                for seg in chunk_segments if str(seg.get("text", "")).strip()
            )
        else:
            chunk_text = transcript_text if len(windows) == 1 else ""

        update_status(
            "creating_scene_plan",
            f"AI Director দৃশ্য পরিকল্পনা তৈরি করছে: অংশ {chunk_index}/{len(windows)} ({round(window_start)}–{round(window_end)} সেকেন্ড)...",
            percent=min(49, 42 + int(7 * chunk_index / max(1, len(windows))))
        )
        prompt = _build_prompt(chunk_text or transcript_text, total_duration, title=title,
                               window_start=window_start, window_end=window_end)
        chunk_plan: Dict[str, Any] = {}
        chunk_provider = ""

        for name, api_key, fn in providers:
            if not api_key:
                continue
            try:
                print(f"[Director] Trying {name} for scene-plan chunk {chunk_index}/{len(windows)}", flush=True)
                candidate = fn(prompt, api_key)
                if _is_valid_provider_plan(candidate, total_duration, window_start, window_end):
                    chunk_plan = candidate
                    chunk_provider = name
                    print(f"[Director] Valid {name} plan: {len(candidate['scenes'])} scenes in chunk {chunk_index}", flush=True)
                    break
                print(f"[Director] {name} returned invalid timestamps/content for chunk {chunk_index}; trying next free provider.", flush=True)
            except Exception as exc:
                print(f"[Director] {name} failed for chunk {chunk_index}: {exc}", flush=True)

        if chunk_plan:
            raw_scenes.extend(chunk_plan.get("scenes", []))
            if chunk_provider not in providers_used:
                providers_used.append(chunk_provider)
            if chunk_index == 1:
                candidate_grade = chunk_plan.get("color_grade")
                candidate_mood = chunk_plan.get("mood")
                if candidate_grade in VALID_GRADES:
                    color_grade = candidate_grade
                if candidate_mood:
                    mood = str(candidate_mood)[:60]
        else:
            fallback_used = True
            raw_scenes.extend(_local_graphic_scenes(
                chunk_segments, window_start, window_end, chunk_text or transcript_text, title
            ))
            print(f"[Director] Using transcript-led local graphics fallback for chunk {chunk_index}", flush=True)

    scenes = _enforce_variety_and_pacing(
        raw_scenes,
        total_duration,
        segments=segments,
        fallback_full=transcript_text,
        title=title,
    )
    provider_used = "+".join(providers_used) if providers_used else "local_graphics_fallback"
    if fallback_used and providers_used:
        planning_mode = "mixed_ai_local"
    elif providers_used:
        planning_mode = "ai_director"
    else:
        planning_mode = "local_graphics_fallback"

    update_status("creating_scene_plan", f"{len(scenes)}টি দৃশ্যের স্বয়ংক্রিয় পরিকল্পনা প্রস্তুত ({round(total_duration, 1)} সেকেন্ড)।", percent=50)
    return {
        "title": title or os.environ.get("DOC_TITLE", "").strip() or "Documentary",
        "color_grade": color_grade,
        "mood": mood,
        "scene_count": len(scenes),
        "ai_provider": provider_used,
        "planning_mode": planning_mode,
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
