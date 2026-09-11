#!/usr/bin/env python3
"""Build snapshot-bound, axis-specific packets for quality-panel reviewers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


AXIS_SURFACES = {
    "coherent_contract": ("instruction.md", "task.toml", "environment", "tests"),
    "correct_reference_solution": ("instruction.md", "solution"),
    "protected_ground_truth": ("environment", "tests"),
    "sound_verifier": ("instruction.md", "tests"),
}
REQUIRED_SURFACES = ("instruction.md", "task.toml", "environment", "solution", "tests")
IGNORED_NAMES = {".DS_Store", ".git", ".pytest_cache", ".ruff_cache", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
PANEL_DOCS = (
    "quality-panel-judge-guide.md",
    "quality-panel-examples.md",
)
PACKET_SCHEMA_VERSION = 3


def ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not ignored(path.relative_to(root)):
            yield path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode())
        else:
            digest.update(b"file\0")
            digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\0")
    return digest.hexdigest()


def copy_surface(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)


def reject_escaping_symlinks(packet: Path) -> None:
    packet_root = packet.resolve()
    for path in packet.rglob("*"):
        if not path.is_symlink():
            continue
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(packet_root):
            raise ValueError(f"symlink escapes review packet: {path} -> {os.readlink(path)}")


def file_manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in iter_files(root)
        if not path.is_symlink()
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def build_packets(task: Path, output: Path, contract_files: tuple[str, ...] = ()) -> Path:
    task = task.resolve()
    output = output.resolve()
    if not task.is_dir():
        raise ValueError(f"task directory does not exist: {task}")
    if output == task or output.is_relative_to(task):
        raise ValueError("packet output must be outside the task directory")
    missing = [surface for surface in REQUIRED_SURFACES if not (task / surface).exists()]
    if missing:
        raise ValueError(f"task is missing required surfaces: {', '.join(missing)}")

    # Explicitly selected candidate-visible authorities, never inferred from
    # solution/test imports. Preserve their original paths for citations.
    selected = sorted(set(contract_files))
    for relative in selected:
        path = Path(relative)
        source = task / path
        if (path.is_absolute() or ".." in path.parts or not path.parts
                or path.parts[0] != "environment"
                or not source.is_file()
                or not source.resolve().is_relative_to(task / "environment")):
            raise ValueError(f"contract file must be an existing file inside environment: {relative}")

    docs_root = repo_root() / "docs" / "testing-and-validation"
    missing_docs = [name for name in PANEL_DOCS if not (docs_root / name).is_file()]
    if missing_docs:
        raise ValueError(f"quality-panel docs are missing: {', '.join(missing_docs)}")

    snapshot = sha256_tree(task)
    recipe = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "contract_files": selected,
        "panel_docs": {name: sha256_file(docs_root / name) for name in PANEL_DOCS},
    }
    recipe_hash = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
    final_root = output / snapshot / recipe_hash
    root_manifest = final_root / "packet-manifest.json"
    if root_manifest.is_file():
        data = json.loads(root_manifest.read_text())
        if (
            data.get("schema_version") == PACKET_SCHEMA_VERSION
            and data.get("snapshot_sha256") == snapshot
        ):
            return root_manifest

    output.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.mkdtemp(prefix=f".{snapshot[:12]}-", dir=output))
    staging = staging_parent / snapshot
    staging.mkdir()
    try:
        axis_paths: dict[str, str] = {}
        for axis, surfaces in AXIS_SURFACES.items():
            packet = staging / axis
            packet.mkdir()
            for surface in surfaces:
                copy_surface(task / surface, packet / surface)
            if axis in {"correct_reference_solution", "sound_verifier"}:
                for relative in selected:
                    copy_surface(task / relative, packet / relative)

            docs_target = packet / "_panel_docs"
            docs_target.mkdir()
            for name in PANEL_DOCS:
                shutil.copy2(docs_root / name, docs_target / name)

            reject_escaping_symlinks(packet)
            manifest = {
                "schema_version": PACKET_SCHEMA_VERSION,
                "axis": axis,
                "snapshot_sha256": snapshot,
                "included_surfaces": list(surfaces),
                "contract_files": selected if axis in {
                    "correct_reference_solution", "sound_verifier"
                } else [],
                "files": file_manifest(packet),
            }
            (packet / "packet-manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            )
            axis_paths[axis] = str((final_root / axis).resolve())

        root_data = {
            "schema_version": PACKET_SCHEMA_VERSION,
            "task_slug": task.name,
            "snapshot_sha256": snapshot,
            "axis_packets": axis_paths,
            "recipe": recipe,
        }
        (staging / "packet-manifest.json").write_text(
            json.dumps(root_data, indent=2, sort_keys=True) + "\n"
        )
        final_root.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(final_root)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)

    return root_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--contract-file", action="append", default=[],
                        help="Task-relative candidate-visible authority under environment; repeat for dependencies")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_packets(args.task_dir, args.output, tuple(args.contract_file))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}") from error
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
