# src/nodes/evaluator.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from ..state import GraphState
import os


class PlanEvaluation(BaseModel):
    """Structured evaluation of an evacuation plan"""
    quality_score: float = Field(description="Overall quality score from 0.0 to 1.0")
    feedback: str = Field(description="Detailed feedback on what could be improved")
    strengths: str = Field(description="What the plan does well")
    weaknesses: str = Field(description="What the plan could improve")


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
        api_key=os.getenv("OPENAI_API_KEY")
    ).with_structured_output(PlanEvaluation)
    
    # Get current plan and context
    proposed_plan = state["proposed_plan"]
    risk_assessments = state["risk_assessments"]
    retry_count = state.get("retry_count", 0)
    
    # Build evaluation prompt
    prompt = f"""
    You are a senior emergency management expert. Evaluate the following evacuation plan.

    PROPOSED EVACUATION PLAN:
    - Assets to evacuate: {proposed_plan.assets_to_evacuate}
    - Helper assets: {proposed_plan.helpers}
    - Reasoning: {proposed_plan.reasoning}
    - Self-assessed quality score: {proposed_plan.plan_quality_score}

    RISK ASSESSMENTS (for reference):
    {[{"asset": r.asset_id, "danger": r.danger_id, "distance_km": r.distance_km, "risk": r.risk_level} for r in risk_assessments]}

    Evaluate this plan critically:
    1. Does it evacuate all high-risk assets?
    2. Are the helper assets appropriate and sufficient?
    3. Is the reasoning sound and complete?
    4. Are there any assets at risk that were missed?
    5. Could the response be more efficient?

    Provide a quality score (0.0-1.0) and detailed feedback.
    A score of 0.8 or higher means the plan is approved.
    """
    
    # Get evaluation
    evaluation = llm.invoke(prompt)
    
    # Update the proposed plan with the evaluated quality score
    updated_plan = proposed_plan.model_copy(update={"plan_quality_score": evaluation.quality_score})
    
    return {
        "proposed_plan": updated_plan,
        "evaluation_feedback": evaluation.feedback,
        "retry_count": retry_count + 1
    }