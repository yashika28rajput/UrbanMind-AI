from __future__ import annotations

from app.phase9.schemas import PolicyResult


def query_policy_rag(city: str, zone: str, interventions: list[str]) -> PolicyResult:
    policies = ["National Clean Air Programme", "Delhi Master Plan guidance"] if interventions else ["General urban planning guidance"]
    constraints = ["Budget approval required", "Zone-level implementation approval"]
    requirements = ["Environmental review before deployment"]
    return PolicyResult(
        applicable_policies=policies,
        constraints=constraints,
        requirements=requirements,
        policy_conflicts=[],
        jurisdiction=city,
        evidence_ids=["policy-evidence-01"],
    )
