from __future__ import annotations

import re

from app.digital_twin.service import get_virtual_city_model
from app.phase11.schemas import SimulationRequest


def _normalize_location(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _digital_twin_baseline(city: str, zone: str | None) -> tuple[dict[str, float], str]:
    if city.strip().casefold() != "delhi":
        return {}, ""

    model = get_virtual_city_model()
    if zone:
        wanted = _normalize_location(zone)
        ward_match = re.search(r"\bward[\s_-]*0*(\d+)\b", zone, re.IGNORECASE)
        matched_ward = None
        for ward in model.get("wards", []):
            values = {
                _normalize_location(str(ward.get("zone", ""))),
                _normalize_location(str(ward.get("location", ""))),
            }
            if ward_match and str(ward.get("ward_no")) == ward_match.group(1):
                matched_ward = ward
                break
            if wanted in values:
                matched_ward = ward
                break
        if matched_ward is None:
            return {}, ""
        source = (
            "Phase 5 Digital Twin "
            f"({matched_ward.get('location', matched_ward.get('zone', 'ward'))}, "
            f"{matched_ward.get('zone', 'ward')})"
        )
        return {
            key: float(matched_ward[key])
            for key in ("aqi", "temperature", "green_cover", "health_risk")
            if matched_ward.get(key) is not None
        }, source

    summary = model.get("summary", {})
    source = "Phase 5 Digital Twin Delhi city summary"
    summary_fields = {
        "aqi": "average_aqi",
        "temperature": "average_temperature_c",
        "green_cover": "average_green_cover_pct",
        "health_risk": "average_health_risk",
    }
    return {
        metric: float(summary[field])
        for metric, field in summary_fields.items()
        if summary.get(field) is not None
    }, source


def adapt_simulation_request(request: SimulationRequest) -> SimulationRequest:
    """Fill missing baseline fields from a matching Phase 5 Delhi Digital Twin record."""
    inputs = request.simulation_input
    baseline, source = _digital_twin_baseline(
        request.scenario.city or request.urban_state.request.city,
        request.scenario.zone or request.urban_state.request.zone,
    )
    if not baseline:
        return request

    merged_baseline = {**baseline, **inputs.baseline_metrics}
    sources = dict(inputs.baseline_sources)
    for metric in inputs.baseline_metrics:
        sources.setdefault(metric, "SimulationInput baseline")
    for metric in baseline:
        sources.setdefault(metric, source)
    adapted_inputs = inputs.model_copy(update={
        "baseline_metrics": merged_baseline,
        "baseline_sources": sources,
    })
    return request.model_copy(update={"simulation_input": adapted_inputs})
