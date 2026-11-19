#!/usr/bin/env python3
"""Check commit messages and added source/documentation lines for repository hygiene."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SUBJECT = re.compile(r"^(feat|fix|docs|test|refactor|perf|chore|ci)(\([a-z0-9-]+\))?!?: .{1,72}$")
SCANNED_PREFIXES = ("src/", "app/", "lib/", "tests/", "scripts/", "docs/")
TRAILER = re.compile(r"^(co-authored-by|signed-off-by|reviewed-by|acked-by|tested-by|closes|fixes|refs?):", re.I)
CO_AUTHOR = re.compile(r"^co-authored-by:\s*(.*)$", re.I)
ATTRIBUTION = re.compile(r"anthropic|openai|claude|codex|copilot|noreply@", re.I)
GENERATED_WITH = re.compile(r"\bgenerated with\b", re.I)
FORBIDDEN = {
    "orchestrat": re.compile(r"orchestrat", re.I),
    "worker lane": re.compile(r"worker lane", re.I),
    "subagent": re.compile(r"\bsubagents?\b", re.I),
    "claude": re.compile(r"claude", re.I),
    "codex": re.compile(r"codex", re.I),
    "copilot": re.compile(r"copilot", re.I),
    "gpt-": re.compile(r"gpt-", re.I),
    "run id": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
}
EXEMPT_PATHS = {"scripts/checks/hygiene.py", "tests/checks/test_hygiene.py"}


@dataclass(frozen=True)
class Finding:
    where: str
    code: str
    message: str


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def resolvable(cwd: Path, ref: str) -> bool:
    return git(cwd, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False).returncode == 0


def base_ref(cwd: Path, requested: str | None) -> str | None:
    if requested and requested.strip("0"):
        if resolvable(cwd, requested):
            return requested
        print(f"hygiene: base {requested} is not resolvable; falling back", file=sys.stderr)
    if resolvable(cwd, "origin/develop"):
        merge_base = git(cwd, "merge-base", "origin/develop", "HEAD", check=False)
        if merge_base.returncode == 0 and merge_base.stdout.strip():
            return merge_base.stdout.strip()
    if resolvable(cwd, "HEAD~1"):
        return "HEAD~1"
    return None


def token_findings(where: str, line: str, commit: bool, file: str | None = None) -> list[Finding]:
    if file in EXEMPT_PATHS:
        return []
    out = []
    for name, pattern in FORBIDDEN.items():
        if name == "run id" and not commit:
            continue
        if pattern.search(line):
            out.append(Finding(where, "forbidden-token", f'carries "{name}"'))
    return out


def check_message(sha: str, message: str) -> list[Finding]:
    lines = message.rstrip().splitlines() or [""]
    where = sha[:7]
    out = []
    if not SUBJECT.match(lines[0]):
        out.append(Finding(where, "subject-format", "subject must be `type(scope): summary`"))
    for index, line in enumerate(lines):
        co_author = CO_AUTHOR.match(line)
        if co_author:
            if ATTRIBUTION.search(co_author.group(1)):
                out.append(Finding(where, "trailer-attribution", "co-author trailer names a tool"))
            continue
        if GENERATED_WITH.search(line):
            out.append(Finding(where, "trailer-attribution", "line says generated with a tool"))
            continue
        if TRAILER.match(line):
            continue
        out.extend(token_findings(where, line, commit=True))
    return out


def check_diff(diff: str) -> tuple[list[Finding], int]:
    out: list[Finding] = []
    file: str | None = None
    line = 0
    scanned = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            file = target[2:] if target.startswith("b/") else None
            continue
        if raw.startswith("--- "):
            continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk:
            line = int(hunk.group(1))
            continue
        if file is None:
            continue
        if raw.startswith("+"):
            if file.startswith(SCANNED_PREFIXES):
                scanned += 1
                out.extend(token_findings(f"{file}:{line}", raw[1:], commit=False, file=file))
            line += 1
        elif not raw.startswith("-") and not raw.startswith("\\"):
            line += 1
    return out, scanned


def check_hygiene(cwd: Path, requested_base: str | None = None) -> dict[str, object]:
    base = base_ref(cwd.resolve(), requested_base)
    if base is None:
        return {
            "findings": [],
            "rangeChecked": None,
            "commitsChecked": 0,
            "linesChecked": 0,
            "notes": ["no parent commit; nothing to check"],
        }
    range_checked = f"{base}..HEAD"
    shas = git(cwd, "rev-list", "--no-merges", range_checked).stdout.splitlines()
    findings: list[Finding] = []
    for sha in shas:
        message = git(cwd, "show", "-s", "--format=%B", sha).stdout
        findings.extend(check_message(sha, message))
    diff = git(cwd, "diff", "--unified=0", "--no-ext-diff", f"{base}..HEAD", "--").stdout
    diff_findings, scanned = check_diff(diff)
    findings.extend(diff_findings)
    return {
        "findings": [finding.__dict__ for finding in findings],
        "rangeChecked": range_checked,
        "commitsChecked": len(shas),
        "linesChecked": scanned,
        "notes": [],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check commit/source hygiene")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)
    result = check_hygiene(args.cwd.resolve(), args.base or None)
    findings = result["findings"]
    range_checked = result["rangeChecked"]
    if range_checked is None:
        print("hygiene: no parent commit; nothing to check")
        return 0
    if findings:
        for finding in findings:
            print(f"{finding['where']}: {finding['code']}: {finding['message']}", file=sys.stderr)
        print(
            f"hygiene: {len(findings)} finding(s), {result['commitsChecked']} commit(s), {result['linesChecked']} added line(s) checked over {range_checked}",
            file=sys.stderr,
        )
        return 1
    print(f"hygiene: clean, {result['commitsChecked']} commit(s), {result['linesChecked']} added line(s) checked over {range_checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
