# Fieldwork Phase 1A stage receipts

**Scope:** local branch `feat/fieldwork-phase-1a`; no push, deployment, DNS/Wix change, real-user data, new repository, tag, release, or licence decision

## Foundation — PASS

- Commit: `468839b` (`docs: establish phase 1a architecture and governance baseline`)
- Inspected the existing public repository, FastAPI source, Render configuration, Wix/public-site relationship, deployment runbook and licence state.
- Recorded the public/private publication boundary and consequential launch gate.
- Baseline regression at this stage: 21 existing slice tests passed.

## Smallest working pilot — PASS locally

- Commit: `3636a70` (`feat: add fail-closed invited fieldwork pilot`)
- Added a responsive English/Bahasa landing page, invited requester/provider intake, private operator queue, status access, explicit two-party introduction consent, service catalogue/schemas, SQLite persistence, aggregate analytics and recovery helper.
- Real-user intake is fail-closed unless every required deployment, privacy, retention, processor, access and approved-notice configuration value is present.
- JavaScript syntax: PASS for the public, status and operator clients.
- Python compile: PASS.
- Mypy: PASS for `api/fieldwork.py` and `scripts/fieldwork_db.py`.
- Critical-path tests: 15 passed.
- Repository offline regression: 476 passed; two live-network overlay checks intentionally deselected; one dependency deprecation warning.
- JSON parse: PASS for the service catalogue and three schemas.
- Browser QA: PASS at 320, 390, 768, 1024 and 1440 CSS-pixel widths with no horizontal overflow; synthetic requester, provider, status and private operator flows exercised.
- Synthetic backup/restore rehearsal: PASS through the automated test.
- Secret/private-data scan: no credential-like tracked value found; identities in tests use the reserved `.invalid` domain.

## Not yet evidenced or approved

Production deployment, real message delivery, persistent-volume durability, backup destination/encryption, deletion propagation, processor terms, privacy-controller facts, final legal/Bahasa text, account/asset publication authority, operational staffing and live rollback remain outside this local PASS. The product catalogue therefore stays `closed_pending_launch_gate`.

## Real-user gate hardening — PASS locally

- Commit: `287e0b4` (`feat: harden real-user pilot launch gate`).
- Added a hard cap of 10 distinct pilot contacts and required explicit public-origin, controller, privacy-contact link, hosting-region, retention-summary, processor-summary, Bahasa-pack, counsel-approval and company-approval configuration before intake can open.
- Public privacy facts render only when the complete gate passes; the WhatsApp route is deployment configuration and no real telephone number is committed.
- Critical-path tests: 16 passed. Repository offline regression: 477 passed; two live-network overlay checks intentionally deselected; one dependency deprecation warning.
- Browser smoke: complete synthetic launch facts rendered correctly, WhatsApp link scheme was preserved, no horizontal overflow appeared, and no browser warning/error was recorded.
- Account inspection: Wix showed the current user as site owner and GitHub showed repository ownership. Render access was not authenticated, so service region, linked branch, persistent storage, backups and deployment settings remain unverified.

## Public invited-pilot entry and Wix routing — PASS with one open form correction

- Public entry: `https://one80climate-fieldwork-preview.onrender.com/fieldwork`.
- Private application form: `https://www.180climate.net/fieldwork-pilot-draft`.
- Wix navigation presents one **Fieldwork Pilot** route. The live explainer presents requester/provider paths and both lead to the same private review form.
- Render service `180climate-fieldwork-preview` was verified in Singapore on public branch `feat/fieldwork-phase-1a`; deployment `dep-dahplgqfngtc73dhkgag` completed successfully and its health check returned HTTP 200.
- Public-routing commits: `af8b160` (Wix intake), `7820bb1` (remove obsolete warning), `79ef46e` (refresh cached status asset), and `d25d2c4` (remove the unusable native-status link from the Wix journey and align `services.json`).
- Live browser inspection confirmed the Fieldwork explainer, English/Bahasa switch, allowed/excluded scope, all three Wix calls to action, the current application banner, and the Wix form fields and consent declaration. No real record was submitted during QA.
- Updated-build browser QA at 320, 390, 768, 1024 and 1440 target widths found no horizontal overflow; all three Wix actions remained visible, the unusable native-status link was absent, and the Bahasa Indonesia switch rendered the translated heading.
- Read-only inspection found the Wix name, email, invitation source, role/category, location, timing, work description, authority/safety description and consent checkbox marked required. The requester/provider radio group was not marked required in the rendered form; that Wix configuration correction remains open.
- Deterministic repository regression: 477 passed, two live-network map-overlay tests deselected, one dependency deprecation warning.
- Focused Fieldwork regression: 16 passed, one dependency deprecation warning.
- A separate all-tests run produced 477 passes and two failures when external BIG KHG/PIPPIB endpoints timed out; both adapters returned `data unavailable`/manual-review outcomes rather than false clean results.

## Remaining pilot evidence

The current free/Wix arrangement can receive invited applications for manual review, but the requester/provider choice should be made mandatory before the form is treated as enforcing that distinction. The arrangement does not prove automated contact verification, native reference/status delivery, persistent datastore durability, email notification delivery, deletion propagation, production database recovery, counsel approval, or adoption outcomes. Those controls must not be claimed from the synthetic native-workflow tests.
