from typing import Dict, List, Optional, TypedDict

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
    comments: Optional[str] = Field(
        default=None,
        description="Additional context about vulnerability or special conditions",
    )
    timestamp: Optional[str] = Field(
        default=None, description="When this asset data was recorded"
    )
    source: Optional[str] = Field(
        default=None, description="Source of this asset information"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="Tags for categorization"
    )


class Danger(BaseModel):
    """
    Represents a threat, like a "Fire" or "Heavy_Storm".
    """

    id: str
    type: str
    location: dict
    comments: Optional[str] = Field(
        default=None, description="Additional threat context or evolution details"
    )
    severity: Optional[str] = Field(
        default=None, description="Threat intensity: low, medium, or high"
    )
    timestamp: Optional[str] = Field(
        default=None, description="When this danger was detected"
    )
    source: Optional[str] = Field(
        default=None, description="Source of this danger information"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="Tags for categorization"
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
    evacuation_zone_assignments: Optional[Dict[str, str]] = Field(
        default=None, description="Mapping of asset_id to assigned evacuation_zone_id"
    )
    helpers: List[str]  # Actors assigned to assist
    plan_quality_score: float  # For self-evaluation
    plan_schematic: str = Field(
        description="Visual schematic summary of the plan with numbered steps, priorities, and timeline. Must be concise and easy to scan."
    )
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
    route_details: Optional[List[dict]]  # NEW: Evacuation route information

    # Planning
    proposed_plan: Optional[EvacuationPlan]
    evaluation_feedback: Optional[str]
    retry_count: int

    # Output
    final_plan: Optional[EvacuationPlan]
    notifications_sent: bool
    error: Optional[str]
