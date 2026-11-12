"""Tests for convert/convert.py, run on the files tests/extract-upstream.sh took out of the pinned image.

    python3 -m unittest discover -s tests

They fail when the pinned upstream image lacks a file or folder the conversion edits, when an anchor no longer
matches, and when the conversion would carry on past a missing file instead of stopping.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
UPSTREAM = HERE / ".upstream"
sys.path.insert(0, str(REPO / "convert"))
import convert  # noqa: E402

os.environ.setdefault("AHI_SKIP_FONTS", "1")  # the fonts come from the Dockerfile's fonts stage


_LOCAL: Path | None = None


def fresh_root() -> Path:
    """A converted-from-scratch copy of the upstream files, on local disk (one read of tests/.upstream)."""
    global _LOCAL
    if not UPSTREAM.is_dir():
        raise unittest.SkipTest("run tests/extract-upstream.sh first (tests/run.sh does)")
    if _LOCAL is None:
        _LOCAL = Path(tempfile.mkdtemp(prefix="ahi-orca-upstream-"))
        shutil.copytree(UPSTREAM, _LOCAL, dirs_exist_ok=True, symlinks=True)
    root = Path(tempfile.mkdtemp(prefix="ahi-orca-"))
    shutil.copytree(_LOCAL, root, dirs_exist_ok=True, symlinks=True)
    return root


class UpstreamHasEverything(unittest.TestCase):
    def test_every_edited_file_is_in_the_pinned_image(self):
        missing = [rel for rel in convert.EDITED if not (UPSTREAM / rel).is_file()]
        self.assertEqual(missing, [], "files convert.py edits are missing from the pinned image")

    def test_every_folder_added_to_is_in_the_pinned_image(self):
        missing = [rel for rel in convert.FOLDERS if not (UPSTREAM / rel).is_dir()]
        self.assertEqual(missing, [], "folders convert.py adds to are missing from the pinned image")


class Pins(unittest.TestCase):
    def test_dockerfile_defaults_match_upstream_env(self):
        env = dict(line.split("=", 1) for line in (REPO / "upstream.env").read_text().splitlines()
                   if line and not line.startswith("#"))
        docker = (REPO / "Dockerfile").read_text()
        for key in ("ORCASLICER_IMAGE", "ORCASLICER_VERSION", "ORCASLICER_DIGEST", "FONTSOURCE_VERSION"):
            self.assertIn(f"ARG {key}={env[key]}\n", docker, key)


class Conversion(unittest.TestCase):
    def setUp(self):
        self.root = fresh_root()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def test_converts_the_pinned_image(self):
        convert.main(["convert.py", str(self.root)])
        index = self.read(f"{convert.DASHBOARD}/index.html")
        self.assertIn('href="./ahi/ahi-dashboard.css"', index)
        self.assertIn("<title>OrcaSlicer</title>", index)
        self.assertTrue((self.root / convert.DASHBOARD / "ahi/ahi-dashboard.css").is_file())
        # The upstream dashboard stays as it was, so DASHBOARD=selkies-dashboard still gives it.
        self.assertNotIn("ahi-dashboard.css", self.read(f"{convert.DASHBOARD_SRC}/index.html"))
        rc = self.read(convert.LABWC_RC)
        self.assertIn("<name>ArtisanHub</name>", rc)
        self.assertIn("<name>Manrope</name>", rc)
        self.assertTrue((self.root / "usr/share/themes/ArtisanHub/labwc/themerc").is_file())
        self.assertTrue((self.root / "usr/share/themes/ArtisanHub/gtk-3.0/gtk.css").is_file())
        self.assertIn("gtk-theme-name=ArtisanHub", self.read(convert.GTK_SETTINGS))
        self.assertIn('\\"theme_color\\": \\"#172028\\"', self.read(convert.INIT_NGINX))
        dark = re.search(r"@media \(prefers-color-scheme: dark\).*?\}\s*\}", self.read(convert.GLOBAL_CSS), re.S).group(0)
        for name, value in convert.GLOBAL_DARK.items():
            self.assertRegex(dark, r"%s\s*:\s*%s;" % (re.escape(name), re.escape(value)))
        guide = self.read(convert.GUIDE_DARK)
        self.assertNotRegex(guide, r"(?i)#009688|#2D2D31")
        for rel in convert.FONT_FILES:
            self.assertIn(convert.FONT_NEW, self.read(rel))
        s6 = self.root / convert.S6
        self.assertTrue((s6 / "init-ahi-orca/run").is_file())
        self.assertEqual((s6 / "init-ahi-orca/type").read_text().strip(), "oneshot")
        self.assertTrue((s6 / "init-config-end/dependencies.d/init-ahi-orca").exists())
        self.assertTrue((s6 / "user/contents.d/init-ahi-orca").exists())

    def test_the_light_values_are_left_alone(self):
        before = self.read(convert.GLOBAL_CSS)
        light = before.split("@media (prefers-color-scheme: dark)")[0]
        convert.main(["convert.py", str(self.root)])
        self.assertEqual(self.read(convert.GLOBAL_CSS).split("@media (prefers-color-scheme: dark)")[0], light)


class StopsOnMissing(unittest.TestCase):
    def test_each_missing_file_stops_the_conversion(self):
        for rel in convert.EDITED:
            with self.subTest(rel=rel):
                root = fresh_root()
                try:
                    (root / rel).unlink()
                    with self.assertRaises(convert.ConvertError) as caught:
                        convert.main(["convert.py", str(root)])
                    self.assertIn(rel, str(caught.exception))
                finally:
                    shutil.rmtree(root, ignore_errors=True)

    def test_each_missing_folder_stops_the_conversion(self):
        for rel in convert.FOLDERS:
            with self.subTest(rel=rel):
                root = fresh_root()
                try:
                    shutil.rmtree(root / rel)
                    with self.assertRaises(convert.ConvertError):
                        convert.main(["convert.py", str(root)])
                finally:
                    shutil.rmtree(root, ignore_errors=True)

    def test_a_changed_anchor_stops_the_conversion(self):
        root = fresh_root()
        try:
            rc = root / convert.LABWC_RC
            rc.write_text(rc.read_text().replace("<name>Clearlooks</name>", "<name>Other</name>"))
            with self.assertRaises(convert.ConvertError) as caught:
                convert.main(["convert.py", str(root)])
            self.assertIn(convert.LABWC_RC, str(caught.exception))
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
