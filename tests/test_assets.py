import json
from pathlib import Path
import struct
import tempfile
import unittest

from bspharness.assets import audit_images, files, stage
from bspharness.pipeline import digest


class RuntimeAssetsTests(unittest.TestCase):
    def fixture(self, root):
        path=root/'textures/arena/wall.png';path.parent.mkdir(parents=True)
        # Only the header is needed for this dependency-free manifest check.
        path.write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',1254,1254)+b'asset')
        return {'textures/arena/wall.png':{'sha256':digest(path),'width':1254,'height':1254,
                                         'engine_name':'textures/arena/wall'}}

    def test_staging_keeps_native_bytes_and_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);records=self.fixture(root/'source')
            stage(root/'source',records,root/'game')
            original=(root/'source/textures/arena/wall.png').read_bytes()
            (root/'source/textures/arena/wall.png').write_bytes(b'replaced during QA')
            self.assertEqual((root/'game/textures/arena/wall.png').read_bytes(),original)
            self.assertEqual(len(files(root/'game',records)),1)
            with self.assertRaisesRegex(ValueError,'Modified or missing'):
                files(root/'source',records)

    def test_path_traversal_absolute_and_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);records=self.fixture(root/'source');record=next(iter(records.values()))
            for name in ('../textures/wall.png','/textures/wall.png','textures/../wall.png',
                         'textures\\wall.png','textures//wall.png','maps/wall.png'):
                with self.subTest(name=name),self.assertRaises(ValueError):
                    files(root/'source',{name:record})
            (root/'source/textures/arena/wall.png').unlink()
            (root/'outside.png').write_bytes(b'outside')
            (root/'source/textures/arena/wall.png').symlink_to(root/'outside.png')
            with self.assertRaisesRegex(ValueError,'escapes'):
                files(root/'source',records)

    def test_dimension_and_content_changes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);records=self.fixture(root);name=next(iter(records))
            bad={name:{**records[name],'width':1024}}
            with self.assertRaisesRegex(ValueError,'dimensions'):
                files(root,bad)
            (root/name).write_bytes(b'downsampled')
            with self.assertRaisesRegex(ValueError,'Modified or missing'):
                files(root,records)

    def test_engine_fallback_and_downsampling_do_not_count_as_native(self):
        record={'textures/arena/wall.png':{'width':1254,'height':1254,'engine_name':'textures/arena/wall'}}
        def log(line):return 'BSPHARNESS_IMAGES_BEGIN\n'+line+'\nBSPHARNESS_IMAGES_END\n'
        self.assertEqual(audit_images(log(' 1254 x1254 textures/arena/wall'),record)[0],[])
        for line in (' 1024 x1024 textures/arena/wall',' 128 x 128 maps/arena.bsp:wall',''):
            self.assertTrue(audit_images(log(line),record)[0])

    def test_particle_config_and_sprite_are_staged_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);records=self.fixture(root/'source')
            sprite='particles/arena/haze.png'
            original=root/'source/textures/arena/wall.png'
            target=root/'source'/sprite;target.parent.mkdir(parents=True)
            target.write_bytes(original.read_bytes())
            records[sprite]={**next(iter(records.values())), 'engine_name':'particles/arena/haze'}
            name='particles/map_arena.cfg'
            path=root/'source'/name;path.write_text('r_part haze\n{\n type normal\n}\n')
            records[name]={'sha256':digest(path),'kind':'fte_particles'}
            stage(root/'source',records,root/'game')
            self.assertEqual((root/'game'/name).read_bytes(),path.read_bytes())
            self.assertEqual(len(files(root/'game',records)),3)
            self.assertEqual(audit_images('',{name:records[name]})[0],[])
            (root/'game'/name).write_text('modified script')
            with self.assertRaisesRegex(ValueError,'Modified or missing'):
                files(root/'game',records)

    def test_particle_allowlist_rejects_general_configs_and_bad_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            record={'sha256':'0'*64,'kind':'fte_particles'}
            for name in ('autoexec.cfg','configs/connect.cfg','particles/effect.dat',
                         'particles/../autoexec.cfg'):
                with self.subTest(name=name),self.assertRaises(ValueError):
                    files(root,{name:record})
            name='particles/map_arena.cfg';path=root/name;path.parent.mkdir()
            path.write_text('// effect\n');record['sha256']=digest(path)
            for bad in ({'sha256':record['sha256']},
                        {**record,'engine_name':'misreported-as-an-image'}):
                with self.assertRaisesRegex(ValueError,'Invalid runtime asset'):
                    files(root,{name:bad})


if __name__=='__main__':unittest.main()
