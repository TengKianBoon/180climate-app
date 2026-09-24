# Three-app controlled beta: production verification (24 September 2026)

This is a public-safe status record. It contains no operator tokens, submissions, backups, private contacts, card details or account identifiers. It reports observed deployment and configuration, not completed end-to-end intake.

## Deployed foundation

- Carbon Pre-Feasibility Screening, EUDR Plot Check and Fieldwork share the production `180climate-app` Render web service in Oregon, USA.
- GitHub `main` commit `49577746722544f577dc615a667ea5f1c10aff83` is deployed and Render reports the service live. The controlled intake code is in merged PR #2; native Fieldwork routing and provisional intake notices are in merged PR #3.
- The Render Hobby workspace has no workspace-plan fee. The selected production service compute costs US$7/month, and its 1 GB persistent disk mounted at `/var/data` costs US$0.25/month. The fixed resource baseline is US$7.25/month before prorating, bandwidth or other metered charges. Render has no general whole-bill hard cap. Cost and notification settings are tracked privately by the operator.
- The shared SQLite file is on the mounted disk. An online backup and restore rehearsal passed against the empty production schema. This confirms the mechanics only; it is not evidence of recurring offsite backups or recovery of actual submissions.

## Readiness read-back after operator-token deployment

The Render Environment page shows `INTAKE_OPERATOR_TOKEN` and `FIELDWORK_OPERATOR_TOKEN` present with values masked. Neither value was copied to this repository or to the verification record. The two public-safe configuration endpoints returned:

| Endpoint | Observed state |
|---|---|
| `/api/intake/config` | `recording_mode=off`, `ready=false`, `configuration_gaps=[]`, geometry retention `true`, retention 180 days, legal review deferred by controller. |
| `/api/fieldwork/config` | `accepting_submissions=false`, `launch_gaps=[]`, provisional terms/privacy/prohibited-use versions, bilingual retention and processor summaries, registration cap 10. |

Thus all required launch configuration is present, while production intake remains closed. Public Carbon and EUDR pages load; the native Fieldwork page loads but, while closed, its calls to action still go to the invitation-only Wix/Formspree route. Do not describe native registrations as live until the switch and route have been verified.

## Verification and remaining work

- Local targeted offline tests on the deployed source revision: `29 passed, 1 warning` for `tests/test_intake.py` and `tests/test_fieldwork.py`. These do not prove production email, Sheets, PDF, external data or database writes.
- Before announcing live submissions, perform synthetic end-to-end submissions for all three applications, verify private records and operator access, confirm intended notification/PDF delivery, and confirm that failures do not claim success. Keep synthetic records out of public GitHub.
- Set a private recurring backup destination and recovery schedule; the empty-schema restore rehearsal is the current bounded evidence. Define and execute the 180-day deletion procedure, including Fieldwork related tables and backup expiry, before the first retention deadline.
- Publish a clear native Fieldwork entry point from the main 180Climate site and verify the old Wix invitation-only route no longer misdirects open-beta visitors.
- Opening public intake requires a separate action-time access confirmation because it will allow people to submit private contacts and plot information to the production database. No such switch is represented by this document.

Public data controller: `180CLIMATE PTE.LTD.`. Public privacy contact: `john@180climate.net`. Beta notices are provisional, and the controller deferred external Indonesian legal review; no counsel approval is claimed. Paid checkout remains off.
