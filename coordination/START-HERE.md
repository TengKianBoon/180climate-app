# ▶ START HERE — 180Climate build (beginner-proof runbook)

**This is the only page you follow.** Everything else runs itself. You'll be asked to do
something only a handful of times — each one is spelled out below, in plain language.
About **15 minutes of setup**, then the build runs on its own to the first checkpoint.

## What's already done for you
- `coordination/` mailbox + **`board.html`** (your live window) — built.
- `docs/application-plan.md`, `orchestration-v2.md`, `project-instructions.md`, `adr/ADR-0011` — written.
- **WO-000** (the first build job) is queued in `coordination/INBOX.md`.

## The only 3 times you ever touch this
1. **Once now** — paste 2 instruction blocks (setup).
2. **The kickoff** — paste one line into VS Code.
3. **At a "Gate"** — about 7 times across the whole build, you say yes/no.

Nothing else needs you. You will **never** have to copy documents around.

---

## STEP 1 — Paste the role instructions  *(one-time, ~3 min)*
Open `docs/project-instructions.md`. It has three blocks.
- **Block A** → paste into **this Cowork project's** instructions (this space's Settings → Instructions).
- **Block C** → paste into your **Claude.ai project's** instructions (the separate Claude project in your browser).
- **Block B** → *do nothing.* VS Code will create it as `.claude/CLAUDE.md` for you in Step 4.

## STEP 2 — Make the private GitHub repo  *(one-time, ~3 min)*
1. Go to **github.com → New repository**.
2. Name **`180climate-app`** · visibility **Private** · do **not** add a README (the build adds one) · **Create**.
3. **Copy the repo URL** (e.g. `https://github.com/<you>/180climate-app`). You'll paste it in Step 4.
*(Keep it private now; flip to public later for your portfolio.)*

## STEP 3 — Connect your Claude.ai project to GitHub  *(one-time, ~2 min)*
In the browser: **Claude.ai → Settings → Connectors → GitHub → Connect →** authorize the `180climate-app` repo.
*(This is why, later, a gate review is just one line — it reads the repo itself, no pasting.)*

## STEP 4 — ▶ Press start in VS Code  *(the kickoff)*
1. Open **VS Code** on the folder **`C:\dev\180climate-app`**.
2. Make sure the **Claude Code** extension is installed and signed in to your **Max** plan.
3. In the Claude Code chat, **paste exactly this** (swap in your repo URL):

   > Read `coordination/INBOX.md` and Block B in `docs/project-instructions.md`. Create the `.claude/` harness from Block B, then run **WO-000 as a workflow, autonomously, until Gate 0**. Use my private repo `https://github.com/<you>/180climate-app`. Regenerate `coordination/board.html` after each step. **Stop** and write `coordination/GATE.md` when Gate 0 is ready, or `coordination/QUESTIONS.md` if you hit a real blocker.

4. When it asks to push to GitHub, say **yes**.

**That's the start — it now builds on its own.** *(Models: it uses Sonnet by default and Opus for the carbon-number work + reviews. Leave "Ask before edits" on for the first step if you want to watch it, then switch to auto-accept.)*

## STEP 5 — Watch  *(optional, anytime)*
**Double-click `coordination/board.html`.** It shows the phase, what's building, the last commit, and any open question — refreshed each step.

## STEP 6 — You'll be pulled in ONLY two ways
- **A QUESTION appears** (`coordination/QUESTIONS.md` not empty): open it, type your answer in plain English, save. The build resumes.
- **The board says `GATE 0 READY`:**
  1. Glance at `coordination/evidence/` (CI green link, screenshots).
  2. Happy? In VS Code type: **"Gate 0 approved — proceed to WO-001."**
  3. Want a second opinion first? Paste **one line** to your Claude.ai project: *"Gate 0 ready — github.com/<you>/180climate-app — what do you think?"*

Nothing else will ever interrupt you.

## If it looks stuck
It tries **at most twice**, then stops and writes a plain-English question into `coordination/QUESTIONS.md`. You answer it. No runaway, no mystery, no surprise cost.

## The 7 gates (your entire job over the whole build)
**Gate 0** scaffold · **1** slice works end-to-end · **M** carbon numbers + methodology · **C** any contract change · **P** your email/lead flow · **E** EUDR verdict · **L** go-live. At each, you say **yes/no**. That's it.
