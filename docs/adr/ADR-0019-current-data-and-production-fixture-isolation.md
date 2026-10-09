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
## Live verification follow-up, 9 October 2026

The deployed release accepted synthetic Carbon, EUDR and Fieldwork submissions and returned both PDFs. EUDR detected 1.32 ha after 2020 on the synthetic 492 ha test polygon. The public-flow check also found stale Carbon chart averaging labels and EUDR wording implying optional radar had always succeeded. Correct the displayed Carbon averaging years from the supplied series, disclose radar as optional and checked per plot, and mark invalid or unread satellite results incomplete in the readiness checklist. Remove the blanket simplified-due-diligence claim that geolocation is never required; the Commission states that information gathering remains required (https://green-forum.ec.europa.eu/countries-and-partnerships_en, checked 9 October 2026). These are bounded corrections within the user's authorized repair and deployment.

PDF and DOCX checks also found the old loss averaging window, a V3 footer, a broken main-site methodology URL and permit-right assertions unsupported by input evidence. Reports now show the screening status, use current loss years and actual dataset attribution, link the deployed methodology page, and describe the declared permit as a scenario assumption. A missing non-peat estimate is not presented as a peat restoration opportunity. Numerical calculations and existing golden quantities remain unchanged by this follow-up.
