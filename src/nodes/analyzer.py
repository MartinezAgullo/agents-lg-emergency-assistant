# src/nodes/analyzer.py

from typing import Any, Dict, List

from ..state import GraphState, RiskAssessment
from ..tools import assess_risk_level, calculate_distance


def analyze_risks(state: GraphState) -> Dict[str, Any]:
    """
    Analyze risks by calculating distances between assets and dangers.

    For each asset-danger pair, computes distance and assigns a risk level
    based on proximity and danger type.
    """
    assets = state["assets"]
    dangers = state["dangers"]

    risk_assessments: List[RiskAssessment] = []

    for asset in assets:
        for danger in dangers:
            # Calculate distance between asset and danger
            distance_km = calculate_distance(
                asset.location["lat"],
                asset.location["lon"],
                danger.location["lat"],
                danger.location["lon"],
            )

            # Assess risk level based on distance, danger type, and contextual info
            risk_level = assess_risk_level(
                distance_km=distance_km,
                danger_type=danger.type,
                asset=asset,
                danger=danger,
            )

            risk_assessment = RiskAssessment(
                asset_id=asset.id,
                danger_id=danger.id,
                distance_km=distance_km,
                risk_level=risk_level,
            )

            risk_assessments.append(risk_assessment)

    return {"risk_assessments": risk_assessments}
