# Private submission register

Saved Carbon and EUDR submissions can generate a current Excel register and
email it to the existing operational mailbox through Brevo. Enable this with
`INTAKE_REGISTER_EMAIL_ENABLED=true`. The default is off. The existing
`LEAD_RECIPIENT_EMAIL`, `BREVO_API_KEY` and intake configuration must be ready.
No additional hosting service or spreadsheet account is required.

## Workbook

The private database is the source of truth. The workbook contains current,
unexpired submissions, newest first, on three tabs:

- **Submissions:** reference, date (UTC), application, saved status, screening
  result, contact/project information, area, provenance and retention date.
- **Coordinates:** stored plot geometry flattened into numeric coordinates,
  linked by submission reference and plot ID.
- **Form answers:** submitted form fields, linked by submission reference.

Carbon columns show indicative lifetime and annual ranges in metric tonnes of
CO2e, with the engine's scenario period (currently 30 years). They do not show
issued or verified VCUs. EUDR rows have no carbon quantity; unknown EUDR area or
forest-loss totals remain blank. User text is literal text, never an Excel
formula.

This records saved submissions. It does not identify anonymous page visitors,
prove a contact's identity, or provide an account-registration system.

## Delivery and operator checks

A job is saved in the same database transaction as each submission. A worker
checks every 15 seconds, rebuilds the current workbook and attaches it as
`180Climate-Submission-Register.xlsx`. Failed delivery attempts do not discard
the submission. Temporary failures retry up to five times using one persistent
Brevo idempotency key within its 30-minute window; ambiguous, oversized or
repeatedly failed jobs require operator attention.

Existing `INTAKE_OPERATOR_TOKEN` authentication protects:

- `GET /api/intake/register.xlsx`: download the current workbook without email.
- `GET /api/intake/register/status`: configuration gaps and queue outcomes.

`accepted` means Brevo accepted the API request. Check Brevo transactional logs
for **Delivered**; API acceptance alone is not mailbox delivery proof.

The current file is kept beside the private intake database. Expired records
are excluded when generating it; idle snapshots refresh hourly. Email copies
are separate copies in the operator's mailbox and must be managed by the data
controller. No public register link is created. The legacy Google Sheets
integration is separate and is not required for this feature.
