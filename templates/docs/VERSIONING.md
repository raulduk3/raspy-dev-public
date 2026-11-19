# Versioning

The repository uses SemVer derived from the git graph. Nobody types the working version into a project file.

## Tags

- `vX.Y.Z` is a release tag. It lives on `main`, is annotated, and is created by the owner.
- `vX.Y.Z-rc.N` is a release-candidate tag. It lives on `develop`, is annotated, and is created by the owner.
- Other version-like tags are not part of the product version contract.

## Derived versions

Run:

```sh
python3 scripts/version.py
python3 scripts/version.py --json
```

The derived version is:

| Git state | Version shape |
| --- | --- |
| Exactly on `v1.2.3` | `1.2.3` |
| Exactly on `v1.2.3-rc.1` | `1.2.3-rc.1` |
| `develop`, three commits after `v1.2.3` | `1.2.4-develop.3+<sha8>` |
| `feat/parser`, five commits after the reachable tag | `1.2.4-feat-parser.5+<sha8>` |
| Dirty tracked tree | append `.dirty` to the build metadata |

Distance is counted through ancestry from the nearest reachable release or candidate tag. That means a branch cut from another branch naturally carries a version that names its branch, its distance and its exact commit. The `+<sha8>` build metadata is the commit identity, so a pull request and every commit on it have a precise version without editing files.

## Project integration

Use the derived version wherever the project has a runtime surface: CLI `--version`, package metadata at build time, image labels, generated artifacts, release notes and health/status endpoints. Do not hand-edit a version file to name a branch or pull request.
