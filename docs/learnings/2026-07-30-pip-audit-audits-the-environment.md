# pip-audit audits the installed environment, not this repo's manifest

ts: 2026-07-30T02:13:49Z
commit: b0c94db
session: C:\Users\hossa\.claude\projects\C--Users-hossa-dev\d0f958ca-7dbd-4976-ad7b-62ccc0f2aae9.jsonl
status: verified

fact: `dependency-audit` can fail on a package this repo does not depend on.
  `pip-audit` walks every distribution installed in the environment, which on a
  GitHub runner includes the image's own build tooling. `setuptools` reddened
  the job on 2026-07-20 and 2026-07-27 while appearing in **none** of the 37
  declared runtime/extra dependencies — it is only a PEP 517 build-backend
  requirement (`pyproject.toml:77`) plus whatever `actions/setup-python` ships.
  So grepping the manifest for a flagged package name and finding nothing does
  **not** mean the finding is spurious; and the fix may belong in the workflow
  (upgrade the ambient package before auditing) rather than in `pyproject.toml`,
  where pinning it would not change what pip-audit sees.

basis: |
  $ grep -n 'setuptools' pyproject.toml
    77:requires = ["setuptools>=61.0"]
    78:build-backend = "setuptools.build_meta"
    80:[tool.setuptools.packages.find]

  $ python -c "<parse project.dependencies + optional-dependencies>"
    runtime+extras deps naming setuptools: NONE
    total declared deps: 37

  The 2026-07-27 job log confirms the audited version came from the runner, not
  from us -- 79.0.1, which no file in this repo requests:
    setuptools 79.0.1  PYSEC-2026-3447  Fix Versions: 83.0.0
    Found 2 known vulnerabilities, ignored 1 in 1 package

re-verify: grep -n 'setuptools' pyproject.toml
