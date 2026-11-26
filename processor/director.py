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
VALID_GRAPHIC_KINDS = {"flowchart", "route_map", "visual_callout", "stat_chart"}


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
You are an elite documentary video director inspired by high-retention Vox & editorial explainer channels.
{title_hint}Create a dynamic, visually varied scene plan for a {total_duration:.1f}s documentary from this timestamped transcript:

TRANSCRIPT:
{transcript_text[:12000]}

CRITICAL VISUAL & PACING RULES:
1. RAPID-CUT & LIST-SYNC RULE (HIGHEST PRIORITY):
   - Whenever the narrator lists multiple distinct visual subjects separated by commas, "এবং", "আর", "ও", or "and", DO NOT combine them into one long scene.
   - Immediately split them into back-to-back rapid-cut "stock_footage" scenes (1.2s to 2.8s each) synced tightly to the exact spoken moment of each item, and set `"rapid_cut": true` and `"show_overlay": false`.
   - Give each split scene its own specific English visual query matching that exact noun.
2. NEVER repeat the exact same stock search query or visual subject across scenes. Give 2 unique, specific English search queries per stock_footage scene in "search_queries".
3. OCCASIONAL ON-SCREEN KEY-POINT CALLOUTS (NOT CONTINUOUS SUBTITLES):
   - For "stock_footage" scenes, set `"show_overlay": true` ONLY on important emphasis moments (roughly 40%-50% of normal stock scenes) so punchy key phrases pop up occasionally rather than cluttering every shot.
   - On scenes with `"show_overlay": true`, provide a short badge label in `subheading` (<= 24 chars), a bold key phrase in `heading` (<= 34 chars), and optionally 1-2 short pill tags in `items`.
4. EDITORIAL MOTION GRAPHICS:
   - Alternate normal stock_footage scenes (3.5s to 7.0s) with "motion_graphic" scenes so no more than 2 normal stock_footage scenes appear in a row.
   - Choose `graphic.kind` from ONLY these 4 animated templates:
     * "flowchart" — step-by-step cause/effect or process (3-4 short steps in `items`)
     * "route_map" — central hub connected to 3-4 locations/concepts in `items`
     * "visual_callout" — bold headline with 2-4 pill callout points in `items`
     * "stat_chart" — animated data bars, format each item as "Label: number" (e.g., ["ধাপ ১: 35", "ধাপ ২: 78", "ধাপ ৩: 100"])
5. Cover 0.0s to {total_duration:.1f}s continuously with zero gaps, keeping scene start/end timestamps aligned with the transcript.
6. Write all `heading`, `subheading`, and `items` in the SAME language as the transcript (Bengali if Bengali, English if English).
7. Choose "color_grade" from: "cinematic_teal", "warm_history", "cool_science", "neutral_doc".

