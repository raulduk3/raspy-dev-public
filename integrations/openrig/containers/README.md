# Local account environments

Candidate deployment for four account-pinned OpenRig hosts. One pinned image, four instances, no credential swapping or proxy. Account environments own execution; project/conversation records own the work. **Four native CLI logins and distinct provider-pair identities are verified. Worker messaging and recovery of actual authenticated sessions remain unverified.**

The source image now also includes Pi 0.87.1. The separate candidate tag
`dev-platform-account-env:pi-0.87.1` built successfully and passed all ten
offline checks at source revision `99bf784`. It has not replaced the running
account environments: their earlier checks cover the image without Pi. The
runtime checker now requires Pi and will reject an older image. Do not recreate
an environment during an active login or worker session simply to satisfy this
check. Pi's native configuration uses the selected account's persistent home;
this does not import or convert Codex/Claude credentials. Canonical conversation
mounts, role resources and account-service launch integration remain necessary.

## Prepare and run

Docker Engine and Compose must be available. Preparation creates private host directories and opaque control tokens, preserving existing tokens on retry. It never copies provider credentials or edits the active OpenRig host registry.

```sh
python3 integrations/openrig/containers/prepare.py /absolute/private/account-environments
docker compose --env-file /absolute/private/account-environments/compose.env -f integrations/openrig/containers/compose.yaml config --quiet
docker compose --env-file /absolute/private/account-environments/compose.env -f integrations/openrig/containers/compose.yaml build
```

Start only `openai-alpha` and `openai-bravo` for the first simultaneous-account/recovery acceptance, then the two Anthropic services. Use `up -d SERVICE...` with the same Compose/env-file arguments. Containers use `unless-stopped`: Docker restores previously running environments when its engine returns, but intentionally stopped containers stay stopped. No automatic worker dispatch is configured. The daemon is foreground under Docker's init; no kernel agent is implicitly requested through `rig daemon start`.

Each service publishes container port 7433 to localhost ports 17433–17436, in this order: anthropic-alpha, anthropic-bravo, openai-alpha, openai-bravo. The OpenRig listener binds its container network interface; only its localhost host port is published. Each account has a separate Docker network. In OpenRig 0.5.14 the bearer token gates selected routes (including transport), not the whole API: ordinary rig reads and other control routes are not globally authenticated. Treat these as trusted local-user endpoints, not hardened remote API hosts. Do not publish the ports on all host interfaces.

## Runtime checks

```sh
python3 integrations/openrig/containers/check.py /absolute/private/account-environments openai-alpha openai-bravo
```

This checks actual containers, pinned versions, non-root execution, separate networks, declared mounts, localhost publication, health and transport rejection of missing/other-account tokens. It does not prove native login, worker startup, message delivery or resume.

For offline Pi component verification, build a separate candidate tag without
recreating the account environments, then run:

```sh
bin/ai-title-bundle > integrations/openrig/containers/naming-install.py
docker build -t dev-platform-account-env:pi-0.87.1 integrations/openrig/containers
python3 integrations/openrig/containers/check-pi-image.py dev-platform-account-env:pi-0.87.1
```

The checker exports committed HEAD, resolves the image to an immutable ID, and
runs the real role, history, session and PTY checks as the image's non-root user.
Its disposable containers have networking disabled, a read-only source mount and
temporary storage; they receive no account homes or control tokens and start no
OpenRig daemon. This checks Linux image compatibility and native fixture transcript recovery
across two containers using the same host bind mount. It verifies the same native
session ID, original messages, unchanged transcript bytes and rejection of a
different account binding. It does not verify authentication, account handover
or production launch. Shared writer locking is checked separately below.

Check the shared-conversation lock separately:

```sh
python3 integrations/openrig/containers/check-conversation-mount.py dev-platform-account-env:pi-0.87.1
```

This uses the committed launch primitive with two disposable containers mounting
one temporary host directory. It verifies concurrent-writer refusal, recovery
after SIGKILL, the same lock-file inode and unchanged existing fixture data.
It passed on this machine's Docker Desktop bind mounts. It uses the host user's
numeric UID/GID as the account environments do, without mounting their homes or
touching their processes. This verifies the lock boundary, not native transcript
recovery, distributed/network-filesystem locking or authenticated account handover.

## Native login and launch

Use Compose `exec` to enter the chosen running environment. For Codex, run `codex login --device-auth`; for Claude, start `claude` and complete its native `/login` flow. The human completes browser authentication. Never paste credentials into chat, the image, Git, or Compose configuration.

Verify native identity for each account before launching a Rig. No login is assumed from the service name. The persistent home holds `.codex`, `.claude`, `.openrig`, native session histories and tmux-related state. Control tokens live separately under that account's `secrets` directory. Processes use the host user's numeric UID/GID so private bind-mounted files remain writable without running as root.

