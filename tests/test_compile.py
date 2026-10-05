"""Real compiler tests, enabled explicitly with BSPHARNESS_INTEGRATION=1."""

import os
from pathlib import Path
import tempfile
import unittest

from bspharness import Map, box
from bspharness.bsp import BSP
from bspharness.pipeline import ROOT, build, package, verified_build
from bspharness.wad import make_blockout


@unittest.skipUnless(os.environ.get("BSPHARNESS_INTEGRATION")=="1","set BSPHARNESS_INTEGRATION=1 after bootstrap")
class CompileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bspharness-test-",dir=ROOT/"out" if (ROOT/"out").exists() else ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wad = make_blockout(self.root/"utility.wad")
        self.map = Map("Compile test",_minlight="16")
        self.map.room("room",(-256,-256,0),(256,256,256))
        self.map.entity("info_player_start",(0,0,24))
        self.map.light((64,64,160),300)
        self.source = self.map.write(self.root/"room.map",[self.wad])

    def test_all_formats_and_release_hashes(self):
        for fmt in ("bsp29","bsp2","2psb"):
            with self.subTest(fmt=fmt):
                result = build(self.source,self.root/fmt,"draft",fmt)
                self.assertTrue(BSP(result).validate(fmt)["passed"])
                verified_build(result)
                if fmt=="bsp29":
                    credits = self.root/"credits.txt"
                    credits.write_text("Original blockout; built with ericw-tools.\n")
                    package(result,self.root/"map.zip",credits)
                    result.write_bytes(result.read_bytes()+b"changed")
                    with self.assertRaisesRegex(ValueError,"successful"):
                        verified_build(result)

    def test_stable_qbsp_with_modern_vis_and_light(self):
        result = build(self.source,self.root/"stable","draft",qbsp_dir=ROOT/"tools/ericw/stable")
        self.assertTrue(BSP(result).validate()["passed"])

    def test_lighting_profile_contracts(self):
        for profile in ("mono","showcase"):
            with self.subTest(profile=profile):
                result = build(self.source,self.root/profile,profile)
                report = BSP(result).validate()
                self.assertTrue(report["passed"])
                if profile=="mono":
                    self.assertFalse(result.with_suffix(".lit").exists())
                    self.assertNotIn("RGBLIGHTING",report["bspx"])
                else:
                    self.assertTrue({"RGBLIGHTING","DECOUPLED_LM","LIGHTGRID_OCTREE","LIGHTING_E5BGR9"}.issubset(report["bspx"]))

    def test_missing_texture_and_leak_fail_and_invalidate_previous_build(self):
        build(self.source,self.root/"failed","draft")
        self.source.write_text(self.source.read_text().replace("bh_wall","unavailable"))
        with self.assertRaises(ValueError):
            build(self.source,self.root/"failed","draft")
        self.assertFalse((self.root/"failed/room/draft/build.json").exists())
        # A floor without enclosing walls is an intentional leak.
        self.source.write_text('{\n"classname" "worldspawn"\n"wad" "'+self.wad.as_posix()+'"\n'+
                               box(-256,-256,-64,256,256,0).text()+'\n}\n'+
                               '{\n"classname" "info_player_start"\n"origin" "0 0 24"\n}\n')
        with self.assertRaises(ValueError):
            build(self.source,self.root/"leaked","draft")
        self.assertFalse((self.root/"leaked/room/draft/build.json").exists())


if __name__=="__main__":
    unittest.main()
