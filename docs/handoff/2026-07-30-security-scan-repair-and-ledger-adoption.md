# Handoff — Security Scan repair + repo-record adoption

**Date:** 2026-07-30 (UTC; local evening of 2026-07-29).
**Newest commit this brief describes:** `b0c94db` ("ci: upgrade setuptools in
scan job for PYSEC-2026-3447") — HEAD, `0 0` ahead/behind `origin/main`, tree
otherwise clean apart from the untracked adoption files listed under Open/next.

Pick-up measures drift from `b0c94db`. Every state claim below carries its own
`re-verify:` line — run it, don't trust the tag. All re-verify lines here are
read-only.

## Current state

- **[built, verified]** The weekly `Security Scan` is **green again**, both
  previously-red jobs included. It had failed 2026-07-20 and 2026-07-27 with no
  code change in between (see the learnings entry on dated greens). Confirmed by
  an on-demand dispatch of the real workflow on `main` @ `b0c94db`, not by local
  reasoning: run `30507863914`, all four jobs `success`.
  `re-verify:` `gh run view 30507863914 --json conclusion,jobs -q '"\(.conclusion) | \(.jobs | map("\(.name)=\(.conclusion)") | join(" "))"'`

- **[built, verified]** `go-audit` fix — `golang.org/x/text` bumped
  `v0.29.0 → v0.39.0` (`7d6a36f`), clearing `GO-2026-5970` (infinite loop on
  invalid input), which was *reachable*: `internal/store/postgres.go:18` →
  `pgxpool.New` → `norm.Form.{Properties,Span,Transform}`. `go mod tidy` also
  carried `x/sync 0.17.0 → 0.21.0`. The `go` directive stayed `1.25.0`, so the
  ci.yml / Dockerfile Go-pin ripple that bit the July pgx bump did **not** apply
  — checked, not assumed. Locally proven non-vacuous: the same probe on the
  pre-bump `go.mod` returns exit 3 naming `GO-2026-5970`; post-bump, exit 0.
  `re-verify:` `cd intent-controller && GOTOOLCHAIN=go1.26.5 "$(go env GOPATH)/bin/govulncheck" ./...`
  → "No vulnerabilities found."

- **[built, verified]** `dependency-audit` fix — a
  `pip install -U "setuptools>=83.0.0"` step added to `security-scan.yml`
  ahead of the audit (`b0c94db`), clearing `PYSEC-2026-3447`. Chosen over a
  second `--ignore-vuln` so the gate stays strict; setuptools is not a declared
  dependency, so `pyproject.toml` was the wrong place to fix it.
  `re-verify:` `grep -n -A2 'Upgrade build-backend' .github/workflows/security-scan.yml`

- **[built, verified]** Local gates, re-run this session at `a777cca`:
  `python -m pytest` → 244 passed / 15 skipped; `go build ./... && go vet ./... &&
  go test ./...` → all packages ok.
  `re-verify:` `python -m pytest -q`

- **[built, verified]** GCP decommission of `prec-genomics-agent` still holds,
  18 days after the 2026-07-11 teardown, with **no drift**: Cloud SQL
  `precision-genomics-pg` STOPPED (activation policy `NEVER`), Redis 0 items,
  VPC connectors 0 items, the 3 Cloud Run services intentionally kept.
  Authoritative record: [`../GCP-DECOMMISSION-EVIDENCE-2026-07-10.md`](../GCP-DECOMMISSION-EVIDENCE-2026-07-10.md).
  `re-verify:` `gcloud sql instances list --project=prec-genomics-agent --format="table(name,settings.activationPolicy,state)"`

- **[built, this session]** Repo-record adoption — `AGENTS.md` as the canonical
  tool-neutral brief, `CLAUDE.md` reduced to an `@AGENTS.md` stub plus
  harness-only notes, and the `docs/learnings/` + `docs/handoff/` ledgers
  (pointer-only index + dated immutable entries). Forward-only: nothing before
  2026-07-30 was backfilled.
  `re-verify (repo-only, no external tooling):`
  `ls docs/learnings docs/handoff && head -1 CLAUDE.md` → both indexes plus 3
  dated entries; `CLAUDE.md` line 1 is `@AGENTS.md`.
  *(The ledger form gate is `check-learnings.mjs`, which ships with the
  verification toolkit checkout, not with this repo — it reported
  `learnings: clean (3 entries)` on 2026-07-30. Named as a dependency because a
  fresh clone cannot run it.)*

- **[open, external, permanent]** GCP **billing-console SKU confirmation** for
  the teardown window. Not a pending task: no BigQuery billing export exists on
  any accessible project, the Cloud Billing API has no cost-read endpoint, and
  enabling export now would not retroactively cover 2026-07-11. Only a one-time
  human console login can close it, and only going forward.

- **[open, permanent]** Gap #1's **blind-test oracle**. The precisionFDA
  challenge withheld the test labels, so `test_pro` / `test_rna` stay
  unscoreable and `evaluate('test')` skips with `applicable=False`. Not
  actionable without the organizers releasing labels.

- **[open, not started]** Gap #1 **provenance cross-check** — the train matrices
  came from a participant mirror, not the official precisionFDA/Synapse portal.
  Sample-namespace and key alignment corroborate, but spot-check cells against
  the official source before quoting F1 0.914 externally.

- **[open, not started]** Auto-deploy is gated on 4 GitHub secrets
  (`GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`,
  `PULUMI_ACCESS_TOKEN`). See [`../../DEPLOY.md`](../../DEPLOY.md). Note this is
  aimed at the project that was decommissioned — decide whether it still wants
  to exist before wiring secrets.

## Locked decisions

1. **Fix a vulnerability finding, don't suppress it** — unless there is nothing
   to upgrade to. Both repairs this session were version bumps. The one standing
   `--ignore-vuln` (`CVE-2025-69872`, diskcache via dspy-ai) is justified in a
   comment *in the workflow* because no fixed release exists; it is reviewed,
   not inherited.
2. **The build-backend upgrade lives in the workflow, not `pyproject.toml`.**
   `pip-audit` audits the installed environment; pinning setuptools in the
   manifest would not change what it sees on the runner.
3. **`AGENTS.md` is canonical, `CLAUDE.md` is a stub that imports it.** Reason:
   identical content in two files drifts. Probe-verified that this harness does
   not load `AGENTS.md` natively, so the stub is required.
4. **Ledger adoption is forward-only.** The two pre-existing briefs
   (`docs/LIVE-RUN-DECOMMISSION-HANDOFF.md`,
   `docs/SECURITY-SCAN-PGX-FIX-HANDOFF.md`) are **not** migrated into
   `docs/handoff/`; they stay put, already banner-marked SUPERSEDED / RESOLVED,
   and the index carries one pointer to them. Reason: backfilling a record
   invents anchors that were never captured.
5. **Entries are immutable.** A wrong entry is superseded by a new dated entry
   with a `kills:` reference — never edited in place.

## Reuse map

- **The scan itself:** `.github/workflows/security-scan.yml` — 4 jobs
  (`dependency-audit`, `sast`, `go-audit`, `secret-detection`), weekly Monday
  06:00 UTC plus `workflow_dispatch`. `go-audit` deliberately uses
  `go-version: stable` (not ci.yml's pin) so govulncheck builds against a
  patched stdlib.
- **Go pin locations** (all three must agree on any floor bump):
  `intent-controller/go.mod`, `.github/workflows/ci.yml:94`,
  `intent-controller/Dockerfile:1`. All currently `1.25`.
- **Local vuln tooling:** `$(go env GOPATH)/bin/govulncheck`, run under
  `GOTOOLCHAIN=go1.26.5` or newer — local Go 1.26.0 emits 12 already-patched
  stdlib findings that CI does not see.
- **Prior briefs, kept for provenance of earlier reasoning** (do not act on
  their "NOT done" markers — both were resolved):
  [`../SECURITY-SCAN-PGX-FIX-HANDOFF.md`](../SECURITY-SCAN-PGX-FIX-HANDOFF.md),
  [`../LIVE-RUN-DECOMMISSION-HANDOFF.md`](../LIVE-RUN-DECOMMISSION-HANDOFF.md).
- **Sibling that consumes this repo read-only:**
  `../passed-vs-true-demo` ingests `docs/TRANSFER_VALIDATION_RUN.md` and
  `docs/GAP_AUDIT.md`, pinned by both SHA and sha256 content hash. **Editing
  either doc breaks that repo's build until it re-pins** — deliberate, and its
  invariant, not a defect here.

## Invariants

- Never report a synthetic number, or the train-partition F1 0.914, as blind
  real-world performance.
- A `go.mod` floor bump must be matched in ci.yml and the Dockerfile.
- Believe a Go vulnerability verdict only from a patched toolchain.
- Every green on `Security Scan` is **dated**. It is a scheduled gate reading a
  moving advisory database; re-read its history before repeating the claim.
- Agents don't write git history here — hand the operator the commands.

## Open / next

1. **Commit the adoption.** These files are untracked, and an untracked ledger
   makes the gate's append-only leg vacuously green — the immutability check
   compares against `HEAD`, and untracked files are invisible to it. Until it is
   committed, the adoption exists only in one working tree:
   `AGENTS.md`, `CLAUDE.md` (modified), `docs/learnings/` (4 files),
   `docs/handoff/` (2 files).
2. **Watch the next scheduled scan** (Monday 06:00 UTC). This gate has failed
   roughly weekly since March 2026; two consecutive greens is the first evidence
   that the watching, not just the patching, is working.
3. Optional, cheap: decide whether `DEPLOY.md`'s auto-deploy path should exist
   at all now that the GCP project is torn down. Leaving it documented as live
   is the kind of stale-doc claim this repo's own audit exists to prevent.
