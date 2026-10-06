"""Import user PNGs with high-resolution runtime copies and BSP fallbacks.

Native masters remain unchanged. Indexed fallbacks are reduced; runtime.py
only increases surface dimensions for QSS-M mipmap compatibility. Sky
projection and waterfall scrolling are derived assets. FFmpeg handles
raster I/O; the harness core uses only the standard library.
"""
import argparse
import json
from math import asin, atan2, floor, pi, sqrt
from pathlib import Path
import os
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bspharness.pipeline import digest, write_json
from bspharness.wad import miptex, write_wad

# Native source name and embedded dimensions. Preserve rectangular aspect.
MATERIALS = {
    'aw_stone':('aw_wall_base',128,128),'aw_wmoss':('aw_wall_moss',128,128),
    'aw_wwet':('aw_wall_wet',128,128),'aw_trim':('aw_stone_plain',128,128),
    'aw_worn':('aw_stone_worn',128,128),'aw_pave':('aw_floor_base',128,128),
    'aw_fmoss':('aw_floor_moss',128,128),'aw_fwet':('aw_floor_wet',128,128),
    'aw_panel':('aw_relief_a',128,256),'aw_plaque':('aw_relief_b',128,128),
    'aw_band':('aw_trim_carved',192,64),'aw_pad':('aw_pad',128,128),
    'aw_light':('aw_light',256,64),'aw_metal':('aw_metal',128,128),
    '{aw_vine':('aw_vine_dense',128,128),'{aw_vines':('aw_vine_sparse',128,128),
    '{aw_roots':('aw_roots',128,256),'{aw_grate':('aw_grate',128,128),
    'aw_cliff':('aw_cliff',128,128),'aw_earth':('aw_earth',128,128),
    '{aw_grass':('aw_grass',128,128),'aw_bark':('aw_bark',128,256),
    '{aw_canopy':('aw_canopy',128,128),'*aw_water':('aw_water',64,64),
}


def decode(path,width,height,filter=None):
    args=['ffmpeg','-hide_banner','-loglevel','error','-i',str(path)]
    if filter:args+=['-vf',filter]
    args+=['-frames:v','1','-pix_fmt','rgba','-f','rawvideo','pipe:1']
    pixels=subprocess.run(args,check=True,stdout=subprocess.PIPE).stdout
    if len(pixels)!=width*height*4:raise ValueError('Unexpected decoded texture dimensions')
    return pixels


def encode(path,width,height,pixels):
    path.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo',
                    '-pixel_format','rgba','-video_size',f'{width}x{height}','-i','pipe:0',
                    '-frames:v','1',str(path)],input=pixels,check=True)


