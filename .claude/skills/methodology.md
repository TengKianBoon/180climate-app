# Skill: methodology

Verra methodology routing by permit type. Apply this whenever writing or reviewing narrative/ code or MethodologyRoute construction.

## Routing table (normative — ADR-0001)

| Permit type | Baseline class | Verra family cited in narrative |
|---|---|---|
| **HTI** (industrial timber plantation; legal right to clear-fell) | Planned clear-fell foregone | **APD route** (VM0009/legacy — advisor-confirm) |
| **HA** (natural-forest logging; legal right to selectively log) | Planned selective-logging foregone | **IFM** (VM0010 / VM0045 v1.2) |
| **Peat** | Avoided drainage/subsidence | **VM0027 (interim)** — advisor-confirm; standalone peat method pending |
| (reference only) Unplanned / illegal loss | — | VM0048 + VMD0055 + VT0007 — **NEVER used for foregone-harvest** |

## Hard rules
- `is_planned` MUST be `True` for HTI and HA baseline routes.
- `additionality_basis` MUST be set to `"legal harvest right foregone"` for HTI and HA.
- **Never** cite VM0007 or the VM0048 family for a foregone-legal-harvest baseline.
- **Never** brand to a deprecated method.
- All peat routes state "advisor-confirm; standalone peat method pending."

## Source of truth
`docs/methodology.md` + `docs/adr/ADR-0001.md`
