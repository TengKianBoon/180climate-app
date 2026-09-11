# Fieldwork deployment and recovery controls

**Status:** implementation draft; no production deployment authorised

## Runtime configuration

Real-user intake remains closed unless `FIELDWORK_ACCEPTING_SUBMISSIONS=true` and all of these are configured in the host secret/configuration store: private persistent `FIELDWORK_DB_PATH`, invitation code, operator token, privacy contact, retention version, processor-list version, and explicit approved versions for the pilot terms, privacy notice and prohibited-use notice.

The database, WAL files, backups and operator exports are protected runtime data. They must never be placed in this public repository or a public build artifact. The selected hosting volume must provide suitable encryption at rest, access control, residency/transfer documentation, durability and backup behaviour. The current Render configuration does not by itself prove those requirements.

## Pre-deployment gate

Before enabling submissions, record:

- authorised route and deployer;
- controller/privacy owner and public contact;
- persistent volume/database product, region, processors and subprocessors;
- table-by-table retention/deletion rules and backup expiry;
- operator access owner, MFA where supported and access-review cadence;
- Indonesian counsel and company approvals for the exact implemented flow and Bahasa Indonesia documents;
- passing security, privacy, accessibility, responsive and critical-journey checks.

## Backup

Create the backup only in an approved private destination:

```powershell
python scripts/fieldwork_db.py backup --db <private-runtime-db> --output <private-backup-file>
```

The helper uses SQLite's online backup API and verifies the copied schema version. A copied file is not recovery evidence until restoration is tested.

## Restore rehearsal

Restore first to a new approved non-production path, never over production during a rehearsal:

```powershell
python scripts/fieldwork_db.py restore --backup <private-backup-file> --db <new-rehearsal-db> --confirm-replace
```

Then start the application against the rehearsal database and verify: public health, one synthetic requester status, one synthetic provider status, the operator queue, consent records, status history, and aggregate analytics. Record backup time, recovery point, responsible person, result and any data-loss window.

## Code/deployment rollback

Keep the last approved Git commit, immutable release identifier, Render deployment revision and schema version. Roll back by redeploying that approved revision, preserving the database, and running the read-only health/status/operator smoke checks. Prefer forward-compatible schema changes; never rewrite public Git history to recover.

## Current limitation

Local backup/restore tests exercise the file mechanics with synthetic data only. Production durability, restoration time, encryption, deletion propagation, processor behaviour and deployment rollback remain unverified until exercised on the authorised environment.
