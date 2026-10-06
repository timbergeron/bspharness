"""Hash-checked external PNGs and FTE particle scripts; no dependencies."""

from pathlib import Path, PurePosixPath
import re
import shutil


def files(root, records):
    from .pipeline import digest
    root = Path(root).resolve()
    if not isinstance(records, dict):
        raise ValueError("Runtime assets must be a path-to-record mapping")
    result = {}
    for name, record in records.items():
        path = PurePosixPath(name)
        if (not name or "\\" in name or path.is_absolute() or
                any(p in ("..", ".", "") for p in name.split("/")) or
                not ((path.parts[0] in ("textures", "gfx", "particles") and path.suffix == ".png") or
                     (path.parts[0] == "particles" and path.suffix == ".cfg"))):
            raise ValueError(f"Unsafe runtime asset path: {name}")
        source = root.joinpath(*path.parts)
        if not source.resolve().is_relative_to(root):
            raise ValueError(f"Runtime asset escapes its root: {name}")
        if (not isinstance(record, dict) or
                not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", "")) or
                (path.suffix == ".png" and
                 any(type(record.get(k)) is not int or record[k] < 1 for k in ("width", "height"))) or
                (path.suffix == ".cfg" and
                 (record.get("kind") != "fte_particles" or record.get("engine_name")))):
            raise ValueError(f"Invalid runtime asset record: {name}")
        if not source.is_file() or digest(source) != record["sha256"]:
            raise ValueError(f"Modified or missing runtime asset: {name}")
        result[name] = source
        if path.suffix == ".cfg":
            continue
        header = source.read_bytes()[:24]
        if (header[:8] != b"\x89PNG\r\n\x1a\n" or
                int.from_bytes(header[16:20], "big") != record["width"] or
                int.from_bytes(header[20:24], "big") != record["height"]):
            raise ValueError(f"Runtime PNG dimensions disagree: {name}")
    return result


def stage(root, records, destination):
    destination = Path(destination).resolve()
    sources = files(root, records)
    for name, source in sources.items():
        target = destination/name
        if not target.resolve().is_relative_to(destination):
            raise ValueError(f"Runtime staging escapes destination: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    files(destination, records)


def audit_images(text, records):
    """Require declared GL upload dimensions for textures used by this build."""
    sections = re.findall(r"BSPHARNESS_IMAGES_BEGIN\s*\n(.*?)BSPHARNESS_IMAGES_END", text, re.S)
    loaded = {}
    for section in sections:
        for width, height, name in re.findall(r"^\s*(\d+)\s+x\s*(\d+)\s+([^\r\n]+)", section, re.M):
            loaded[name.strip()] = (int(width), int(height))
    errors = []
    for path, record in records.items():
        name = record.get("engine_name")
        if name and loaded.get(name) != (record["width"], record["height"]):
            errors.append(f"Required engine texture missing or resized: {path}")
    return errors, loaded


def bind(bsp, sidecar, destination):
    """Create a separate verified runtime asset variant of an unchanged BSP/LIT."""
    import json
    from datetime import datetime, timezone
    from .pipeline import digest, verified_build, write_json
    bsp,sidecar=Path(bsp).resolve(),Path(sidecar).resolve()
    manifest=verified_build(bsp)
    data=json.loads(sidecar.read_text())
    if data.get("schema")!=1 or data.get("map_sha256")!=manifest["source_sha256"]:
        raise ValueError("Runtime asset variant must match the compiled MAP hash")
    root=sidecar.parent/data["root"];records=data["files"]
    files(root,records)
    destination=Path(destination).resolve()
    if destination.exists():
        raise ValueError("Use a fresh destination for a runtime asset variant")
    destination.mkdir(parents=True)
    for source in bsp.parent.iterdir():
        if source.is_file() and source.name!="build.json":
            shutil.copy2(source,destination/source.name)
    stage(root,records,destination/"runtime")
    shutil.copy2(sidecar,destination/(bsp.stem+".assets.json"))
    previous=manifest.get("assets_manifest_sha256")
    manifest["runtime_assets"]=records
    manifest["assets_manifest_sha256"]=digest(sidecar)
    manifest["runtime_binding"]={"time_utc":datetime.now(timezone.utc).isoformat(),
                                 "from_build":str(bsp.parent),"previous_assets_manifest_sha256":previous,
                                 "scope":"External runtime assets only; identical compiled BSP, LIT, MAP and seam evidence"}
    write_json(destination/"build.json",manifest)
    result=destination/bsp.name
    verified_build(result)
    return result
