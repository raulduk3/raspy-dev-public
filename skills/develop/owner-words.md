# The owner's words: one meaning for each word

This list applies to the owner's prompts in all projects, on all machines and in all agents. A project can add words in its own instructions. A project cannot change a meaning in this list.

## Ask first

If a prompt names no object or no end state, and the conversation does not supply them, ask one short question before you act. Short answers to your last question are complete prompts.

- A short answer is, for example, "Continue", "Yes", "Do it" or "Done". It answers your last question or your last proposal. Do what you proposed.
- A vague verb with no object or no end state needs the question. The vague verbs are: make, do, get, ensure, make sure, improve, polish, fix (with no symptom), harden, stabilize, integrate, align, look at, assess, clean up, finalize, handle, work on, provide (with no destination).
- Ask one question only. Give your best guess as the first answer, so that the owner can say "yes".
- Do not ask when the repository, the task or the conversation already gives the object and the end state.

## Words

Status `PROPOSED`: the owner did not decide this meaning. Use it, but if a different meaning is possible in the conversation, ask one question first. Status `DECIDED`: use this meaning.

| Word | Status | Meaning |
| --- | --- | --- |
| push | PROPOSED | `git push` of the current branch to its remote. It does not mean "deploy" or "make it live". If the tier of the repository does not allow the push, say so and stop. |
| ship | PROPOSED | Make the work available to the users of the project. Ask "staging or production?" if the project has both. |
| deploy | PROPOSED | Install a built version on a named environment. With no environment named, deploy to staging. Never deploy to production without a decision from the owner in this conversation. |
| live | PROPOSED | Production: the environment that real users see. "Make it live" means deploy to production. Ask before you do it. |
| save | PROPOSED | Make a save point: record where the work is (a checkpoint page and the handoff), and keep a copy of every unpushed ref and every uncommitted change in a second place. Do not push or deploy. A project can give the steps in its own memory or documents. |
| land | PROPOSED | Land the goal branch as the tier of the repository says (`dev-loop land`, `docs/source-control.md`). At tier 2, the owner lands. |
| fold | PROPOSED | Add one squash commit for one finished task to the goal branch (`dev-loop fold`, `docs/source-control.md`). |
| continue | PROPOSED | Do the next step of the current plan, or the step that you proposed last. Do not start a new task. |
| do it | PROPOSED | Do the action that you proposed last, as you proposed it. |
| clean up | PROPOSED | Remove what this work made and does not need: temporary files, merged branches, old worktrees. Do not change code behavior. Do not delete the work of another session. |
| finalize | PROPOSED | Make the work ready for the owner to land or merge: the full check passes, the commits are made and the report is written. Do not land, merge or deploy. |
