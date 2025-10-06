from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field

"""
Defines the data structure of the emergency assistant project.
It has pydantic models and the TypedDict for the graph state.
"""


class Asset(BaseModel):
    """
    Represents a static entity on the map, such as a "Radar" or "DataCenter".
    """

    id: str
    type: str
    location: dict
    description: str
    comments: Optional[str] = Field(
        default=None,
        description="Additional context about vulnerability or special conditions",
    )


class Danger(BaseModel):
    """
    Represents a threat, like a "Fire" or "Heavy_Storm".
    """

    id: str
    type: str
    location: dict
    description: str
    comments: Optional[str] = Field(
        default=None, description="Additional threat context or evolution details"
    )
    severity: Optional[str] = Field(
        default=None, description="Threat intensity: low, medium, or high"
    )


class RiskAssessment(BaseModel):
    """
    This model is used to formalize the output of an analysis step.
    It links an asset_id to a danger_id, calculates the distance_km between them,
    and assigns a risk_level to help with prioritization.
    """

    asset_id: str
    danger_id: str
    distance_km: float
    risk_level: str  # "high", "medium", "low"


class EvacuationPlan(BaseModel):
    """
    This is the core output of your planning agent.
    It's a structured format for the final plan.
    """

    assets_to_evacuate: List[str]
    helpers: List[str]  # Actors assigned to assist
    plan_quality_score: float  # For self-evaluation
    reasoning: str


class GraphState(TypedDict):
    """
    The GraphState is a specialized dictionary that serves as the central
    memory for LangGraph. Every node in your graph reads from and writes
    to this state.
    """

    # Input
    raw_input: dict
    assets: List[Asset]
    dangers: List[Danger]

    # Analysis
    risk_assessments: List[RiskAssessment]
    route_details: Optional[List[dict]]

    # Planning
    proposed_plan: Optional[EvacuationPlan]
    evaluation_feedback: Optional[str]
    retry_count: int

    # Output
    final_plan: Optional[EvacuationPlan]
    notifications_sent: bool
    error: Optional[str]
