from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.config import settings


class KnowledgeGraphService:
    """A lightweight graph abstraction with an optional Neo4j-backed layer."""

    def __init__(self) -> None:
        self._entities: dict[str, dict[str, Any]] = {}
        self._relationships: list[dict[str, Any]] = []
        self._neo4j_driver = None
        self._initialize_neo4j_driver()
        self._seed_default_graph()

    def _initialize_neo4j_driver(self) -> None:
        if not settings.USE_NEO4J or not settings.NEO4J_URI:
            return
        try:
            from neo4j import GraphDatabase
        except ImportError:
            return

        try:
            self._neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME or "neo4j", settings.NEO4J_PASSWORD or "neo4j"),
            )
        except Exception:
            self._neo4j_driver = None

    def _seed_default_graph(self) -> None:
        if self._entities:
            return
        self.add_entity("City", "Delhi", {"country": "India", "state": "Delhi"})
        self.add_entity("Zone", "Central Delhi", {"city": "Delhi", "land_use": "mixed_use"})
        self.add_entity("Pollutant", "PM2.5", {"unit": "ug/m3", "description": "Fine particulate matter"})
        self.add_entity("HealthImpact", "Respiratory Risk", {"population_group": "urban_population"})
        self.add_entity("Intervention", "Green Infrastructure", {"category": "nature_based"})
        self.add_entity("Policy", "National Clean Air Programme", {"jurisdiction": "India", "year": 2019})

        self.add_relationship("Delhi", "City", "HAS_ZONE", "Central Delhi", "Zone")
        self.add_relationship("Central Delhi", "Zone", "HAS_POLLUTANT_EXPOSURE", "PM2.5", "Pollutant")
        self.add_relationship("PM2.5", "Pollutant", "ASSOCIATED_WITH", "Respiratory Risk", "HealthImpact")
        self.add_relationship("Central Delhi", "Zone", "HAS_HEALTH_RISK", "Respiratory Risk", "HealthImpact")
        self.add_relationship("Green Infrastructure", "Intervention", "ADDRESSES", "PM2.5", "Pollutant")
        self.add_relationship("Green Infrastructure", "Intervention", "MAY_IMPROVE", "Respiratory Risk", "HealthImpact")
        self.add_relationship("National Clean Air Programme", "Policy", "SUPPORTS", "Green Infrastructure", "Intervention")
        self.add_relationship("Delhi", "City", "HAS_POLICY", "National Clean Air Programme", "Policy")

    def add_entity(self, entity_type: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        entity_key = self._entity_key(entity_type, name)
        payload = {"type": entity_type, "name": name, **(properties or {})}
        self._entities[entity_key] = payload
        return payload

    def add_relationship(
        self,
        source: str,
        source_type: str,
        relationship: str,
        target: str,
        target_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "source": source,
            "source_type": source_type,
            "relationship": relationship,
            "target": target,
            "target_type": target_type,
            **(properties or {}),
        }
        self._relationships.append(payload)
        self._entities.setdefault(self._entity_key(source_type, source), {"type": source_type, "name": source})
        self._entities.setdefault(self._entity_key(target_type, target), {"type": target_type, "name": target})
        return payload

    @staticmethod
    def _entity_key(entity_type: str, name: str) -> str:
        return f"{entity_type}:{name}"

    def get_related_entities(
        self,
        *,
        entity: str | None = None,
        entity_type: str | None = None,
        relationship: str | None = None,
        target_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if self._neo4j_driver is not None:
            try:
                return self._query_neo4j(
                    entity=entity,
                    entity_type=entity_type,
                    relationship=relationship,
                    target_type=target_type,
                )
            except Exception:
                pass

        matches: list[dict[str, Any]] = []
        for row in self._relationships:
            if entity and row["source"] != entity:
                continue
            if entity_type and row["source_type"] != entity_type:
                continue
            if relationship and row["relationship"] != relationship:
                continue
            if target_type and row["target_type"] != target_type:
                continue
            matches.append({
                "entity": row["source"],
                "entity_type": row["source_type"],
                "relationship": row["relationship"],
                "target": row["target"],
                "target_type": row["target_type"],
            })
        return matches

    def _query_neo4j(
        self,
        *,
        entity: str | None = None,
        entity_type: str | None = None,
        relationship: str | None = None,
        target_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if self._neo4j_driver is None:
            return []
        with self._neo4j_driver.session() as session:
            query = (
                "MATCH (n)-[r]->(m) WHERE (:Entity) <-[:IS_A]- (n) OR true "
                "RETURN n.name as entity, labels(n) as entity_types, type(r) as relationship, m.name as target, labels(m) as target_types"
            )
            if entity:
                query += " AND n.name = $entity"
            if entity_type:
                query += " AND $entity_type IN labels(n)"
            if relationship:
                query += " AND type(r) = $relationship"
            if target_type:
                query += " AND $target_type IN labels(m)"
            return list(
                session.run(
                    query,
                    entity=entity,
                    entity_type=entity_type,
                    relationship=relationship,
                    target_type=target_type,
                )
            )

    def get_interventions_for_pollutant(self, pollutant: str) -> list[str]:
        return [
            row["source"]
            for row in self._relationships
            if row["relationship"] == "ADDRESSES" and row["target"] == pollutant and row["target_type"] == "Pollutant"
        ]

    def get_policies_for_intervention(self, intervention: str) -> list[str]:
        return [
            row["source"]
            for row in self._relationships
            if row["relationship"] == "SUPPORTS" and row["target"] == intervention and row["target_type"] == "Intervention"
        ]

    def get_context_for_query(self, *, city: str | None = None, pollutant: str | None = None, intervention: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if city:
            results.extend(
                self.get_related_entities(entity=city, entity_type="City")
            )
        if pollutant:
            results.extend(
                self.get_related_entities(entity=pollutant, entity_type="Pollutant")
            )
        if intervention:
            results.extend(
                self.get_related_entities(entity=intervention, entity_type="Intervention")
            )
        return results

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        return len(self._relationships)

    def close(self) -> None:
        if self._neo4j_driver is not None:
            self._neo4j_driver.close()


knowledge_graph_service = KnowledgeGraphService()


def get_related_entities(*, entity: str | None = None, entity_type: str | None = None, relationship: str | None = None, target_type: str | None = None) -> list[dict[str, Any]]:
    return knowledge_graph_service.get_related_entities(
        entity=entity,
        entity_type=entity_type,
        relationship=relationship,
        target_type=target_type,
    )


def get_interventions_for_pollutant(pollutant: str) -> list[str]:
    return knowledge_graph_service.get_interventions_for_pollutant(pollutant)


def get_policies_for_intervention(intervention: str) -> list[str]:
    return knowledge_graph_service.get_policies_for_intervention(intervention)


def get_graph_context(*, city: str | None = None, pollutant: str | None = None, intervention: str | None = None) -> list[dict[str, Any]]:
    return knowledge_graph_service.get_context_for_query(city=city, pollutant=pollutant, intervention=intervention)
