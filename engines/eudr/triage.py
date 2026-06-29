"""engines/eudr/triage.py — EUDR per-plot satellite triage engine (ADR-0018, E3).

For each geometry-valid plot, combine three deterministic adapters into a single
`PlotVerdict.detection ∈ {clear_in_screen, loss_detected, inconclusive}` against the EUDR
31-Dec-2020 cutoff, with a `datasets_version` + `run_date` provenance stamp. The
`geometry_ok` and `plot_satellite_risk` computed fields follow from `detection` automatically
(ADR-0018 micro-amendments).

Datasets (each: live HTTP + fixture-cache fallback + *_DISABLE_LIVE switch + version stamp):
  1. JRC GFC2020  — 2020 forest baseline (the EU's reference map; credibility anchor)
  2. Hansen lossyear — post-2020 optical loss (reuses core/data/gfw.py)
  3. RADD radar alerts — post-2020 radar loss (ENRICHES; stubbed by default — non-blocking)

Detection logic (deterministic, pure):
  • loss_detected   — forest in JRC GFC2020 AND a post-2020 loss signal
                      (Hansen loss_ha > 0 OR RADD alert after 2020-12-31).
  • clear_in_screen — forest in JRC GFC2020 AND Hansen confirms ZERO post-2020 loss AND
                      RADD shows no alert (RADD None is allowed — it enriches, not blocks).
  • inconclusive    — anything else: no/unknown 2020 baseline, Hansen unavailable, sub-
                      resolution, data gaps, or any adapter returns None/uncertain.

HONESTY RULE (value-first, non-negotiable): when in doubt → inconclusive or loss_detected,
NEVER clear_in_screen. `clear_in_screen` requires a POSITIVE "real 2020 forest baseline +
Hansen-confirmed no post-2020 loss" read. Determinism: pure functions; no LLM; live reads
are cached/fixture for CI.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from shapely.geometry import shape as _shapely_shape

from core.contracts import Boundary, PlotVerdict
from core.overlays.hansen_loss import query_hansen_loss
from core.overlays.jrc_gfc2020 import query_jrc_gfc2020
from core.overlays.radd import query_radd

EUDR_CUTOFF_YEAR = 2020
EUDR_CUTOFF_DATE = "2020-12-31"

Detection = Literal["clear_in_screen", "loss_detected", "inconclusive"]


def _decide_detection(
    forest_2020: Optional[bool],
    hansen_loss_ha: Optional[float],
    radd_alert_after_cutoff: Optional[bool],
) -> Detection:
    """Pure detection rule. Honesty rule: never clear_in_screen in doubt.

    Truth table (forest_2020, hansen_loss_ha, radd_alert):
      (True,  >0,    *   ) -> loss_detected      # optical loss on a forest baseline
      (True,  any,   True) -> loss_detected      # radar caught loss (even if Hansen 0/None)
      (True,  ==0,   not-True) -> clear_in_screen  # positive no-loss read; RADD None ok
      (True,  None,  not-True) -> inconclusive   # Hansen unavailable — cannot confirm no-loss
      (False, *,     *   ) -> inconclusive       # no 2020 forest baseline to clear/lose
      (None,  *,     *   ) -> inconclusive       # baseline unknown — never clear
    """
    has_post_cutoff_loss = (
        hansen_loss_ha is not None and hansen_loss_ha > 0.0
    ) or (radd_alert_after_cutoff is True)

    # loss_detected requires a confirmed 2020 forest baseline AND a positive loss signal.
    if forest_2020 is True and has_post_cutoff_loss:
        return "loss_detected"

    # clear_in_screen is the ONLY positive case: real baseline + Hansen-confirmed zero loss,
    # and no RADD alert (RADD None is acceptable — it enriches, it does not block).
    if (
        forest_2020 is True
        and hansen_loss_ha is not None
        and hansen_loss_ha == 0.0
        and radd_alert_after_cutoff is not True
    ):
        return "clear_in_screen"

    # Everything else — unknown baseline, non-forest baseline, Hansen unavailable, ambiguity.
    return "inconclusive"


def _boundary_from_geojson(geojson: dict, area_ha: float = 0.0) -> Boundary:
    """Build a Boundary (centroid + area) from a validated plot geometry."""
    geom = _shapely_shape(geojson)
    centroid = geom.centroid
    return Boundary(
        geojson=geojson,
        area_ha=area_ha,
        centroid_lat=float(centroid.y),
        centroid_lon=float(centroid.x),
        is_valid=True,            # geometry already validated in E2
        within_indonesia=True,    # scope assumption (Indonesia screen); not used by triage
        source_fmt="geojson",
    )


def triage_plot(
    plot_id: str,
    geojson: dict,
    commodity: str,
    *,
    area_ha: float = 0.0,
    run_date: Optional[date] = None,
) -> PlotVerdict:
    """Run the three-dataset satellite triage on ONE geometry-valid plot → PlotVerdict.

    `run_date` is injectable for deterministic tests (defaults to today's date).
    """
    if run_date is None:
        run_date = date.today()

    boundary = _boundary_from_geojson(geojson, area_ha)

    jrc = query_jrc_gfc2020(boundary)
    hansen = query_hansen_loss(boundary, cutoff_year=EUDR_CUTOFF_YEAR)
    radd = query_radd(boundary, cutoff_date=EUDR_CUTOFF_DATE)

    detection = _decide_detection(
        jrc.forest_2020, hansen.loss_after_2020_ha, radd.alert_after_cutoff
    )

    # The verdict carries a concrete loss figure; None (unavailable) surfaces as 0.0 but the
    # detection is already inconclusive in that case (no false "clear").
    loss_ha = hansen.loss_after_2020_ha if hansen.loss_after_2020_ha is not None else 0.0

    datasets_version = "; ".join(
        [jrc.datasets_version, hansen.datasets_version, radd.datasets_version]
    )

    return PlotVerdict(
        plot_id=plot_id,
        detection=detection,
        loss_after_2020_ha=round(float(loss_ha), 2),
        commodity=commodity,
        datasets_version=datasets_version,
        run_date=run_date,
    )


def triage_validated_plots(
    validations,
    commodity: str,
    *,
    run_date: Optional[date] = None,
) -> list[PlotVerdict]:
    """Triage a batch of E2 `PlotValidation` results → one PlotVerdict per plot.

    geometry_invalid plots (already handled in E2) are passed through as a geometry_invalid
    verdict WITHOUT any adapter calls — they are skipped from satellite triage. All other
    plots are screened. `commodity` is the file/operator-level commodity (EUDRInput.commodity).
    """
    if run_date is None:
        run_date = date.today()

    verdicts: list[PlotVerdict] = []
    for v in validations:
        if v.detection == "geometry_invalid" or not v.geometry_ok or v.geojson is None:
            verdicts.append(
                PlotVerdict(
                    plot_id=v.plot_id,
                    detection="geometry_invalid",
                    loss_after_2020_ha=0.0,
                    commodity=commodity,
                    datasets_version="n/a — geometry invalid (Art-9, E2); not screened",
                    run_date=run_date,
                )
            )
            continue
        verdicts.append(
            triage_plot(
                v.plot_id,
                v.geojson,
                commodity,
                area_ha=v.area_ha,
                run_date=run_date,
            )
        )
    return verdicts
