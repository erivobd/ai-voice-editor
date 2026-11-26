import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
JOB_ID = os.environ.get("JOB_ID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "").strip()

STAGES = {
    "uploading_audio": {
        "label": "Uploading Audio",
        "percent": 5,
        "message": "অডিও আপলোড সম্পন্ন হয়েছে। প্রসেসিং শুরু হচ্ছে..."
    },
    "analyzing_voice": {
        "label": "Analyzing Voice",
        "percent": 14,
        "message": "আপনার ভয়েসওভার বিশ্লেষণ করা হচ্ছে..."
    },
    "generating_transcript": {
        "label": "Generating Transcript",
        "percent": 28,
        "message": "নিখুঁত টাইমস্ট্যাম্পসহ ট্রান্সক্রিপ্ট তৈরি হচ্ছে..."
    },
    "creating_scene_plan": {
        "label": "Creating Scene Plan",
        "percent": 44,
        "message": "AI ডিরেক্টর দৃশ্য ও ইনফোগ্রাফিক স্টোরিবোর্ড তৈরি করছে..."
    },
    "collecting_footage": {
        "label": "Collecting Footage",
        "percent": 58,
        "message": "প্রতিটি দৃশ্যের জন্য বাস্তব HD ও ক্রেডিট-মুক্ত মিডিয়া সংগ্রহ করা হচ্ছে..."
    },
    "creating_graphics": {
        "label": "Creating Graphics",
        "percent": 72,
        "message": "ইনফোগ্রাফিক্স, পিল কলআউট ও মোশন গ্রাফিক্স তৈরি হচ্ছে..."
    },
    "editing_video": {
        "label": "Editing Video",
        "percent": 85,
        "message": "সিনেম্যাটিক ট্রানজিশন, কালার গ্রেডিং ও দৃশ্য সাজানো হচ্ছে..."
    },
    "rendering_final_video": {
        "label": "Rendering Final Video",
        "percent": 94,
        "message": "আপনার মূল ভয়েসের সাথে চূড়ান্ত 1080p MP4 রেন্ডার হচ্ছে..."
    },
    "completed": {
        "label": "Completed",
        "percent": 100,
        "message": "আপনার ডকুমেন্টারি ভিডিও তৈরি সম্পন্ন হয়েছে!"
    },
    "failed": {
        "label": "Failed",
        "percent": 0,
        "message": "প্রসেসিং চলাকালীন একটি ত্রুটি ঘটেছে।"
    }
}

_RELEASE_CACHE = None


def _gh_headers(accept="application/vnd.github+json"):
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-documentary-worker"
    }


def get_release(force_refresh=False):
    global _RELEASE_CACHE
    if _RELEASE_CACHE is not None and not force_refresh:
        return _RELEASE_CACHE
    if not (GITHUB_TOKEN and GITHUB_REPOSITORY and JOB_ID):
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/tags/{JOB_ID}"
    r = requests.get(url, headers=_gh_headers(), timeout=30)
    r.raise_for_status()
    _RELEASE_CACHE = r.json()
    return _RELEASE_CACHE


def upload_asset_to_release(file_path, asset_name=None, content_type="application/octet-stream"):
    if not (GITHUB_TOKEN and GITHUB_REPOSITORY and JOB_ID):
        return False
    file_path = Path(file_path)
    if not file_path.exists():
        return False

    name = asset_name or file_path.name
    release = get_release(force_refresh=True)
    if not release:
        return False

    for asset in release.get("assets", []):
        if asset.get("name") == name:
            del_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/assets/{asset['id']}"
            requests.delete(del_url, headers=_gh_headers(), timeout=30)

    upload_base = release["upload_url"].split("{")[0]
    upload_url = f"{upload_base}?name={name}"
    headers = _gh_headers()
    headers["Content-Type"] = content_type

    with open(file_path, "rb") as f:
        r = requests.post(upload_url, headers=headers, data=f, timeout=600)
        r.raise_for_status()
    return True


def _download_asset_by_name(asset_name, dest_path):
    release = get_release(force_refresh=True)
    if not release:
        return None
    asset = next((a for a in release.get("assets", []) if a.get("name") == asset_name), None)
    if not asset:
        return None
    headers = _gh_headers(accept="application/octet-stream")
    with requests.get(asset["url"], headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest_path


def download_custom_srt():
    WORK.mkdir(parents=True, exist_ok=True)
    local_srt = WORK / "custom_input.srt"
    if local_srt.exists() and local_srt.stat().st_size > 0:
        return local_srt
    downloaded = _download_asset_by_name("custom_input.srt", local_srt)
    if downloaded and downloaded.exists() and downloaded.stat().st_size > 0:
        return downloaded
    return None


def download_original_audio():
    WORK.mkdir(parents=True, exist_ok=True)
    existing = sorted(WORK.glob("original_audio.*"))
    if existing:
        return existing[0]

    release = get_release(force_refresh=True)
    if not release:
        raise RuntimeError("GitHub Release metadata unavailable and no local original_audio.* found.")

    audio_asset = next((a for a in release.get("assets", []) if a["name"].startswith("original_audio.")), None)
    if not audio_asset:
        raise RuntimeError("No original_audio.* asset found in GitHub Release.")

    dest = WORK / audio_asset["name"]
    headers = _gh_headers(accept="application/octet-stream")
    with requests.get(audio_asset["url"], headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest


def update_status(stage_key, message=None, percent=None, extra=None, sync_remote=True):
    WORK.mkdir(parents=True, exist_ok=True)
    info = STAGES.get(stage_key, STAGES["analyzing_voice"])
    payload = {
        "job_id": JOB_ID,
        "title": os.environ.get("DOC_TITLE", ""),
        "stage_key": stage_key,
        "stage": info["label"],
        "percent": info["percent"] if percent is None else int(percent),
        "message": message or info["message"],
        "error": None,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if extra and isinstance(extra, dict):
        payload.update(extra)

    status_path = WORK / "status.json"
    tmp_path = WORK / "status.json.tmp"
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, status_path)
    print(f"[{payload['percent']}%] {payload['stage']}: {payload['message']}", flush=True)

    if sync_remote:
        try:
            upload_asset_to_release(status_path, "status.json", "application/json")
        except Exception as e:
            print(f"[WARN] Could not sync status.json to release: {e}", flush=True)
    return payload


def fail_job(stage_key, error_message):
    WORK.mkdir(parents=True, exist_ok=True)
    info = STAGES.get(stage_key, STAGES["failed"])
    payload = {
        "job_id": JOB_ID,
        "title": os.environ.get("DOC_TITLE", ""),
        "stage_key": "failed",
        "failed_at_stage": info["label"],
        "stage": "Failed",
        "percent": 0,
        "message": f"{info['label']} ধাপে সমস্যা হয়েছে।",
        "error": str(error_message)[:2000],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    status_path = WORK / "status.json"
    tmp_path = WORK / "status.json.tmp"
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, status_path)
    print(f"[FAILED at {info['label']}] {error_message}", flush=True)
    try:
        upload_asset_to_release(status_path, "status.json", "application/json")
    except Exception as e:
        print(f"[WARN] Could not sync failure status.json: {e}", flush=True)
    return payload
