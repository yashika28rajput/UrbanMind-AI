from __future__ import annotations

import re

from app.phase10.schemas import InterventionDefinition


class InterventionCatalog:
    """In-process extensible registry of intervention metadata, not impact estimates."""

    def __init__(self, definitions: list[InterventionDefinition] | None = None) -> None:
        self._definitions: dict[str, InterventionDefinition] = {}
        for definition in definitions or default_interventions():
            self.register(definition)

    def register(self, definition: InterventionDefinition) -> None:
        self._definitions[definition.intervention_id] = definition

    def get(self, intervention_id: str) -> InterventionDefinition | None:
        normalized = normalize_intervention(intervention_id)
        for definition in self._definitions.values():
            if normalized in {
                normalize_intervention(definition.intervention_id),
                normalize_intervention(definition.name),
                *(normalize_intervention(alias) for alias in definition.aliases),
            }:
                return definition
        return None

    def all(self) -> list[InterventionDefinition]:
        return list(self._definitions.values())

    def relevant_to(self, problems: list[str]) -> list[InterventionDefinition]:
        problem_set = set(problems)
        return [
            definition
            for definition in self._definitions.values()
            if problem_set.intersection(definition.target_problems)
        ]


def normalize_intervention(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def default_interventions() -> list[InterventionDefinition]:
    return [
        InterventionDefinition(
            intervention_id="urban_forest_expansion",
            name="Urban Forest Expansion",
            category="green_infrastructure",
            description="Expand urban forest coverage in suitable areas identified by the planner.",
            target_problems=["high_pm25", "high_aqi", "high_uhi", "low_green_cover", "high_population_exposure"],
            required_parameters=["area_hectares", "tree_density"],
            optional_parameters=["target_zone", "species"],
            applicable_contexts=["urban", "publicly accessible land"],
            cost_model=None,
            impact_models=[],
            policy_dependencies=["land-use approval", "environmental review"],
            aliases=["urban forest", "tree plantation", "tree cover expansion", "green infrastructure"],
        ),
        InterventionDefinition(
            intervention_id="electric_bus_deployment",
            name="Electric Bus Deployment",
            category="public_transport",
            description="Deploy electric buses on planner-selected public transport routes.",
            target_problems=[
                "high_pm25",
                "high_aqi",
                "high_traffic_emissions",
                "high_carbon_emissions",
                "high_population_exposure",
            ],
            required_parameters=["number_of_buses", "deployment_period_years"],
            optional_parameters=["routes", "charging_sites"],
            applicable_contexts=["public transport network"],
            cost_model=None,
            impact_models=[],
            policy_dependencies=["fleet procurement approval", "charging infrastructure approval"],
            aliases=["electric buses", "e-bus deployment", "electric bus fleet"],
        ),
        InterventionDefinition(
            intervention_id="green_roof_program",
            name="Green Roof Program",
            category="green_infrastructure",
            description="Install green roofs on buildings selected for the program.",
            target_problems=["high_uhi", "low_green_cover", "high_pm25", "high_aqi"],
            required_parameters=["building_count", "roof_area_m2"],
            optional_parameters=["target_zone"],
            applicable_contexts=["buildings with structurally suitable roofs"],
            cost_model=None,
            impact_models=[],
            policy_dependencies=["building-owner consent", "building-code review"],
            aliases=["green roofs", "green roof programme"],
        ),
        InterventionDefinition(
            intervention_id="cool_roof_program",
            name="Cool Roof Program",
            category="building_efficiency",
            description="Apply cool-roof measures to eligible buildings selected by the planner.",
            target_problems=["high_uhi", "high_energy_demand"],
            required_parameters=["building_count", "roof_area_m2"],
            optional_parameters=["target_zone"],
            applicable_contexts=["buildings with eligible roofs"],
            cost_model=None,
            impact_models=[],
            policy_dependencies=["building-code review"],
            aliases=["cool roofs", "cool roof programme"],
        ),
        InterventionDefinition(
            intervention_id="traffic_management",
            name="Traffic Management",
            category="transport",
            description="Apply planner-defined traffic management measures to specified roads.",
            target_problems=["high_pm25", "high_traffic_emissions", "high_carbon_emissions", "high_population_exposure"],
            required_parameters=["target_roads", "implementation_period_years"],
            optional_parameters=["measure"],
            applicable_contexts=["road network"],
            cost_model=None,
            impact_models=[],
            policy_dependencies=["traffic authority approval"],
            aliases=["traffic reduction", "traffic demand management"],
        ),
        InterventionDefinition(
            intervention_id="public_transport_expansion",
            name="Public Transport Expansion",
            category="public_transport",
            description="Expand public transport service according to a planner-provided service plan.",
            target_problems=["high_traffic_emissions", "high_carbon_emissions", "high_population_exposure"],
            required_parameters=["additional_route_km", "implementation_period_years"],
            optional_parameters=["target_routes"],
            applicable_contexts=["public transport network"],
            cost_model=None,
            impact_models=[],
            policy_dependencies=["transport authority approval"],
            aliases=["public transport improvement", "transit expansion"],
        ),
    ]


intervention_catalog = InterventionCatalog()
