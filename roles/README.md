# Roles

A role is one markdown file: who the agent is here, what it owns, what it never does, and when
it stops. Everything else (proof rules, git rules, skills) comes from `AGENTS.md` and does not
belong in a role.

- **Personas** are long-lived assistants a person talks to: `engineer`, `assistant`, `ops`.
  Start one by telling your agent to read `roles/<name>.md` and `contexts/persona/`.
- **Seats** are positions in a team (`teams/`): `lead`, `reviewer`, `worker`, `moderator`,
  `participant`, `writer`. A team file names the role each seat reads.

To add a role, add `roles/<name>.md` with the four headings below and name it from a team or a
persona prompt. No code changes.

```markdown
# Reviewer
## You are
## You own
## You never
## You stop when
```
