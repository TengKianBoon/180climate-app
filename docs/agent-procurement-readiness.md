# Agent procurement readiness

Status: guarded v1 contract, 11 September 2026.

This repository makes the three 180Climate services easier for an authorised AI agent to discover and evaluate without giving the agent authority to contract, pay, disclose private information, dispatch people or make regulated conclusions.

## Discovery contract

- `/.well-known/180climate-services.json` is the stable catalogue URL.
- `/openapi.json` describes the HTTP operations.
- `/schemas/*.json` contains versioned request and response contracts.
- Each catalogue action declares its operation ID, transport, side effects, retry hint, open-world interaction and immediate approval requirement.

The tool annotations use the same four risk concepts exposed by MCP—read-only, destructive, idempotent and open-world—but are descriptive hints, not security enforcement. The API and operator workflow remain the enforcing controls.

## Safe agent journey

1. **Discover.** Read the catalogue and select the service by `service_id`; do not infer an action from marketing copy.
2. **Evaluate.** Check region, eligibility, required inputs, limitations, price status and blocked autonomous actions.
3. **Establish authority.** Confirm that the represented person controls the contact and land or plot information and may request the service.
4. **Preview consequence.** Show the user the exact data, destination and declared side effects.
5. **Approve at the edge.** Obtain explicit approval immediately before any call that communicates externally, stores personal data or creates a registration or delivery.
6. **Invoke once.** Use the declared operation and schema. Retry only when `idempotentHint` is true and the same idempotency key is reused.
7. **Verify.** Check the returned state or receipt. Do not convert a screening state into a professional or legal conclusion.
8. **Stop at human gates.** Contact disclosure, introduction, site access, contracting, payment and regulated reliance remain human decisions.

## Current readiness by service

| Service | Current agent use | Important boundary |
|---|---|---|
| Carbon Pre-Feasibility | Guarded machine screening for declared REDD, IFM and peat routes | The `other` route may send a lead; all results are indicative and non-bankable |
| EUDR Plot Screening | Guarded user-authorised call | The current call emails 180Climate, so it is not safe for speculative or unattended execution |
| Fieldwork Network | Machine discovery and human Wix handoff; typed native intake is staged | Native intake stays fail-closed until privacy, datastore, access and deployment controls pass; matching and disclosure remain human-controlled |

## Not claimed

This v1 is not an MCP server, A2A agent, autonomous purchasing system, payment rail, identity delegation service or contracting system. Those would need authenticated delegated authority, policy enforcement, auditability, abuse controls, commercial terms and separate legal and deployment approval.

## Standards alignment

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html): machine-readable HTTP interface and unique operation IDs.
- [MCP tool-annotation risk vocabulary](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/): read-only, destructive, idempotent and open-world hints; the specification warns that hints are not enforcement.
- [A2A Protocol overview](https://a2a-protocol.org/dev/specification/): useful future discovery and agent-to-agent interoperability reference. This repository does not claim an A2A Agent Card or A2A runtime.
