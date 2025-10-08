# src/state.py

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
    reasoning: str = Field(
        description="Detailed reasoning explaining the plan's strategy, risk considerations, and decision-making process"
    )


# ==================== EVALUATION MODELS ====================


class OperationalEvaluation(BaseModel):
    """Evaluation focused on saving lives and minimizing losses"""

    quality_score: float = Field(
        description="Score 0.0-1.0 based on life-saving effectiveness (STRICT: 0.7+ to approve)"
    )
    feedback: str = Field(
        description="Detailed feedback on operational feasibility and safety"
    )
    critical_gaps: List[str] = Field(
        default_factory=list,
        description="List of critical safety gaps that MUST be addressed",
    )
    acceptable_losses: List[str] = Field(
        default_factory=list,
        description="List of assets/areas where losses are acceptable if necessary to save higher-value targets",
    )
    approved: bool = Field(
        description="True if plan meets minimum operational safety standards"
    )


class PoliticalCost(BaseModel):
    """A single political cost item"""

    issue: str = Field(description="The political issue or concern")
    severity: str = Field(
        description="Severity level: 'low', 'medium', 'high', or 'critical'"
    )


class SocialPoliticalEvaluation(BaseModel):
    """Evaluation of social and political implications"""

    quality_score: float = Field(
        description="Score 0.0-1.0 based on political feasibility (LENIENT: 0.5+ to approve)"
    )
    feedback: str = Field(
        description="Analysis of political risks and social implications"
    )
    political_costs: List[PoliticalCost] = Field(
        default_factory=list,
        description="List of political costs with their severity levels",
    )
    sovereignty_violations: List[str] = Field(
        default_factory=list,
        description="List of border/airspace/territorial violations",
    )
    public_perception_risks: List[str] = Field(
        default_factory=list,
        description="Issues that may cause panic, perceived favoritism, or inequality",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Suggestions to reduce political costs while maintaining effectiveness",
    )
    approved: bool = Field(
        description="True if political costs are acceptable given the emergency"
    )


class EconomicEvaluation(BaseModel):
    """Evaluation of economic feasibility and cost-effectiveness"""

    quality_score: float = Field(
        description="Score 0.0-1.0 based on cost-effectiveness (LENIENT: 0.5+ to approve)"
    )
    feedback: str = Field(
        description="Analysis of costs, resource availability, and economic impact"
    )
    estimated_total_cost: str = Field(
        description="Rough estimate of total cost (e.g., '$500K-1M', 'High', 'Moderate')"
    )
    resource_constraints: List[str] = Field(
        default_factory=list,
        description="List of potential resource shortages (fuel, vehicles, personnel)",
    )
    cost_benefit_analysis: str = Field(description="Brief cost vs. benefit assessment")
    recommendations: List[str] = Field(
        default_factory=list,
        description="Suggestions to reduce costs while maintaining effectiveness",
    )
    approved: bool = Field(description="True if plan is economically feasible")


class MetaEvaluation(BaseModel):
    """Synthesized evaluation combining all three perspectives"""

    overall_approved: bool = Field(
        description="True only if ALL three evaluators approved"
    )
    overall_quality_score: float = Field(
        description="Weighted average: Operational 50%, Social 30%, Economic 20%"
    )
    synthesized_feedback: str = Field(
        description="Coherent, prioritized feedback combining insights from all evaluators. Start with most critical issues."
    )
    priority_improvements: List[str] = Field(
        default_factory=list,
        description="Numbered list of specific improvements ordered by importance",
    )
    conflicting_requirements: List[str] = Field(
        default_factory=list,
        description="Areas where evaluators have conflicting recommendations (if any)",
    )


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

    # Multi-Evaluation (NEW)
    operational_evaluation: Optional[OperationalEvaluation]
    social_evaluation: Optional[SocialPoliticalEvaluation]
    economic_evaluation: Optional[EconomicEvaluation]
    meta_evaluation: Optional[MetaEvaluation]

    evaluation_feedback: Optional[str]  # Synthesized feedback for proposer
    retry_count: int

    # Output
    final_plan: Optional[EvacuationPlan]
    notifications_sent: bool
    error: Optional[str]
