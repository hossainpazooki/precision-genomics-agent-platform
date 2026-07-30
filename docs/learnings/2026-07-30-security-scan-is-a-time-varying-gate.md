# Security Scan is a time-varying gate — green does not stay green

ts: 2026-07-30T02:12:53Z
commit: b0c94db
session: C:\Users\hossa\.claude\projects\C--Users-hossa-dev\d0f958ca-7dbd-4976-ad7b-62ccc0f2aae9.jsonl
status: verified

fact: The weekly `Security Scan` workflow can go from green to red with **zero
  commits in between**, because `govulncheck` and `pip-audit` are queried
  against advisory databases that change under a frozen tree. It passed
  2026-07-13, then failed 2026-07-20 and 2026-07-27 — and the only two commits
  in that window (`7d6a36f`, `b0c94db`) are the *repair*, pushed after the
  second failure. A "we fixed the security scan" claim therefore has a
  shelf life measured in weeks, not a permanent status. Treat every green as
  dated, and read the scan's own history before repeating the claim.

basis: |
  $ gh run view 29239220454 --json conclusion,createdAt,displayTitle
    2026-07-13T09:28:12Z Security Scan -> success
  $ gh run view 29730689852 --json conclusion,createdAt,displayTitle
    2026-07-20T09:14:42Z Security Scan -> failure
  $ gh run view 30255763501 --json conclusion,createdAt,displayTitle
    2026-07-27T09:52:40Z Security Scan -> failure

  Tree was frozen across the whole window: HEAD was a777cca (2026-07-14) for
  both failures. Per-job breakdown shows the two failures are NOT the same
  failure -- the red surface grew while the tree stood still:
    2026-07-20  dependency-audit FAIL · go-audit ok
    2026-07-27  dependency-audit FAIL · go-audit FAIL  (GO-2026-5970 published
                in that window, in an already-present x/text v0.29.0)

  This is the same rot the 2026-07-09 pgx handoff predicted in its own
  invariants: "green needs the pins fixed AND someone watching future
  failures, or it silently rots again." It rotted in 7 days.

re-verify: gh run list --workflow="Security Scan" --json conclusion,createdAt,databaseId
