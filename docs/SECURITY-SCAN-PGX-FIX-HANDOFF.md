# Handoff — Security-scan CI fix (pgx GO-2026-5004): bump applied+verified, Go-floor ripple NOT done

**Date:** 2026-07-09. **Base:** branch `fix/pgx-GO-2026-5004` off `main` **`a3ff359`**
("docs: handoff for live run + GCP decommission"). **Nothing is committed on the branch** —
pick-up measures drift from `a3ff359` plus the uncommitted working tree described below.

**One line:** Monday's weekly security scan (run `28775687386`) failed on one reachable Go vuln
(`GO-2026-5004` in `jackc/pgx/v5`). The pgx bump that fixes it is applied and verified, but it
raised the module's Go floor to 1.25 — and two build configs still pin Go 1.22, which the fix must
also update. Those two edits were **paused before application** at the operator's request.

## Current state

- **[built + verified]** pgx bumped `v5.7.2 -> v5.9.2` in `intent-controller/go.mod` (+ `go.sum` via
  `go mod tidy`; also pulled minor transitive bumps: testify, x/sync, x/text). This fixes the CALLED
  vuln `GO-2026-5004` (the only thing that failed Monday: job `go-audit` step `govulncheck`, exit 3).
  The call site (`internal/store/workflow_repo.go:144`) already uses a parameterized query — the flaw
  was internal to the driver, so this is a version bump, no code change. `go build ./...` passes.
  `re-verify:` `cd ~/dev/upstream-label-correction/intent-controller && grep 'jackc/pgx/v5 ' go.mod`
  -> `v5.9.2`; `go build ./...` -> clean.
  `re-verify (gate clean on a PATCHED toolchain = what CI's ` + "`stable`" + ` uses):`
  `GOTOOLCHAIN=go1.26.5 "$(go env GOPATH)/bin/govulncheck" ./...` -> **exit 0, "No vulnerabilities found."**

- **[known artifact — NOT a real failure]** Plain `govulncheck ./...` on this machine reports **12
  stdlib vulnerabilities**. Cause: local Go is **1.26.0** (outdated) — every finding is "Found in
  go1.26 / Fixed in go1.26.1-1.26.5". CI's `security-scan.yml:72` uses `go-version: stable` (a
  patched toolchain), so these do **not** fail CI. Do not chase them.
  `re-verify (it's a local-toolchain artifact):` `go version` -> `1.26.0`; the `GOTOOLCHAIN=go1.26.5`
  run above -> 0 vulns.

- **[NOT done — REQUIRED before this fix is mergeable]** pgx v5.9.2 forced `go.mod` `go 1.22 -> 1.25.0`.
  Two places still pin 1.22 and WILL break (a module requiring 1.25 cannot build under 1.22):
  - `.github/workflows/ci.yml:94` -> `go-version: "1.22"` (the `go-build` job) — change to `"1.25"`.
  - `intent-controller/Dockerfile:1` -> `FROM golang:1.22-alpine AS builder` — change to
    `golang:1.25-alpine` (`ci.yml:82` docker-builds this image too).
  `security-scan.yml:72` already uses `stable` — leave it.
  `re-verify (still pinned):` `grep -n 'go-version: "1.22"' .github/workflows/ci.yml` and
  `grep -n 'golang:1.22' intent-controller/Dockerfile` -> both still present.

- **[not started]** Commit / PR. Nothing committed on the branch.

## Locked decisions

1. **Fix = bump pgx to v5.9.2, not suppress the finding.** Reason: `GO-2026-5004` is fixed-in v5.9.2
   (per govulncheck); no lower version fixes it, and the call site is already parameterized -> low-risk
   driver-internal fix.
2. **The 12 stdlib vulns are NOT fixed here.** Reason: local-toolchain artifact; CI's `stable` is
   already patched. Fixing them would be solving a non-problem.
3. **ci.yml + Dockerfile must move off Go 1.22 (to >=1.25).** Reason: forced by the go.mod floor bump;
   skipping it trades a red `security-scan` for a red `go-build`.

## Reuse map

- Monday's failing run: `gh run view 28775687386 --log-failed` (job `go-audit`/`govulncheck`, exit 3).
- `.github/workflows/security-scan.yml` (the scan; `stable` toolchain, with a comment explaining the
  choice), `.github/workflows/ci.yml` `go-build` job (line 84+), `intent-controller/Dockerfile`.
- Local govulncheck binary: `C:\Users\hossa\go\bin\govulncheck` (installed this session).
- CLAUDE.md Commands: `cd intent-controller && go build ./... && go vet ./... && go test ./...`
  (integration behind `-tags=integration` + `DATABASE_URL`).

## Invariants

- **Verify the gate on a PATCHED toolchain, not local Go.** Local 1.26.0 shows false stdlib vulns;
  CI uses `stable`. Reproduce with `GOTOOLCHAIN=go1.26.5` (or newer) before believing red/green.
- **A dep bump that raises the go.mod floor must be matched everywhere Go is pinned** (ci.yml,
  Dockerfile) or a different CI job breaks. Grep all pins:
  `grep -rnE 'go-version:|golang:1\.' .github/workflows/ intent-controller/Dockerfile`.
- **Chronic-red context:** this scan has failed ~weekly since March 2026 (only 2026-06-22 passed).
  Green needs the pins fixed AND someone watching future failures, or it silently rots again.
- **Git:** hand over the commit; do not commit. **8 UNRELATED files are already dirty on `main`**
  (`docs/*`, `infra-ts/index.ts`, `web/*`) and carried onto this branch — do NOT stage them. Stage
  ONLY `intent-controller/go.mod`, `intent-controller/go.sum`, `.github/workflows/ci.yml`,
  `intent-controller/Dockerfile`.

## Open / next

**Finish the two Go-floor edits, then verify, then hand over the commit.**
1. Apply: `ci.yml:94` -> `go-version: "1.25"`; `intent-controller/Dockerfile:1` -> `golang:1.25-alpine`.
2. Verify: `cd intent-controller && go build ./...` (clean); if docker is available,
   `docker build -f intent-controller/Dockerfile intent-controller/` succeeds on golang:1.25-alpine
   (NOT verified locally this session — flag it). Then `GOTOOLCHAIN=go1.26.5 govulncheck ./...` -> 0 vulns.
3. Hand over commit on branch `fix/pgx-GO-2026-5004`, staging ONLY the four files above, e.g.:
   `fix(security): bump pgx to v5.9.2 (GO-2026-5004); raise Go floor to 1.25 in ci + Dockerfile`
   -> push -> open PR.

**Blocker:** none technical. Note: the `intent-controller` is slated for GCP teardown (see
`docs/LIVE-RUN-DECOMMISSION-HANDOFF.md`), but `main`/the repo live on (the demo consumes CLUE's
artifacts; there's a released PyPI port), so the scan fix still matters.
