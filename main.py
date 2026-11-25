import json
import os
import re
import tempfile
import requests

from processor.director import plan_scenes
from processor.transcriber import transcribe_audio
from processor.video_builder import build_final_video


def _resolve_audio(audio_source: str, work_dir: str) -> str:
    if os.path.exists(audio_source):
        return audio_source
    if audio_source.startswith(("http://", "https://")):
        local_audio = os.path.join(work_dir, "input_voiceover.mp3")
        print(f"[Main] Downloading voiceover audio...")
        with requests.get(audio_source, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(local_audio, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
        return local_audio
    raise FileNotFoundError(f"Audio source not found: {audio_source}")


def main() -> None:
    audio_source = os.environ.get("AUDIO_URL", "").strip()
    if not audio_source:
        raise ValueError("AUDIO_URL environment variable is required.")

    enable_bg_music = os.environ.get("ENABLE_BG_MUSIC", "true").lower() == "true"
    raw_title = os.environ.get("VIDEO_TITLE", "documentary").strip()
    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_title) or "documentary"
    output_mp4 = os.path.join("output", f"{safe_title}.mp4")

    with tempfile.TemporaryDirectory(prefix="doc_audio_") as work_dir:
        audio_path = _resolve_audio(audio_source, work_dir)
        print("[Main] Step 1/3: Transcribing audio...")
        transcript_text, total_duration, _ = transcribe_audio(audio_path)
        print(f"[Main] Audio duration: {total_duration:.2f}s")

        print("[Main] Step 2/3: Generating sample-style documentary scene plan...")
        plan = plan_scenes(transcript_text, total_duration)
        os.makedirs("output", exist_ok=True)
        with open(os.path.join("output", "scene_plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

        print("[Main] Step 3/3: Rendering final video (stream-trimmed unique clips + Hind Siliguri overlays)...")
        build_final_video(
            scenes=plan["scenes"],
            audio_path=audio_path,
            output_path=output_mp4,
            enable_bg_music=enable_bg_music,
        )
        print(f"[Main] Done! Final video saved to: {output_mp4}")


if __name__ == "__main__":
    main()
