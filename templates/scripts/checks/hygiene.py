"""Commit and source hygiene over base..HEAD.

Commit subjects read `type(scope): summary`; no attribution trailer or generated-with line; no
word from words.txt in a commit message or an added line. The base is HYGIENE_BASE, else the
merge base with origin/main, else HEAD~1.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

SUBJECT = re.compile(r"^(feat|fix|docs|test|refactor|perf|chore|ci)(\([a-z0-9._/-]+\))?!?: \S.{0,70}$")
ATTRIBUTION = re.compile(r"^co-authored-by:.*noreply@|\bgenerated with\b", re.I)
HERE = Path(__file__).resolve().parent
EXEMPT = {"scripts/checks/words.txt", "scripts/checks/hygiene.py"}


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], text=True, capture_output=True).stdout


def base(root):
    for ref in (os.environ.get("HYGIENE_BASE", ""), git(root, "merge-base", "origin/main", "HEAD").strip(), "HEAD~1"):
        if ref.strip("0") and git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip():
            return ref
    return None


def main(root):
    words = [w.strip().lower() for w in (HERE / "words.txt").read_text().splitlines() if w.strip() and not w.startswith("#")]
    word = re.compile("|".join(map(re.escape, words)), re.I) if words else None
    start = base(root)
    if start is None:
        print("hygiene: no parent commit; nothing to check")
        return 0
    findings = []
    for sha in git(root, "rev-list", "--no-merges", f"{start}..HEAD").split():
        lines = git(root, "show", "-s", "--format=%B", sha).rstrip().splitlines() or [""]
        if not SUBJECT.match(lines[0]):
            findings.append(f"{sha[:7]}: subject must be `type(scope): summary` under 72 characters")
        for line in lines:
            if ATTRIBUTION.search(line):
                findings.append(f"{sha[:7]}: attribution trailer or generated-with line")
            elif word and word.search(line):
                findings.append(f"{sha[:7]}: names a tool or model")
    path, number = None, 0
    for raw in git(root, "diff", "-U0", "--no-ext-diff", f"{start}..HEAD").splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            number = int(re.match(r"@@ -\S+ \+(\d+)", raw).group(1))
        elif raw.startswith("+") and path:
            if word and path not in EXEMPT and word.search(raw):
                findings.append(f"{path}:{number}: names a tool or model")
            number += 1
    for finding in findings:
        print(finding, file=sys.stderr)
    print(f"hygiene: {len(findings)} finding(s) over {start[:12]}..HEAD")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
