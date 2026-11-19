# User timers

`dev-loop-tidy.timer` runs `skills/loop/scripts/tidy-all.sh` each day at 04:30. The script runs
`loop.sh tidy <repo> --apply` for each line in `repos.conf`. Tidy bundles each ref first. It keeps
the rig worktree, the worker slots, every worktree with changes, the base and each trunk in the
`keep=` field of the `repos.conf` line.

Install it as the owner:

```bash
mkdir -p ~/.config/systemd/user
ln -sf /opt/dev-platform/current/integrations/systemd/dev-loop-tidy.service ~/.config/systemd/user/
ln -sf /opt/dev-platform/current/integrations/systemd/dev-loop-tidy.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now dev-loop-tidy.timer
```
