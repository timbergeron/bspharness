import json
from pathlib import Path
import tempfile
import unittest

from bspharness.pipeline import digest
from bspharness.review import compare
from bspharness.wad import png


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root/"shot.png"
        png(self.image,2,2,bytes([100,120,140])*4)
        self.report = {"passed":True,"artifacts":{"map.bsp":"source-hash"},
                       "engine_sha256":"engine-hash","render":{"fov":90},
                       "screenshots":[{"camera":"view <test>","file":"shot.png",
                                       "sha256":digest(self.image),
                                       "view":{"origin":[0,0,24],"angles":[0,0,0]}}]}
        self.before = self.root/"before.json"
        self.after = self.root/"after.json"
        self.before.write_text(json.dumps(self.report))
        self.after.write_text(json.dumps(self.report))

    def test_portable_comparison_preserves_hashes_and_requires_human_review(self):
        path = compare(self.before,self.after,self.root/"review")
        report = json.loads(path.with_name("comparison.json").read_text())
        self.assertEqual(report["cameras"][0]["warnings"],[])
        self.assertIn("pending",report["visual_review"])
        self.assertEqual(digest(path.with_name("00-before.png")),digest(self.image))
        self.assertIn("view &lt;test&gt;",path.read_text())
        with self.assertRaisesRegex(ValueError,"fresh"):
            compare(self.before,self.after,path.parent)

    def test_changed_views_and_older_reports_expose_comparison_limits(self):
        self.report["screenshots"][0]["view"]["origin"][2] = 128
        self.report.pop("render")
        self.report["passed"] = False
        self.after.write_text(json.dumps(self.report))
        path = compare(self.before,self.after,self.root/"review")
        report = json.loads(path.with_name("comparison.json").read_text())
        self.assertEqual(len(report["cameras"][0]["warnings"]),2)
        self.assertFalse(report["after"]["passed"])

    def test_tampered_images_or_mismatched_camera_sets_fail_before_writing(self):
        self.image.write_bytes(self.image.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            compare(self.before,self.after,self.root/"review")
        self.assertFalse((self.root/"review").exists())
        self.report["screenshots"][0]["sha256"] = digest(self.image)
        self.before.write_text(json.dumps(self.report))
        self.report["screenshots"][0]["camera"] = "different"
        self.after.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError,"matching named"):
            compare(self.before,self.after,self.root/"review")
