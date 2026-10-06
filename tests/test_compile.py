"""Real compiler tests, enabled explicitly with BSPHARNESS_INTEGRATION=1."""

import os
import json
from pathlib import Path
import tempfile
import unittest

from bspharness import Map, Material, Palette, arch, box, fixture, stairs
from bspharness.bsp import BSP
from bspharness.pipeline import ROOT, build, digest, package, verified_build
from bspharness.seams import bsp_surfaces
from bspharness.collision import EMPTY, SOLID, Hull
from bspharness.source import read
from bspharness.wad import make_blockout, miptex, write_wad


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
                    qa = self.root/"qa.json"
                    evidence = {"passed":True,"bsp_sha256":digest(result),
                                "artifacts":verified_build(result)["artifacts"]}
                    qa.write_text(json.dumps(evidence))
                    package(result,self.root/"reviewed.zip",credits,qa)
                    evidence["artifacts"][result.with_suffix(".lit").name] = "changed-lighting"
                    qa.write_text(json.dumps(evidence))
                    with self.assertRaisesRegex(ValueError,"including colored lighting"):
                        package(result,self.root/"stale-qa.zip",credits,qa)
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

    def material_source(self, density_mismatch=False):
        extra = write_wad(self.root/"extra.wad",{
            "tile64":miptex("tile64",64,64,bytes([9])*4096),
            "tile128":miptex("tile128",128,128,bytes([9])*16384),
            "wide":miptex("wide",128,64,bytes([9])*8192)})
        small = Material("tile64",repeat=(128,128),anchor=(64,32,0),family="tiles")
        large = Material("tile128",repeat=(256 if density_mismatch else 128,128),
                         anchor=(64,32,0),family="tiles")
        wall = Material("wide",repeat=(128,256),anchor=(0,0,32))
        arena = Map("Material compile test",_minlight="16")
        arena.room("west",(-256,-128,0),(0,128,256),Palette(wall=wall,floor=small))
        arena.room("east",(0,-128,0),(256,128,256),Palette(wall=wall,floor=large))
        arena.wall_run(wall,[(-256,-128),(256,-128),(256,128),(-256,128),(-256,-128)])
        arena.entity("info_player_start",(-128,0,24))
        arena.light((0,0,160),300)
        return arena.write(self.root/"materials.map",[extra,self.wad])

    def test_compiled_materials_and_wrapped_corners_in_all_formats(self):
        source = self.material_source()
        for fmt in ("bsp29","bsp2","2psb"):
            with self.subTest(fmt=fmt):
                result = build(source,self.root/f"materials-{fmt}","draft",fmt)
                report = json.loads((result.parent/"seams.json").read_text())
                self.assertTrue(report["passed"])
                self.assertGreater(report["checked_wrapped_edges"],0)
                self.assertEqual(report["unchecked_wall_corners"],0)
                self.assertEqual(report["warnings"],[])
                surfaces = bsp_surfaces(BSP(result))
                for texture,size in (("tile64",64),("tile128",128)):
                    faces = [s for s in surfaces if s.texture==texture]
                    self.assertTrue(faces)
                    for face in faces:
                        self.assertEqual(face.uv((64,32,0)),(0,0))
                        self.assertEqual(face.uv((192,-96,0)),(size,size))
                for face in (s for s in surfaces if s.texture=="wide"):
                    self.assertEqual(face.density(),(1,0.25))
                verified_build(result)

    def test_compiled_misalignment_and_repeat_mismatch_fail_build(self):
        source = self.material_source()
        # Move only tile128's U offset by eight pixels. Update the source
        # hash to test compiled UV rejection, rather than stale metadata.
        lines = source.read_text().splitlines()
        for index,line in enumerate(lines):
            if " tile128 " in line:
                lines[index] = line.replace("[ 1 0 0 -64 ]","[ 1 0 0 -56 ]")
        source.write_text("\n".join(lines)+"\n")
        sidecar = source.with_suffix(".materials.json")
        contract = json.loads(sidecar.read_text())
        contract["map_sha256"] = digest(source)
        sidecar.write_text(json.dumps(contract))
        with self.assertRaisesRegex(ValueError,"Texture seam checks failed"):
            build(source,self.root/"misaligned","draft")
        evidence, = (self.root/"misaligned/materials/draft").glob("run-*/seams.json")
        self.assertIn("uv_discontinuity",json.loads(evidence.read_text())["counts"])
        source = self.material_source(density_mismatch=True)
        with self.assertRaisesRegex(ValueError,"Texture seam checks failed"):
            build(source,self.root/"density","draft")

    def test_material_contract_and_evidence_hashes(self):
        source = self.material_source()
        original = source.read_text()
        source.write_text(original+"// changed\n")
        with self.assertRaisesRegex(ValueError,"contract is stale"):
            build(source,self.root/"stale","draft")
        source.write_text(original)
        result = build(source,self.root/"evidence","draft")
        credits = self.root/"credits.txt"
        credits.write_text("Original test textures.\n")
        archive = package(result,self.root/"materials.zip",credits)
        import zipfile
        with zipfile.ZipFile(archive) as release:
            self.assertIn("seams.json",release.namelist())
            self.assertIn("source/materials.materials.json",release.namelist())
        evidence = result.parent/"seams.json"
        evidence.write_text(evidence.read_text()+" ")
        with self.assertRaisesRegex(ValueError,"Modified material/seam evidence"):
            verified_build(result)
        with self.assertRaisesRegex(ValueError,"Modified material/seam evidence"):
            package(result,self.root/"tampered.zip",credits)

    def test_wad_precedence_matches_material_dimension_lookup(self):
        first = write_wad(self.root/"first.wad",{"duplicate":miptex("duplicate",64,64,bytes([9])*4096)})
        last = write_wad(self.root/"last.wad",{"duplicate":miptex("duplicate",128,128,bytes([9])*16384)})
        self.map.airs.clear()
        self.map.room("room",(-256,-256,0),(256,256,256),
                      Palette(floor=Material("duplicate",repeat=(128,128))))
        source = self.map.write(self.root/"precedence.map",[first,last,self.wad])
        for compiler in ("modern","stable"):
            with self.subTest(compiler=compiler):
                result = build(source,self.root/f"precedence-{compiler}","draft",
                               qbsp_dir=ROOT/"tools/ericw"/compiler)
                faces = [s for s in bsp_surfaces(BSP(result)) if s.texture=="duplicate"]
                self.assertTrue(faces)
                self.assertTrue(all(s.size==(128,128) for s in faces))
                self.assertTrue(all(s.density()==(1,1) for s in faces))

    def test_compiler_detail_roles_preserve_selected_collision_in_all_formats(self):
        self.map.structural(box(-144,-16,0,-112,16,64))
        self.map.detail(box(-80,-16,0,-48,16,64))
        self.map.detail(box(-16,-16,0,16,16,64),mode="wall")
        self.map.detail(box(48,-16,0,80,16,64),mode="fence")
        self.map.detail(box(112,-16,0,144,16,64),mode="illusionary",_shadow="1")
        source = self.map.write(self.root/"roles.map",[self.wad])
        for fmt in ("bsp29","bsp2","2psb"):
            with self.subTest(fmt=fmt):
                result = build(source,self.root/f"roles-{fmt}","draft",fmt)
                bsp = BSP(result)
                hull = Hull(bsp)
                self.assertEqual(hull.contents((-128,0,48)),SOLID)
                self.assertEqual(hull.contents((-64,0,48)),SOLID)
                self.assertEqual(hull.contents((0,0,48)),SOLID)
                self.assertEqual(hull.contents((64,0,48)),SOLID)
                self.assertEqual(hull.contents((128,0,48)),EMPTY)
                self.assertEqual(bsp.count("models"),1)
                self.assertFalse(any(e["classname"].startswith("func_detail") for e in bsp.entities()))

    def test_compiled_stair_surfaces_arch_clearance_and_fixture(self):
        self.map.structural(*stairs((-192,64,0),width=96,rise=12,run=48,steps=4))
        self.map.detail(*arch((0,0,0),width=160,spring=104,rise=64,thickness=16,wall_height=256),mode="detail")
        fixture(self.map,(-32,240,96),(32,248,144),offset=16)
        source = self.map.write(self.root/"kits.map",[self.wad])
        result = build(source,self.root/"kits","draft")
        hull = Hull(BSP(result))
        for i in range(4):
            self.assertEqual(hull.contents((-168+i*48,112,(i+1)*12+24.1)),EMPTY)
            self.assertEqual(hull.contents((-168+i*48,112,(i+1)*12+10)),SOLID)
        self.assertEqual(hull.contents((0,0,24.1)),EMPTY)
        self.assertEqual(hull.contents((100,0,48)),SOLID)
        self.assertEqual(hull.contents((0,0,220)),SOLID)

    def test_explicit_build_budgets_fail_and_metrics_match_actual_bsp(self):
        result = build(self.source,self.root/"budget","draft",budgets={"faces":5000,"clipnodes":5000})
        manifest = verified_build(result)
        self.assertEqual(manifest["metrics"],BSP(result).metrics())
        with self.assertRaisesRegex(ValueError,"Build budget exceeded"):
            build(self.source,self.root/"budget","draft",budgets={"faces":1})
        self.assertFalse((result.parent/"build.json").exists())

    def test_imported_explicit_shell_seals_without_generated_room_geometry(self):
        imported=read(self.source)
        arena=Map("Imported test",shell="explicit",_minlight="16")
        arena.structural(*(b.mapped(lambda f:f.texture) for b in imported[0].brushes))
        for entity in imported[1:]:
            keys=entity.keys.copy();name=keys.pop("classname");origin=keys.pop("origin",None)
            arena.entity(name,tuple(map(float,origin.split())) if origin else None,**keys)
        source=arena.write(self.root/"imported.map",[self.wad])
        for fmt in ("bsp29","bsp2","2psb"):
            result=build(source,self.root/f"import-{fmt}","draft",fmt)
            self.assertTrue(BSP(result).validate(fmt)["passed"])
            self.assertEqual(Hull(BSP(result)).contents((0,0,24.1)),EMPTY)
        # Removing an outer structural wall must expose a leak, not trigger
        # an automatically generated box that conceals the missing geometry.
        before=len(arena.details)
        arena.details=[b for b in arena.details if min(p[0] for p in b.vertices)<255.9]
        self.assertLess(len(arena.details),before)
        source=arena.write(source,[self.wad])
        with self.assertRaises(ValueError):build(source,self.root/"import-leaked","draft")


if __name__=="__main__":
    unittest.main()
