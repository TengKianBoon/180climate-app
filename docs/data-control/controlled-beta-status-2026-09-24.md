# Three-app controlled beta: production verification (24 September 2026)

This is a public-safe status record. It contains no operator tokens, submissions, backups, private contacts, card details or account identifiers. It distinguishes verified recording from notification and browser behavior that still needs checking.

## Deployed foundation

- Carbon Pre-Feasibility Screening, EUDR Plot Check and Fieldwork share the production `180climate-app` Render web service in Oregon, USA.
- At the intake switch, Render deployed GitHub `main` commit `0ccdc16d5cc1c806efc1322ce9b27fdaae344596` and reported the service Live. The controlled intake code is in merged PR #2; native Fieldwork routing and provisional intake notices are in merged PR #3; PR #4 recorded the pre-opening state.
- The Render Hobby workspace has no workspace-plan fee. The selected production service compute costs US$7/month, and its 1 GB persistent disk mounted at `/var/data` costs US$0.25/month. The fixed resource baseline is US$7.25/month before prorating, bandwidth or other metered charges. Render has no general whole-bill hard cap. Cost and notification settings are tracked privately by the operator.
- The shared SQLite file is on the mounted disk. An online backup and restore rehearsal passed against the empty production schema. This confirms the mechanics only; it is not evidence of recurring offsite backups or recovery of actual submissions.

## Live intake read-back after public beta switch

The Render Environment page shows `INTAKE_OPERATOR_TOKEN` and `FIELDWORK_OPERATOR_TOKEN` present with values masked. Neither value was copied to this repository or to the verification record. The two public-safe configuration endpoints returned:

| Endpoint | Observed state |
|---|---|
| `/api/intake/config` | `recording_mode=required`, `ready=true`, `configuration_gaps=[]`, geometry retention `true`, retention 180 days, legal review deferred by controller. |
| `/api/fieldwork/config` | `accepting_submissions=true`, `launch_gaps=[]`, provisional terms/privacy/prohibited-use versions, bilingual retention and processor summaries, registration cap 10. |

The public HTTPS configuration endpoints and Fieldwork page returned HTTP 200. The service catalogue advertises `native_registration` at `https://eudr.180climate.net/fieldwork`. The page script routes its requester/provider buttons to native forms when the live config says acceptance is true. The separate old Wix invitation URL has not been cut over.

## Verification and remaining work

- Local targeted offline tests on the deployed source revision: `29 passed, 1 warning` for `tests/test_intake.py` and `tests/test_fieldwork.py`.
- Synthetic production Carbon and EUDR calls returned HTTP 200 and submission references. The shared SQLite database contained one record for each, both with stored geometry. Synthetic Fieldwork requester and provider calls returned HTTP 200 and references; the database contained one of each. Token-protected operator endpoints returned HTTP 200 and the expected record counts. These tests used `.invalid` contacts and did not prove real-user completion or browser rendering.
- Confirm intended email/PDF/Sheets delivery and external-data behavior separately; a saved record is not proof that a notification or report reached anyone. Keep all synthetic and real records out of public GitHub.
- Set a private recurring backup destination and recovery schedule; the empty-schema restore rehearsal is the current bounded evidence. Define and execute the 180-day deletion procedure, including Fieldwork related tables and backup expiry, before the first retention deadline.
- Publish a clear native Fieldwork entry point from the main 180Climate site and verify the old Wix invitation-only route no longer misdirects open-beta visitors.
- The controller authorised opening the beta intake after the operator tokens were set. Render accepted the two switch changes and reported the deploy Live; the running service and public HTTPS config both reported acceptance on.

Public data controller: `180CLIMATE PTE.LTD.`. Public privacy contact: `john@180climate.net`. Beta notices are provisional, and the controller deferred external Indonesian legal review; no counsel approval is claimed. Paid checkout remains off.
