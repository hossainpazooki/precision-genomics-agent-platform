# Handoff — Live run + GCP decommission of upstream-label-correction (probe deferred)

**Date:** 2026-07-09. **Newest commit this brief leans on:** `passed-vs-true-demo` origin/main
`91ebb13` (the demo that consumes CLUE's recorded artifacts is done + pushed). This handoff
file is itself **untracked** in `upstream-label-correction` until committed — pick-up measures
drift from the live GCP state and from `91ebb13`, not from this file.

Context in one line: the `passed-vs-true-demo` v1 is built, gate-green, and pushed. The next
event is a **one-off live run of the GCP-hosted CLUE closed loop, captured as dated evidence,
followed by tearing the GCP hosting down to stop ~$270–400/mo of spend.** The read-only
pre-flight probe was deliberately **left for tomorrow** — nothing has been probed, run, or
deleted yet.

## Current state

- **[built, verified]** `passed-vs-true-demo` v1 — the "passed != true" replay site. All 17 plan
  tasks implemented, reviewed, whole-branch-reviewed (Opus), pushed to `origin/main`.
  `re-verify:` `cd ~/dev/passed-vs-true-demo && git rev-list --left-right --count origin/main...HEAD` -> `0	0`;
  `git log --oneline -1 origin/main` -> `91ebb13`.
  `re-verify (gate):` `cd ~/dev/passed-vs-true-demo && npm run ingest && npm test && npm run build`
  -> "Ingest OK: 180 episodes, cross-check passed, F1=0.9143, 8 gap findings", 31 tests pass,
  Exporting (2/2); then `grep -c 0.9143 out/index.html` -> `3`.

- **[planned, not started]** Vercel deploy of the demo. Instructions given, NOT executed. The
  Build Command MUST be overridden to `next build` (the default `npm run build` fires
  `prebuild -> npm run ingest`, which reads the two sibling repos that are ABSENT on Vercel's
  builder -> ingest exits 1 -> build fails). The committed `public/data/*.json` is the snapshot
  the cloud build serves.
  `re-verify (the gotcha is real):` `cd ~/dev/passed-vs-true-demo && grep -A3 '"prebuild"' package.json`
  -> prebuild runs ingest; `grep -nE '\.\./(correct-shaped-lies|upstream-label-correction)' scripts/ingest.ts`
  -> ingest reads both siblings by relative path.

- **[planned, not started]** Live run + GCP decommission of THIS repo (project
  `prec-genomics-agent`, us-central1). Grounded read-only inventory done 2026-07-08; the
  **pre-flight probe is DEFERRED** ("leave the probe for tomorrow"). No live run executed,
  nothing torn down.
  `re-verify (resources still up):` `gcloud run services list --project=prec-genomics-agent`
  -> 3 services `precision-genomics-{api,mcp-sse,worker}` (deployed 2026-03-13);
  `gcloud sql instances list --project=prec-genomics-agent` -> `precision-genomics-pg`
  (`db-custom-2-8192`, RUNNABLE).

## Locked decisions

1. **Demo is replay-with-provenance, NOT live execution.** Reason: F1 0.9143 is a fixed offline
   eval against a fixed key — a live re-run yields the SAME number and forfeits commit-provenance
   + reproducibility, which are the demo's entire trust basis.
2. **For the headline number, live GCP is NOT used.** Live GCP CLUE is useful ONLY as an external
   "go see the real system" link/CTA — never to recompute the F1. Reason: same number, and a live
   call breaks the read-only-boundary + provenance invariants.
3. **"true run" framing is wrong; corrected to "replays the real recorded results ... does not
   execute a live run."** Reason: implemented-vs-planned honesty — the demo must not overclaim
   about itself (that IS its thesis).
4. **Vercel build command = `next build`, not `npm run build`.** Reason: skips the
   sibling-dependent prebuild ingest; uses committed `public/data`. (Same trick as demo plan
   Task 1's `npx next build`.)
5. **Provenance fix landed in the demo:** `HonestyLedger` F1 and `LiveEpisodeRunner` SHA are now
   interpolated from the bundle, not hand-typed. Reason: closes the one provenance-invariant
   breach the whole-branch review found. `re-verify:` `cd ~/dev/passed-vs-true-demo && grep -n
   'transferValidation.f1.toFixed\|generatedFrom.csl' components/HonestyLedger.tsx components/LiveEpisodeRunner.tsx`.

## Decisions NOT yet made — do NOT treat as locked; resolve before any destructive step

- **What the "live run" exercises:** a genuine closed-loop intent run (DECLARED->...->ACHIEVED
  under the real `all_passed()` gate) vs. a recorded tour of the live API. PENDING the probe —
  the `intent` service is NOT in the live list, so the closed loop may not be reachable as-is.
- **Database:** export-before-delete (recommended) vs. delete outright vs. **stop** the instance
  (halts compute billing, keeps data at ~$1–2/mo).
- **Teardown depth / mechanism:** keep `infra-ts/` IaC + Artifact Registry images for redeploy
  (recommended) vs. full nuke; and `pulumi destroy` vs. targeted `gcloud ... delete` — unresolved
  until the probe maps stack<->reality (see DRIFT invariant).

## Reuse map

- `DEPLOY.md` — architecture, services, backing services (Cloud SQL, Memorystore Redis, VPC
  connector, 3 GCS buckets, Artifact Registry, Secret Manager). WARNING: it documents
  `web/intent/ml/mcp`; live is `api/mcp-sse/worker` (drift — see invariants).
- `docs/COST_PROJECTION.md` — cost model (~$270–325/mo baseline; note the live DB is bigger than
  the doc's `f1-micro` assumption: `db-custom-2-8192` ~$100–130/mo).
- `infra-ts/` (Pulumi `dev` stack, `Pulumi.dev.yaml`) — the IaC to destroy/redeploy from.
- `passed-vs-true-demo/docs/HANDOFF.md` — the demo's own built-state handoff.
- `passed-vs-true-demo/.git/sdd/progress.md` — the 17-task build ledger (local, inside .git).

## Invariants

- **Capture BEFORE teardown.** The run is irreproducible once GCP is down. Record the deployed
  identity FIRST — each service's image digest + revision + the git SHA it was built from — then
  the run evidence (request/response, timestamps, a screen recording).
- **verify-effect on teardown, not the delete's exit code.** After teardown, re-run the inventory
  (0 Cloud Run, SQL gone, Redis gone, connector gone) AND confirm the recurring billing SKUs drop
  to zero. "Deleted" != "no longer billed" until proven.
- **Refute the "live" claim.** Vary an input; confirm the output is COMPUTED, not canned/replayed —
  else it is not a live run and we do not call it one.
- **implemented-vs-planned after teardown.** Once decommissioned, the demo must say "live run
  captured 2026-07-09 against revision X; system since decommissioned to cut cost" — NEVER "runs
  live now." A live-now claim about a deleted system is the exact failure this whole thread guards
  against.
- **DRIFT:** running services (`api/mcp-sse/worker`, 2026-03-13) != current `infra-ts` stack
  (`web/intent/ml/mcp`). `pulumi destroy` may not map to what is actually running — verify teardown
  against the live `gcloud` inventory, not the stack's success message.
- **Demo's five invariants still hold** (read-only boundary; provenance mandatory; cross-check
  gates build; honesty tags verbatim; live never fabricates). `re-verify:` the gate command above.
- **Git:** hand over commit commands; do not commit. (The demo is already pushed; this handoff and
  any decommission artifacts are hand-over.)

## Open / next

**First thing next session (2026-07-09): run the DEFERRED read-only pre-flight probe.**
1. Health-probe `precision-genomics-api` + `-worker` (curl their URLs) to learn what they expose
   and whether the closed-loop / intent flow is reachable -> settles "what does the live run
   exercise".
2. Enumerate the FULL cost-bearing set for the teardown checklist (all `--project=prec-genomics-agent`):
   `gcloud redis instances list --region=us-central1`,
   `gcloud compute networks vpc-access connectors list --region=us-central1`,
   `gcloud storage buckets list`, `gcloud secrets list`, `gcloud sql instances list`.
3. Pin real current spend (billing / SKU console).

**Blocker:** the three not-yet-made decisions above need the operator's call before any delete;
and the drift means the teardown mechanism stays unresolved until the probe maps stack<->reality.
Nothing destructive runs until those are settled.
