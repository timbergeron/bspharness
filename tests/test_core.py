from pathlib import Path
import random
import struct
import tempfile
import unittest

from bspharness import Bounds, Map, Palette, box, ramp
from bspharness.bsp import BSP
from bspharness.geometry import dot, vector
from bspharness.pak import entries
from bspharness.qa import audit_log, camera_config
from bspharness.wad import make_blockout, read_wad, validate_miptex


class GeometryTests(unittest.TestCase):
    def test_subtraction_preserves_volume_and_disjointness(self):
        rng = random.Random(42)
        world = Bounds((0,0,0),(100,100,100))
        for _ in range(100):
            low = tuple(rng.randint(-50,120) for _ in range(3))
            high = tuple(x+rng.randint(1,100) for x in low)
            cut = Bounds(low,high)
            result = world.subtract(cut)
            overlap = 1
            for axis in range(3):
                overlap *= max(0,min(100,high[axis])-max(0,low[axis]))
            self.assertEqual(sum(b.volume for b in result)+overlap,world.volume)
            for a in result:
                self.assertTrue(world.contains(a.mins) and world.contains(a.maxs))
                for b in result:
                    if a is not b:
                        self.assertFalse(all(max(a.mins[i],b.mins[i])<min(a.maxs[i],b.maxs[i]) for i in range(3)))

    def test_planes_point_outward_for_boxes_and_both_ramp_axes(self):
        brushes = [box(-64,-32,-8,64,32,64),ramp(-64,-32,64,32,-8,8,64),
                   ramp(-64,-32,64,32,-8,64,8,along="y")]
        for brush in brushes:
            for face in brush.faces:
                self.assertGreater(dot(face.normal,vector(face.points[1],brush.interior)),0)

    def test_reject_degenerate_geometry(self):
        with self.assertRaises(ValueError):
            box(0,0,0,0,32,32)
        with self.assertRaises(ValueError):
            ramp(0,0,32,32,0,0,32)
        with self.assertRaises(ValueError):
            Bounds((0,0,0),(float("inf"),1,1))

    def test_adjacent_palettes_and_sky_are_partitioned(self):
        arena = Map()
        arena.room("left",(-128,-128,0),(0,128,128),Palette(wall="left",ceiling="left_ceil"))
        arena.room("right",(0,-128,0),(128,128,128),Palette(wall="right",ceiling="right_ceil"))
        arena.room("sky",(0,-128,128),(128,128,192),kind="sky")
        textures = {f.texture for b in arena.world_brushes() for f in b.faces}
        self.assertTrue({"left","right","sky_bh"}.issubset(textures))
        # Room air never overlaps any seal solid's interior.
        for brush in arena.world_brushes():
            self.assertFalse(any(all(a.bounds.mins[i]<brush.interior[i]<a.bounds.maxs[i] for i in range(3)) for a in arena.airs))


class BinaryTests(unittest.TestCase):
    def test_generated_wad_mips_and_corrupt_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = make_blockout(Path(temp)/"blockout.wad")
            textures = read_wad(path)
            self.assertEqual(textures["sky_bh"]["width"],256)
            data = bytearray(path.read_bytes())
            # First texture begins immediately after the WAD2 header.
            struct.pack_into("<I",data,12+16,0x0D0CB00D)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"dimensions"):
                read_wad(path)

    def test_reject_truncated_mips(self):
        header = struct.pack("<16s6I",b"test",16,16,40,296,360,376)
        with self.assertRaisesRegex(ValueError,"truncated"):
            validate_miptex(header+bytes(256))

    def test_reject_bsp_lumps_outside_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"broken.bsp"
            data = bytearray(struct.pack("<i",29)+bytes(120))
            struct.pack_into("<ii",data,4,124,900)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"range"):
                BSP(path)

    def test_reject_pak_directory_outside_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"broken.pak"
            path.write_bytes(struct.pack("<4sii",b"PACK",100,64))
            with self.assertRaisesRegex(ValueError,"directory"):
                list(entries(path))


class QATests(unittest.TestCase):
    def test_runtime_audit_catches_missing_item_and_bad_ground(self):
        text = """BSPHARNESS_AUDIT_BEGIN
EDICT 1:
classname      player
origin         '0 0 24'
health         100
flags          FL_CLIENT | FL_ONGROUND
EDICT 2:
classname      weapon_rocketlauncher
origin         '128 0 6'
BSPHARNESS_AUDIT_END
BSPHARNESS_QA_COMPLETE
"""
        expected = [{"classname":"weapon_rocketlauncher","origin":"128 0 24"}]
        self.assertEqual(audit_log(text,expected),[])
        self.assertTrue(any("absent" in e for e in audit_log(text,[{"classname":"item_armorInv","origin":"256 0 24"}])))
        self.assertTrue(any("ground" in e for e in audit_log(text.replace("FL_ONGROUND","FL_SWIM"),expected)))

    def test_camera_input_cannot_inject_commands(self):
        with self.assertRaises((ValueError,TypeError)):
            camera_config([{"name":"camera","origin":["0;quit",0,0],"angles":[0,0,0]}])


if __name__=="__main__":
    unittest.main()
