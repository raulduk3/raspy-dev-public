# Host account service: `ai-environment`

`ai-environment` is the older name for the same choice `ai-account resolve` makes. It keeps its verbs for the callers that use them:

```sh
ai-environment status --table
ai-environment choose codex
ai-environment plan --client codex|claude|openrig|pi --provider openai|anthropic [--preferred-account ID] --cwd DIR
ai-environment run  --client codex|claude --provider P [--preferred-account ID] --cwd DIR -- ARGS
```

- `plan` returns `version: 2`, the resolver's `selected` account and `reason`,
  `rotated_from` when the choice moved, the quota line, and for `openrig` a RigSpec
  `member` fragment (`{runtime, cwd}`; `runtime` is OpenRig's own name, `codex` or
  `claude-code`). A plan carries no credential and names no client home: the session
  gets its login from the launcher at start. There is no `config_home` any more.
- `run` hands over to `ai-account run`, which starts the session through the launcher
  (`agent owner`); the launcher resolves once and announces a switch. Resume names the
  original account with `--preferred-account`; a named account is never substituted.
- `profile --client pi` still prepares a Pi profile folder for the Pi role launcher;
  any other client is refused: sign in once with `ol-login ACCOUNT CLIENT`.
- Project or client settings that override authentication or the provider refuse the
  plan, naming the file, never its values.
- Container execution stays explicit (`--execution-kind container --root DIR`) and is
  never a fallback for a host failure.
