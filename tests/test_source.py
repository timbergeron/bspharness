from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from bspharness import Map, Material, box, ramp
from bspharness.geometry import Brush
from bspharness.source import parse
from bspharness.wad import make_blockout


class SourceTests(unittest.TestCase):
    def source(self):
        # Q2-style texture paths and face flags, with non-vertex plane points.
        brush=box(-64,-64,0,64,64,128)
        lines=[]
        for f in brush.faces:
            a,b,c=f.points
            a=tuple(b[i]+(a[i]-b[i])*10 for i in range(3))
            c=tuple(b[i]+(c[i]-b[i])*10 for i in range(3))
            face=replace(f,points=(a,b,c))
            lines.append(face.line().replace('bh_wall','long/path/to/q2texture')+' 134217729 1 250')
        return '{\n"classname" "worldspawn"\n"message" "https://example.com" // comment\n{\n'+'\n'.join(lines)+'\n}\n}\n'

    def test_q2_planes_flags_and_uvs_are_preserved_before_material_mapping(self):
        source=parse(self.source())
        self.assertEqual(source[0].keys['message'],'https://example.com')
        face=source[0].brushes[0].faces[0]
        self.assertEqual((face.contents,face.flags,face.value),(134217729,1,250))
        brush=source[0].brushes[0].mapped('bh_floor')
        self.assertEqual(brush.interior,(0,0,64))
        self.assertEqual(len(brush.vertices),8)
        self.assertEqual(brush.faces[0].uv((128,128,128)),face.mapped('bh_floor').uv((128,128,128)))

    def test_explicit_shell_uses_imported_solids_and_material_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);wad=make_blockout(root/'utility.wad')
            arena=Map(shell='explicit')
            arena.structural(parse(self.source())[0].brushes[0].mapped(Material('bh_floor',repeat=(128,128))))
            path=arena.write(root/'converted.map',[wad])
            self.assertTrue(path.with_suffix('.materials.json').exists())
            self.assertNotIn('134217729',path.read_text())
            self.assertEqual(len(parse(path.read_text())[0].brushes),1)
            with self.assertRaises(ValueError):arena.room('invalid',(0,0,0),(128,128,128))
            with self.assertRaises(ValueError):Map().write(root/'unsealed.map',[wad])

    def test_negative_scales_preserve_the_imported_texture_projection(self):
        original=parse(self.source())[0].brushes[0].faces[0]
        flipped=replace(original,scale=-2,vscale=-4).mapped('bh_floor')
        p=(17,29,128)
        self.assertEqual(flipped.uv(p),
                         (sum(a*b for a,b in zip(original.uaxis,p))/-2+original.uoff,
                          sum(a*b for a,b in zip(original.vaxis,p))/-4+original.voff))

    def test_invalid_or_unsupported_map_input_fails_explicitly(self):
        for text in ('{}','{\n"classname" "worldspawn"','{\n{\n{\n',
                     self.source().replace(' 0 1 1',' 0 0 1'),
                     self.source().replace(' 0 1 1',' 1e400 1 1'),
                     self.source().replace('"message"','"classname"'),
                     self.source().replace('134217729 1 250','not-a-number')):
            with self.subTest(text=text[:100]),self.assertRaises(ValueError):parse(text)
        with self.assertRaises(ValueError):Brush.from_planes(box(0,0,0,64,64,64).faces[:3])
        # A bent floor has noncoplanar vertices and an interior, but no roof.
        floor=ramp(0,0,64,64,-64,-32,32).faces[0].oriented((32,32,64))
        with self.assertRaisesRegex(ValueError,'unbounded'):
            Brush.from_planes((*box(0,0,0,64,64,64).faces[1:],floor))
