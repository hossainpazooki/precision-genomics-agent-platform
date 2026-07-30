# Learnings index

Pointers only — never evidence. Each row points at a dated, immutable entry
carrying its own `ts` / `commit` / `session` / `status` / `fact` / `basis` /
`re-verify` fields. A wrong entry is never edited: a new dated entry is
appended with a `kills:` reference to the one it refutes.

Adopted 2026-07-30, forward-only — findings from before that date are not
backfilled here. Prior durable gotchas live in [`../../CLAUDE.md`](../../CLAUDE.md)
(now `AGENTS.md`) and [`../GAP_AUDIT.md`](../GAP_AUDIT.md).

| Entry | Status | Hook |
|---|---|---|
| [2026-07-30-security-scan-is-a-time-varying-gate.md](2026-07-30-security-scan-is-a-time-varying-gate.md) | verified | The weekly scan went red twice with zero commits in between — advisory databases move under a frozen tree, so every green is dated. |
| [2026-07-30-go-mod-why-needs-m-for-module-reachability.md](2026-07-30-go-mod-why-needs-m-for-module-reachability.md) | refuted-assumption | `go mod why x/text` says "does not need package" while the module is reached through pgx — only `go mod why -m` answers the module question. |
| [2026-07-30-pip-audit-audits-the-environment.md](2026-07-30-pip-audit-audits-the-environment.md) | verified | `dependency-audit` failed on setuptools, which is in none of the 37 declared deps — pip-audit walks the installed environment, not this manifest. |
