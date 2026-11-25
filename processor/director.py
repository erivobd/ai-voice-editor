import json
import os
import re
from typing import Any, Dict, List, Set
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


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


def _build_prompt(transcript_text: str, total_duration: float) -> str:
    return f"""
You are an elite documentary video director inspired by high-retention engineering & explainer channels.
Create a dynamic, visually varied scene plan for a {total_duration:.1f}s documentary from this transcript:

TRANSCRIPT:
{transcript_text}

CRITICAL VISUAL & PACING RULES:
1. NEVER repeat the exact same stock search query or visual subject across scenes. Every stock query must be unique and specific in English.
2. NEVER put more than 2 stock_footage scenes in a row. Frequently alternate with motion_graphic scenes (stat_bars, callout_card, headline_card, comparison) so the video never feels like a serial slideshow of stock clips.
3. Keep scene durations punchy and varied (3.5s to 7.0s), covering 0.0s to {total_duration:.1f}s with zero gaps or overlaps.
4. For overlay_headline and overlay_subtext: write short, punchy text in the SAME language as the transcript (Bengali if the transcript is Bengali, English if English). Keep headline <= 32 chars and subtext <= 44 chars.
5. For stat_bars scenes, provide 3 to 4 concise [label, numeric_value] pairs in "stat_items".

Return ONLY valid JSON with this exact schema:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "start": 0.0,
      "end": 5.0,
      "type": "stock_footage",
      "overlay_style": "headline",
      "accent": "gold",
      "motion_effect": "slow_zoom_in",
      "search_query": "aerial skyscraper dusk wide shot",
      "overlay_headline": "৮২৮ মিটার উচ্চতা",
      "overlay_subtext": "বিশ্বের সর্বোচ্চ স্থাপনা",
      "stat_items": []
    }},
    {{
      "scene_id": 2,
      "start": 5.0,
      "end": 10.5,
      "type": "motion_graphic",
      "overlay_style": "stat_bars",
      "accent": "gold",
      "motion_effect": "slow_zoom_out",
      "search_query": "",
      "overlay_headline": "উচ্চতার সাথে বাতাসের চাপ",
      "overlay_subtext": "উপরে বাতাস অনেক বেশি তীব্র",
      "stat_items": [["২০০মি", 35], ["৪০০মি", 58], ["৬০০মি", 82], ["৮০০মি", 100]]
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
        "temperature": 0.55,
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
            "temperature": 0.55,
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
                temperature=0.5,
            )
            return _extract_json(completion.choices[0].message.content or "")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Groq failed: {last_err}")


def _call_gemini(prompt: str, api_key: str) -> Dict[str, Any]:
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return _extract_json(response.text or "")


def _enforce_variety_and_pacing(raw_scenes: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
    total_duration = max(total_duration, 8.0)
    motions = ["slow_zoom_in", "pan_left", "slow_zoom_out", "pan_right", "ken_burns_up"]
    overlay_styles = ["headline", "callout_card", "stat_bars"]
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
    ]

    if not raw_scenes:
        step = 5.0
        count = max(1, int(total_duration // step))
        raw_scenes = [
            {
                "scene_id": i + 1,
                "start": round(i * step, 2),
                "end": round(min((i + 1) * step, total_duration), 2),
                "type": "motion_graphic" if i % 3 == 1 else "stock_footage",
                "overlay_style": overlay_styles[i % len(overlay_styles)],
                "accent": "red" if i % 4 == 3 else "gold",
                "motion_effect": motions[i % len(motions)],
                "search_query": fallback_queries[i % len(fallback_queries)],
                "overlay_headline": f"অধ্যায় {i + 1}",
                "overlay_subtext": "",
                "stat_items": [],
            }
            for i in range(count)
        ]

    seen_queries: Set[str] = set()
    consecutive_stock = 0
    cleaned: List[Dict[str, Any]] = []
    cursor = 0.0

    for idx, sc in enumerate(raw_scenes):
        if cursor >= total_duration - 0.25:
            break
        orig_start = float(sc.get("start", cursor))
        orig_end = float(sc.get("end", orig_start + 5.0))
        dur = max(3.5, min(7.5, orig_end - orig_start if orig_end > orig_start else 5.0))
        start = round(cursor, 2)
        end = round(min(total_duration, start + dur), 2)
        if end <= start:
            end = round(total_duration, 2)

        stype = sc.get("type", "stock_footage")
        if stype not in ("stock_footage", "motion_graphic"):
            stype = "motion_graphic" if idx % 3 == 0 else "stock_footage"

        # Never allow more than 2 consecutive stock footage scenes
        if stype == "stock_footage":
            if consecutive_stock >= 2:
                stype = "motion_graphic"
                consecutive_stock = 0
            else:
                consecutive_stock += 1
        else:
            consecutive_stock = 0

        query = (sc.get("search_query") or "").strip()
        if stype == "stock_footage":
            norm_q = query.lower()
            if not query or norm_q in seen_queries:
                for fq in fallback_queries:
                    if fq.lower() not in seen_queries:
                        query = fq
                        break
                else:
                    query = f"{fallback_queries[idx % len(fallback_queries)]} cinematic view {idx + 1}"
            seen_queries.add(query.lower())
        else:
            query = ""

        ov_style = sc.get("overlay_style") or overlay_styles[idx % len(overlay_styles)]
        if ov_style not in ("headline", "callout_card", "stat_bars"):
            ov_style = "callout_card" if stype == "motion_graphic" else "headline"

        stat_items = sc.get("stat_items") or []
        if ov_style == "stat_bars" and not stat_items:
            ov_style = "callout_card"

        cleaned.append({
            "scene_id": len(cleaned) + 1,
            "start": start,
            "end": end,
            "type": stype,
            "overlay_style": ov_style,
            "accent": "red" if sc.get("accent") == "red" else "gold",
            "motion_effect": sc.get("motion_effect") or motions[idx % len(motions)],
            "search_query": query,
            "overlay_headline": (sc.get("overlay_headline") or "").strip()[:48],
            "overlay_subtext": (sc.get("overlay_subtext") or "").strip()[:64],
            "stat_items": stat_items,
        })
        cursor = end

    # Fill any remaining tail duration cleanly
    if cleaned and cleaned[-1]["end"] < total_duration:
        cleaned[-1]["end"] = round(total_duration, 2)

    return cleaned


def plan_scenes(transcript_text: str, total_duration: float) -> Dict[str, Any]:
    prompt = _build_prompt(transcript_text, total_duration)
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
            print(f"[Director] Trying provider: {name}")
            plan = fn(prompt, api_key)
            if isinstance(plan, dict) and isinstance(plan.get("scenes"), list) and plan["scenes"]:
                print(f"[Director] Scene plan generated via {name} ({len(plan['scenes'])} scenes)")
                break
        except Exception as e:
            print(f"[Director] {name} failed: {e}")
            continue

    raw_scenes = plan.get("scenes") if isinstance(plan, dict) else []
    scenes = _enforce_variety_and_pacing(raw_scenes or [], total_duration)
    return {"scenes": scenes}
