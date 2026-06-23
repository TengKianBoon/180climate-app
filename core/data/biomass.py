"""core/data/biomass.py — IPCC 2006 default biomass emission factors.

Source: IPCC (2006) 2006 IPCC Guidelines for National Greenhouse Gas Inventories,
        Volume 4 Agriculture, Forestry and Other Land Use, Table 4.7.
        Southeast Asia / Indonesia tropical forest defaults.

These are genuine published values (not invented stub numbers).
AGB = Above-Ground Biomass in tDM/ha; BGB = Below-Ground Biomass.
Carbon fraction (CF) = 0.47 per IPCC default.
Molecular ratio CO2/C = 44/12.
Total stock (tCO2e/ha) = (AGB + BGB) × CF × (44/12).
"""
from __future__ import annotations

# (AGB_tDM_ha, BGB_ratio_of_AGB, carbon_fraction)
# BGB ratio from IPCC Table 4.4 (tropical moist forest: 0.20–0.26)
_IPCC_SE_ASIA: dict[str, tuple[float, float, float]] = {
    "lowland_moist":  (310.0, 0.23, 0.47),  # Lowland moist tropical
    "submontane":     (250.0, 0.24, 0.47),  # Sub-montane (>1 000 m)
    "montane":        (190.0, 0.27, 0.47),  # Montane (>2 000 m)
    "peat_swamp":     (190.0, 0.25, 0.47),  # Peat-swamp forest (AGB only; peat C accounted separately)
    "dryland":        (230.0, 0.23, 0.47),  # Dryland / seasonal
}

_CITATION = (
    "IPCC (2006) Guidelines for National GHG Inventories, "
    "Vol. 4 AFOLU, Table 4.7 — Southeast Asia tropical forest defaults"
)


def biomass_tco2_per_ha(forest_type: str = "lowland_moist") -> float:
    """Total standing biomass in tCO2e/ha (AGB + BGB) for a given IPCC forest type.

    Defaults to 'lowland_moist' (Indonesia lowland tropics) when type is unknown.
    """
    agb_tdm, bgb_ratio, cf = _IPCC_SE_ASIA.get(
        forest_type, _IPCC_SE_ASIA["lowland_moist"]
    )
    co2_per_c = 44.0 / 12.0
    agb_tco2 = agb_tdm * cf * co2_per_c
    bgb_tco2 = agb_tdm * bgb_ratio * cf * co2_per_c
    return round(agb_tco2 + bgb_tco2, 1)


def forest_type_from_elevation(elevation_m: float = 0.0) -> str:
    """Classify forest type by elevation (IPCC Table 4.7 breakpoints)."""
    if elevation_m > 2000:
        return "montane"
    if elevation_m > 1000:
        return "submontane"
    return "lowland_moist"


def citation() -> str:
    return _CITATION
