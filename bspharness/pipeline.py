"""Fail-closed compilation with per-stage logs and reproducible manifests."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

from .bsp import BSP
from .seams import check_bsp

ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")


def resolve_tool(directory, name):
    directory = Path(directory).resolve()
    candidates = sorted(p for p in directory.rglob(name+(".exe" if os.name=="nt" else "")) if p.is_file())
    if len(candidates) != 1:
        raise ValueError(f"Expected exactly one {name} in {directory}; run tools/bootstrap.py")
    return candidates[0]


def run_stage(command, directory, log, timeout):
    start = time.monotonic()
    environment = os.environ.copy()
    # The pinned Linux bundles ship Embree/TBB beside the executable.
    variable = "DYLD_LIBRARY_PATH" if platform.system()=="Darwin" else "LD_LIBRARY_PATH" if os.name!="nt" else "PATH"
    environment[variable] = str(command[0].parent)+os.pathsep+environment.get(variable,"")
    print(f"Running {command[0].name}…",flush=True)
    with Path(log).open("w",encoding="utf-8") as stream:
        stream.write("Command: "+json.dumps([str(x) for x in command])+"\n")
        stream.flush()
        try:
            result = subprocess.run([str(x) for x in command],cwd=directory,env=environment,
                                    stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"{command[0].name} timed out; see {log}") from exc
    output = Path(log).read_text(errors="replace")
    output = re.sub(r"\x1b\[[0-9;]*m","",output)
    if result.returncode:
        raise ValueError(f"{command[0].name} exited {result.returncode}; see {log}\n{output[-2500:]}")
    return {"command":[str(x) for x in command],"tool_sha256":digest(command[0]),
            "seconds":round(time.monotonic()-start,3),"log":Path(log).name},output


def build(source, output, profile="final", bsp_format="bsp29", qbsp_dir=None, lighting_dir=None,
          reference=None, timeout=1800, threads=4, check_seams=False, budgets=None):
    source = Path(source).resolve()
    if source.suffix != ".map" or not source.is_file():
        raise ValueError("Build needs an existing .map source")
    if not re.fullmatch(r"[A-Za-z0-9_-]+",source.stem):
        raise ValueError("Map basename must contain letters, digits, underscores, or hyphens")
    if threads < 1:
        raise ValueError("Thread count must be positive")
    budgets = budgets or {}
    if any(key not in ("faces","nodes","clipnodes","leaves","models","visibility_bytes",
                       "lighting_bytes","textures_bytes","bsp_bytes") or
           not isinstance(value,int) or value<1 for key,value in budgets.items()):
        raise ValueError("Build budgets need known metric names and positive integer limits")
    settings = json.loads((ROOT/"configs/profiles.json").read_text())[profile]
    qbsp = resolve_tool(qbsp_dir or ROOT/"tools/ericw/modern","qbsp")
    vis = resolve_tool(lighting_dir or ROOT/"tools/ericw/modern","vis")
    light = resolve_tool(lighting_dir or ROOT/"tools/ericw/modern","light")
    destination = Path(output).resolve()/source.stem/profile
    destination.mkdir(parents=True,exist_ok=True)
    # Invalidate approval of older BSPs before starting a new compile.
    manifest_path = destination/"build.json"
    if manifest_path.exists():
        manifest_path.unlink()
    work = Path(tempfile.mkdtemp(prefix="run-",dir=destination))
    bsp = work/(source.stem+".bsp")
    manifest = {"schema":1,"time_utc":datetime.now(timezone.utc).isoformat(),
                "source":str(source),"source_sha256":digest(source),"profile":profile,
                "format":bsp_format,"stages":{},"budgets":budgets,"passed":False}
    try:
        sidecar = source.with_suffix(".materials.json")
        contract = None
        if sidecar.exists():
            contract = json.loads(sidecar.read_text())
            if contract.get("schema")!=1 or contract.get("map_sha256")!=manifest["source_sha256"]:
                raise ValueError("Material contract is stale; regenerate the MAP and its .materials.json together")
            shutil.copy2(sidecar,work/sidecar.name)
        formats = {"bsp29":[],"bsp2":["-bsp2"],"2psb":["-2psb"]}
        command = [qbsp,*settings["qbsp"],*formats[bsp_format],source,bsp]
        stage,output_text = run_stage(command,work,work/"qbsp.log",timeout)
        manifest["stages"]["qbsp"] = stage
        if re.search(r"(?:texture[^\n]*(?:not found|missing)|missing[^\n]*texture)",output_text,re.I):
            raise ValueError(f"Missing texture; see {work/'qbsp.log'}")
        portal = bsp.with_suffix(".prt")
        if not bsp.exists() or not portal.exists() or portal.stat().st_size==0:
            raise ValueError("qbsp did not produce both BSP and portal data; refusing VIS")
        for name,tool in [("vis",vis),("light",light)]:
            stage,_ = run_stage([tool,"-threads",str(threads),*settings[name],bsp],work,work/(name+".log"),timeout)
            manifest["stages"][name] = stage
        report = BSP(bsp).validate(bsp_format,BSP(reference) if reference else None)
        manifest["metrics"] = report["metrics"] = BSP(bsp).metrics()
        for metric,limit in budgets.items():
            if manifest["metrics"][metric]>limit:
                report["errors"].append(f"Build budget exceeded: {metric}={manifest['metrics'][metric]} > {limit}")
        for name in settings.get("required_bspx",[]):
            if name not in report["bspx"]:
                report["errors"].append(f"Missing required BSPX lump: {name}")
        if "-bspxlit" in settings["light"] and "RGBLIGHTING" not in report["bspx"]:
            report["errors"].append("Missing embedded colored lighting")
        lit = bsp.with_suffix(".lit")
        if profile == "mono" and lit.exists():
            lit.unlink()
        if "-lit" in settings["light"]:
            if not lit.exists() or lit.read_bytes()[:8] != b"QLIT\x01\x00\x00\x00":
                report["errors"].append("Missing or invalid classic QLIT sidecar")
        report["passed"] = not report["errors"]
        if report["passed"] and (contract is not None or check_seams):
            seam_report = check_bsp(BSP(bsp),contract)
            write_json(work/"seams.json",seam_report)
            if (check_seams or contract.get("strict",True)) and not seam_report["passed"]:
                report["errors"].append(f"Texture seam checks failed ({len(seam_report['errors'])} errors); see seams.json")
            report["passed"] = not report["errors"]
        write_json(work/"validation.json",report)
        if not report["passed"]:
            raise ValueError("BSP validation failed: "+"; ".join(report["errors"]))
        if digest(source)!=manifest["source_sha256"]:
            raise ValueError("Source changed during compilation; rebuild the map")
        if contract is not None and digest(sidecar)!=digest(work/sidecar.name):
            raise ValueError("Material contract changed during compilation; rebuild the map")
        shutil.copy2(source,work/source.name)
        manifest["artifacts"] = {p.name:digest(p) for p in [bsp,lit] if p.exists()}
        manifest["evidence"] = {p.name:digest(p) for p in (work/"seams.json",work/sidecar.name) if p.exists()}
        manifest["passed"] = True
        # Logs and hashes refer to the actual run directory, which is retained.
        manifest["run_directory"] = str(work)
        for file in work.iterdir():
            if file.is_file():
                shutil.copy2(file,destination/file.name)
        for extension in (".lit",".lux",".pts"):
            old = destination/(source.stem+extension)
            if old.exists() and not (work/old.name).exists():
                old.unlink()
        for filename in ("seams.json",sidecar.name):
            old = destination/filename
            if old.exists() and not (work/filename).exists():
                old.unlink()
        write_json(manifest_path,manifest)
        return destination/bsp.name
    except Exception as exc:
        manifest["error"] = str(exc)
        write_json(work/"failed-build.json",manifest)
        raise


def verified_build(bsp):
    bsp = Path(bsp).resolve()
    manifest = json.loads((bsp.parent/"build.json").read_text())
    if not manifest.get("passed") or manifest.get("artifacts",{}).get(bsp.name) != digest(bsp):
        raise ValueError("BSP does not match a successful harness build")
    report = BSP(bsp).validate(manifest["format"])
    if not report["passed"]:
        raise ValueError("BSP failed current validation: "+"; ".join(report["errors"]))
    for filename,sha in manifest["artifacts"].items():
        if digest(bsp.parent/filename) != sha:
            raise ValueError(f"Modified build artifact: {filename}")
    for filename,sha in manifest.get("evidence",{}).items():
        if digest(bsp.parent/filename)!=sha:
            raise ValueError(f"Modified material/seam evidence: {filename}")
    return manifest


def package(bsp, output, credits, qa_report=None):
    bsp = Path(bsp).resolve()
    manifest = verified_build(bsp)
    credits = Path(credits).resolve()
    if not credits.is_file() or not credits.read_text().strip():
        raise ValueError("Supply a nonempty credits/readme file")
    if qa_report:
        qa = json.loads(Path(qa_report).read_text())
        if not qa.get("passed") or qa.get("bsp_sha256") != digest(bsp):
            raise ValueError("QA report must pass and match this BSP")
        if "artifacts" in qa and qa["artifacts"]!=manifest["artifacts"]:
            raise ValueError("QA report must match all build artifacts, including colored lighting")
    source = bsp.parent/(bsp.stem+".map")
    if digest(source) != manifest["source_sha256"]:
        raise ValueError("Packaged source does not match build manifest")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in manifest["artifacts"]:
            archive.write(bsp.parent/filename,"maps/"+filename)
        archive.write(source,"source/"+source.name)
        archive.write(credits,"README.txt")
        archive.write(bsp.parent/"build.json","build.json")
        archive.write(bsp.parent/"validation.json","validation.json")
        for filename in manifest.get("evidence",{}):
            archive.write(bsp.parent/filename,"source/"+filename if filename.endswith(".materials.json") else filename)
        if qa_report:
            archive.write(qa_report,"qa.json")
    return output
