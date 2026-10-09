# ADR-0019: current satellite data and production isolation

Decision date: 9 October 2026. This is a corrective release to the existing public beta, authorised by John's request to carry out the combined repair now. The existing controller, storage, access, retention and hosting decisions continue to apply.

## Problem

The production release defaults to a JRC V3 file that now returns 404 and Hansen loss ending in 2022. Carbon also takes historical canopy from a deterministic sample adapter. Overlay fixtures are currently checked in production by rounded coordinates; the Carbon cache is keyed only by centroid and area. A healthy process does not establish a healthy satellite connection.

## Decision

- Read JRC GFC2020 V4 and Hansen GFC-2025-v1.13. Keep version provenance with results. JRC directory discovery may recover a replacement filename after a 404.
- Count pixels within the polygon. Missing pixels, unresolved tile crossings and sub-pixel plots remain unavailable. Bound raster windows to protect the existing small host.
- Carbon uses actual historical Hansen treecover2000 and the latest eight available loss years from 2016 onward. Missing essential reads yield a review flag without a quantity. No generated sample replaces a failed live read.
- Committed fixtures are accessible only under explicit `SCREENING_USE_TEST_FIXTURES=true` in tests. Production cache keys include the geometry and release, live cache entries expire after 24 hours, and failures are not cached as successful data.
- Add `/health/data` (503 when a required source is unavailable), `/methodology`, robots and sitemap. Health probes prove HTTP reachability, not plot coverage. Radar enrichment remains optional and its absence is disclosed.
- Preserve the existing 30-year illustrative Carbon scenario and registry/legality review boundaries. No shared contract is changed.

## Verification

Use synthetic rasters to prove 2024–2025 loss is included, neighbouring loss is excluded, nodata cannot become zero loss, and forest outside the polygon is excluded. Run the existing numerical, API, report and intake tests. Verify real public raster reads and synthetic public application flows after deployment. Source, CI, deployment, database acceptance and recipient email delivery are distinct evidence.
