"""Native history locators for the four persistent local OpenRig environments.

Host paths are projections of container paths, never a claim of host execution.
Credentials are not read. Discovery grants neither launch nor adoption authority.
"""
from pathlib import Path, PurePosixPath
from .adapters import Source, read_claude, read_codex

ACCOUNTS = ('anthropic-apple', 'anthropic-gmail', 'openai-apple', 'openai-gmail')


def mapped_path(account_root, value):
    """Map only declared mounts. Refuse traversal and unmapped locations."""
    native = PurePosixPath(value)
    if '..' in native.parts:
        raise ValueError('container path contains traversal')
    for origin, target in (('/home/node','home'),('/workspace','workspace')):
        try:
            relative = native.relative_to(origin)
        except ValueError:
            continue
        return account_root / target / Path(*relative.parts)
    raise ValueError('container path is outside declared mounts')


def sources(root):
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError('account environment root does not exist')
    result = []
    for account in ACCOUNTS:
        runtime = 'claude' if account.startswith('anthropic-') else 'codex'
        folder = root/account
        native_home = folder/'home'/('.claude' if runtime == 'claude' else '.codex')
        def read(folder=folder, account=account, runtime=runtime, native_home=native_home):
            mapper = lambda value: mapped_path(folder, value)
            rows = read_claude(native_home, mapper) if runtime == 'claude' else read_codex(native_home)
            for row in rows:
                native_cwd = row.get('cwd')
                row['native'].update(environment_host=account, container_cwd=native_cwd,
                                     account_profile=account, account_identity='unverified')
                try:
                    row['cwd'] = str(mapper(native_cwd)) if native_cwd else None
                except ValueError:
                    row['cwd'] = None
                    row['native']['workspace_unmapped'] = True
                rollout = row['native'].get('rollout_path')
                if rollout:
                    row['native']['container_rollout_path'] = rollout
                    row['native']['rollout_path'] = str(mapper(rollout))
                yield row
        result.append(Source(f'{runtime}:environment:{account}',runtime,str(native_home),'openrig',read))
    return result
