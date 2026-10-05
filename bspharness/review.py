"""Portable, hash-checked camera comparisons for human visual review."""

from html import escape
import json
from pathlib import Path
import shutil
import struct

from .pipeline import digest, write_json


def load_shots(path):
    path = Path(path).resolve()
    report = json.loads(path.read_text())
    shots = {}
    for shot in report["screenshots"]:
        name = shot["camera"]
        if not isinstance(name,str) or not name.strip() or name in shots:
            raise ValueError("Screenshot camera names must be nonempty and unique")
        source = Path(shot["file"])
        if not source.is_absolute():
            source = path.parent/source
        if digest(source)!=shot["sha256"]:
            raise ValueError(f"Screenshot hash mismatch: {name}")
        data = source.read_bytes()[:24]
        if len(data)!=24 or data[:8]!=b"\x89PNG\r\n\x1a\n" or data[12:16]!=b"IHDR":
            raise ValueError(f"Expected a PNG screenshot: {name}")
        size = struct.unpack(">II",data[16:24])
        if not all(size):
            raise ValueError(f"Invalid screenshot dimensions: {name}")
        shots[name] = {**shot,"source":source,"size":size}
    if not shots:
        raise ValueError("Comparison needs camera screenshots")
    return path,report,shots


def compare(before, after, output):
    before_path,before_report,old = load_shots(before)
    after_path,after_report,new = load_shots(after)
    if old.keys()!=new.keys():
        raise ValueError("Comparison requires matching named camera sets")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Use a fresh comparison output directory")
    rows,entries = [],[]
    # Validate all inputs before creating the portable comparison folder.
    for index,name in enumerate(old):
        a,b = old[name],new[name]
        warnings = []
        if a["size"]!=b["size"]:
            warnings.append("Image dimensions differ")
        if a.get("view") is None or b.get("view") is None:
            warnings.append("Camera coordinates were not recorded in an older report")
        elif a["view"]!=b["view"]:
            warnings.append("Camera coordinates differ")
        if before_report.get("render") is None or after_report.get("render") is None:
            warnings.append("Render settings were not recorded in an older report")
        elif before_report["render"]!=after_report["render"]:
            warnings.append("Render settings differ")
        if before_report.get("engine_sha256")!=after_report.get("engine_sha256"):
            warnings.append("Engine binaries differ")
        images = [f"{index:02d}-{label}.png" for label in ("before","after")]
        entries.append({"camera":name,"warnings":warnings,"before":{
            k:v for k,v in a.items() if k!="source"},"after":{
            k:v for k,v in b.items() if k!="source"},"images":images})
        title = escape(name)
        notice = escape("; ".join(warnings))
        rows.append(f'<section><h2>{title}</h2><p>{notice}</p><div class="pair">'+
                    ''.join(f'<figure><figcaption>{label}</figcaption><a href="{file}">'
                            f'<img src="{file}" alt="{title} {label}" loading="lazy"></a></figure>'
                            for label,file in zip(("Before","After"),images))+"</div></section>")
    metadata = {"schema":1,"visual_review":"pending; compare every camera",
                "before":{"report":str(before_path),"report_sha256":digest(before_path),
                          "passed":before_report["passed"],"artifacts":before_report.get("artifacts",{})},
                "after":{"report":str(after_path),"report_sha256":digest(after_path),
                         "passed":after_report["passed"],"artifacts":after_report.get("artifacts",{})},
                "cameras":entries}
    output.mkdir(parents=True)
    for entry in entries:
        for shot,file in zip((old[entry["camera"]],new[entry["camera"]]),entry["images"]):
            shutil.copy2(shot["source"],output/file)
    write_json(output/"comparison.json",metadata)
    html = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Quake camera comparison</title><style>'
            'body{background:#171717;color:#eee;font:16px system-ui;margin:24px}'
            '.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}'
            'figure{margin:0}img{width:100%;height:auto}figcaption{margin-bottom:8px}'
            'section{margin-bottom:40px}p{color:#ffc978}'
            '@media(max-width:700px){.pair{grid-template-columns:1fr}}</style>'
            '<h1>Quake camera comparison</h1><p>Human visual review required. '
            f'Before QA: {before_report["passed"]}; After QA: {after_report["passed"]}.</p>'+
            ''.join(rows)+'</html>')
    (output/"index.html").write_text(html,encoding="utf-8")
    return output/"index.html"
