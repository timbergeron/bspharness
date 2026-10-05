from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from bspharness import Map, Material, Palette, TextureLibrary, TransitionRule, WallRun, box, ramp
from bspharness.geometry import dot, normalize
from bspharness.seams import Surface, audit
from bspharness.wad import make_blockout, miptex, write_wad


def library_fixture(root):
    utility = make_blockout(root/"utility.wad")
    extra = write_wad(root/"extra.wad",{
        "small":miptex("small",64,64,bytes([9])*4096),
        "large":miptex("large",128,128,bytes([9])*16384),
        "wide":miptex("wide",128,64,bytes([9])*8192)})
    return [extra,utility],TextureLibrary([extra,utility])


def floor(index, texture="small", size=(64,64), x0=0, x1=128, y0=0, y1=128, rows=None):
    return Surface(index,0,texture,size,(0,0,1),((x0,y0,0),(x1,y0,0),(x1,y1,0),(x0,y1,0)),
                   rows or ((0.5,0,0,0),(0,-0.5,0,0)))


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wads,self.library = library_fixture(self.root)

    def test_density_anchor_and_phase_have_physical_meaning(self):
        material = Material("small",density=0.5,anchor=(64,32,16),phase=(0.25,0.5))
        face = material.map_face(box(0,0,0,128,128,32).faces[0],self.library)
        self.assertEqual(face.uv(material.anchor),(16,32))
        self.assertEqual(face.uv((96,32,16)),(32,32))

    def test_same_repeat_for_different_resolutions_and_rectangular_texture(self):
        for texture in ("small","large","wide"):
            material = Material(texture,repeat=(128,256),anchor=(16,32,0))
            face = material.map_face(box(0,0,0,128,128,32).faces[0],self.library)
            w,h = self.library[texture]["width"],self.library[texture]["height"]
            uv = face.uv((144,-224,0))
            self.assertAlmostEqual(uv[0]/w,1)
            self.assertAlmostEqual(uv[1]/h,1)

    def test_surface_projection_preserves_density_on_a_slope(self):
        face = ramp(0,0,128,128,-8,8,72).faces[0]
        mapped = Material("small",density=2,projection="surface").map_face(face,self.library)
        self.assertAlmostEqual(dot(mapped.uaxis,normalize(face.normal)),0)
        self.assertAlmostEqual(dot(mapped.vaxis,normalize(face.normal)),0)
        self.assertAlmostEqual(dot(mapped.uaxis,mapped.uaxis),1)
        self.assertAlmostEqual(dot(mapped.vaxis,mapped.vaxis),1)
        self.assertAlmostEqual(mapped.scale,0.5)

    def test_wall_path_unrolls_continuously_around_corner(self):
        material = Material("small",repeat=(128,128))
        run = WallRun(material,((0,0),(128,0),(128,128)),z_anchor=32)
        a = box(0,-16,0,128,0,128)
        b = box(128,0,0,144,128,128)
        first = run.map_face(a.faces[2],a.face_vertices(a.faces[2]),self.library)
        second = run.map_face(b.faces[5],b.face_vertices(b.faces[5]),self.library)
        self.assertEqual(first.uv((128,0,32)),second.uv((128,0,32)))
        self.assertEqual(second.uv((128,128,32)),(128,0))

    def test_legacy_texture_axes_and_offsets_are_preserved(self):
        face = replace(box(0,0,0,32,32,32).faces[0],scale=2,uoff=8,voff=16)
        self.assertEqual(face.uv((32,16,32)),(24,8))
        self.assertIn("[ 1 0 0 8 ] [ 0 -1 0 16 ] 0 2 2",face.line())

    def test_invalid_materials_are_rejected(self):
        for options in ({"density":0},{"repeat":(0,128)}, {"density":1,"repeat":(128,128)},
                        {"anchor":(0,0,float("nan"))},{"phase":(0,float("inf"))}):
            with self.subTest(options=options),self.assertRaises(ValueError):
                Material("small",**options)

    def test_material_export_uses_wad_dimensions_and_records_contract(self):
        arena = Map()
        arena.room("room",(0,0,0),(256,256,256),Palette(floor=Material("wide",repeat=(256,128))))
        path = arena.write(self.root/"room.map",self.wads)
        import json
        contract = json.loads(path.with_suffix(".materials.json").read_text())
        self.assertEqual(contract["materials"][0]["scales"],[2,2])
        self.assertIn("wide [ 1 0 0 0 ] [ 0 -1 0 0 ] 0 2 2",path.read_text())

    def test_export_does_not_mutate_authored_details_or_entity_brushes(self):
        arena = Map()
        arena.room("room",(0,0,0),(256,256,256))
        detail = box(16,16,0,32,32,32,texture=Material("small",density=0.5))
        entity = box(64,64,0,80,80,32,texture=Material("small",density=0.5))
        arena.detail(detail)
        arena.entity("func_wall",brushes=[entity])
        arena.write(self.root/"immutable.map",self.wads)
        self.assertIsNone(detail.faces[0].uaxis)
        self.assertIsNone(entity.faces[0].uaxis)

    def test_unused_wall_run_fails_instead_of_silently_falling_back(self):
        arena = Map()
        arena.room("room",(0,0,0),(256,256,256))
        arena.wall_run(Material("bh_wall"),[(1024,1024),(1280,1024)])
        with self.assertRaisesRegex(ValueError,"matched no faces"):
            arena.write(self.root/"unused.map",self.wads)


