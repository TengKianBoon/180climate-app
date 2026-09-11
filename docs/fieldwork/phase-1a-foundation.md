# Fieldwork Phase 1A foundation and publication boundary

**Status:** local implementation baseline; not approved for publication or real-user intake  
**Recorded:** 2026-09-11

## Confirmed implementation relationship

- `www.180climate.net` is the Wix marketing site.
- This existing public repository is the FastAPI application source for the standalone 180Climate tools. `api/main.py` serves the API and browser UI, `render.yaml` defines the Render service, and the existing subdomain arrangement links standalone tools from the Wix site.
- Fieldwork therefore extends this application and deployment shape rather than creating a new framework, service, or GitHub repository.
- The repository already contains an Apache-2.0 `LICENSE`. Phase 1A preserves it and makes no new licence selection.
- The working public product name is **180Climate Fieldwork Network** and the stable service ID is `fieldwork.match_intro.v1`.
- The first implemented low-risk request type is **owner-authorised property condition photographs and checklists**. Other allowed categories remain available only when they satisfy the same authority, non-invasive, non-hazardous, non-regulated boundary.

## Public/private boundary

Suitable for a later approved public checkpoint:

- application source, schemas, and service catalogue definitions;
- deterministic validation and consent rules;
- synthetic fixtures and tests;
- non-secret architecture, security, and recovery documentation;
- privacy-safe aggregate test evidence.

Never commit or publish:

- invite codes, operator credentials, API keys, cookies, connection strings, or private endpoints;
- real names, contacts, provider profiles, requests, complaints, status keys, audit records, or analytics identifiers;
- exact property, mine, plantation, forest, concession, plot, or other sensitive-site details;
- runtime databases, backups, logs, support exports, prompt traces, or processor payloads;
- confidential contracts, private legal advice, unresolved exploitable findings, or rights-restricted data and media.

Runtime Fieldwork data is stored outside the repository at `FIELDWORK_DB_PATH`. Public tests use generated synthetic records only. Status and operator secrets are submitted in request bodies or headers and are never placed in analytics events.

## Fail-closed launch controls

`FIELDWORK_ACCEPTING_SUBMISSIONS` defaults to `false`. Production must refuse submissions unless all required runtime values are present. Enabling real-user intake requires a recorded consequential approval after these facts are confirmed:

1. operating entity, data controller, privacy owner/contact, and authorised deployer;
2. final route within `180climate.net` and company authority to use the brand/logo there;
3. encrypted persistent datastore, hosting region, operator access owner, backups, restore target, and deletion propagation;
4. retention schedule and versions of every public notice and processor disclosure;
5. invitation distribution, first invited users, and operational receipt/response process;
6. Bahasa Indonesia controlling documents and qualified Indonesian counsel review of the implemented flow;
7. security, accessibility, responsive, smoke, incident, backup/restore, and rollback evidence;
8. explicit company publication and deployment approval.

Until then, local and non-user staging may use synthetic data only. A local preview, passing tests, or a local commit is not Phase 1A completion.

## Deployment relationship still requiring confirmation

The repository and configuration establish the technical relationship, but they do not prove current account ownership, publication rights, persistent-datastore suitability, processor terms, or authority to deploy. Those remain evidence gates. No push, deployment, DNS/Wix change, licence change, or public claim is part of this implementation stage.