Install the selected project checkout or worktree into each account's `workspace` directory, visible at `/workspace`. Do not mount all of the Mac home. A linked Git worktree whose common Git directory is outside this mount needs that directory explicitly accessible; prefer an independent checkout for initial acceptance. Different account workers must not write the same checkout.

`hosts.candidate.json` contains proposed HTTP hosts and bearer-file references, not secrets. After endpoints pass verification, register each with native `rig host add` using its `--id`, `--transport http`, `--url` and `--bearer-file`. Do not replace an existing hosts registry wholesale. Use explicit host IDs when sending messages or launching work.

## Filesystem/session integration still required

Record the environment host ID, project, actual host/container workspace mapping, native runtime and native session ID against the existing conversation. The persistent home is native software storage; the conversation index references it rather than copying transcripts into a second live store. Container paths such as `/workspace` are not host paths: discovery/resume must translate through an explicit environment binding. Use `ai-session scan --no-openclaw --environments-root /absolute/private/account-environments` to scan the persistent native homes. The index translates the two declared mount paths, retains container paths, reports unavailable homes honestly, and refuses host-native resume of these OpenRig-owned records. Actual host-targeted Rig resume and verified seat/occupant associations remain pending.

No automatic usage-based routing is implemented by this deployment. Accounts stay pinned; choose a host for new work and use a checkpointed handoff for changing execution environments. Pi must use these same account environments through the account service, while retaining its own role/session lifecycle. Host-level Assistant tools still need explicit capability integration.

## Acceptance before activation

- Build exact image and confirm CLI/runtime versions.
- Verify two simultaneous same-provider logins resolve to distinct expected accounts.
- Launch an appropriate one-seat Rig in each, then verify actual native identity and messages.
- Recreate a container using the same directories and verify history plus native resume.
- Register the host and verify host-targeted inventory, messaging and transcript reads.
- Bind real worker sessions into the existing conversation index with correct path mappings.
- Repeat for the other provider. Only then enable all four for Engineer.

Do not delete environment directories or credentials when stopping/recreating containers. Retain their history in the preservation/backup process. No old OpenClaw state is removed by this deployment.

## Shutdown and account readiness

The account service belongs to all agents/tools; these containers are one
execution backend. Pi remains host-native with real host filesystem context.
The shared entrypoint is `bin/ai-environment`, backed by
`lib/ai_ecosystem/environment_service.py`. It reuses native account probing from
`ai_ecosystem.accounts`; it does not create a token broker or another daemon.

```sh
bin/ai-environment --execution-kind container --root /absolute/private/account-environments status
bin/ai-environment --execution-kind container --root /absolute/private/account-environments choose codex
bin/ai-environment --execution-kind container --root /absolute/private/account-environments plan --client openrig --provider openai
```

Plans return JSON version 1, an explicit execution kind, readiness, capability
state, fresh quota evidence, and declared mounts. Exit 2 with `launch_allowed:
false` is a normal refusal; callers should retain work and show the reason.
An explicitly preferred unavailable account is never silently replaced. Native
identity enrollment is idempotent and refuses changed/duplicate bindings.
`enroll` records only identity fingerprints; credentials remain native.

Known exhausted accounts are excluded on every fresh selection. Missing usage
is unknown, not zero used. Only an explicit account plus
`--allow-unknown-quota` permits a plan with unknown quota. Claude's native auth
status does not expose usage. `plan --client pi` currently refuses launch and
reports `execution_kind: host` until the host-native Pi integration is verified;
there is no container fallback. A valid worker login does not prove Pi auth.

Readiness is a preflight, not a guarantee that the next provider request will
succeed. Consumers must stop on a runtime quota/auth failure, retain the native
session, then request a fresh plan for new work. Never automatically replay an
interrupted command or switch credentials underneath an existing conversation.
Consumer wiring, a live usage TUI, native interrupted-worker resume, and Pi
host-profile support remain separate acceptance items.

On this Mac, `com.dev-platform.docker-login.plist` is installed under
`~/Library/LaunchAgents/` and loaded as a one-shot login item. It opens Docker
Desktop at user login; it does not restart an already-running engine or supervise
agents. Containers have persistent host homes/workspaces and the live restart
policy was updated without recreating them. A Mac boot/login and real interrupted
worker recovery have not been tested. With FileVault, log in before user services
can return. Process/tmux memory is not persisted by Docker; native saved history
is. Manual stops remain stopped.

Compose also declares a 45-second stop grace period and daemon health checks.
Those two settings require container recreation and are not applied to the
currently running containers. Docker does not restart a merely unhealthy process
by itself. Report it as unavailable; do not add a competing watchdog that blindly
replays agent work. Keep recovery ownership with Docker for processes and the
native tool/conversation owner for work.
