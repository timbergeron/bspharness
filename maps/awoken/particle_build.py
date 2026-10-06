"""Add the four particle anchors to a verified BSP copy, preserving its bake."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bspharness.assets import stage
from bspharness.bsp import BSP, NAMES
from bspharness.pipeline import digest, resolve_tool, run_stage, verified_build, write_json
from bspharness.seams import check_bsp
from maps.awoken.particles import PADS


def build(reference, source, destination):
    reference,source,destination=(Path(p).resolve() for p in (reference,source,destination))
    parent=verified_build(reference)
    recipe=json.loads(source.with_suffix('.particles.json').read_text())
    original=reference.parent/(reference.stem+'.map')
    anchors='\n'.join('{\n"classname" "light_globe"\n"origin" "'+
                      ' '.join(map(str,p))+'"\n"light" "1"\n}\n' for p in PADS.values())
    if (digest(original)!=parent['source_sha256'] or
            recipe['source_sha256']!=digest(original) or
            recipe['map_sha256']!=digest(source) or
            source.read_bytes()!=original.read_bytes()+b'\n'+anchors.encode('ascii')):
        raise ValueError('Entity-only build requires the exact original MAP plus four declared anchors')
    prt=reference.with_suffix('.prt')
    if not prt.is_file() or not prt.stat().st_size:
        raise ValueError('Reference build is missing its nonempty portal file')
    if destination.exists():
        raise ValueError('Use a fresh build destination; original builds are preserved')
    asset_path=source.with_suffix('.assets.json')
    assets=json.loads(asset_path.read_text())
    contract_path=source.with_suffix('.materials.json')
    contract=json.loads(contract_path.read_text())
    if assets['map_sha256']!=digest(source) or contract['map_sha256']!=digest(source):
        raise ValueError('Stale source-bound runtime assets or material contract')
    destination.mkdir(parents=True)
    bsp=destination/(source.stem+'.bsp')
    try:
        for suffix in ('.bsp','.lit','.prt'):
            old=reference.with_suffix(suffix)
            if old.exists():
                shutil.copy2(old,bsp.with_suffix(suffix))
        format_flags={'bsp29':[], 'bsp2':['-bsp2'], '2psb':['-2psb']}[parent['format']]
        command=[resolve_tool(ROOT/'tools/ericw/modern','qbsp'),*format_flags,'-onlyents',source,bsp]
        compiled,output=run_stage(command,destination,destination/'qbsp-entities.log',180)
        if re.search(r'(?:texture[^\n]*(?:not found|missing)|missing[^\n]*texture|leak)',output,re.I):
            raise ValueError('Entity compiler reported a missing texture/leak; inspect qbsp-entities.log')
        before,after=BSP(reference),BSP(bsp)
        if before.format!=after.format or any(before.lump(n)!=after.lump(n) for n in NAMES[1:]):
            raise ValueError('Entity update changed a non-entity BSP lump')
        def extended(b):
            return {n:b.data[r['offset']:r['offset']+r['bytes']] for n,r in b.bspx.items()}
        if extended(before)!=extended(after):
            raise ValueError('Entity update changed the BSPX lighting/extension contract')
        if after.entities()!=before.entities()+[
                dict(classname='light_globe',origin=' '.join(map(str,p)),light='1') for p in PADS.values()]:
            raise ValueError('Entity update changed original gameplay entities')
        if reference.with_suffix('.lit').exists() and digest(reference.with_suffix('.lit'))!=digest(bsp.with_suffix('.lit')):
            raise ValueError('Entity update changed external colored lighting')
        validation=after.validate(before.format,before)
        if not validation['passed']:
            raise ValueError('Entity variant failed BSP validation: '+str(validation['errors']))
        seams=check_bsp(after,contract)
        if not seams['passed']:
            raise ValueError('Entity variant failed material seam validation')
        stage(asset_path.parent/assets['root'],assets['files'],destination/'runtime')
        for path in (source,asset_path,contract_path,source.with_suffix('.particles.json')):
            shutil.copy2(path,destination/path.name)
        write_json(destination/'validation.json',validation)
        write_json(destination/'seams.json',seams)
        write_json(destination/'inherited-build.json',parent)
        manifest={**parent,'time_utc':datetime.now(timezone.utc).isoformat(),
                  'source':str(source),'source_sha256':digest(source),
                  'stages':{'qbsp_entities':compiled},'runtime_assets':assets['files'],
                  'assets_manifest_sha256':digest(asset_path),'metrics':after.metrics(),
                  'run_directory':str(destination),
                  'entity_update':dict(reference_bsp=str(reference),reference_sha256=digest(reference),
                      scope='Four visual anchors only; all original entities and non-entity/BSPX lumps unchanged',
                      inherited_profile=parent['profile']),
                  'artifacts':{p.name:digest(p) for p in (bsp,bsp.with_suffix('.lit')) if p.exists()},
                  'evidence':{p.name:digest(p) for p in (destination/'seams.json',
                      destination/contract_path.name,destination/'inherited-build.json',
                      destination/source.with_suffix('.particles.json').name)},'passed':True}
        write_json(destination/'build.json',manifest)
        verified_build(bsp)
    except Exception as exc:
        write_json(destination/'failed-build.json',dict(passed=False,error=str(exc)))
        raise
    print(bsp)
    return bsp


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=ROOT/'out/awoken/final/awoken.bsp')
    parser.add_argument('--source',type=Path,default=ROOT/'src/awoken_vortex.map')
    parser.add_argument('--output',type=Path,default=ROOT/'out/awoken-vortex-final')
    args=parser.parse_args()
    build(args.reference,args.source,args.output)
