# 180Climate — Coordination Board (zero-setup view)

> The same mailbox as `board.html`, but as plain Markdown. Open it in VS Code's
> Markdown preview (Ctrl+Shift+V) — no browser, no server. The Hands rewrite the
> top block each step; you just watch.

**Phase:** P0 → P1   **Active WO:** WO-000 · scaffold + contracts   **Status:** RUNNING
**Last commit:** `feat: core/contracts type-check clean`   **Updated:** 2026-06-23

---

## 📥 INBOX — the task right now  · _written by: Brain_
WO-000 — Repo scaffold + contracts + harness + CI.
Objective: stand up the monorepo, typed contracts, `.claude/` harness, green CI on a placeholder test.
Acceptance: tree matches spec §12 · contracts type-check clean · CI green · no secrets · first commit pushed (private, `main` protected).
Retry budget: 2 → STOP. Gate: **Gate 0** (John).

## 📤 OUTBOX — last result  · _written by: VS Code (Hands)_
Built repo tree + `core/contracts/` (type-checks clean) + `.claude/` harness + `coordination/` mailbox + CI.
Status: contracts PASS · CI green on placeholder · Verifier pending.

## ❓ QUESTIONS — blockers  · _non-empty = a human/Brain turn is needed_
_(empty — nothing to answer)_

## 🚦 GATE
Gate 0 — **ASSEMBLING** (not yet READY). Needs: repo tree, CI green link, type-check output, main-protection proof.

## 🧾 EVIDENCE
`coordination/evidence/WO-000/` → ci-green.txt · contracts-typecheck.txt · repo-tree.txt
(Verifier PASS/FAIL/CLARIFY report on high-stakes WOs only.)

## 📓 JOURNAL — recent (append-only)
- 2026-06-23 · seeded `coordination/` mailbox + board
- 2026-06-23 · ADR-0001..0010 committed to `docs/adr/`
- 2026-06-23 · scaffold underway; Opus reserved for the number path

---

### Who writes what (the only rules that matter here)
| Actor | Reads | Writes | When |
|---|---|---|---|
| **Brain** (Claude project) | repo via GitHub | INBOX, gate verdict | at a gate |
| **VS Code** (Hands) | INBOX | STATE / OUTBOX / evidence / journal + commits | continuously |
| **Cowork** (planner) | STATE / OUTBOX | plan notes, may refine INBOX (never code) | on a schedule |
| **John** | GATE / QUESTIONS | "Gate X ready" + gate decisions | the 7 gates |

**Two signals pull a human turn:** `QUESTIONS` non-empty, or `GATE` = READY. Everything else runs itself.
