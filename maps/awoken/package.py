"""Package Awoken with matching movement, actual DM, and reviewed camera evidence."""

import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bspharness.pipeline import digest, package, verified_build


def release(bsp, movement, deathmatch, cameras, review, output):
    bsp=Path(bsp).resolve()
    manifest=verified_build(bsp)
    if manifest["profile"]!="final":
        raise ValueError("Awoken release packaging requires the full-VIS final profile")
    if digest(ROOT/"src/awoken.map")!=manifest["source_sha256"]:
        raise ValueError("Current Awoken source must match the packaged build")
    conversion=json.loads((ROOT/"src/awoken.conversion.json").read_text())
    if conversion["generator_sha256"]!=digest(ROOT/"maps/awoken/build.py"):
        raise ValueError("Regenerate Awoken after changing its conversion recipe")
    art=None
    if conversion.get("style")=="video":
        art=json.loads((ROOT/"maps/awoken/art.json").read_text())
        for source in art["sources"].values():
            if digest(ROOT/"assets/awoken"/source["file"])!=source["sha256"]:
                raise ValueError("Modified original texture source")
        if (digest(ROOT/"assets/wads/awoken.wad")!=conversion["art_wad_sha256"] or
                digest(ROOT/"maps/awoken/polish.py")!=conversion["polish_sha256"]):
            raise ValueError("Modified polish geometry or texture WAD; regenerate and rebuild")
        texture_manifest=json.loads((ROOT/"assets/wads/awoken.json").read_text())
        if (texture_manifest["generator_sha256"]!=digest(ROOT/"maps/awoken/materials.py") or
                texture_manifest["wad_sha256"]!=conversion["art_wad_sha256"]):
            raise ValueError("Texture generator evidence is stale")
    paths={"movement":Path(movement),"deathmatch":Path(deathmatch),"cameras":Path(cameras)}
    reports={k:json.loads(p.read_text()) for k,p in paths.items()}
    for name,report in reports.items():
        if (not report.get("passed") or report.get("bsp_sha256")!=digest(bsp)
                or report.get("artifacts")!=manifest["artifacts"]):
            raise ValueError(f"{name} QA must pass and match the BSP and LIT")
    expected={r["name"]:r for r in json.loads((ROOT/"src/awoken.routes.json").read_text())}
    actual={r["name"]:r for r in reports["movement"]["routes"]}
    if set(actual)!=set(expected) or any(not actual[n]["passed"] or actual[n]["specification"]!=s
                                        for n,s in expected.items()):
        raise ValueError("Movement report must cover the complete current Awoken route specification")
    if reports["deathmatch"]["physics"]["mode"]!="stock deathmatch":
        raise ValueError("Supply an actual deathmatch spawn/item audit")
    shots=reports["cameras"]["screenshots"]
    views={c["name"]:c for c in json.loads((ROOT/"src/awoken.cameras.json").read_text())}
    names=set(views)
    if (len(shots)!=len(names) or {s["camera"] for s in shots}!=names
            or any(s["view"]!=views[s["camera"]] for s in shots)):
        raise ValueError("Camera pass must contain all current Awoken views")
    reviewed=json.loads(Path(review).read_text())
    if reviewed.get("artifacts")!=manifest["artifacts"] or any(
            not reviewed.get("cameras",{}).get(n,{}).get("accepted") for n in names):
        raise ValueError("Review must accept every camera for these exact artifacts")
    for shot in shots:
        if (digest(shot["file"])!=shot["sha256"] or
                reviewed["cameras"][shot["camera"]].get("sha256")!=shot["sha256"]):
            raise ValueError("A reviewed screenshot was modified")
    archive=package(bsp,output,ROOT/"maps/awoken/credits.txt",paths["cameras"])
    with zipfile.ZipFile(archive,"a",compression=zipfile.ZIP_DEFLATED) as z:
        z.write(paths["movement"],"qa/movement.json")
        z.write(paths["deathmatch"],"qa/deathmatch.json")
        z.write(review,"qa/visual-review.json")
        z.write(ROOT/"maps/awoken/reference.json","reference.json")
        for suffix in ("routes.json","cameras.json","conversion.json"):
            z.write(ROOT/f"src/awoken.{suffix}",f"source/awoken.{suffix}")
        for shot in shots:z.write(shot["file"],f"screenshots/{shot['camera']}.png")
        for filename in ("build.py","materials.py","polish.py","review.py","package.py",
                         "art.json","README.md","POLISH.md"):
            z.write(ROOT/"maps/awoken"/filename,"source/recipe/"+filename)
        if art:
            for source in art["sources"].values():
                z.write(ROOT/"assets/awoken"/source["file"],"source/art/"+source["file"])
            z.write(ROOT/"assets/wads/awoken.wad","source/wads/awoken.wad")
            z.write(ROOT/"assets/wads/awoken.json","source/wads/awoken.json")
    # Also provide directly usable files next to the archive.
    folder=archive.with_suffix("");folder.mkdir(parents=True,exist_ok=True)
    for suffix in (".bsp",".lit"):shutil.copy2(bsp.with_suffix(suffix),folder/("awoken"+suffix))
    shutil.copy2(ROOT/"maps/awoken/credits.txt",folder/"README.txt")
    print(archive)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bsp",type=Path,default=ROOT/"out/awoken/final/awoken.bsp")
    for name in ("movement","deathmatch","cameras","review"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--output",type=Path,default=ROOT/"dist/awoken.zip")
    args=parser.parse_args()
    release(**vars(args))
