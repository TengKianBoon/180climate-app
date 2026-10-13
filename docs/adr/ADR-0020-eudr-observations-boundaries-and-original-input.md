# ADR-0020: EUDR observations, boundary review and original input

Decision date: 13 October 2026. John authorised investigation and repair of the
EUDR application following an eleven-plot user test. Existing private intake,
geometry retention, access controls, processor destinations and hosting remain.

## Problem

An inconclusive decision can mean a successful non-forest baseline classification
or an unavailable read. The previous message guessed at imagery causes without
recording observations. Individually valid polygons were not checked against
one another. Small areas rounded to zero in findings. The private intake stored
the simplified DDS preparation pack: small polygons became points and invalid
shapes were omitted, preventing complete historical replay.

## Decision

- Add backward-compatible optional observation fields to PlotVerdict: forest_2020,
  baseline_forest_pct, hansen_available, radar_available and reason_codes. Missing
  historical fields remain unknown. Preserve the existing decision truth table
  and derived geometry_ok / satellite-risk invariants. The 10% forest-pixel
  threshold is a tool assumption, not a legal forest classification.
- Explain the actual observations. A read below the baseline threshold is not
  called an image failure. Keep separately measured tree-cover loss visible even
  when the baseline needs review. Missing loss values cannot be described as
  confirmed zero; availability is explicit. Radar absence remains optional.
- Check overlapping interiors among valid polygons in the same upload using a
  spatial index and WGS84 geodesic area. Shared borders and sub-0.01-square-metre
  numerical slivers are excluded. Points and invalid inputs remain unassessed.
  No cross-submission or ownership check is claimed. Overlap findings do not
  change satellite detections, but prevent an overall clear result and complete
  screening readiness.
- Render actual validated boundaries on the map. Keep the separate simplified
  geolocation download for backward compatibility. Display small areas in
  decimal hectares or square metres.
- When existing geometry retention is enabled, the private geometry object
  contains full validated features plus `_source_input` with format, encoding
  and original file bytes (base64). This retains malformed/invalid input and
  literal precision too. Pasted GeoJSON text is preserved. The field is never
  returned in the public response or persisted in result/form JSON. The existing
  geometry-retention switch, expiry and protected operator export apply to the
  entire object. No schema migration or public raw-upload endpoint is added.
- Commodity remains user-declared. No rubber classification model or compliance
  clearance is introduced. No historical missing boundary is reconstructed.

## Gate C verification

Run contract type-check and the existing contracts, EUDR geometry/triage/API,
intake, reports and register suite, plus synthetic regressions for overlapping
and touching polygons, holes, points, non-forest versus unavailable data,
small areas, and original-source recovery with retention on and off. Keep real
user coordinates, results and investigation notes outside Git. Local tests,
CI, deployment and plot accuracy are separate evidence.
