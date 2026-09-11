# 180Climate application working rules

## Scope

- Preserve the existing FastAPI application, deterministic Carbon Pre-FS and EUDR behaviour, and Render deployment shape.
- Build Fieldwork Phase 1A as the smallest open-registration, free public beta for human-reviewed matching and consent-based introductions. Registration and operating criteria are public; requester/provider records, contacts and precise sites remain private. Do not add Fieldwork payments, public profiles, open marketplace search, employment placement, regulated conclusions, or automated dispatch.
- The 11 September 2026 commercial amendment permits a fail-closed Stripe-hosted payment handoff for 180Climate's own fixed-scope EUDR and carbon professional services. It does not permit card-data collection, payment custody, worker/provider payouts, escrow, autonomous purchasing, live activation, public deployment or unapproved external cost. Keep checkout `off` by default and preserve the separate live controls.
- Use synthetic data only in source, tests, screenshots, logs, and public artefacts.

## Consequential gates

Do not push, deploy, publish, create a repository, change the licence, expose protected data, send an introduction, incur cost, or make a regulated conclusion without the recorded approval for that exact action.

Production submission intake must fail closed until the privacy controller, public privacy contact, retention schedule, processor inventory, persistent data destination, operator access owner, authorised deployer, Indonesian legal review, Bahasa Indonesia controlling documents, and company publication approval are recorded.

## Public/private boundary

Public-safe material is limited to source code, schemas, synthetic fixtures, non-secret deployment templates, tests, and reviewed governance/recovery documentation. Keep runtime contacts, submissions, status keys, operator secrets, databases, backups, logs, support exports, exact sensitive sites, private legal advice, and rights-restricted assets outside Git.

## Checks and commits

- Run the smallest relevant deterministic tests before each stage commit.
- Inspect the diff and run a secret/private-data scan before committing.
- Commit only coherent passing stages with truthful messages.
- A local commit is not publication, CI evidence, a release, deployment, backup, or completion.
