"""Export a standalone before/after slider with the inspected video frames."""

import argparse
import base64
from html import escape
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bspharness.pipeline import digest
from bspharness.review import load_shots


def export(before, after, output, frames, before_label="Geometry pass", after_label="Generated textures"):
    _,old_report,old=load_shots(before)
    _,new_report,new=load_shots(after)
    if not old_report["passed"] or not new_report["passed"] or old.keys()!=new.keys():
        raise ValueError("Use passing QA reports with identical named camera sets")
    if (old_report["render"]!=new_report["render"] or
            old_report["engine_sha256"]!=new_report["engine_sha256"]):
        raise ValueError("Use the same engine and render settings")
    def data(path):
        return "data:image/png;base64,"+base64.b64encode(Path(path).read_bytes()).decode("ascii")
    sections=[]
    for name in old:
        if old[name]["view"]!=new[name]["view"]:
            raise ValueError("Camera coordinates changed: "+name)
        title=escape(name.replace("-"," ").title())
        sections.append(f'<section><h2>{title}</h2><figure><div class="comparison">'
                        f'<img src="{data(old[name]["source"])}" alt="{title}, {escape(before_label)}">'
                        f'<img class="after" src="{data(new[name]["source"])}" alt="{title}, {escape(after_label)}">'
                        f'<span class="marker"></span><b class="left">{escape(after_label)}</b><b class="right">{escape(before_label)}</b></div>'
                        f'<label>Reveal {escape(after_label)} <input aria-label="Reveal {escape(after_label)} for {title}" type="range" min="0" max="100" value="50" '
                        'oninput="this.closest(\'figure\').querySelector(\'.comparison\').style.setProperty(\'--reveal\',this.value+\'%\')"></label>'
                        '</figure></section>')
    reference_data=json.loads((ROOT/"maps/awoken/reference.json").read_text())
    reference=reference_data["video_reference"]
    cards=[]
    selected=[(f,Path(frames)/f["file"]) for f in reference["frames"]]
    selected.extend((f,Path(frames).parent/f["file"]) for f in reference.get("geometry_frames",[])
                    if f["seconds"] in (45,65,115,605))
    for frame,path in sorted(selected,key=lambda pair:pair[0]["seconds"]):
        if digest(path)!=frame["sha256"]:
            raise ValueError("Modified reference frame: "+str(path))
        second=frame["seconds"];stamp=f"{second//60}:{second%60:02d}"
        cards.append(f'<figure><img src="{data(path)}" alt="Awoken video at {stamp}"><figcaption>{stamp}</figcaption></figure>')
    for clip in reference_data.get("additional_video_references",[]):
        for frame in clip["frames"]:
            if frame["seconds"] not in (5,30,55,60,70,85):continue
            path=Path(frames).parent/frame["file"]
            if digest(path)!=frame["sha256"]:
                raise ValueError("Modified additional reference frame: "+str(path))
            second=frame["seconds"];stamp=f"{second//60}:{second%60:02d}"
            cards.append(f'<figure><img src="{data(path)}" alt="Clutch reference at {stamp}">'
                         f'<figcaption>Clutch reference · {stamp}</figcaption></figure>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Awoken texture review</title>
<style>body{background:#171d20;color:#e6eae7;font:16px system-ui;margin:24px auto;max-width:1200px;padding:0 16px}
h1{margin-bottom:8px}p{line-height:1.6;color:#bdcbc4}section{margin:36px 0}figure{margin:0}
.comparison{position:relative;--reveal:50%;overflow:hidden;line-height:0;border-radius:8px}
img{display:block;width:100%;height:auto}.after{position:absolute;inset:0;clip-path:inset(0 calc(100% - var(--reveal)) 0 0)}
.marker{position:absolute;top:0;bottom:0;left:var(--reveal);width:2px;background:white}
.comparison b{position:absolute;top:12px;padding:8px;background:#111b;line-height:1;border-radius:4px}.left{left:12px}.right{right:12px}
label{display:flex;align-items:center;gap:12px;padding-top:12px}input{flex:1;accent-color:#8dc9b0}
.references{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}figcaption{padding:8px;color:#bdcbc4}
</style><h1>Awoken: high-resolution textures</h1>
<p>Drag each slider to compare the same view before and after importing the supplied texture set.
Full-color high-resolution PNGs replace the embedded palette textures. Carved bands, hanging ivy, stone variants,
waterfall and projected cloudy sky retain the existing geometry. Original masters stay untouched; runtime PNGs
upsample to powers of two to avoid QSS-M mipmap row skew. Both captures use the same engine,
camera and render settings. Match balance still needs playtesting.</p>
'''+''.join(sections)+'<h2>Inspected video frames</h2><div class="references">'+''.join(cards)+'</div></html>'
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding="utf-8")
    print(output.resolve())


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before",type=Path)
    parser.add_argument("after",type=Path)
    parser.add_argument("--output",type=Path,default=ROOT/"dist/awoken-review.html")
    parser.add_argument("--frames",type=Path,default=ROOT/"out/references/awoken/video")
    parser.add_argument("--before-label",default="Geometry pass")
    parser.add_argument("--after-label",default="Generated textures")
    export(**vars(parser.parse_args()))
