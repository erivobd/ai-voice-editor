import os
import subprocess
import tempfile
from typing import List, Optional, Set, Tuple
import requests


def _search_pexels(query: str, api_key: str, per_page: int = 8) -> List[Tuple[str, str]]:
    """Return list of (media_id, hd_mp4_url) from Pexels."""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        results: List[Tuple[str, str]] = []
        for vid in r.json().get("videos", []):
            mid = f"pexels_{vid.get('id')}"
            files = vid.get("video_files", [])
            # Pick ~720p-1080p mp4 for fast stream-trim
            mp4s = [f for f in files if f.get("file_type") == "video/mp4" and f.get("width", 0) >= 960]
            mp4s.sort(key=lambda x: abs(x.get("width", 1280) - 1280))
            if not mp4s:
                mp4s = [f for f in files if f.get("file_type") == "video/mp4"]
            if mp4s:
                results.append((mid, mp4s[0]["link"]))
        return results
    except Exception:
        return []


def _search_pixabay(query: str, api_key: str, per_page: int = 8) -> List[Tuple[str, str]]:
    """Return list of (media_id, mp4_url) from Pixabay."""
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": per_page, "safesearch": "true"}
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        results: List[Tuple[str, str]] = []
        for hit in r.json().get("hits", []):
            mid = f"pixabay_{hit.get('id')}"
            vids = hit.get("videos", {})
            chosen = vids.get("medium") or vids.get("large") or vids.get("small")
            if chosen and chosen.get("url"):
                results.append((mid, chosen["url"]))
        return results
    except Exception:
        return []


def fetch_trimmed_stock_clip(
    query: str,
    needed_duration: float,
    output_path: str,
    used_media_ids: Set[str],
    start_offset: float = 0.5,
) -> Optional[str]:
    """
    Searches Pexels/Pixabay for a UNIQUE clip (never in used_media_ids) and downloads
    ONLY the needed duration via FFmpeg stream-trim. Never keeps full raw footage.
    """
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    candidates: List[Tuple[str, str]] = []
    if pexels_key:
        candidates.extend(_search_pexels(query, pexels_key))
    if pixabay_key:
        candidates.extend(_search_pixabay(query, pixabay_key))

    # Pick first unused clip
    selected: Optional[Tuple[str, str]] = None
    for mid, vurl in candidates:
        if mid not in used_media_ids:
            selected = (mid, vurl)
            break

    if not selected:
        return None

    media_id, video_url = selected
    clip_len = max(2.5, round(needed_duration + 0.25, 2))
    # Sample-inspired desaturated cool cinematic grade + normalized 720p 30fps
    vf_filter = (
        "scale=1280:720:force_original_aspect_ratio=increase,"
        "crop=1280:720,fps=30,eq=saturation=0.72:contrast=1.06:brightness=-0.03"
    )

    # 1) Direct FFmpeg HTTP stream-trim (downloads only needed seconds)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_offset),
        "-i", video_url,
        "-t", str(clip_len),
        "-vf", vf_filter,
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10_000:
        used_media_ids.add(media_id)
        return output_path

    # 2) Fallback: stream-download to temp, trim exact seconds, delete raw immediately
    raw_fd, raw_path = tempfile.mkstemp(suffix=".mp4")
    os.close(raw_fd)
    try:
        with requests.get(video_url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(raw_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
        cmd2 = [
            "ffmpeg", "-y",
            "-ss", "0",
            "-i", raw_path,
            "-t", str(clip_len),
            "-vf", vf_filter,
            "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        res2 = subprocess.run(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res2.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10_000:
            used_media_ids.add(media_id)
            return output_path
    except Exception:
        return None
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)

    return None
