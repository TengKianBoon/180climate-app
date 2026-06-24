phase: P4 · Pre-launch — WO-DEPLOY-PREP-001 DONE. All code tasks complete.
active_wo: none — all remaining Gate-L items are deploy-time (John).
status: Procfile + .python-version 3.13 + render.yaml committed (ef17857). App boots, GET / 200, GET /health 200, 246 tests pass. CI will stay green (245 + 1 skipped). No code blockers to Gate L remain.
last_commit: ef17857 feat(deploy): Procfile + .python-version 3.13 + render.yaml (WO-DEPLOY-PREP-001)
remaining_to_gate_L: (deploy-time, John follows docs/deploy-runbook.md) PIPPIB snapshot + PIPPIB_SNAPSHOT_PATH; EMAIL_* creds (EMAIL_FROM=john@180climate.net critical); GOOGLE_SHEETS_ID + GOOGLE_CREDENTIALS_JSON; ANTHROPIC_API_KEY (optional); Render deploy + app.180climate.net DNS; end-to-end Gate L test.
next_step: John executes deploy-time items per docs/deploy-runbook.md -> Gate P end-to-end live test -> Gate L sign-off.
updated: 2026-06-25