def indexed(rgba,palette,masked=False,cache=None):
    if len(palette)!=768 or len(rgba)%4:raise ValueError('Expected Quake palette and RGBA pixels')
    colors=[tuple(palette[i:i+3]) for i in range(0,224*3,3)]
    cache={} if cache is None else cache
    output=bytearray()
    for offset in range(0,len(rgba),4):
        r,g,b,a=rgba[offset:offset+4]
        if masked and a<96:
            output.append(255);continue
        # Only the portable fallback uses the memoized 4-bit RGB palette lookup.
        key=tuple(min(255,(c//16)*16+8) for c in (r,g,b))
        if key not in cache:
            cache[key]=min(range(224),key=lambda i:sum((x-y)**2 for x,y in zip(key,colors[i])))
        output.append(cache[key])
    return bytes(output)


def record(path,texture=None,source=None):
    width,height=struct.unpack('>II',path.read_bytes()[16:24])
    return {'sha256':digest(path),'width':width,'height':height,'texture':texture,'source':source}


def skybox(source,runtime):
    """Project 2:1 equirectangular art onto Quake gl_sky.c's exact cube bases.

    Rows run downward. Longitude wraps; poles clamp. Each 90-degree face uses
    512px, covering the source's approximately 443 samples per 90 degrees.
    """
    w,h=struct.unpack('>II',source.read_bytes()[16:24]);pixels=decode(source,w,h)
    bases={'rt':(3,-1,2),'lf':(-3,1,2),'bk':(1,3,2),
           'ft':(-1,-3,2),'up':(-2,-1,3),'dn':(2,-1,-3)}
    paths=[];size=512
    for suffix,basis in bases.items():
        image=bytearray()
        for row in range(size):
            t=1-2*(row+0.5)/size
            for col in range(size):
                st=(2*(col+0.5)/size-1,t,1)
                x,y,z=(st[abs(k)-1]*(1 if k>0 else -1) for k in basis)
                u=(atan2(y,x)/(2*pi)+0.5)*w-0.5
                v=max(0,min(h-1,(0.5-asin(z/sqrt(x*x+y*y+z*z))/pi)*h-0.5))
                a,b=floor(u),floor(v);fx,fy=u-a,v-b
                offsets=[(b*w+a%w)*4,(b*w+(a+1)%w)*4,
                         (min(h-1,b+1)*w+a%w)*4,(min(h-1,b+1)*w+(a+1)%w)*4]
                for channel in range(4):
                    p,q,r,s=(pixels[i+channel] for i in offsets)
                    image.append(round((p*(1-fx)+q*fx)*(1-fy)+(r*(1-fx)+s*fx)*fy))
        path=runtime/f'gfx/env/awoken{suffix}.png';encode(path,size,size,bytes(image));paths.append(path)
    return paths


def make_materials(output=ROOT/'assets/wads/awoken.wad',palette=ROOT/'assets/palette.lmp',
                   sources=ROOT/'assets/awoken'):
    metadata=json.loads((ROOT/'maps/awoken/art.json').read_text());sources=Path(sources)
    paths={n:sources/d['file'] for n,d in metadata['sources'].items()}
    for n,path in paths.items():
        if digest(path)!=metadata['sources'][n]['sha256']:raise ValueError(f'Original texture source changed: {path}')
    palette=Path(palette);colors=palette.read_bytes()
    runtime=sources/'runtime';runtime.mkdir(parents=True,exist_ok=True)
    textures,records,cache={},{},{}
    for name,(source,w,h) in MATERIALS.items():
        pixels=decode(paths[source],w,h,f'scale={w}:{h}:flags=area')
        textures[name]=miptex(name,w,h,indexed(pixels,colors,masked=name.startswith('{'),cache=cache))
        filename='#'+name[1:] if name.startswith('*') else name
        target=runtime/f'textures/awoken/{filename}.png';target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(paths[source],target)
        records[target.relative_to(runtime).as_posix()]=record(target,name,source)
    # Eight standard Quake animation frames: 5 Hz, lossless downward row wraps.
    fall=metadata['sources']['aw_fall'];w,h=fall['width'],fall['height']
    original=decode(paths['aw_fall'],w,h)
    fallback=decode(paths['aw_fall'],128,256,'scale=128:256:flags=area')
    for frame in range(8):
        name=f'+{frame}aw_fall';shift=round(frame*h/8)*w*4
        pixels=original[-shift:]+original[:-shift] if shift else original
        target=runtime/f'textures/awoken/{name}.png';encode(target,w,h,pixels)
        records[target.relative_to(runtime).as_posix()]=record(target,name,'aw_fall')
        shift=frame*32*128*4;low=fallback[-shift:]+fallback[:-shift] if shift else fallback
        textures[name]=miptex(name,128,256,indexed(low,colors,cache=cache))
    for path in skybox(paths['aw_sky'],runtime):
        records[path.relative_to(runtime).as_posix()]=record(path,None,'aw_sky')
    sky=indexed(decode(paths['aw_sky'],128,128,'scale=128:128:flags=area'),colors,cache=cache)
    classic=b''.join(bytes(128)+sky[y*128:(y+1)*128] for y in range(128))
    textures['sky_aw']=miptex('sky_aw',256,128,classic)
    output=write_wad(output,textures)
    from maps.awoken.runtime import compatible
    runtime_root,runtime_files=compatible(sources,records)
    write_json(output.with_suffix('.json'),{
        'schema':2,'wad_sha256':digest(output),'palette_sha256':digest(palette),
        'generator_sha256':digest(__file__),'source_sha256':{n:digest(p) for n,p in paths.items()},
        'textures':list(textures),'runtime_files':runtime_files,'native_runtime_files':records,
        'runtime_root':str(runtime_root),
        'transparency':'Native PNG alpha preserved; masked indexed fallbacks use 255. Opaque fallback colors stay below 224.',
        'resolution':'Native masters preserved. Runtime surfaces upscale to next power of two to avoid QSS-M odd-width mipmap skew; no axis is reduced. Sky uses six 512px projected faces.'})
    return output


def bind_runtime(map_path):
    """Bind only used replacements to the MAP, including all animation frames."""
    from bspharness.source import read
    used={f.texture for e in read(map_path) for b in e.brushes for f in b.faces}
    metadata=json.loads((ROOT/'assets/wads/awoken.json').read_text());records={}
    for path,r in metadata['runtime_files'].items():
        tex=r['texture']
        active=(tex in used or bool(tex and tex.startswith('+') and '+0aw_fall' in used)
                or path.startswith('gfx/env/'))
        if active:records[path]={**r,'engine_name':path[:-4]}
    write_json(Path(map_path).with_suffix('.assets.json'),{
        'schema':1,'map_sha256':digest(map_path),
        'root':os.path.relpath(metadata['runtime_root'],Path(map_path).resolve().parent),'files':records})
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'assets/wads/awoken.wad')
    parser.add_argument('--palette',type=Path,default=ROOT/'assets/palette.lmp')
    parser.add_argument('--sources',type=Path,default=ROOT/'assets/awoken')
    print(make_materials(**vars(parser.parse_args())))
