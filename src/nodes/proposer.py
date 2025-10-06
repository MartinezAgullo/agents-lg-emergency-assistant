# src/nodes/proposer.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from ..state import EvacuationPlan, GraphState


def propose_plan(state: GraphState) -> Dict[str, Any]:
    """
    Generate an evacuation plan based on risk assessments
    and route analysis.

    Uses LLM with structured output to propose which assets need evacuation
    and which assets can help (e.g., fire stations, police).
    Incorporates feedback from previous evaluations if retrying.
    """

    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY")
    ).with_structured_output(EvacuationPlan)

    # Prepare context
    assets = state["assets"]
    dangers = state["dangers"]
    risk_assessments = state["risk_assessments"]
    route_details = state.get("route_details", [])
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
    """

    # Add route details if available
    if route_details:
        prompt += """
        Generate an evacuation plan that:
        1.  **Prioritizes Evacuation:** **Immediately identifies and lists** all assets that are at **High** or **Medium** risk (based on `risk_assessments`) and must be evacuated. For each, state the **primary danger** and the **specific reason** for evacuation, citing relevant context (e.g., asset type, danger severity, comments).
        2.  **Identifies Critical Assets:** Assesses assets with sensitive material (e.g., "Nuclear power plant," "Very sensible material" from `comments`) and determines if they need **protection or evacuation**. If they are deemed helper assets (like a hospital or police station), ensure they are **secured before or during** their deployment.
        3.  **Proposes Strategic Helpers:** Identifies potential **Helper Assets** (e.g., fire station, police, hospitals, or any asset not being evacuated) that are **closest** to the most critical evacuation/danger points. Specify the **role** they should play (e.g., "Police to secure high-security perimeter," "Fire Station to manage Fire ad88377c").
            Depending on the situation, some assets may be evacuated by themselves others may need help.
            Depending on the situation, a single assset can be a helper or a evacuee.
        4.  **Defines Actionable Steps:** For the highest priority evacuation, proposes a brief, **sequential action plan** (e.g., "1. Notify local police. 2. Begin controlled shutdown of X. 3. Deploy Z units to Y.")
        5.  **Analyzes Danger Context:** Explicitly integrates information from the **danger comments** (e.g., "Storm traveling to the north-east direction," "High flood risk") into the plan's justification, ensuring the plan accounts for changing or blocking access routes.
            Provides clear reasoning for your decisions
        """
    # 6.  **Assigns Quality Score:** Assigns a quality score (**0.0-1.0**) based on how effectively the plan addresses the **High Severity** dangers and protects the most **sensitive assets**.

    # Add feedback if this is a retry
    if evaluation_feedback:
        prompt += f"""

        PREVIOUS EVALUATION FEEDBACK:
        {evaluation_feedback}

        Please improve the plan based on this feedback.
        """

    # Generate plan
    proposed_plan = llm.invoke(prompt)

    return {"proposed_plan": proposed_plan, "retry_count": retry_count}
