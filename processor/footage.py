import os
import subprocess
from pathlib import Path
import requests
from PIL import Image, ImageOps
from status import update_status

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))
USER_AGENT = "AIDocumentaryVideoMaker/1.0 (https://github.com/; contact: documentary-worker)"

BLOCKED_LICENSE_TOKENS = ("nc", "non-commercial", "noncommercial", "nd", "no-derivatives", "rights-managed")


def _is_license_unrestricted(license_label: str) -> bool:
    # Wikimedia results are accepted only when their metadata explicitly says
    # CC0 or Public Domain. Missing/ambiguous labels are not treated as free.
    low = (license_label or "").strip().lower()
    if not low:
        return False
    if any(tok in low for tok in BLOCKED_LICENSE_TOKENS):
        return False
    return "cc0" in low or "public domain" in low


def _pick_best_pexels_file(video_files):
    landscape = [
        f for f in video_files
        if (f.get("width") or 0) > (f.get("height") or 0) and (f.get("width") or 0) >= 1280
    ]
    if not landscape:
        landscape = [f for f in video_files if (f.get("width") or 0) >= (f.get("height") or 0)]
    if not landscape:
        return None
    landscape.sort(key=lambda f: abs((f.get("width") or 0) - 1920))
    return landscape[0].get("link")


def _search_pexels_video(query, api_key, used_ids):
    if not api_key:
        return None, None
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key, "User-Agent": USER_AGENT},
            params={"query": query, "orientation": "landscape", "per_page": 10},
            timeout=20
        )
        if r.status_code != 200:
            return None, None
        for v in r.json().get("videos", []):
            vid = f"pexels_vid_{v.get('id')}"
            if vid in used_ids:
                continue
            link = _pick_best_pexels_file(v.get("video_files", []))
            if link:
                return vid, link
    except Exception as e:
        print(f"[WARN] Pexels video search error for '{query}': {e}", flush=True)
    return None, None


def _search_pexels_photo(query, api_key, used_ids):
    if not api_key:
        return None, None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key, "User-Agent": USER_AGENT},
            params={"query": query, "orientation": "landscape", "per_page": 10},
            timeout=20
        )
        if r.status_code != 200:
            return None, None
        for p in r.json().get("photos", []):
            pid = f"pexels_img_{p.get('id')}"
            if pid in used_ids:
                continue
            if (p.get("width") or 0) < (p.get("height") or 0):
                continue
            src = p.get("src") or {}
            url = src.get("large2x") or src.get("landscape") or src.get("original")
            if url:
                return pid, url
    except Exception as e:
        print(f"[WARN] Pexels photo search error for '{query}': {e}", flush=True)
    return None, None


def _search_pixabay_video(query, api_key, used_ids):
    if not api_key:
        return None, None
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            headers={"User-Agent": USER_AGENT},
            params={"key": api_key, "q": query, "per_page": 10, "safesearch": "true"},
            timeout=20
        )
        if r.status_code != 200:
            return None, None
        for h in r.json().get("hits", []):
            vid = f"pixabay_vid_{h.get('id')}"
            if vid in used_ids:
                continue
            videos = h.get("videos") or {}
            chosen = videos.get("large") or videos.get("medium") or videos.get("small")
            if chosen and chosen.get("url"):
                if (chosen.get("width") or 1920) >= (chosen.get("height") or 1080):
                    return vid, chosen["url"]
    except Exception as e:
        print(f"[WARN] Pixabay video search error for '{query}': {e}", flush=True)
    return None, None


def _search_pixabay_photo(query, api_key, used_ids):
    if not api_key:
        return None, None
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            headers={"User-Agent": USER_AGENT},
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "min_width": 1280,
                "per_page": 10,
                "safesearch": "true"
            },
            timeout=20
        )
        if r.status_code != 200:
            return None, None
        for h in r.json().get("hits", []):
            pid = f"pixabay_img_{h.get('id')}"
            if pid in used_ids:
                continue
            url = h.get("largeImageURL") or h.get("webformatURL")
            if url:
                return pid, url
    except Exception as e:
        print(f"[WARN] Pixabay photo search error for '{query}': {e}", flush=True)
    return None, None


