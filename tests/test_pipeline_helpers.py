import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "processor"))
os.environ.setdefault("WORK_DIR", tempfile.mkdtemp(prefix="docmaker-test-"))

from transcribe import parse_srt_or_script
from video_render import GRADE_FILTERS, _camera_filter, _fmt_srt_time
from quality_control import _rate
from director import _enforce_variety_and_pacing, _is_valid_provider_plan, _build_prompt, plan_scenes
from footage import _is_license_unrestricted


class TranscriptTests(unittest.TestCase):
    def test_srt_timestamps_and_bengali_text_are_preserved(self):
        raw = "1\n00:00:01,000 --> 00:00:03,500\nবাংলাদেশের অর্থনীতি\n\n2\n00:00:03,500 --> 00:00:05,000\nবিশ্ব বাণিজ্য\n"
        segs = parse_srt_or_script(raw, 8.0)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0]["text"], "বাংলাদেশের অর্থনীতি")
        self.assertAlmostEqual(segs[1]["end"], 5.0)

    def test_plain_transcript_is_split_over_audio_duration(self):
        segs = parse_srt_or_script("প্রথম বাক্য\nদ্বিতীয় বাক্য", 10.0)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[-1]["end"], 10.0)


class DirectorStyleTests(unittest.TestCase):
    def test_modern_youtube_style_does_not_force_graphics_every_two_scenes(self):
        raw = [
            {"start": i * 5.0, "end": (i + 1) * 5.0, "visual_type": "stock_footage",
             "search_queries": [f"subject specific documentary footage shot {i}"]}
            for i in range(6)
        ]
        scenes = _enforce_variety_and_pacing(raw, 30.0, fallback_full="বাংলাদেশের ইতিহাস ও অর্থনীতি")
        self.assertGreaterEqual(sum(s["visual_type"] == "stock_footage" for s in scenes), 5)
        self.assertLessEqual(sum(s["visual_type"] == "motion_graphic" for s in scenes), 1)

    def test_scene_timestamps_are_preserved_instead_of_retimed(self):
        raw = [
            {"start": 0.0, "end": 2.4, "duration": 2.4, "visual_type": "stock_footage", "search_queries": ["first topic"]},
            {"start": 2.4, "end": 8.1, "duration": 5.7, "visual_type": "stock_footage", "search_queries": ["second topic"]},
            {"start": 8.1, "end": 13.2, "duration": 5.1, "visual_type": "stock_footage", "search_queries": ["third topic"]},
        ]
        scenes = _enforce_variety_and_pacing(raw, 13.2, fallback_full="বাংলাদেশের ইতিহাস")
        self.assertAlmostEqual(scenes[0]["start"], 0.0)
        self.assertAlmostEqual(scenes[0]["end"], 2.4)
        self.assertAlmostEqual(scenes[1]["start"], 2.4)
        self.assertAlmostEqual(scenes[1]["end"], 8.1)
        self.assertAlmostEqual(scenes[-1]["end"], 13.2)

    def test_editorial_overlays_are_not_enabled_on_every_scene(self):
        raw = [
            {"start": i * 5.0, "end": (i + 1) * 5.0, "visual_type": "stock_footage",
             "search_queries": [f"distinct documentary shot {i}"]}
            for i in range(8)
        ]
        scenes = _enforce_variety_and_pacing(raw, 40.0, fallback_full="বাংলাদেশের ইতিহাস")
        overlay_scenes = sum(bool(s.get("show_overlay")) for s in scenes)
        self.assertLess(overlay_scenes, len(scenes))
        self.assertGreater(overlay_scenes, 0)


    def test_scene_absolute_start_gap_is_not_pulled_earlier(self):
        raw = [
            {"start": 0.0, "end": 4.0, "duration": 4.0, "visual_type": "stock_footage", "search_queries": ["first scene"]},
            {"start": 7.0, "end": 11.0, "duration": 4.0, "visual_type": "stock_footage", "search_queries": ["second scene"]},
        ]
        scenes = _enforce_variety_and_pacing(raw, 11.0, fallback_full="বাংলাদেশের ইতিহাস")
        self.assertEqual(scenes[0]["start"], 0.0)
        self.assertEqual(scenes[0]["end"], 7.0)
        self.assertEqual(scenes[1]["start"], 7.0)
        self.assertEqual(scenes[1]["end"], 11.0)

    def test_long_timeline_gap_gets_local_graphics_instead_of_stretched_shot(self):
        raw = [
            {"start": 0.0, "end": 4.0, "duration": 4.0, "visual_type": "stock_footage", "search_queries": ["opening shot"]},
            {"start": 14.0, "end": 18.0, "duration": 4.0, "visual_type": "stock_footage", "search_queries": ["later shot"]},
        ]
        scenes = _enforce_variety_and_pacing(raw, 18.0, fallback_full="বাংলাদেশের ইতিহাস")
        gap_scenes = [s for s in scenes if 4.0 <= s["start"] < 14.0]
        self.assertTrue(gap_scenes)
        self.assertTrue(all(s["visual_type"] == "motion_graphic" for s in gap_scenes))
        self.assertEqual(scenes[-1]["start"], 14.0)

    def test_short_audio_scene_plan_does_not_reference_undefined_variables(self):
        scenes = _enforce_variety_and_pacing([], 5.0, fallback_full="রাতের আকাশে অসংখ্য তারা")
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0]["end"], 5.0)
        self.assertEqual(scenes[0]["visual_type"], "motion_graphic")
        self.assertEqual(scenes[0]["search_queries"], [])

    def test_local_fallback_uses_graphics_instead_of_unrelated_stock(self):
        scenes = _enforce_variety_and_pacing([], 18.0, fallback_full="বাংলাদেশের অর্থনীতির পরিবর্তন")
        self.assertTrue(scenes)
        self.assertTrue(all(scene["visual_type"] == "motion_graphic" for scene in scenes))
        self.assertTrue(all(not scene["search_queries"] for scene in scenes))

    def test_provider_plan_requires_valid_scene_timestamps(self):
        self.assertTrue(_is_valid_provider_plan({"scenes": [{"start": 0, "end": 5, "visual_type": "stock_footage", "search_queries": ["river aerial"]}]}, 10))
        self.assertFalse(_is_valid_provider_plan({"scenes": [{"start": 8, "end": 3, "visual_type": "stock_footage", "search_queries": ["bad"]}]}, 10))

    def test_chunk_prompt_uses_absolute_narration_timestamps(self):
        prompt = _build_prompt("[120.0s - 125.0s] নদীর দৃশ্য", 600.0, window_start=120.0, window_end=240.0)
        self.assertIn("from 120.0s to 240.0s", prompt)
        self.assertIn("ABSOLUTE timestamps", prompt)

    def test_long_documentary_falls_back_per_chunk_without_api_keys(self):
        import os
        from unittest.mock import patch
        segments = [
            {"start": 0.0, "end": 100.0, "text": "প্রথম অংশের বিবরণ"},
            {"start": 120.0, "end": 190.0, "text": "দ্বিতীয় অংশের বিবরণ"},
        ]
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": "", "OPENROUTER_API_KEY": "", "AI_SCENE_CHUNK_SECONDS": "120"}):
            plan = plan_scenes("সম্পূর্ণ ডকুমেন্টারি", 190.0, segments=segments)
        self.assertEqual(plan["planning_mode"], "local_graphics_fallback")
        self.assertTrue(all(scene["visual_type"] == "motion_graphic" for scene in plan["scenes"]))
        self.assertAlmostEqual(plan["scenes"][-1]["end"], 190.0)

    def test_wikimedia_fallback_requires_explicit_free_license(self):
        self.assertTrue(_is_license_unrestricted("CC0"))
        self.assertTrue(_is_license_unrestricted("Public domain"))
        self.assertFalse(_is_license_unrestricted(""))
        self.assertFalse(_is_license_unrestricted("CC BY-NC 4.0"))


class RenderTests(unittest.TestCase):
    def test_all_documentary_grades_exist(self):
        self.assertTrue({"cinematic_teal", "warm_history", "cool_science", "neutral_doc"}.issubset(GRADE_FILTERS))

    def test_camera_motion_has_supported_modes(self):
        for mode in ("slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"):
            self.assertIn("crop=1920:1080", _camera_filter({"motion_effect": mode}))

    def test_srt_time_format(self):
        self.assertEqual(_fmt_srt_time(65.125), "00:01:05,125")

    def test_frame_rate_parser(self):
        self.assertAlmostEqual(_rate("30/1"), 30.0)
        self.assertAlmostEqual(_rate("30000/1001"), 29.97002997, places=5)


if __name__ == "__main__":
    unittest.main()
