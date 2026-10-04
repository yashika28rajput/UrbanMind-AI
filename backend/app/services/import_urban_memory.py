import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.urban_memory import create_memory


PROJECT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_DIR / "data" / "processed"


def _json_safe_row(row: pd.Series) -> dict[str, Any]:
    return json.loads(row.to_json(date_format="iso"))


def import_existing_phase_data() -> dict[str, int]:
    counts = {"created": 0, "already_present": 0, "sources": 0}
    sources = [
        (
            DATA_DIR / "ml" / "environmental" / "delhi_ward_environmental_risk.csv",
            "environment",
            "environmental_risk",
            "Environmental conditions",
            "environmental_risk_category",
        ),
        (
            DATA_DIR / "decision" / "delhi_ward_final_decisions.csv",
            "recommendation",
            "final_decision",
            "Urban intervention recommendation",
            "final_decision_status",
        ),
        (
            DATA_DIR / "scenarios" / "delhi_intervention_scenarios.csv",
            "simulation",
            "intervention_scenario",
            "Intervention scenario simulation",
            None,
        ),
        (
            DATA_DIR / "ml" / "interventions" / "delhi_ward_intervention_impacts.csv",
            "simulation",
            "intervention_impact",
            "Estimated intervention impact",
            None,
        ),
    ]

    for path, memory_type, source_name, title_prefix, outcome_column in sources:
        if not path.exists():
            continue
        counts["sources"] += 1
        frame = pd.read_csv(path)
        if frame.empty:
            continue

        for _, row in frame.iterrows():
            data = _json_safe_row(row)
            ward = data.get("Ward_No")
            ward_name = data.get("Ward_Name")
            intervention = data.get("intervention")
            location = f"Ward {ward}" if ward is not None else "Delhi"
            if ward_name:
                location += f" ({ward_name})"
            title_parts = [title_prefix, location]
            if intervention:
                title_parts.append(str(intervention))
            title = " — ".join(title_parts)
            content = " | ".join(
                f"{key}: {value}"
                for key, value in data.items()
                if value is not None
            )

            outcome = "unknown"
            if outcome_column:
                raw_outcome = str(data.get(outcome_column, "")).strip().lower()
                if raw_outcome in {"success", "successful"}:
                    outcome = "success"
                elif raw_outcome in {"failure", "failed"}:
                    outcome = "failure"
                elif raw_outcome in {"ongoing", "in_progress"}:
                    outcome = "ongoing"

            source_ref = f"{source_name}:{ward}:{intervention or 'current'}"
            stored = create_memory(
                memory_type=memory_type,
                city="Delhi",
                zone=f"Ward_{ward}" if ward is not None else None,
                title=title,
                content=content,
                structured_data=data,
                outcome=outcome,
                source_ref=source_ref,
            )
            if stored["created"]:
                counts["created"] += 1
            else:
                counts["already_present"] += 1

    return counts


if __name__ == "__main__":
    print(json.dumps(import_existing_phase_data(), indent=2))
