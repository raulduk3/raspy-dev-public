#!/usr/bin/env python3
"""Harness guard for a controlled specification (docs/spec/SDD.md, SDD-SW-12).

Reads the hook input on stdin (JSON with tool_name, tool_input and cwd). Where the control of the
specification is on for the repository, it refuses a direct write of an agent to a file of the system
requirements, the SDD or the TDD, and names the command to use: exit 2 with the reason. Each other
case is exit 0. It covers the edit tools and the usual shell writes (a redirect, sed -i, tee, mv, cp, rm).
A write that it cannot see is caught at the commit: the commit hook refuses content that no command recorded.
"""
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))

EDIT_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')


def controlled(folder):
    """(top of the checkout, its specification paths) when the control is on for it, else None."""
    from ai_ecosystem import specwrite, spectree
    top = spectree.git(folder, 'rev-parse', '--show-toplevel')
    if not top:
        return None
    try:
        conf = spectree.load_config(specwrite.config_of(top))
    except (specwrite.Refused, spectree.ConfigError, OSError, ValueError):
        return None
    return (top, specwrite.spec_paths(conf, top)) if conf['control'] else None


def refuse(rel):
    reason = (f'dev-platform guard: {rel} is a specification file of a controlled project. No agent edits it directly. '
              'Change it with a command: dev-spec set, add, remove, link, unlink, bind, unbind, own or move '
              '(dev-spec set --help). The owner records a hand edit with dev-spec accept in a terminal.')
    print(reason)
    print(reason, file=sys.stderr)
    return 2


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    tool, given, cwd = data.get('tool_name', ''), data.get('tool_input') or {}, data.get('cwd') or os.getcwd()
    from ai_ecosystem import specwrite
    if tool in EDIT_TOOLS:
        path = given.get('file_path') or given.get('notebook_path') or ''
        if not path:
            return 0
        full = os.path.realpath(os.path.join(cwd, os.path.expanduser(path)))
        folder = os.path.dirname(full)
        while folder and not os.path.isdir(folder):
            folder = os.path.dirname(folder)
        found = controlled(folder or cwd)
        if found and specwrite.is_spec(os.path.relpath(full, found[0]), found[1]):
            return refuse(os.path.relpath(full, found[0]))
        return 0
    command = given.get('command') or ''
    if not command or not os.path.isdir(cwd):
        return 0
    found = controlled(cwd)
    if not found:
        return 0
    for path in found[1]:
        name = re.escape(path.rstrip('/'))
        target = rf'(?:\S*/)?{name}(?:/[^\s;&|]*)?'
        writes = (rf'>>?\s*["\x27]?{target}',
                  rf'\btee\b[^;&|\n]*\s["\x27]?{target}',
                  rf'\bsed\s+(?:-[A-Za-z]*i\b|--in-place)[^;&|\n]*\s["\x27]?{target}',
                  rf'\bperl\s+-[A-Za-z]*i[^;&|\n]*\s["\x27]?{target}',
                  rf'\b(?:rm|truncate)\b[^;&|\n]*\s["\x27]?{target}',
                  rf'\b(?:mv|cp|install)\b[^;&|\n]*\s["\x27]?{target}["\x27]?\s*(?:$|[;&|\n])')
        if any(re.search(pattern, command) for pattern in writes):
            return refuse(path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
