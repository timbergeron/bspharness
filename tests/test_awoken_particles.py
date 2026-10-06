"""The optional particle variant must preserve its source and native artwork."""

import json
from pathlib import Path
import re
import tempfile
import unittest

from bspharness.assets import files
from bspharness.pipeline import digest, write_json
from bspharness.source import read
from maps.awoken.particles import config, generate, png, LAYERS, SECTORS, effect_nodes


class AwokenParticleVariantTests(unittest.TestCase):
    def test_all_effect_sectors_are_reachable_with_short_explicit_names(self):
        script=config('map_variant')
        blocks=re.findall(r'r_part (\S+)\n\{\n(.*?)\n\}',script,re.S)
        names={name for name,body in blocks}
        self.assertEqual(len(names),len(effect_nodes()))
        self.assertTrue(all(not n.startswith('+') and len('map_variant.'+n)<64 for n in names))
        links={name:re.findall(r'^\s*assoc (\S+)',body,re.M) for name,body in blocks}
        visited=set();current='vortex'
        while current:
            self.assertIn(current,names)
            self.assertNotIn(current,visited)
            visited.add(current)
            current=links[current][0] if links[current] else None
        self.assertEqual(len(visited),SECTORS*len(LAYERS))
        # Child orbits must terminate and cannot spawn the entire root chain.
        emitted=set()
        bodies=dict(blocks)
        for root in visited:
            current=root;path=set()
            while current:
                self.assertIn(current,names)
                self.assertNotIn(current,path)
                path.add(current)
                children=re.findall(r'^\s*emit (\S+)',bodies[current],re.M)
                self.assertLessEqual(len(children),1)
                if children:
                    lifetime=float(re.search(r'^\s*die ([\d.]+)',bodies[current],re.M)[1])
                    start=float(re.search(r'^\s*emitstart ([\d.]+)',bodies[current],re.M)[1])
                    interval=float(re.search(r'^\s*emitinterval ([\d.]+)',bodies[current],re.M)[1])
                    self.assertLess(start,lifetime)
                    self.assertGreater(interval,lifetime)
                if current not in visited:
                    self.assertFalse(links[current])
                    self.assertIn('    count 0 0 1',bodies[current])
                    self.assertNotIn('    countextra ',bodies[current])
                current=children[0] if children else None
            emitted.update(path)
        self.assertEqual(emitted,names)

    def test_copy_preserves_entities_and_rebinds_map_texture_namespace(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'awoken.map'
            source.write_text('{\n"classname" "worldspawn"\n}\n'+
                              '{\n"classname" "trigger_push"\n"speed" "60"\n}\n'*4)
            original=source.read_bytes()
            art=root/'art';name='textures/awoken/aw_pad.png'
            png(art/name,'haze',size=128)
            records={name:dict(sha256=digest(art/name),width=128,height=128,
                              engine_name=name[:-4])}
            write_json(source.with_suffix('.assets.json'),dict(schema=1,map_sha256=digest(source),
                                                              root='art',files=records))
            write_json(source.with_suffix('.materials.json'),dict(schema=1,map_sha256=digest(source)))
            for suffix in ('routes.json','cameras.json'):
                write_json(source.with_suffix('.'+suffix),[])
            output=root/'variant.map';runtime=root/'runtime'
            generate(source,output,runtime)
            self.assertEqual(source.read_bytes(),original)
            self.assertTrue(output.read_bytes().startswith(original))
            entities=read(output)
            self.assertEqual(entities[:5],read(source))
            self.assertEqual(len(entities),9)
            self.assertTrue(all(e.keys['classname']=='light_globe' and not e.brushes
                                for e in entities[5:]))
            data=json.loads(output.with_suffix('.assets.json').read_text())
            rebound='textures/variant/aw_pad.png'
            self.assertNotIn(name,data['files'])
            self.assertEqual(data['files'][rebound]['engine_name'],rebound[:-4])
            self.assertEqual((runtime/rebound).read_bytes(),(art/name).read_bytes())
            self.assertEqual(len(files(runtime,data['files'])),len(LAYERS)+2)
            self.assertEqual(data['map_sha256'],digest(output))
            with self.assertRaisesRegex(ValueError,'fresh'):
                generate(source,output,runtime)
            self.assertEqual(source.read_bytes(),original)


if __name__=='__main__':
    unittest.main()
