# src/nodes/proposer.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from ..state import GraphState, EvacuationPlan
import os


def propose_plan(state: GraphState) -> Dict[str, Any]:
    """
    Generate an evacuation plan based on risk assessments.
    
    Uses LLM with structured output to propose which assets need evacuation
    and which assets can help (e.g., fire stations, police).
    Incorporates feedback from previous evaluations if retrying.
    """
    
    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    ).with_structured_output(EvacuationPlan)
    
    # Prepare context
    assets = state["assets"]
    dangers = state["dangers"]
    risk_assessments = state["risk_assessments"]
    evaluation_feedback = state.get("evaluation_feedback")
    retry_count = state.get("retry_count", 0)
    
    # Build prompt
    prompt = f"""
    You are an emergency response coordinator. Based on the following information, create an evacuation plan.

    ASSETS:
    {[{"id": a.id, "type": a.type, "location": a.location} for a in assets]}

    DANGERS:
    {[{"id": d.id, "type": d.type, "location": d.location} for d in dangers]}

    RISK ASSESSMENTS:
    {[{"asset": r.asset_id, "danger": r.danger_id, "distance_km": r.distance_km, "risk": r.risk_level} for r in risk_assessments]}

    Generate an evacuation plan that:
    1. Identifies assets that need to be evacuated (those at high risk)
    2. Identifies helper assets (e.g., fire stations, police) that can assist. 
       Depending on the asset and the danger, some assets may be evacuated by themselves others may need help.
       A single assset can be a helper or a evacuee depending on the situation.
    3. Provides clear reasoning for your decisions
    4. Assigns a quality score (0.0-1.0) based on how well the plan addresses the risks
    """
    
    # Add feedback if this is a retry
    if evaluation_feedback:
        prompt += f"""

        PREVIOUS EVALUATION FEEDBACK:
        {evaluation_feedback}

        Please improve the plan based on this feedback.
        """
    
    # Generate plan
    proposed_plan = llm.invoke(prompt)
    
    return {
        "proposed_plan": proposed_plan,
        "retry_count": retry_count
    }