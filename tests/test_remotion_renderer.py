import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "processor"))
os.environ.setdefault("WORK_DIR", tempfile.mkdtemp(prefix="docmaker-remotion-test-"))
from remotion_render import FPS, _bn


class RemotionRendererTests(unittest.TestCase):
    def test_fps_matches_reference_composition(self):
        self.assertEqual(FPS, 30)

    def test_bengali_text_is_unicode_nfc_normalized(self):
        self.assertEqual(_bn("বাংলাদেশের  ইতিহাস"), "বাংলাদেশের  ইতিহাস")

    def test_renderer_files_are_present(self):
        self.assertTrue((ROOT / "remotion" / "src" / "Video.tsx").exists())
        self.assertTrue((ROOT / "remotion" / "src" / "Root.tsx").exists())
        self.assertTrue((ROOT / "remotion" / "package.json").exists())

    def test_workflow_installs_node_remotion_dependencies(self):
        workflow = (ROOT / ".github" / "workflows" / "documentary-maker.yml").read_text()
        self.assertIn("Set up Node.js for in-app Remotion rendering", workflow)
        self.assertIn("working-directory: remotion", workflow)


if __name__ == "__main__":
    unittest.main()
