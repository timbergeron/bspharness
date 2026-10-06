"""Capture a short, hash-checked in-engine vortex loop and an offline player."""

import argparse
import base64
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bspharness.pipeline import digest, write_json
from bspharness import qa


def preview(bsp, engine, basedir, gamedir, output):
    output=Path(output).resolve()
    if output.exists():
        raise ValueError('Use a fresh preview output directory')
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        raise ValueError('FFmpeg is required to encode the engine captures')
    cameras=[dict(name=f'vortex-frame-{i:03d}',origin=(768,920,-664),angles=(46,270,0),
                  settle_frames=72 if i==0 else 6) for i in range(24)]
    # Use the uploaded reference's 4:3 resolution and keep the whole pad visible.
    original_render=qa.RENDER
    qa.RENDER={**original_render,'width':1448,'height':1086,'fov':70}
    try:
        qa_path,report=qa.run(bsp,cameras,basedir,engine,gamedir,timeout=480)
    finally:
        qa.RENDER=original_render
    if not report['passed']:
        raise ValueError('Engine preview failed QA: '+str(report['errors']))
    output.mkdir(parents=True)
    frames=output/'frames';frames.mkdir()
    for i,shot in enumerate(report['screenshots']):
        if digest(shot['file'])!=shot['sha256']:
            raise ValueError('An engine capture changed before encoding')
        shutil.copy2(shot['file'],frames/f'{i:03d}.png')
    video=output/'awoken-vortex.mp4'
    command=[str(Path(ffmpeg).resolve()),'-v','error','-framerate','12',
             '-i',str(frames/'%03d.png'),'-c:v','libx264','-crf','20',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    subprocess.run(command,check=True)
    payload=base64.b64encode(video.read_bytes()).decode('ascii')
    page=output/'index.html'
    page.write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Awoken jump-pad vortex</title><style>'
        'body{margin:32px auto;max-width:1100px;padding:0 20px;background:#10191d;'
        'color:#e4f3f7;font:17px system-ui}video{width:100%;border-radius:8px}'
        'h1{font-size:25px}p{line-height:1.5;color:#afc9d2}</style>'
        '<h1>Awoken jump-pad vortex</h1><p>Original FTE particles captured in QSS-M: '
        'electric-blue filaments, white star-like hot spots, '
        'rising arcs and sparse lightning snaps, tuned against goal.png. '
        '512-pixel particle sprites; 1448 × 1086 engine capture.</p>'
        '<video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+
        payload+'"></video><p>The pad, original collision, full VIS and lighting bake '
        'are preserved. The floor and center remain visible through the vapor.</p></html>',
        encoding='utf-8')
    write_json(output/'preview.json',dict(qa=str(qa_path),
               qa_sha256=digest(qa_path),video_sha256=digest(video),
               html_sha256=digest(page),fps=12,frames=24,seconds=2,
               width=1448,height=1086,fov=70,
               camera=cameras[0],
               command=command,generator_sha256=digest(__file__),
               runtime_assets=report['runtime_assets'],artifacts=report['artifacts']))
    print(page)
    return page


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bsp',type=Path)
    parser.add_argument('--engine',type=Path,required=True)
    parser.add_argument('--basedir',type=Path,required=True)
    parser.add_argument('--gamedir',default='awoken-vortex-motion')
    parser.add_argument('--output',type=Path,default=ROOT/'out/awoken-vortex-motion')
    args=parser.parse_args()
    preview(args.bsp,args.engine,args.basedir,args.gamedir,args.output)
