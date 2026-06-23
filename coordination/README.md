# coordination/ — the shared mailbox (how Cowork & VS Code talk)

This folder **is** the communication channel between the two folder-aware agents.
No app-to-app wire, no copy-paste — both agents read/write these files on the same
disk. Full design: [`../docs/orchestration-v2.md`](../docs/orchestration-v2.md).

> **For the VS Code coding agent / WO-000:** this folder is **already created**.
> Do **not** recreate or overwrite it. Just start reading `INBOX.md` and writing
> `STATE.md` / `OUTBOX.md` / `evidence/` / `journal.md` per the protocol below.

## The files
| File | Truth it holds | Written by |
|---|---|---|
| `STATE.md` | phase · active WO · status · last commit · next step | VS Code, every step |
| `INBOX.md` | the task right now | Cowork (planner) |
| `OUTBOX.md` | last result + links into `evidence/` | VS Code |
| `QUESTIONS.md` | blockers — **non-empty pulls a human** | whoever is blocked |
| `GATE.md` | `GATE x READY` + evidence pointers at a phase boundary | VS Code |
| `evidence/` | CI output, golden-case results, screenshots, Verifier reports | Verifier + VS Code |
| `journal.md` | append-only episodic log (feeds the Dreaming pass) | both |

## Your window
- **`board.html`** — self-contained dashboard. **Double-click it** (no server). It is
  **regenerated after every step** by `render_board.py`.
- **`BOARD.md`** — the same thing as Markdown, for VS Code's preview (Ctrl+Shift+V).

## Regenerate the board (run after each step)
```bash
python coordination/render_board.py
```
Deterministic, stdlib-only, no model. Reads the `.md` files (+ `git log`) and rewrites
`board.html`. Wire it into the Stop-hook or the end of each Work-Order step so the board
is always current.

## The two rules that matter
1. **Only two signals interrupt John:** `QUESTIONS.md` non-empty, or `GATE.md` READY.
2. **Loop limit:** retry budget **2 → STOP** and write `QUESTIONS.md`. Never thrash.
