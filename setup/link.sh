#!/usr/bin/env bash
# setup/link.sh: wire this repository into your agents, as you (no sudo). Safe to re-run; run it
# again after you add a skill, an MCP server or a context. setup/linux.sh and setup/macos.sh end
# by running it.
#   - commands guard, notify, check-before-stop, loop, new-repo in ~/.local/bin
#   - global git hooks (core.hooksPath): no push to main, no force push, no secrets
#   - skills in ~/.agents/skills, then each installed agent's adapter in contexts/cli-session/
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"; export ROOT
for tool in git jq curl; do
  command -v "$tool" >/dev/null || { echo "link: $tool is missing; run setup/linux.sh or setup/macos.sh" >&2; exit 1; }
done
bin="$HOME/.local/bin"; mkdir -p "$bin"
for file in hooks/guard hooks/notify hooks/check-before-stop bin/loop bin/new-repo; do
  ln -sfn "$ROOT/$file" "$bin/$(basename "$file")"
done
previous="$(git config --global core.hooksPath || true)"
[ -z "$previous" ] || [ "$previous" = "$ROOT/hooks/git" ] || echo "link: core.hooksPath was $previous; now $ROOT/hooks/git" >&2
git config --global core.hooksPath "$ROOT/hooks/git"

link_skills() {   # link every skill into $1; remove links to skills that are gone
  mkdir -p "$1"
  for link in "$1"/*; do
    [ -L "$link" ] && case "$(readlink "$link")" in "$ROOT"/skills/*) [ -e "$link" ] || rm "$link" ;; esac
  done
  for skill in "$ROOT"/skills/*/; do
    target="$1/$(basename "$skill")"
    [ -e "$target" ] && [ ! -L "$target" ] && { echo "link: $target is your own; left alone" >&2; continue; }
    ln -sfn "${skill%/}" "$target"
  done
}
link_skills "$HOME/.agents/skills"
export -f link_skills
for adapter in "$ROOT"/contexts/*/*/install.sh; do bash "$adapter"; done
case ":$PATH:" in *":$bin:"*) ;; *) echo "link: add $bin to your PATH" >&2 ;; esac
echo "link: done ($ROOT)"
