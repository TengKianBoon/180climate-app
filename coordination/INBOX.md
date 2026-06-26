# INBOX — Cowork (planner) · 2026-06-26 · WO-METHFIX-002 (ADR-0016 uncertainty propagation) · GATE C SIGNED

## WO-METHFIX-002 · M1 uncertainty propagation + M2 density gating · **Opus** (number-path)
**Gate C SIGNED (ADR-0016, John "proceed").** Build on `main` · retry 2 → QUESTIONS.md.
**Spec:** `docs/adr/ADR-0016-uncertainty-propagation.md`. **Ranges WIDEN — intended. Re-baseline goldens + document before→after.**

### M1 — propagate real uncertainty into the range (then buffer separately)
- Error budget: combine **density relative-SE** (ESA CCI per-pixel uncertainty layer; a wide default CV when only the
  IPCC value is used) + **loss-rate CV** (std/mean of the annual Hansen loss series on `ForestData.annual_loss_ha`)
  **in quadrature** → central estimate ∓ combined band.
- **Apply the VCS buffer (20–30%) as a SEPARATE, labelled deduction** — not as the band. `uncertainty` string lists
  the components (density SE, loss CV, buffer) separately. Applies to **REDD (APD) and IFM** (`_estimate_redd` + `_estimate_ifm`).
- Contract: add `ForestData.biomass_uncertainty_pct: Optional[float] = None` (the engine consumes it).

### M2 — density-fallback gating + saturation honesty
- ESA CCI present → use it + **state the saturation caveat** (>~150–250 Mg/ha) + carry its SE into M1.
- ESA CCI missing, IPCC 657 default → **LOUD "default density — high uncertainty" flag** + widen the density SE. **No
  credible biomass source → FLAG (no number).**
- **GEDI/ICESat-2 → pre-launch backlog** (note it; don't build now).

### Tests / goldens
- Ranges **widen** (central ~stable; band wider) — **re-baseline goldens; document before→after per case in OUTBOX.**
- Buffer applied **separately + labelled**. Default-density (657) → loud flag. No-biomass → flag/no-number.
- Peat unchanged. Determinism intact. **No methodology-routing change** (APD/IFM/peat routing untouched).

### NOT in scope (later): M3 wording WO, then WO-DERIVE-001 (derivation, last on the corrected engine).
Commit + push; **OUTBOX = before→after golden table + contract diff**; **STOP for Cowork review.**
