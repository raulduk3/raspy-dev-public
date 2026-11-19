#!/usr/bin/env python3
"""Derive a SemVer-compatible version from the git graph.

No project file owns the version. The nearest annotated tag shaped as vX.Y.Z or
vX.Y.Z-rc.N and the exact HEAD commit produce one string:

- On vX.Y.Z: X.Y.Z
- On vX.Y.Z-rc.N: X.Y.Z-rc.N
- After a tag: <next-patch>-<branch-slug>.<distance>+<sha8>
- Dirty tracked tree: append .dirty to build metadata

This makes every branch, pull request and commit addressable by one derived
version while keeping release tags as the only hand-authored versions.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$")
TAG_GLOB = "v[0-9]*.[0-9]*.[0-9]*"


class VersionUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class DerivedVersion:
    version: str
    tag: str
    distance: int
    sha: str
    branch: str
    dirty: bool


def git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
        )
    except OSError as exc:
        raise VersionUnavailable(f"git is unavailable: {exc}") from exc
    if result.returncode != 0:
        raise VersionUnavailable(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def branch_slug(branch: str) -> str:
    slug = re.sub(r"[^0-9a-z]+", "-", branch.lower()).strip("-")
    return slug or "detached"


def branch_name(cwd: Path) -> str:
    name = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if name != "HEAD":
        return name
    return os.environ.get("GITHUB_REF_NAME") or "detached"


def derive(cwd: Path) -> DerivedVersion:
    sha = git(cwd, "rev-parse", "HEAD")
    try:
        described = git(cwd, "describe", "--tags", "--long", "--match", TAG_GLOB, "HEAD")
    except VersionUnavailable as exc:
        described = f"error: {exc}"
    match = re.match(r"^(.*)-(\d+)-g([0-9a-f]+)$", described)
    tag = match.group(1) if match else ""
    shape = TAG_PATTERN.match(tag)
    if match is None or shape is None:
        raise VersionUnavailable(
            f"no reachable tag shaped vX.Y.Z or vX.Y.Z-rc.N from HEAD (git describe: {described})"
        )
    distance = int(match.group(2))
    dirty = bool(git(cwd, "status", "--porcelain", "--untracked-files=no"))
    branch = branch_name(cwd)
    if distance == 0:
        version = tag[1:] + (f"+{sha[:8]}.dirty" if dirty else "")
    else:
        major, minor, patch = (int(shape.group(i)) for i in range(1, 4))
        version = f"{major}.{minor}.{patch + 1}-{branch_slug(branch)}.{distance}+{sha[:8]}"
        if dirty:
            version += ".dirty"
    return DerivedVersion(version, tag, distance, sha, branch, dirty)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="derive the repository version from git")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--cwd", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        derived = derive(args.cwd.resolve())
    except VersionUnavailable as exc:
        print(f"version: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(derived), sort_keys=True) if args.json else derived.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