Return ONLY valid JSON with this exact schema:
{{
  "color_grade": "cinematic_teal",
  "mood": "documentary_ambient",
  "scenes": [
    {{
      "scene_id": 1,
      "start": 0.0,
      "end": 5.0,
      "visual_type": "stock_footage",
      "rapid_cut": false,
      "show_overlay": true,
      "search_queries": ["night sky stars milky way timelapse", "deep space cosmos stars wide"],
      "graphic": {{
        "kind": "visual_callout",
        "heading": "রাতের আকাশের অজানা রহস্য",
        "subheading": "অধ্যায় ০১ // সূচনা",
        "items": ["১০০% অনন্য", "অসীম মহাবিশ্ব"]
      }}
    }},
    {{
      "scene_id": 2,
      "start": 5.0,
      "end": 10.0,
      "visual_type": "motion_graphic",
      "rapid_cut": false,
      "show_overlay": false,
      "search_queries": [],
      "graphic": {{
        "kind": "flowchart",
        "heading": "কীভাবে এই প্রক্রিয়া কাজ করে?",
        "subheading": "বিশ্লেষণ // ফ্লোচার্ট",
        "items": ["প্রথম ধাপ: শক্তির উৎস", "দ্বিতীয় ধাপ: তাপমাত্রার ভারসাম্য", "তৃতীয় ধাপ: প্রাণের বিকাশ"]
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
        "temperature": 0.45,
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
            "temperature": 0.45,
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
                temperature=0.45,
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


def _normalize_graphic(sc: Dict[str, Any], idx: int) -> Dict[str, Any]:
    g = sc.get("graphic") if isinstance(sc.get("graphic"), dict) else {}
    kind = g.get("kind") or ""
    if kind not in VALID_GRAPHIC_KINDS:
        kind = ["visual_callout", "flowchart", "route_map", "stat_chart"][idx % 4]

    heading = str(g.get("heading") or sc.get("overlay_headline") or f"অধ্যায় {idx + 1}").strip()[:48]
    subheading = str(g.get("subheading") or sc.get("overlay_subtext") or "").strip()[:72]

    items_raw = g.get("items") or sc.get("stat_items") or []
    items: List[str] = []
    for it in items_raw[:4]:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            items.append(f"{it[0]}: {it[1]}")
        elif str(it).strip():
            items.append(str(it).strip()[:42])

    return {
        "kind": kind,
        "heading": heading,
        "subheading": subheading,
        "items": items,
    }


def _enforce_variety_and_pacing(raw_scenes: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
    total_duration = max(float(total_duration or 0.0), 8.0)
    motions = ["slow_zoom_in", "pan_left", "slow_zoom_out", "pan_right"]
    fallback_queries = [
        "architectural blueprint engineering table",
        "aerial city skyline twilight drone",
        "wind turbine airflow motion",
        "steel construction structure closeup",
        "modern glass tower reflection",
        "desert sunrise wide horizon",
        "structural engineer reviewing plans",
        "city traffic night timelapse",
        "bridge cables architecture perspective",
        "laboratory scientific data screen",
        "earth from space night lights",
        "ocean waves aerial cinematic",
        "mountain range clouds timelapse",
        "industrial factory robotics motion",
        "historical architecture columns wide",
        "solar panels energy field aerial",
    ]

    if not raw_scenes:
        step = 5.5
        count = max(1, int(total_duration // step))
        raw_scenes = [
            {
                "scene_id": i + 1,
                "start": round(i * step, 2),
                "end": round(min((i + 1) * step, total_duration), 2),
                "visual_type": "motion_graphic" if i % 3 == 2 else "stock_footage",
                "rapid_cut": False,
                "show_overlay": (i % 2 == 0),
                "search_queries": [fallback_queries[i % len(fallback_queries)]],
                "graphic": {
                    "kind": ["visual_callout", "flowchart", "route_map", "stat_chart"][i % 4],
                    "heading": f"অধ্যায় {i + 1}",
                    "subheading": "",
                    "items": [],
                },
            }
            for i in range(count)
        ]

    seen_queries: Set[str] = set()
    consecutive_normal_stock = 0
    consecutive_rapid_stock = 0
    cleaned: List[Dict[str, Any]] = []
    cursor = 0.0

    for idx, sc in enumerate(raw_scenes):
        if cursor >= total_duration - 0.2:
            break

        orig_start = float(sc.get("start", cursor))
        orig_end = float(sc.get("end", orig_start + 5.0))
        orig_dur = float(sc.get("duration") or (orig_end - orig_start if orig_end > orig_start else 5.0))

        is_rapid = bool(sc.get("rapid_cut")) or orig_dur < 3.2
        if is_rapid:
            dur = max(1.0, min(3.2, orig_dur))
        else:
            dur = max(3.2, min(7.5, orig_dur))

        start = round(cursor, 2)
        end = round(min(total_duration, start + dur), 2)
        if total_duration - end < 1.2:
            end = round(total_duration, 2)
        actual_dur = round(max(1.0, end - start), 2)

        vtype = sc.get("visual_type") or sc.get("type") or "stock_footage"
        if vtype not in ("stock_footage", "motion_graphic"):
            vtype = "stock_footage" if is_rapid else ("motion_graphic" if idx % 3 == 2 else "stock_footage")

        if is_rapid:
            if consecutive_rapid_stock >= 5:
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

        raw_qs = sc.get("search_queries")
        if isinstance(raw_qs, str):
            raw_qs = [raw_qs]
        elif not isinstance(raw_qs, list):
            single_q = sc.get("search_query")
            raw_qs = [single_q] if single_q else []

        queries: List[str] = []
        if vtype == "stock_footage":
            for q in raw_qs:
                q_str = str(q or "").strip()
                if q_str and q_str.lower() not in seen_queries:
                    queries.append(q_str)
                    seen_queries.add(q_str.lower())
                if len(queries) >= 2:
                    break

            if not queries:
                for fq in fallback_queries:
                    if fq.lower() not in seen_queries:
                        queries.append(fq)
                        seen_queries.add(fq.lower())
                        break
                if not queries:
                    fq = f"{fallback_queries[idx % len(fallback_queries)]} wide shot"
                    queries.append(fq)

        graphic = _normalize_graphic(sc, len(cleaned))
        if "show_overlay" in sc:
            show_overlay = bool(sc.get("show_overlay")) and not is_rapid
        else:
            show_overlay = (not is_rapid) and (len(cleaned) % 2 == 0)

        cleaned.append({
            "scene_id": len(cleaned) + 1,
            "start": start,
            "end": end,
            "duration": actual_dur,
            "visual_type": vtype,
            "type": vtype,
            "rapid_cut": is_rapid,
            "show_overlay": show_overlay,
            "search_queries": queries,
            "search_query": queries[0] if queries else "",
            "motion_effect": sc.get("motion_effect") or motions[idx % len(motions)],
            "graphic": graphic,
            "overlay_headline": graphic["heading"] if show_overlay else "",
            "overlay_subtext": graphic["subheading"] if show_overlay else "",
        })
        cursor = end

    if cleaned and cleaned[-1]["end"] < total_duration:
        gap = round(total_duration - cleaned[-1]["end"], 2)
        if gap <= 3.5:
            cleaned[-1]["end"] = round(total_duration, 2)
            cleaned[-1]["duration"] = round(cleaned[-1]["end"] - cleaned[-1]["start"], 2)
        else:
            while cursor < total_duration - 0.2:
                s_idx = len(cleaned)
                start = round(cursor, 2)
                end = round(min(total_duration, start + 5.5), 2)
                if total_duration - end < 1.5:
                    end = round(total_duration, 2)
                dur = round(max(1.2, end - start), 2)
                vtype = "motion_graphic" if s_idx % 3 == 2 else "stock_footage"
                fq = fallback_queries[s_idx % len(fallback_queries)]
                cleaned.append({
                    "scene_id": s_idx + 1,
                    "start": start,
                    "end": end,
                    "duration": dur,
                    "visual_type": vtype,
                    "type": vtype,
                    "rapid_cut": False,
                    "show_overlay": (s_idx % 2 == 0),
                    "search_queries": [fq] if vtype == "stock_footage" else [],
                    "search_query": fq if vtype == "stock_footage" else "",
                    "motion_effect": motions[s_idx % len(motions)],
                    "graphic": {
                        "kind": ["visual_callout", "flowchart", "route_map", "stat_chart"][s_idx % 4],
                        "heading": f"অধ্যায় {s_idx + 1}",
                        "subheading": "",
                        "items": [],
                    },
                    "overlay_headline": f"অধ্যায় {s_idx + 1}" if s_idx % 2 == 0 else "",
                    "overlay_subtext": "",
                })
                cursor = end

    return cleaned


def plan_scenes(transcript_text: str, total_duration: float, title: str = "") -> Dict[str, Any]:
    update_status("creating_scene_plan", "AI ডিরেক্টর দৃশ্য পরিকল্পনা ও গ্রাফিক্স ডিজাইন তৈরি করছে...", percent=42)
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

    scenes = _enforce_variety_and_pacing(raw_scenes or [], total_duration)
    update_status("creating_scene_plan", f"{len(scenes)}টি ডাইনামিক দৃশ্য পরিকল্পনা প্রস্তুত হয়েছে।", percent=50)

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
    """Entry point called by processor/pipeline.py."""
    inferred_duration = duration or kwargs.get("total_duration") or kwargs.get("audio_duration")
    doc_title = title or kwargs.get("doc_title") or os.environ.get("DOC_TITLE", "").strip()

    if isinstance(transcript, dict):
        segments = transcript.get("segments") or []
        if segments:
            transcript_text = "\n".join(
                f"[{float(s.get('start', 0)):.1f}s - {float(s.get('end', 0)):.1f}s] {str(s.get('text', '')).strip()}"
                for s in segments
                if str(s.get("text", "")).strip()
            )
            if inferred_duration is None:
                inferred_duration = max((float(s.get("end", 0)) for s in segments), default=60.0)
        else:
            transcript_text = str(transcript.get("text") or transcript.get("full_text") or "")
        if inferred_duration is None and transcript.get("duration"):
            inferred_duration = float(transcript["duration"])
    elif isinstance(transcript, list):
        transcript_text = "\n".join(
            f"[{float(s.get('start', 0)):.1f}s - {float(s.get('end', 0)):.1f}s] {str(s.get('text', '')).strip()}"
            for s in transcript
            if isinstance(s, dict) and str(s.get("text", "")).strip()
        )
        if inferred_duration is None:
            inferred_duration = max((float(s.get("end", 0)) for s in transcript if isinstance(s, dict)), default=60.0)
    else:
        transcript_text = str(transcript or "")

    total_duration = float(inferred_duration) if inferred_duration else 60.0
    return plan_scenes(transcript_text, total_duration, title=doc_title)
