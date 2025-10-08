# src/nodes/evaluator.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..state import GraphState


class PlanEvaluation(BaseModel):
    """Structured evaluation of an evacuation plan"""

    quality_score: float = Field(
        description="Overall quality score from 0.0 to 1.0 (0.7+ is approved)"
    )
    feedback: str = Field(
        description="Specific, actionable feedback on improvements needed. Include concrete suggestions with asset IDs and actions."
    )
    strengths: str = Field(description="What the plan does well - be specific")
    weaknesses: str = Field(
        description="Critical gaps or issues - be specific with examples"
    )
    specific_actions: str = Field(
        description="Numbered list of specific actions to improve the plan (e.g., '1. Add evacuation for asset_x due to proximity to danger_y')"
    )


def evaluate_plan(state: GraphState) -> Dict[str, Any]:
    """
    Evaluate the proposed evacuation plan for quality and completeness.

    Uses LLM to critically assess the plan and provide feedback.
    Updates the plan's quality score and provides improvement suggestions.
    """

    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,  # Lower temperature for more consistent evaluation
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(PlanEvaluation)

    # Get current plan and context
    proposed_plan = state["proposed_plan"]
    risk_assessments = state["risk_assessments"]
    route_details = state.get("route_details", [])
    assets = state["assets"]
    dangers = state["dangers"]
    retry_count = state.get("retry_count", 0)

    # Build evaluation prompt
    prompt = f"""
    You are a senior emergency management expert conducting a critical safety review.
    Evaluate this evacuation plan with ZERO tolerance for gaps that could endanger lives.

    PROPOSED EVACUATION PLAN:
    - Assets to evacuate: {proposed_plan.assets_to_evacuate}
    - Evacuation zone assignments: {proposed_plan.evacuation_zone_assignments}
    - Helper assets: {proposed_plan.helpers}
    - Plan schematic: {proposed_plan.plan_schematic}
    - Reasoning: {proposed_plan.reasoning}
    - Self-assessed quality score: {proposed_plan.plan_quality_score}

    RISK ASSESSMENTS:
    {[{"asset": r.asset_id, "danger": r.danger_id, "distance": r.distance_km, "risk": r.risk_level} for r in risk_assessments]}

    ROUTE DETAILS:
    {[{"asset": r["asset_id"], "zone": r.get("safe_place_id"), "distance": r.get("route_distance_km"), "time": r.get("estimated_time_minutes"), "feasibility": r.get("feasibility")} for r in route_details] if route_details else "No route data"}

    ALL ASSETS:
    {[{"id": a.id, "type": a.type, "comments": a.comments} for a in assets]}

    ALL DANGERS:
    {[{"id": d.id, "type": d.type, "severity": getattr(d, 'severity', 'unknown')} for d in dangers]}

    CRITICAL EVALUATION CRITERIA:

    1. **Completeness (30 points):**
       - Are ALL high-risk assets evacuated? (List any missing)
       - Are ALL medium-risk assets addressed (evacuate or protect)?
       - Are evacuation zones assigned for every asset to evacuate?

    2. **Safety (25 points):**
       - Are evacuation routes feasible within the timeframe?
       - Are evacuation zones far enough from dangers?
       - Are helper assets properly positioned?

    3. **Efficiency (20 points):**
       - Is the priority ordering logical?
       - Are helpers assigned specific, actionable roles?
       - Is the timeline realistic?

    4. **Clarity (15 points):**
       - Is the schematic easy to follow?
       - Are actions specific and concrete?
       - Is the reasoning well-justified?

    5. **Risk Mitigation (10 points):**
       - Are critical assets protected?
       - Are there contingencies for failures?
       - Does it account for danger movement?

    Scoring guide:
    - 0.9-1.0: Excellent, comprehensive plan
    - 0.7-0.9: Good plan, minor improvements needed → APPROVED
    - 0.5-0.7: Significant gaps, needs improvement → RETRY
    - <0.5: Critical flaws, major revision needed → RETRY

    Provide:
    - **quality_score**: Honest assessment (0.0-1.0)
    - **strengths**: Specific good decisions
    - **weaknesses**: Specific gaps or concerns
    - **specific_actions**: Numbered list of concrete improvements (e.g., "1. Evacuate hospital_yokohama_4 which is at high risk from flood_yokohama_4 (0.58 km)")
    - **feedback**: Overall assessment synthesizing the above

    Be direct and specific. Lives depend on this plan.
    """

    # Get evaluation
    evaluation = llm.invoke(prompt)

    # Build comprehensive feedback including specific actions
    comprehensive_feedback = f"""
{evaluation.feedback}

SPECIFIC ACTIONS REQUIRED:
{evaluation.specific_actions}

STRENGTHS:
{evaluation.strengths}

WEAKNESSES:
{evaluation.weaknesses}
"""

    # Update the proposed plan with the evaluated quality score
    updated_plan = proposed_plan.model_copy(
        update={"plan_quality_score": evaluation.quality_score}
    )

    return {
        "proposed_plan": updated_plan,
        "evaluation_feedback": comprehensive_feedback,
        "retry_count": retry_count + 1,
    }
