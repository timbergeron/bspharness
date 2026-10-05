#!/usr/bin/env python3
"""Install checksum-pinned ericw bundles; keep downloaded assets out of Git."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def install(label, system, offline=False):
    settings = json.loads((ROOT/"configs/tools-lock.json").read_text())[label]
    asset = settings["platforms"][system]
    cache = ROOT/"tools/cache"
    cache.mkdir(parents=True,exist_ok=True)
    archive = cache/asset["url"].rsplit("/",1)[1]
    if not archive.exists():
        if offline:
            raise ValueError(f"Offline archive missing: {archive}")
        partial = archive.with_suffix(".partial")
        print(f"Downloading {settings['version']} ({system})…",flush=True)
        if shutil.which("curl"):
            subprocess.run(["curl","-fsSL","--retry","2","--max-time","120",asset["url"],"-o",str(partial)],check=True)
        else:
            with urlopen(asset["url"],timeout=120) as response, partial.open("wb") as stream:
                shutil.copyfileobj(response,stream)
        if hashlib.sha256(partial.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError(f"Checksum mismatch: {partial}")
        partial.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != asset["sha256"]:
        raise ValueError(f"Checksum mismatch: {archive}; remove it and retry")
    destination = ROOT/"tools/ericw"/label
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise ValueError("Unsafe path in compiler archive")
            if not info.is_dir() and "doc" not in path.parts:
                target = destination.joinpath(*path.parts)
                content = bundle.read(info)
                if target.exists() and target.read_bytes()==content:
                    continue
                target.parent.mkdir(parents=True,exist_ok=True)
                temporary = target.with_suffix(target.suffix+".new")
                temporary.write_bytes(content)
                temporary.replace(target)
    for path in destination.rglob("*"):
        if path.name in ("qbsp","vis","light","bsputil","bspinfo"):
            path.chmod(0o755)
    print(f"Installed {label}: {settings['version']} -> {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain",choices=("modern","stable","all"),default="all")
    parser.add_argument("--offline",action="store_true")
    args = parser.parse_args()
    system = {"Linux":"Linux","Darwin":"Darwin","Windows":"win64"}.get(platform.system())
    if not system:
        parser.error("No pinned bundle for this operating system")
    if system!="Darwin" and platform.machine().lower() not in ("x86_64","amd64"):
        parser.error("Pinned Linux/Windows bundles require x86_64; use a native ericw build and --qbsp-dir/--lighting-dir")
    if system=="Darwin" and platform.machine().lower() in ("arm64","aarch64"):
        print("The pinned Darwin binaries use x86_64 and require Rosetta.")
    try:
        for label in (["modern","stable"] if args.toolchain=="all" else [args.toolchain]):
            install(label,system,args.offline)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print(f"bootstrap: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