def _search_nasa_photo(query, used_ids):
    try:
        r = requests.get(
            "https://images-api.nasa.gov/search",
            headers={"User-Agent": USER_AGENT},
            params={"q": query, "media_type": "image", "page_size": 10},
            timeout=20
        )
        if r.status_code != 200:
            return None, None
        items = (r.json().get("collection") or {}).get("items") or []
        for item in items:
            data_list = item.get("data") or []
            if not data_list:
                continue
            nasa_id = data_list[0].get("nasa_id")
            if not nasa_id:
                continue
            pid = f"nasa_pd_{nasa_id}"
            if pid in used_ids:
                continue
            links = item.get("links") or []
            img_link = next((l.get("href") for l in links if l.get("render") == "image" and l.get("href")), None)
            if img_link:
                return pid, img_link
    except Exception as e:
        print(f"[WARN] NASA search error for '{query}': {e}", flush=True)
    return None, None


def _search_wikimedia_cc0_photo(query, used_ids):
    cc0_query = f'{query} incategory:"CC0" OR incategory:"Public domain" filetype:bitmap'
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            headers={"User-Agent": USER_AGENT},
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": cc0_query,
                "gsrnamespace": 6,
                "gsrlimit": 10,
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
                "iiurlwidth": 1920
            },
            timeout=20
        )
        if r.status_code != 200:
            return None, None
        pages = (r.json().get("query") or {}).get("pages") or {}
        for page_id, page in pages.items():
            pid = f"wiki_cc0_{page_id}"
            if pid in used_ids:
                continue
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            mime = info.get("mime", "")
            if mime not in ("image/jpeg", "image/png"):
                continue
            w = int(info.get("width") or 0)
            h = int(info.get("height") or 0)
            if w < 1000 or w < h:
                continue
            extmeta = info.get("extmetadata") or {}
            lic = ((extmeta.get("LicenseShortName") or {}).get("value") or "").lower()
            if not _is_license_unrestricted(lic):
                continue
            url = info.get("thumburl") or info.get("url")
            if url:
                return pid, url
    except Exception as e:
        print(f"[WARN] Wikimedia CC0 search error for '{query}': {e}", flush=True)
    return None, None


def _download_file(url, dest_path):
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk:
                    f.write(chunk)
    return dest_path


