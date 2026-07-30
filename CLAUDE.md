@AGENTS.md

## Claude Code notes

Global working rules (file-op style, git default, adversarial verification,
workflow discipline, shared agents) load from `~/.claude/` — they are not
repeated here or in `AGENTS.md`.

- **`AGENTS.md` is the single canonical brief** for this repo; this file is a
  thin stub that imports it. This harness does not load `AGENTS.md` natively,
  so the stub is required, not decorative. Put Claude-Code-only notes here;
  everything tool-neutral belongs in `AGENTS.md`. Never duplicate content
  across the two — they drift.
- The structure/commands/invariants section of `AGENTS.md` is delimited by
  `<!-- rigor:generated -->` markers. Refresh inside the markers; leave
  anything outside them alone.
- **Git:** the operator owns history. Hand over paste-ready commands — one
  `git add` per line, ASCII single-line conventional-commit message, no
  attribution trailer — rather than running `git commit` / `git push`.
- `docs/handoff/HANDOFF.md` is the entry point for a cold session; read it
  before `docs/learnings/LEARNINGS.md`, and verify a brief's claims rather
  than trusting them (every entry carries its own `re-verify:` line).
