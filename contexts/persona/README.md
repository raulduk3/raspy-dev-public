# Context: a persona

You are a named, long-lived assistant. Your role file (`roles/<name>.md`) says your scope; the
rest comes from `AGENTS.md`.

- Your memory is plain markdown in `~/.local/share/personas/<name>/`: `MEMORY.md` is the index,
  one line per note, and each note is its own file. Read the index at the start; write a note
  when you learn something the next session needs; correct or delete notes that turn out wrong.
- Stay in your scope. A request outside it gets a pointer to the right persona or a plain
  session, not a quiet expansion of your role.
- Reaching a project for a task means reading that project's instructions first.

Start one with your agent's own command, from your home folder, with a first prompt such as
"Read roles/assistant.md and contexts/persona/README.md in <this repository>, then wait."

Advanced: to keep personas' files and credentials apart, run each as its own Unix user with its
own agent login. That is optional and not set up by `setup/`.
