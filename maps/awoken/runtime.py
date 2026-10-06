"""Preserve source detail while avoiding QSS-M's odd-width mipmap skew."""

from pathlib import Path
import shutil
import subprocess


def compatible(sources, records):
    from bspharness.pipeline import digest
    original=Path(sources)/"runtime"
    root=Path(sources)/"runtime-compatible"
    result={}
    for name,record in records.items():
        source=original/name;target=root/name
        target.parent.mkdir(parents=True,exist_ok=True)
        width,height=record["width"],record["height"]
        w,h=1<<(width-1).bit_length(),1<<(height-1).bit_length()
        if (w,h)==(width,height):
            shutil.copy2(source,target)
        else:
            # Both axes only increase: no original image detail is discarded.
            # Normalized BSP UVs preserve the artwork's physical aspect ratio.
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                            "-i",str(source),"-vf",f"scale={w}:{h}:flags=lanczos",
                            "-frames:v","1",str(target)],check=True)
        result[name]={**record,"sha256":digest(target),"width":w,"height":h,
                      "runtime_generator_sha256":digest(__file__),
                      "native_width":width,"native_height":height,
                      "native_sha256":record["sha256"],
                      "processing":"byte copy" if (w,h)==(width,height) else "Lanczos upsample for QSS-M mipmap compatibility"}
    return root,result
