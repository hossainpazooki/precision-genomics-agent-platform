# upstream-label-correction (CLUE)

**CLUE — Closed-Loop Upstream Error-correction.** An agentic loop that generates
fidelity-verified synthetic multi-omics cohorts to measure — and improve —
label-error detection at corruption rates real data can't probe. Built on the
precisionFDA NCI-CPTAC Multi-omics Sample Mislabeling Correction Challenge.

Authoritative docs to read first: [`README.md`](README.md), then
[`docs/GAP_AUDIT.md`](docs/GAP_AUDIT.md) (the per-finding integrity record).
Empirical claims in this repo must be recomputed from the raw source and
survive a refutation attempt before they are written down — the whole point of
the project is measuring a detector against ground truth, so a number restated
from memory defeats it.

<!-- rigor:generated -->

## Structure (polyglot)

- **`intent-controller/` (Go)** — the intent lifecycle + workflow engine. It is
  the **single authority for `ACHIEVED`**: `verify()` runs each `IntentSpec` eval
  criterion via the ML service and gates on the aggregate. Multi-replica-safe
  (Postgres `FOR UPDATE SKIP LOCKED` lease).
- **`core/` + `evals/` + `clue/` (Python)** — the ML engine
  (`SyntheticCohortGenerator`, cross-omics detector), the eval stack, and the
  closed loop (`CLUELoop`).
- **`ml_service/` (FastAPI)** — `/ml/evaluate` routes `eval_name` → the matching
  eval runner; this is the controller↔ML seam.
- **`web/` (Next.js)** + **`infra-ts/` (Pulumi)** — dashboard/MCP and GCP IaC.
- **`docs/learnings/` + `docs/handoff/`** — the repo's own record. Each is a
  pointer-only index plus dated, immutable entry files; entries are appended,
  never edited, and a wrong one is superseded by a new entry carrying a
  `kills:` reference. Adopted 2026-07-30, forward-only: nothing before that
  date is backfilled, and the two pre-existing briefs at `docs/*-HANDOFF.md`
  stay where they are (both already carry SUPERSEDED / RESOLVED banners).

## How it's operated

```
cd intent-controller && go build ./... && go vet ./... && go test ./...
python -m pytest
python -m ruff check <paths> && python -m ruff format --check <paths>
```

- Go integration tests are behind `-tags=integration` and need Postgres via
  `DATABASE_URL`.
- CI's `lint` job runs **both** ruff commands — a passing `ruff check` does
  **not** catch formatting drift, so always run `--check` too before handing
  over a commit. (This caused 3 red CI runs.)
- **`Security Scan` is a scheduled weekly gate, and a dated one.** It can go
  red with no commit in between, because `govulncheck` and `pip-audit` query
  advisory databases that move under a frozen tree. Read its run history
  before repeating any "the scan is green" claim; re-run on demand with
  `gh workflow run "Security Scan" --ref main`. See
  [`docs/learnings/2026-07-30-security-scan-is-a-time-varying-gate.md`](docs/learnings/2026-07-30-security-scan-is-a-time-varying-gate.md).

## Security / integrity model

The verification gate has been hardened across an 8-finding audit (read through
the [`correct-shaped-lies`](../correct-shaped-lies) red-team lens: a producer
that clears every evaluator yet is dishonest). It is now **server-authoritative**:
authenticated control plane (`X-Service-Token`), server-pinned cohort params (no
caller seed-shopping), a dual decorrelated fidelity detector, and a Go-side
consistency check that won't trust a self-inconsistent `passed`.
[`docs/GAP_AUDIT.md`](docs/GAP_AUDIT.md) is the authoritative per-finding record.

## Invariants

- **Determinism is hard.** All randomness flows through a seeded `PCG64` stream
  (generator) or `RandomState(42)` (detector). Global `np.random` use breaks
  byte-identical reproduction.
- **Never report a synthetic number, or the train-partition F1 0.914, as blind
  real-world performance.** The synthetic gate validates self-consistency, not
  real-world transfer. Gap #1's independent oracle is what closes that, and it
  is closed **for the TRAIN partition only**: the real precisionFDA training
  matrices (public `ACHG2018/fda-mislabeling-challenge` mirror) live in
  gitignored `data/raw/`, so `evals/transfer_validation.py('train')` runs for
  real and scores F1 0.914 against the challenge organizers' own key. The
  **blind test oracle stays gated** (the challenge withheld test labels), so
  `evaluate('test')` skips gracefully. See `data/raw/README.md` and
  [`docs/TRANSFER_VALIDATION_RUN.md`](docs/TRANSFER_VALIDATION_RUN.md) (Run 3).
- **CPTAC-derived data never enters git history** — `data/raw/` is gitignored
  (`*.tsv` / `*.csv` / `*.json`).
- **`all_passed()` authority stays in the Go controller.** Evaluators stay in
  Python behind `/ml/evaluate`; don't move the gate decision into Python.
- **Agents don't write git history here** — the commit commands are handed to
  the operator, who runs them.
- **A dependency bump that raises the `go.mod` floor must be matched everywhere
  Go is pinned** (`.github/workflows/ci.yml`, `intent-controller/Dockerfile`)
  or a different CI job breaks. Grep all pins:
  `grep -rnE 'go-version:|golang:1\.' .github/workflows/ intent-controller/Dockerfile`.
- **Verify a Go vulnerability gate on a PATCHED toolchain, not local Go.** An
  outdated local toolchain reports already-fixed stdlib vulns that CI's
  `stable` does not; reproduce CI with `GOTOOLCHAIN=go1.26.5` (or newer) before
  believing red or green.

## Platform notes

**Windows-local** is cp1252 + CRLF: keep `print()` / stdout ASCII, and run
`gofmt -w` only on files you changed (it flags untouched files for CRLF alone).

<!-- /rigor:generated -->
