import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from status import update_status, fail_job, upload_asset_to_release
from transcribe import run_transcription
from director import create_scene_plan
from footage import collect_stock_footage
from graphics import create_motion_graphics
from video_render import render_documentary
from quality_control import validate_final_video

WORK = Path(os.environ.get("WORK_DIR", "/tmp/doc_job"))


def main():
    current_stage = "analyzing_voice"
    try:
        WORK.mkdir(parents=True, exist_ok=True)

        current_stage = "generating_transcript"
        transcript_data, original_audio_path = run_transcription()
        upload_asset_to_release(WORK / "transcript.json", "transcript.json", "application/json")

        current_stage = "creating_scene_plan"
        scene_plan = create_scene_plan(transcript_data)

        current_stage = "collecting_footage"
        scene_plan = collect_stock_footage(scene_plan)

        current_stage = "creating_graphics"
        scene_plan = create_motion_graphics(scene_plan)
        upload_asset_to_release(WORK / "scene_plan.json", "scene_plan.json", "application/json")

        current_stage = "rendering_final_video"
        final_mp4, srt_path = render_documentary(scene_plan, transcript_data, original_audio_path)

        current_stage = "quality_control"
        update_status("quality_control", "স্বয়ংক্রিয় Quality Control: 1080p, 30 FPS, অডিও ও সময় যাচাই হচ্ছে...", percent=95)
        qc_report = validate_final_video(final_mp4, transcript_data["duration"], WORK / "quality_report.json")
        qc_report["ai_provider"] = scene_plan.get("ai_provider", "unknown")
        qc_report["planning_mode"] = scene_plan.get("planning_mode", "unknown")
        (WORK / "quality_report.json").write_text(
            json.dumps(qc_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        upload_asset_to_release(WORK / "quality_report.json", "quality_report.json", "application/json")

        update_status("quality_control", "Quality Check সম্পন্ন। চূড়ান্ত MP4 আপলোড হচ্ছে...", percent=97,
                      extra={"quality_check_passed": qc_report["passed"], "quality_warnings": qc_report["warnings"]})
        upload_asset_to_release(final_mp4, "final_documentary.mp4", "video/mp4")
        if srt_path.exists():
            upload_asset_to_release(srt_path, "subtitles.srt", "text/plain")

        size_mb = round(final_mp4.stat().st_size / (1024 * 1024), 2)
        update_status(
            "completed",
            f"ডকুমেন্টারি ভিডিও প্রস্তুত! (1080p MP4, {size_mb} MB, {scene_plan['scene_count']}টি দৃশ্য)",
            percent=100,
            extra={
                "video_size_mb": size_mb,
                "duration_sec": transcript_data["duration"],
                "scene_count": scene_plan["scene_count"],
                "ai_provider": scene_plan.get("ai_provider", "unknown"),
                "planning_mode": scene_plan.get("planning_mode", "unknown"),
                "quality_check_passed": qc_report["passed"],
                "quality_warnings": qc_report["warnings"]
            }
        )
    except Exception as exc:
        fail_job(current_stage, str(exc))
        raise


if __name__ == "__main__":
    main()
