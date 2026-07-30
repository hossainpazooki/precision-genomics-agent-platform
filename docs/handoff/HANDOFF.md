# Handoff index

Pointers only — never evidence. Each row points at a dated, immutable brief.
The newest row is the one to read first; a brief is a batch of claims whose
author is gone, so verify its `re-verify:` lines rather than trusting its tags.

Adopted 2026-07-30, forward-only. Two briefs predate the folder and were **not**
migrated into it — both already carry accurate banners and stay where they are:
[`../LIVE-RUN-DECOMMISSION-HANDOFF.md`](../LIVE-RUN-DECOMMISSION-HANDOFF.md)
(SUPERSEDED by [`../GCP-DECOMMISSION-EVIDENCE-2026-07-10.md`](../GCP-DECOMMISSION-EVIDENCE-2026-07-10.md))
and [`../SECURITY-SCAN-PGX-FIX-HANDOFF.md`](../SECURITY-SCAN-PGX-FIX-HANDOFF.md)
(RESOLVED, merged `92af8ad` / PR #5).

| Brief | Covers |
|---|---|
| [2026-07-30-security-scan-repair-and-ledger-adoption.md](2026-07-30-security-scan-repair-and-ledger-adoption.md) | Weekly `Security Scan` green again at `b0c94db` (both red jobs fixed and confirmed by a real dispatched run, `30507863914`); repo-record adoption (`AGENTS.md` canonical + `CLAUDE.md` stub + both ledgers). Open: commit the adoption; watch the next scheduled scan; 3 pre-existing gaps unchanged (blind-test oracle, provenance cross-check, deploy secrets) plus the permanent GCP billing oracle-gap. |
