# `go mod why` without `-m` cannot answer "is this module reachable?"

ts: 2026-07-30T02:13:37Z
commit: b0c94db
session: C:\Users\hossa\.claude\projects\C--Users-hossa-dev\d0f958ca-7dbd-4976-ad7b-62ccc0f2aae9.jsonl
status: refuted-assumption

fact: `go mod why <module-path>` answers a question about the **package** at
  that exact import path, not about the **module**. For `golang.org/x/text` it
  prints "main module does not need package golang.org/x/text" — which reads
  like "this module is unreachable, ignore the advisory" and is wrong. The
  reachable code lives in *subpackages*. `go mod why -m <module-path>` is the
  invocation that answers the module question, and it prints the real chain
  through `pgx`. Do not use the non-`-m` form to dismiss a vulnerability
  advisory against an indirect dependency.

basis: |
  $ cd intent-controller && go mod why golang.org/x/text
    # golang.org/x/text
    (main module does not need package golang.org/x/text)

  $ go mod why -m golang.org/x/text
    # golang.org/x/text
    github.com/precision-genomics/intent-controller/internal/store
    github.com/jackc/pgx/v5
    github.com/jackc/pgx/v5/pgconn
    golang.org/x/text/secure/precis

  $ go list -m golang.org/x/text
    golang.org/x/text v0.39.0

  Corroborated independently by govulncheck's call graph on the pre-bump tree,
  which reached a *different* subpackage again (unicode/norm, not secure/precis):
    internal/store/postgres.go:18:26: store.NewPostgres calls pgxpool.New,
    which eventually calls norm.Form.Properties

re-verify: cd intent-controller && go mod why -m golang.org/x/text
