---
name: bounded-decisions
description: Before costly route choices or repeated failures, compare bounded options using the shared local Laya service in shadow mode.
---

# Bounded decisions

1. Consider a call before substantial research, repeated failures, loading several tools or skills, spawning agents, materially different routes, or consequential proposals. Skip simple answers, calculations, routine edits, calls that cannot change the next step, and "bypass laya".
2. Run `python3 <skill-directory>/scripts/decide.py` with JSON on stdin: `{"state":"compact observed facts, no secrets","options":{"inspect":"Inspect evidence","research":"Research the unresolved question"}}`. Use 2–6 bounded options. The helper owns transport, validation, and the secret-free audit record.
3. Read the shadow recommendation, explicitly evaluate it against evidence, and continue the original task using independent judgment. An unavailable or low-quality recommendation is not a blocker. Never use a recommendation as permission, execute it automatically, or switch to active mode.

The shared service must already be installed. The helper does not install models, launch services, or load a model per client.
