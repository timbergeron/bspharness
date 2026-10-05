from pathlib import Path
import tempfile
import unittest

from bspharness import (Map, Material, Palette, arch, beam, box, column,
                        fixture, lighting_recipe, stairs, trim_profile)
from bspharness.geometry import dot, vector
from bspharness.wad import make_blockout


class KitTests(unittest.TestCase):
    def test_stair_heights_run_and_material_roles_in_all_directions(self):
        palette = Palette(floor="bh_floor",trim="bh_trim")
        for along in ("x","-x","y","-y"):
            with self.subTest(along=along):
                brushes = stairs((16,32,64),width=128,rise=12,run=24,steps=8,along=along,palette=palette)
                self.assertEqual(len(brushes),8)
                for i,brush in enumerate(brushes):
                    self.assertEqual(max(p[2] for p in brush.vertices),64+12*(i+1))
                    self.assertEqual(brush.faces[0].texture,"bh_floor")
                    self.assertTrue(all(f.texture=="bh_trim" for f in brush.faces[1:]))
                axis = 0 if along.endswith("x") else 1
                coordinates = [p[axis] for b in brushes for p in b.vertices]
                self.assertEqual(max(coordinates)-min(coordinates),192)

    def test_arch_column_beam_and_trim_are_bounded_convex_volumes(self):
        groups = [arch((0,0,0),width=256,rise=96,wall_height=280),
                  arch((0,0,0),axis="x",jambs=False),column((0,0,0)),
                  beam((0,0,0),(128,64,48)),trim_profile((0,0,32),(256,0,32))]
        for brushes in groups:
            for brush in brushes:
                self.assertGreaterEqual(len(brush.vertices),4)
                for face in brush.faces:
                    self.assertGreater(dot(face.normal,vector(face.points[1],brush.interior)),0)
                    for vertex in brush.vertices:
                        self.assertLessEqual(dot(face.normal,vector(vertex,face.points[1])),0.001)

    def test_invalid_or_unwalkable_dimensions_are_rejected(self):
        calls = [lambda:stairs((0,0,0),rise=19),lambda:stairs((0,0,0),width=32),
                 lambda:stairs((0,0,0),run=8),lambda:arch((0,0,0),segments=3),
                 lambda:arch((0,0,0),wall_height=128),lambda:column((0,0,0),height=16),
                 lambda:beam((0,0,0),(0,0,0)),lambda:trim_profile((0,0,0),(32,0,8))]
        for call in calls:
            with self.assertRaises(ValueError):
                call()


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wad = make_blockout(self.root/"utility.wad")
        self.map = Map()
        self.map.room("room",(-256,-256,0),(256,256,256))

    def test_geometry_roles_emit_distinct_compiler_entities(self):
        for i,mode in enumerate(("detail","wall","fence","illusionary")):
            self.map.detail(box(i*32,0,0,i*32+16,16,32),mode=mode)
        self.map.structural(box(-64,0,0,-32,32,32))
        source = self.map.write(self.root/"roles.map",[self.wad]).read_text()
        for classname in ("func_detail","func_detail_wall","func_detail_fence","func_detail_illusionary"):
            self.assertIn('"classname" "'+classname+'"',source)
        with self.assertRaises(ValueError):
            self.map.detail(box(0,0,0,16,16,16),mode="unknown")

    def test_fixture_emitter_and_light_point_outward_in_all_directions(self):
        for face in ("north","south","east","west","top","bottom"):
            with self.subTest(face=face):
                fixture(self.map,(-32,-32,64),(32,32,128),face=face,
                        emitter=Material("bh_light"),offset=12)
                keys, = [e for e,b in self.map.entities[-2:] if e["classname"]=="light"]
                point = tuple(map(float,keys["origin"].split()))
                axis,sign = {"north":(1,1),"south":(1,-1),"east":(0,1),"west":(0,-1),
                             "top":(2,1),"bottom":(2,-1)}[face]
                plane = (32 if axis!=2 else 128) if sign>0 else (-32 if axis!=2 else 64)
                self.assertEqual(point[axis],plane+sign*12)
                _,brushes = self.map.entities[-2]
                self.assertEqual(sum(f.texture=="bh_light" for b in brushes for f in b.faces),1)
        self.map.write(self.root/"fixtures.map",[self.wad])

    def test_lighting_recipe_keeps_contrast_configurable(self):
        values = lighting_recipe(minlight=6,bounce=2,sun=150)
        self.assertEqual(values["_minlight"],"6")
        self.assertEqual(values["_bounce"],"2")
        self.assertEqual(values["_sunlight"],"150")
        for options in ({"bounce":1.5},{"sun_color":(256,0,0)},
                        {"sky_color":(0,float("nan"),0)},{"sun_angles":(0,float("inf"),0)}):
            with self.assertRaises(ValueError):
                lighting_recipe(**options)
