"""dev-spec export DIR [--name NAME]: a copy of the tool for a repository that owns it (docs/spec/SDD.md, ST-18).

A native project keeps the tool in its own repository, and its pipeline runs that copy. The copy names no platform:
the command, the module, the schema, the variables and the folders get the neutral name. The copy has no `export`
command. A manifest holds the hash of each file, so that a review can see that a copy is not changed by hand.

    DIR/NAME                 the command
    DIR/<module>/            spectree.py, specwrite.py
    DIR/MANIFEST.json        the name, the commit of the source, the hash of each file
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

SOURCES = ('spectree.py', 'specwrite.py')
# No word of this list is in a copy. The check runs on each export.
FORBIDDEN = re.compile(r'dev-platform|dev-spec|dev-project|dev-loop|dev-forge|ai_ecosystem|DEV_PLATFORM|specexport', re.I)
LAUNCHER = '''#!/usr/bin/env python3
"""{name}: compile and check the specification tree of this repository. See {name} --help."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from {module}.spectree import main  # noqa: E402

sys.exit(main())
'''


def neutral(text, name):
    module = name.replace('-', '_')
    text = re.sub(r'\n[ \t]*# export-begin.*?# export-end[^\n]*', '', text, flags=re.S)
    for old, new in (('dev-platform.spec-tree@1', f'{name}@1'), ('DEV_PLATFORM_', module.upper() + '_'),
                     ('dev-platform', name), ('dev-spec', name), ('ai_ecosystem', module)):
        text = text.replace(old, new)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(prog='dev-spec export', description='Write a copy of the tool with a neutral name into a folder.')
    ap.add_argument('folder')
    ap.add_argument('--name', default='spec-tree', help='the name of the command in the copy (default: spec-tree)')
    args = ap.parse_args(argv)
    if not re.fullmatch(r'[a-z][a-z0-9]*(-[a-z0-9]+)*', args.name) or FORBIDDEN.search(args.name):
        print('dev-spec export: the name is lowercase words with hyphens, and no name of the platform', file=sys.stderr)
        return 2
    here = Path(__file__).resolve().parent
    module = args.name.replace('-', '_')
    files = {f'{module}/__init__.py': f'"""{args.name}: the specification tree of a repository."""\n',
             args.name: LAUNCHER.format(name=args.name, module=module)}
    for source in SOURCES:
        files[f'{module}/{source}'] = neutral((here / source).read_text(encoding='utf-8'), args.name)
    left = sorted({f'{rel}: {found.group(0)}' for rel, text in files.items() for found in FORBIDDEN.finditer(text)})
    if left:
        print('dev-spec export: refused: the copy would hold a name of the platform:\n  ' + '\n  '.join(left), file=sys.stderr)
        return 1
    commit = subprocess.run(['git', '-C', str(here), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    out = Path(args.folder)
    for rel, text in files.items():
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    (out / args.name).chmod(0o755)
    manifest = {'name': args.name, 'source_commit': commit,
                'files': {rel: hashlib.sha256(text.encode()).hexdigest() for rel, text in sorted(files.items())}}
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'wrote {len(files)} files and MANIFEST.json to {out}; the command is {out / args.name}')
    return 0