class TransitionTests(unittest.TestCase):
    def map(self, east_floor=0, width=256):
        arena = Map()
        arena.room("west",(-256,0,0),(0,width,256),Palette(wall="bh_wall"))
        arena.room("east",(0,0,east_floor),(256,width,256),Palette(wall="bh_accent"))
        return arena

    def test_registered_rule_adds_frame_and_flush_floor_band(self):
        arena = self.map()
        arena.transition_rule(TransitionRule(("bh_wall","bh_accent"),Material("bh_trim")))
        portal, = arena.portals()
        self.assertEqual(len(portal.frame_brushes()),3)
        self.assertEqual(portal.band.maxs[2],0)
        # Floor trim belongs to the existing structural seal; there is no
        # duplicate coplanar slab or raised threshold in the opening.
        floors = [f for b in arena.world_brushes() for f in b.faces
                  if f.texture=="bh_trim" and f.normal[2]>0 and all(p[2]==0 for p in f.points)]
        self.assertTrue(floors)

    def test_clearance_and_different_floor_heights_fail_explicitly(self):
        for arena in (self.map(east_floor=32),self.map(width=112)):
            arena.transition("west","east","bh_trim")
            with self.assertRaises(ValueError):
                arena.world_brushes()

    def test_explicit_transition_overrides_a_rule_and_can_disable_threshold(self):
        arena = self.map(east_floor=32)
        arena.transition_rule(TransitionRule(("bh_wall","bh_accent"),"bh_trim"))
        arena.transition("west","east","bh_trim",threshold=False,width=8)
        portal, = arena.portals()
        self.assertIsNone(portal.band)
        self.assertEqual(portal.rule.width,8)

    def test_transition_cannot_extend_outside_its_rooms(self):
        arena = self.map()
        arena.transition("west","east","bh_trim",depth=1024)
        with self.assertRaisesRegex(ValueError,"extends beyond"):
            arena.portals()

    def test_intersecting_thresholds_with_different_trims_are_rejected(self):
        arena = self.map()
        arena.room("north",(-256,256,0),(0,512,256))
        arena.transition("west","east","bh_trim")
        arena.transition("west","north","bh_accent")
        with self.assertRaisesRegex(ValueError,"Conflicting floor trim"):
            arena.portals()


class SeamTests(unittest.TestCase):
    def test_compiled_texture_dimensions_must_match_the_material_contract(self):
        contract = {"materials":[{"texture":"small","width":128,"height":128}]}
        report = audit([floor(0)],contract)
        self.assertFalse(report["passed"])
        self.assertEqual(report["counts"],{"texture_dimensions_mismatch":1})

    def test_compatible_different_resolutions_match_in_normalized_uv_space(self):
        surfaces = [floor(0),floor(1,"large",(128,128),128,256,rows=((1,0,0,0),(0,-1,0,0)))]
        contract = {"materials":[{"texture":t,"family":"tiles"} for t in ("small","large")]}
        self.assertTrue(audit(surfaces,contract)["passed"])
        surfaces[1] = replace(surfaces[1],uv_rows=((1,0,0,8),(0,-1,0,0)))
        self.assertFalse(audit(surfaces,contract)["passed"])

    def test_t_junctions_and_period_equivalent_offsets(self):
        surfaces = [floor(0),floor(1,x0=128,x1=256,y1=64),floor(2,x0=128,x1=256,y0=64)]
        surfaces[1] = replace(surfaces[1],uv_rows=((0.5,0,0,64),(0,-0.5,0,0)))
        report = audit(surfaces)
        self.assertTrue(report["passed"])
        self.assertEqual(report["checked_edges"],3)

    def test_integer_endpoint_match_does_not_hide_frequency_reversal(self):
        report = audit([floor(0),floor(1,x0=128,x1=256,rows=((0.5,0,0,0),(0,0.5,0,0)))])
        self.assertFalse(report["passed"])
        self.assertGreater(report["errors"][0]["edge_drift_pixels"],0)

    def test_density_mismatch_perpendicular_to_edge_is_detected(self):
        report = audit([floor(0),floor(1,x0=128,x1=256,rows=((1,0,0,0),(0,-0.5,0,0)))])
        self.assertIn("repeat_density_mismatch",report["counts"])

    def test_unrelated_material_change_requires_review_unless_declared(self):
        surfaces = [floor(0),floor(1,"trim",x0=128,x1=256)]
        self.assertEqual(len(audit(surfaces)["warnings"]),1)
        self.assertEqual(audit(surfaces,{"allowed_pairs":[["small","trim"]]})["warnings"],[])


if __name__=="__main__":
    unittest.main()
