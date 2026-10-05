import argparse
import json
from pathlib import Path
import sys

from . import bsp, pak, pipeline, qa, seams, wad


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bspharness",description="Generate, compile, and verify Quake 1 BSP maps")
    commands = parser.add_subparsers(dest="command",required=True)
    utility = commands.add_parser("blockout-wad",help="Generate original development/tool textures")
    utility.add_argument("output",type=Path)
    stock = commands.add_parser("id-wad",help="Extract textures from locally owned pak0/pak1 BSPs")
    stock.add_argument("paks",type=Path,nargs="+")
    stock.add_argument("--output",type=Path,default=Path("assets/wads/id1.wad"))
    stock.add_argument("--palette",type=Path)
    textures = commands.add_parser("wad-info",help="Validate and list a WAD2")
    textures.add_argument("path",type=Path)
    preview = commands.add_parser("wad-preview",help="Generate PNGs and a texture contact sheet")
    preview.add_argument("path",type=Path)
    preview.add_argument("--palette",type=Path,required=True)
    preview.add_argument("--output",type=Path,required=True)
    compiler = commands.add_parser("build",help="Run qbsp, vis, light, and BSP validation")
    compiler.add_argument("source",type=Path)
    compiler.add_argument("--out",type=Path,default=Path("out"))
    compiler.add_argument("--profile",choices=json.loads((pipeline.ROOT/"configs/profiles.json").read_text()),default="final")
    compiler.add_argument("--format",choices=("bsp29","bsp2","2psb"),default="bsp29")
    compiler.add_argument("--qbsp-dir",type=Path)
    compiler.add_argument("--lighting-dir",type=Path)
    compiler.add_argument("--reference",type=Path,help="Compare clipnodes against an existing BSP")
    compiler.add_argument("--threads",type=int,default=4)
    compiler.add_argument("--timeout",type=int,default=1800)
    compiler.add_argument("--check-seams",action="store_true",help="Require UV seam checks even for maps without a material contract")
    inspect = commands.add_parser("inspect",help="Validate BSP format, textures, lumps, and entity bounds")
    inspect.add_argument("path",type=Path)
    inspect.add_argument("--format",choices=("bsp29","bsp2","2psb"))
    inspect.add_argument("--reference",type=Path)
    seam_check = commands.add_parser("seams",help="Check compiled shared-edge UV continuity and material boundaries")
    seam_check.add_argument("path",type=Path)
    seam_check.add_argument("--materials",type=Path,help="Alignment families, wall runs, and transition rules")
    seam_check.add_argument("--output",type=Path)
    extract = commands.add_parser("extract-wad",help="Recover embedded textures from a BSP")
    extract.add_argument("path",type=Path)
    extract.add_argument("output",type=Path)
    cameras = commands.add_parser("qa",help="Run isolated QSS-M cameras and a runtime spawn/item audit")
    cameras.add_argument("bsp",type=Path)
    cameras.add_argument("--cameras",type=Path,required=True)
    cameras.add_argument("--basedir",type=Path,required=True)
    cameras.add_argument("--engine",type=Path,required=True)
    cameras.add_argument("--gamedir",default="bspharness_qa")
    cameras.add_argument("--timeout",type=int,default=90)
    release = commands.add_parser("package",help="Package a verified BSP, lighting, source, and credits")
    release.add_argument("bsp",type=Path)
    release.add_argument("--output",type=Path,required=True)
    release.add_argument("--credits",type=Path,required=True)
    release.add_argument("--qa-report",type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command=="blockout-wad":
            print(wad.make_blockout(args.output))
        elif args.command=="id-wad":
            print(json.dumps(pak.extract_id_wad(args.paks,args.output,args.palette),indent=2))
        elif args.command=="wad-info":
            print(json.dumps([{k:v for k,v in t.items() if k!="pixels"} for t in wad.read_wad(args.path).values()],indent=2))
        elif args.command=="wad-preview":
            print(wad.preview(args.path,args.palette,args.output))
        elif args.command=="build":
            print(pipeline.build(args.source,args.out,args.profile,args.format,args.qbsp_dir,args.lighting_dir,
                                 args.reference,args.timeout,args.threads,args.check_seams))
        elif args.command=="inspect":
            report = bsp.BSP(args.path).validate(args.format,bsp.BSP(args.reference) if args.reference else None)
            print(json.dumps(report,indent=2))
            return 0 if report["passed"] else 1
        elif args.command=="seams":
            contract_path = args.materials or args.path.with_suffix(".materials.json")
            if args.materials and not contract_path.is_file():
                raise ValueError(f"Material contract does not exist: {contract_path}")
            contract = json.loads(contract_path.read_text()) if contract_path.exists() else None
            report = seams.check_bsp(bsp.BSP(args.path),contract)
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                pipeline.write_json(args.output,report)
                print(args.output)
            else:
                print(json.dumps(report,indent=2))
            return 0 if report["passed"] else 1
        elif args.command=="extract-wad":
            print(bsp.BSP(args.path).extract_wad(args.output))
        elif args.command=="qa":
            path,report = qa.run(args.bsp,json.loads(args.cameras.read_text()),args.basedir,args.engine,args.gamedir,args.timeout)
            print(path)
            if not report["passed"]:
                print("\n".join(report["errors"]),file=sys.stderr)
                return 1
        elif args.command=="package":
            print(pipeline.package(args.bsp,args.output,args.credits,args.qa_report))
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        print(f"bspharness: {exc}",file=sys.stderr)
        return 1
    return 0
