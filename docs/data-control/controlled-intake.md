# 180Climate controlled form and database map

**Status:** see [the 24 September production verification](controlled-beta-status-2026-09-24.md). The paid service and persistent disk are deployed; real-user native intake remains switched off. The steps below are the original migration control map and do not themselves authorise a public switch.

## One controlled record location

The smallest current migration uses one private SQLite database for all three 180Climate applications:

- production environment variable: `INTAKE_DB_PATH`;
- proposed Render persistent mount: `/var/data`;
- proposed database file: `/var/data/180climate-intake.sqlite3`;
- Carbon and EUDR table: `intake_submissions`;
- Fieldwork tables: `principals`, `requester_profiles`, `provider_profiles`, `work_requests`, `consents`, `introductions`, `status_keys`, `status_history`, `audit_events` and `aggregate_analytics`;
- accountable owner: to be recorded before launch;
- operator interface: authenticated `/api/intake/submissions` and `/api/intake/export.csv` for Carbon/EUDR, plus the existing authenticated `/fieldwork/operator` workflow for Fieldwork.

`FIELDWORK_DB_PATH` remains accepted as a compatibility alias. New deployments should set `INTAKE_DB_PATH` and point both intake systems to the same private file. Runtime databases, WAL files, backups, exports, tokens and real submissions must stay outside Git.

## What each form records

| Application | Public submission route after migration | Database records | Geometry handling |
|---|---|---|---|
| Carbon Pre-Feasibility | `POST /api/carbon` and the separate enquiry form `POST /api/lead` | Contact, company, IUP/project form fields, screening/enquiry result, timestamps, status and retention deadline | Normalised GeoJSON is stored only when `INTAKE_STORE_GEOMETRY=true`; a SHA-256 digest is retained when geometry storage is explicitly disabled. |
| EUDR Plot Check | `POST /api/eudr` | Contact, company, commodity, role, source filename/format, triage result, timestamps, status and retention deadline | The normalised geolocation pack is stored only when `INTAKE_STORE_GEOMETRY=true`; it is kept out of the duplicated form/result JSON fields. |
| Fieldwork | `POST /api/fieldwork/requests` and `POST /api/fieldwork/providers` | Structured requester/provider registrations, status, consent, introduction and audit records | Fieldwork currently asks for a broad service area/location rather than an exact plot geometry. |

The orphaned Formspree form `mbgjnedr` is not a migration dependency. The Wix Fieldwork page must remain unchanged until the native route is configured, tested and explicitly approved. After that controlled cutover, the Wix page can link or redirect to the native `/fieldwork` form and Formspree can be retired.

## Required runtime controls

Recording has only two modes:

- `INTAKE_RECORDING_MODE=off`: current safe default; no database record is created.
- `INTAKE_RECORDING_MODE=required`: every Carbon/EUDR submission must be written successfully before the application claims it was saved or sends an EUDR lead notification.

Required with `required` mode:

- `INTAKE_DB_PATH=/var/data/180climate-intake.sqlite3` on an approved persistent mount;
- `INTAKE_RETENTION_DAYS=<approved number>`;
- `INTAKE_STORE_GEOMETRY=true|false` as an explicit privacy decision;
- `INTAKE_OPERATOR_TOKEN=<strong private token>`;
- `LEAD_RECIPIENT_EMAIL=<approved 180Climate operational mailbox>`; there is no personal-email fallback;
- `INTAKE_CONTROLLER_NAME`, `INTAKE_PRIVACY_CONTACT` and `INTAKE_HOSTING_REGION`;
- `INTAKE_RETENTION_VERSION` and `INTAKE_PROCESSOR_LIST_VERSION`;
- `INTAKE_OPERATOR_OWNER` and `INTAKE_AUTHORISED_DEPLOYER`;
- `INTAKE_BAHASA_PACK_VERSION` and `INTAKE_COMPANY_APPROVAL_ID`;
- either `INTAKE_COUNSEL_APPROVAL_ID`, or both `INTAKE_LEGAL_REVIEW_STATUS=deferred_by_controller` and `INTAKE_LEGAL_REVIEW_RECORD=<dated controller decision>`; the latter is reported as a deferral, never as counsel approval;
- the separate Fieldwork controller, privacy, processor, Bahasa, counsel and company launch controls already documented in `docs/fieldwork/deployment-and-recovery.md`.

The safe public endpoint `/api/intake/config` reports readiness and legal-review status without exposing the database path or token. Operator endpoints require a bearer token and exclude coordinates from normal listing/export unless the operator explicitly requests them.

## Backup and recovery

Because Fieldwork and Carbon/EUDR share the same SQLite file, one verified SQLite online backup covers all three applications. Use `python scripts/intake_db.py backup --db <private-runtime-db> --output <private-backup-file>` and store backups in an approved private destination outside Git. A database file or platform snapshot is not sufficient recovery evidence until a restore rehearsal passes.

Render's normal service filesystem is ephemeral. A paid persistent disk or a managed datastore is therefore mandatory before `INTAKE_RECORDING_MODE=required`. Adding a paid resource, changing the live Wix form, deploying, or enabling real-user submissions remains a separate approval.

## Cutover sequence

1. Record the legal/data owner, operator, retention period, geometry-retention decision, hosting region and processor notice.
2. Approve and create the private persistent database destination.
3. Configure the five `INTAKE_*` values while keeping `INTAKE_RECORDING_MODE=off`.
4. Run synthetic Carbon, EUDR, Fieldwork requester and Fieldwork provider submissions; verify the operator views, export, backup and restore.
5. Set `INTAKE_RECORDING_MODE=required` and confirm storage failures return a clear `503` without claiming success.
6. Only after explicit publication approval, point the live Wix Fieldwork route to the native form and retire the Formspree dependency.
7. Record the final dashboard URL, service name, region, database path, backup destination, recovery owner and verification date in the private Form Data Register.