def _stream_trim_video(url, dest_mp4, needed_duration):
    clip_len = max(2.5, round(float(needed_duration) + 0.5, 2))
    cmd = [
        "ffmpeg", "-y",
        "-user_agent", USER_AGENT,
        "-ss", "0.5",
        "-i", url,
        "-t", f"{clip_len:.2f}",
        "-an",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(dest_mp4),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    if proc.returncode == 0 and dest_mp4.exists() and dest_mp4.stat().st_size > 15_000:
        return dest_mp4

    _download_file(url, dest_mp4)
    return dest_mp4


def _image_to_ken_burns_mp4(img_path, out_mp4, duration, scene_id):
    prepared_jpg = img_path.with_suffix(".prepared.jpg")
    with Image.open(img_path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, (2040, 1148), method=Image.Resampling.LANCZOS)
        im.save(prepared_jpg, format="JPEG", quality=92)

    dur = max(1.5, float(duration))
    frames = max(45, int(round(dur * 30)))

    if scene_id % 2 == 1:
        zp = f"zoompan=z='min(zoom+0.0006,1.10)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
    else:
        zp = f"zoompan=z='max(1.10-0.0006*on,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(prepared_jpg),
        "-t", f"{dur:.3f}",
        "-an",
        "-vf", f"{zp},setsar=1,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_mp4)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for tmp in (img_path, prepared_jpg):
        try:
            tmp.unlink()
        except OSError:
            pass

    if proc.returncode != 0 or not out_mp4.exists():
        raise RuntimeError(f"Ken Burns render failed: {proc.stderr[-800:]}")
    return out_mp4


def _find_video_asset(queries, pexels_key, pixabay_key, used_ids):
    for q in queries:
        found_id, found_url = _search_pexels_video(q, pexels_key, used_ids)
        if found_url:
            return "video", found_id, found_url
        found_id, found_url = _search_pixabay_video(q, pixabay_key, used_ids)
        if found_url:
            return "video", found_id, found_url
    return None, None, None


def _expand_queries_with_short_fallbacks(queries):
    expanded = []
    seen = set()
    for q in queries:
        clean = str(q or "").strip()
        if clean and clean.lower() not in seen:
            expanded.append(clean)
            seen.add(clean.lower())
    for q in list(expanded):
        words = [w for w in q.split() if len(w) >= 3]
        if len(words) > 2:
            short_q = " ".join(words[:2])
            if short_q.lower() not in seen:
                expanded.append(short_q)
                seen.add(short_q.lower())
    return expanded


def _find_photo_asset(queries, pexels_key, pixabay_key, used_ids):
    for q in _expand_queries_with_short_fallbacks(queries):
        found_id, found_url = _search_pexels_photo(q, pexels_key, used_ids)
        if found_url:
            return "photo", found_id, found_url
        found_id, found_url = _search_pixabay_photo(q, pixabay_key, used_ids)
        if found_url:
            return "photo", found_id, found_url
        found_id, found_url = _search_wikimedia_cc0_photo(q, used_ids)
        if found_url:
            return "photo", found_id, found_url
        found_id, found_url = _search_nasa_photo(q, used_ids)
        if found_url:
            return "photo", found_id, found_url
    return None, None, None


def collect_stock_footage(scene_plan):
    update_status("collecting_footage", "প্রতিটি দৃশ্যের জন্য প্রাসঙ্গিক HD ভিডিও ও Ken Burns ছবি সংগ্রহ করা হচ্ছে...", percent=54)

    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    raw_dir = WORK / "raw_footage"
    raw_dir.mkdir(parents=True, exist_ok=True)

    used_ids = set()
    video_count = 0
    photo_count = 0
    fallback_count = 0

    for scene in scene_plan.get("scenes", []):
        if scene.get("visual_type") != "stock_footage":
            scene["footage_path"] = None
            continue

        queries = scene.get("search_queries") or []
        if isinstance(queries, str):
            queries = [queries]
        if not queries and scene.get("search_query"):
            queries = [scene["search_query"]]

        dest_mp4 = raw_dir / f"scene_{scene['scene_id']:03d}.mp4"
        prefer_photo = str(scene.get("media_preference") or "video").strip().lower() == "photo"

        if prefer_photo:
            media_kind, found_id, found_url = _find_photo_asset(queries, pexels_key, pixabay_key, used_ids)
            if not found_url:
                media_kind, found_id, found_url = _find_video_asset(queries, pexels_key, pixabay_key, used_ids)
        else:
            media_kind, found_id, found_url = _find_video_asset(queries, pexels_key, pixabay_key, used_ids)
            if not found_url:
                media_kind, found_id, found_url = _find_photo_asset(queries, pexels_key, pixabay_key, used_ids)

        if found_url and found_id:
            try:
                if media_kind == "video":
                    _stream_trim_video(found_url, dest_mp4, scene.get("duration", 6.0))
                    video_count += 1
                else:
                    tmp_img = raw_dir / f"scene_{scene['scene_id']:03d}_raw.img"
                    _download_file(found_url, tmp_img)
                    _image_to_ken_burns_mp4(tmp_img, dest_mp4, scene.get("duration", 6.0), scene["scene_id"])
                    photo_count += 1

                used_ids.add(found_id)
                scene["footage_path"] = str(dest_mp4)
                scene["footage_source_id"] = found_id
                scene["resolved_media_kind"] = media_kind
            except Exception as e:
                print(f"[WARN] Media fetch/prepare failed for scene {scene['scene_id']}: {e}", flush=True)
                scene["footage_path"] = None
                scene["visual_type"] = "motion_graphic"
                fallback_count += 1
        else:
            scene["footage_path"] = None
            scene["visual_type"] = "motion_graphic"
            fallback_count += 1

    update_status(
        "collecting_footage",
        f"মিডিয়া সংগ্রহ সম্পন্ন ({video_count}টি HD ভিডিও, {photo_count}টি Ken Burns ছবি, {fallback_count}টি ইনফোগ্রাফিক)।",
        percent=64
    )
    return scene_plan
