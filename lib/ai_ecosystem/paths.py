"""Where the platform lives on this machine.

One install serves every user (owner, assistant, ops, engineer), so it cannot sit in anyone's home:

  SHARE     /opt/dev-platform            root-owned, world-readable
              releases/<commit>/         built by `ai-release activate` with git archive
              current -> releases/<sha>  the activated release; DEV_PLATFORM_HOME
              pi-runtime/<version>/      the pinned Pi package (npm ci from the lockfile)
              openrig-runtime/           the pinned OpenRig runtime and its Node
  CHECKOUT  ~/dev/dev-platform           the owner's working repository (development only)

Each can be overridden by the environment, which is how tests and a second machine move them:
DEV_PLATFORM_SHARE, DEV_PLATFORM_HOME, DEV_PLATFORM_CHECKOUT. Shell surfaces (hooks, Codex
rules) use the literal `${DEV_PLATFORM_HOME:-/opt/dev-platform/current}`.
"""
import os
import platform
from pathlib import Path

DEFAULT_SHARE = '/opt/dev-platform'
SHELL_HOME = '${DEV_PLATFORM_HOME:-' + DEFAULT_SHARE + '/current}'


def share():
    return Path(os.environ.get('DEV_PLATFORM_SHARE') or DEFAULT_SHARE)


def install():
    """The activated release every user runs, whether or not it exists yet."""
    return Path(os.environ.get('DEV_PLATFORM_HOME') or share() / 'current')


def teams():
    """Each team's control folder is teams()/<team>, beside the code: rig.yaml or RIG.md, role
    guidance, start prompts, and untracked notes. One place for every project, grouped or not."""
    return Path(os.environ.get('DEV_PLATFORM_TEAMS') or Path.home() / 'dev/teams').expanduser()


def checkout():
    return Path(os.environ.get('DEV_PLATFORM_CHECKOUT') or Path.home() / 'dev/dev-platform').expanduser()


def pi_runtimes():
    return share() / 'pi-runtime'


def openrig_runtime():
    return share() / 'openrig-runtime'


SEAT_BIN = '/usr/local/lib/dev-server/seat-bin'


def daemon_path(*first):
    """PATH for the OpenRig daemon, which every seat inherits: the machine's seat programs
    (`claude` and `codex` that start a seat through the launcher, on a resolved account and its
    stored login) come before anything else, then `first`, then the caller's PATH. Only here:
    nobody else's PATH carries them. DEV_PLATFORM_SEAT_BIN moves them for tests."""
    seat = Path(os.environ.get('DEV_PLATFORM_SEAT_BIN') or SEAT_BIN)
    parts = [str(seat)] if seat.is_dir() else []
    return os.pathsep.join([*parts, *map(str, first), os.environ.get('PATH', '')])


def node_platform():
    """The Node distribution name for this machine: linux-arm64 on dev-server, darwin-arm64 on a Mac."""
    system = {'Darwin': 'darwin', 'Linux': 'linux'}.get(platform.system(), platform.system().lower())
    machine = {'aarch64': 'arm64', 'arm64': 'arm64', 'x86_64': 'x64', 'AMD64': 'x64'}.get(
        platform.machine(), platform.machine())
    return f'{system}-{machine}'


def expand(value):
    """Expand a shell-style path, including ${VAR:-default}, the way a hook's shell would."""
    text = str(value)
    while '${' in text:
        start = text.index('${')
        end = text.index('}', start)
        name, _, default = text[start + 2:end].partition(':-')
        text = text[:start] + (os.environ.get(name) or default) + text[end + 1:]
    return Path(os.path.expandvars(text)).expanduser()
