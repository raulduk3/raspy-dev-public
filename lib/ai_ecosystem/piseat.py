"""A Pi seat on the OpenRouter key: its model, and its Pi agent folder made ready before launch.

OpenRig starts a `pi` seat as `pi --mode rpc` with PI_CODING_AGENT_DIR set to
$OPENRIG_HOME/state/pi/<session>/agent and only the declared provider's key (OPENROUTER_API_KEY
for an `openrouter/...` model) passed on from the daemon's environment. Pi has no hooks, so the
platform's guard and the advice tool reach the seat as Pi extensions, named in that folder's
settings.json (Pi discovers .js and .ts in extensions/, not .mjs; a listed path loads either way).
"""
import json
import os
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ''):  # run as a script by the loop
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_ecosystem import paths  # noqa: E402
else:
    from . import paths

PLATFORM = Path(__file__).resolve().parents[2]
EXTENSIONS = ('seat-guard.mjs', 'advice-tool.mjs')
# The seats of a shape and the model file's role for each; any other seat is a worker.
SEAT_ROLES = {'lead': 'rig control', 'overseer': 'rig overseer', 'second': 'rig second overseer'}


def platform_root():
    """The activated release's link when this is that release, so a seat follows each activation."""
    current = paths.install()
    if current.exists() and current.resolve() == PLATFORM:
        return current
    return PLATFORM


def model(role):
    """`openrouter/<maker>/<model>[:<effort>]` for a role, as Pi's --model takes it. The
    openrouter runtime never falls back to a subscription."""
    found = subprocess.run([sys.executable, str(PLATFORM / 'bin/pstack-model'), 'resolve', role,
                            '--runtime', 'openrouter', '--no-inherit'], capture_output=True, text=True)
    line = found.stdout.splitlines()[0] if found.returncode == 0 and found.stdout.strip() else ''
    if not line:
        raise ValueError(f'the model file has no OpenRouter model for {role!r} (pstack-model show; /setup-pstack)')
    name, _, effort = line.partition('\t')
    return name + (f':{effort}' if effort else '')


def seat_model(member):
    return model(SEAT_ROLES.get(member, 'rig worker'))


def maker(name):
    """openrouter/anthropic/claude-fable-5.1:max -> anthropic"""
    parts = name.split('/')
    return parts[1] if len(parts) > 2 else parts[0]


def openrig_home(env=None):
    env = os.environ if env is None else env
    return Path(env.get('OPENRIG_HOME') or Path.home() / '.openrig')


def agent_dir(session, home=None):
    return Path(home or openrig_home()) / 'state/pi' / session / 'agent'


def prepare(session, home=None, root=None, models=None):
    """Write the seat's Pi settings so the guard and the advice tool load. Idempotent; keeps
    every other setting and extension already there. Returns the agent folder."""
    return prepare_dir(agent_dir(session, home), root=root, models=models)


def prepare_dir(folder, root=None, extra=(), models=None):
    """The same for any Pi agent folder: a headless loop worker's adds worker-limits.mjs.
    models (or DEV_PLATFORM_PI_MODELS) is a Pi models.json to give the seat as well: a custom
    endpoint or model metadata, the rig's `pi_models` setting. It carries no key."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    models = models or os.environ.get('DEV_PLATFORM_PI_MODELS')
    if models:
        text = Path(models).read_text()
        json.loads(text)
        (folder / 'models.json').write_text(text)
    settings = folder / 'settings.json'
    try:
        data = json.loads(settings.read_text()) if settings.is_file() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    names = (*EXTENSIONS, *extra)
    ours = [str(Path(root or platform_root()) / 'integrations/pi' / name) for name in names]
    kept = [e for e in data.get('extensions', []) if isinstance(e, str) and not e.endswith(names)]
    data['extensions'] = kept + ours
    tmp = settings.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    os.chmod(tmp, 0o600)
    tmp.replace(settings)
    return folder


def main(argv=None):
    """piseat prepare-dir FOLDER [EXTENSION...] | piseat model ROLE: for the loop's shell script."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) >= 2 and argv[0] == 'prepare-dir':
        print(prepare_dir(argv[1], extra=tuple(argv[2:])))
        return 0
    if len(argv) == 2 and argv[0] == 'model':
        try:
            print(model(argv[1]))
        except ValueError as error:
            print(f'piseat: {error}', file=sys.stderr)
            return 2
        return 0
    print('usage: piseat prepare-dir FOLDER [EXTENSION...] | piseat model ROLE', file=sys.stderr)
    return 64


if __name__ == '__main__':
    sys.exit(main())
