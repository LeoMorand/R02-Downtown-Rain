"""Freeze selected mud files and compare deployments without editing any source.

Run with ordinary Python, not Unreal Python. The snapshot is deliberately not a
full project backup: shared/vendor assets, engine files and DerivedDataCache are
excluded. Each run gets a new directory and validates its own copied bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
PLUGINS = ("MudRuntime", "MudShaderLab")
SOURCE_EXTENSIONS = {".h", ".cpp", ".cs", ".usf", ".ush"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plugin_files(root: Path, include_binaries: bool = False) -> list[Path]:
    files = []
    for name in PLUGINS:
        plugin = root / "Plugins" / name
        descriptor = plugin / (name + ".uplugin")
        if descriptor.is_file():
            files.append(descriptor)
        for part in ("Source", "Shaders"):
            files.extend(p for p in (plugin / part).rglob("*")
                         if p.is_file() and p.suffix in SOURCE_EXTENSIONS)
        if include_binaries:
            files.extend(p for p in (plugin / "Binaries/Win64").glob("*")
                         if p.is_file() and p.suffix in {".dll", ".modules"})
    return sorted(set(files))


def compare_plugins(source: Path, target: Path) -> dict:
    relative = {p.relative_to(source) for p in plugin_files(source)}
    relative.update(p.relative_to(target) for p in plugin_files(target))
    rows = []
    for rel in sorted(relative):
        a, b = source / rel, target / rel
        ah = digest(a) if a.is_file() else None
        bh = digest(b) if b.is_file() else None
        rows.append({"path": rel.as_posix(), "source_sha256": ah,
                     "target_sha256": bh, "same": ah is not None and ah == bh})
    return {"source": str(source), "target": str(target), "files": rows,
            "matching": sum(x["same"] for x in rows),
            "different_or_missing": [x["path"] for x in rows if not x["same"]]}


def freeze(research: Path) -> Path:
    research = research.resolve(strict=True)
    project = research / "FluidNinjaLive.uproject"
    if research.name != "FluidNinjaStudy" or not project.is_file():
        raise ValueError("Expected the verified FluidNinjaStudy research project")
    mud = research / "Content/MudStudy"
    assets = sorted(p for p in mud.rglob("*")
                    if p.is_file() and p.suffix in {".uasset", ".umap"})
    if not assets:
        raise ValueError("No mud assets found; refusing an empty snapshot")
    for name in PLUGINS:
        if not (research / "Plugins" / name / (name + ".uplugin")).is_file():
            raise ValueError("Missing mud plugin: " + name)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = WORKSPACE / "Verification/MudProfessional" / (stamp + "-baseline")
    out.mkdir(parents=True, exist_ok=False)
    files = assets + plugin_files(research, include_binaries=True) + [project]
    files += sorted((research / "Config").glob("Default*.ini"))
    rows = []
    for source in sorted(set(files)):
        rel = source.relative_to(research)
        data = source.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        target = out / "Baseline" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        if digest(target) != checksum or digest(source) != checksum:
            raise RuntimeError("Snapshot copy/source changed: " + str(source))
        rows.append({"path": rel.as_posix(), "bytes": len(data), "sha256": checksum})

    historical_path = WORKSPACE / "Verification/MudRegression/20261027_01/baseline_manifest.json"
    historical = json.loads(historical_path.read_text(encoding="utf-8-sig"))
    old_changes = []
    for row in historical["files"]:
        current = research / row["path"]
        if not current.is_file() or digest(current) != row["sha256"]:
            old_changes.append(row["path"])
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "scope": "MudStudy assets/maps, two mud plugins and project defaults. Not a full dependency backup or a new runtime acceptance.",
        "snapshot_verified": True,
        "files": rows,
        "total_bytes": sum(row["bytes"] for row in rows),
        "historical_comparison": {"manifest": str(historical_path),
                                  "checked": len(historical["files"]),
                                  "changed_or_missing": old_changes},
        "deployment_comparisons": [
            compare_plugins(WORKSPACE, research),
            compare_plugins(WORKSPACE, WORKSPACE / "Verification/MudShaderHost")],
    }
    # Recheck all frozen research files after comparisons, not only during copy.
    changed = [row["path"] for row in rows
               if digest(research / row["path"]) != row["sha256"]]
    if changed:
        raise RuntimeError("Research files changed during baseline: " + repr(changed))
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "files": len(rows), "bytes": manifest["total_bytes"],
                      "historical_changes": old_changes,
                      "plugin_comparisons": [{"target": x["target"], "matching": x["matching"],
                                              "different_or_missing": x["different_or_missing"]}
                                             for x in manifest["deployment_comparisons"]]},
                     ensure_ascii=False))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", required=True, type=Path)
    freeze(parser.parse_args().research)
