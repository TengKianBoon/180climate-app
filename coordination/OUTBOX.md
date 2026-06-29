# OUTBOX — Builder → Cowork · WO-EUDR-CONTRACTS-001 (E1) · 2026-06-29

## Status: CI GREEN ✅ — Reviewer PASS — STOPPED for Cowork review (306 tests passed, 7 new)

Implements **ADR-0018** (Gate C signed). EUDR section of `core/contracts` only — **carbon contracts untouched**. Triage & DDS-prep screen, never a compliance verdict.

---

## Change — `core/contracts/__init__.py` (EUDR section)

| ADR-0018 point | Before | After |
|---|---|---|
| 1. Detection | `PlotVerdict.deforestation_free: bool` | `detection: Literal["clear_in_screen","loss_detected","inconclusive","geometry_invalid"]` |
| 2. Readiness | `EUDRVerdict.readiness_score: int` (0–100) | `readiness: list[ReadinessItem]` (new model; `status: Literal["complete","incomplete"]`) — **no numeric score** |
| 3. Role | `EUDRInput.role: Literal["operator","trader"]` | `Literal["eu_first_placer","downstream_operator","non_eu_supplier"]` |
| 3. Commodity | (only on `Plot`) | `EUDRInput.commodity` enum (5 + `manual_review`); `Plot.commodity` also extended with `manual_review` |
| 4. Risk axes | `EUDRVerdict.indonesia_risk_tier` (single) | **two separate fields**: `country_benchmark_risk` (Indonesia→`standard`, on `EUDRInput`+`EUDRVerdict`) and `plot_satellite_risk: Literal["low","high","inconclusive"]` (on `PlotVerdict`) |
| 5. Provenance | — | `datasets_version: str` + `run_date: date` on **both** `PlotVerdict` and `EUDRVerdict` |
| 6. Overall verdict | `Literal["compliant","non_compliant","needs_review"]` | `Literal["clear_in_screen","loss_detected","review_needed"]` — removes the banned `compliant` |
| 6. Export naming | `dds_pack: dict` | `geolocation_pack: dict` ("geolocation pack for DDS preparation") |
| 6. Banned guard | — | `EUDR_BANNED_SUBSTRINGS` module constant (single source of truth) |

Added `from datetime import date`. No LLM/HTTP imports — determinism intact.

---

## Banned-string contract-guard (ADR-0018 §6)

Banned substrings (case-insensitive): **`compliant`** (also catches `non_compliant`), **`deforestation-free`**, **`dds-ready`**, **`due diligence statement ready`**.

`test_eudr_banned_strings_absent_from_serialized_output_and_schema` scans, for every EUDR model:
- `model_dump_json()` of fully-populated instances (covers runtime values), **and**
- `model_json_schema()` (covers enum literals, field names, defaults, and class docstrings-as-descriptions).

All clean. `test_eudr_banned_string_guard_catches_a_violation` proves the guard fires on a deliberately-bad fixture. **Additionally verified out-of-band** that injecting a banned phrase into a real `EUDRVerdict` free-text field is caught (`compliant` + `dds-ready` detected) — bad fixture discarded, not committed.

---

## Tests — `tests/test_contracts.py` (7 new)

`test_eudr_input_role_commodity_and_country_risk`, `test_plot_verdict_uses_detection_enum_not_bool`, `test_eudr_readiness_is_categorical_no_numeric_score`, `test_eudr_country_and_plot_risk_are_distinct_fields`, `test_eudr_provenance_stamp_present`, `test_eudr_banned_strings_absent_from_serialized_output_and_schema`, `test_eudr_banned_string_guard_catches_a_violation`.

**306 tests green** (was 299). Carbon contract tests unchanged + green.

---

## Reviewer (white-box) — PASS

All 8 ADR-0018 decision points satisfied; carbon contracts confirmed untouched (only `date` import + EUDR section changed); determinism intact (stdlib + pydantic only).

### Advisor-divergence flags to resolve before E4+ (informational — NOT blockers; ADR-0018 sanctions current names)
1. **Three vocabularies for the "middle" (not-clear, not-loss) state**: `EUDRVerdict.overall="review_needed"` vs `PlotVerdict.detection="inconclusive"` vs readiness `"incomplete"`. Deliberate (`review_needed` avoids `needs_review`→compliant-family), but an advisor may want one consistent term.
2. **`plot_satellite_risk` = `["low","high","inconclusive"]`** omits a `standard` mid-tier, unlike `country_benchmark_risk = ["low","standard","high"]`. Intentional asymmetry (binary triage + inconclusive escape vs EU 3-tier benchmark); ADR-0018 §4 doesn't pin the plot set — advisor nod wanted.
3. **`detection="geometry_invalid"` vs `PlotVerdict.geometry_ok: bool`** — mild redundancy. Engine (E2+) must keep them consistent; advisor may ask whether one is derivable.

---

## Commit

`90d4a3e` — pushed to `main` — `feat(contracts): EUDR detection enum + categorical readiness + provenance (ADR-0018, Gate C)`
