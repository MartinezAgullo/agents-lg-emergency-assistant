# src/nodes/proposer.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from ..config import PROPOSER_TEMPERATURE
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
        model="gpt-4o-mini",
        temperature=PROPOSER_TEMPERATURE,
        api_key=os.getenv("OPENAI_API_KEY"),
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
    {[{"id": a.id, "type": a.type, "location": a.location, "comments": a.comments} for a in assets]}

    DANGERS:
    {[{"id": d.id, "type": d.type, "location": d.location, "severity": getattr(d, 'severity', 'unknown'), "comments": d.comments} for d in dangers]}

    RISK ASSESSMENTS:
    {[{"asset": r.asset_id, "danger": r.danger_id, "distance_km": r.distance_km, "risk": r.risk_level} for r in risk_assessments]}
    """

    # Add route details if available
    if route_details:
        prompt += f"""

        EVACUATION ROUTES (actual road distances and times):
        {[{
            "asset": r["asset_id"],
            "safe_place": r.get("safe_place_id"),
            "straight_distance": r.get("straight_distance_km"),
            "route_distance": r.get("route_distance_km"),
            "time_minutes": r.get("estimated_time_minutes"),
            "feasibility": r.get("feasibility")
        } for r in route_details]}

        AVAILABLE EVACUATION ZONES:
        {[{"id": a.id, "type": a.type, "location": a.location, "comments": a.comments} for a in assets if a.type == "EVACUATION_ZONE"]}

        Generate a comprehensive evacuation plan with TWO parts:

        ## PART 1: plan_schematic (Visual Action Plan)
        Create a concise, scannable schematic using this format:

        🚨 PRIORITY 1 - IMMEDIATE (0-15 min)
        └─ [EVACUATE] asset_id → evacuation_zone (X.X km, XX min)
           ├─ Danger: danger_type at X.X km
           └─ Action: Brief specific action

        🔴 PRIORITY 2 - URGENT (15-30 min)
        └─ [EVACUATE] asset_id → evacuation_zone (X.X km, XX min)
           └─ Action: Brief specific action

        🟡 PRIORITY 3 - HIGH (30-60 min)
        └─ [PROTECT] asset_id
           └─ Action: Brief specific action

        🚑 HELPER DEPLOYMENT
        ├─ helper_id: Specific role (e.g., "Secure perimeter at asset_x")
        └─ helper_id: Specific role

        ⚠️ CRITICAL NOTES
        • Any time-sensitive constraints
        • Weather/danger movement considerations
        • Coordination requirements

        Requirements for schematic:
        - Use tree characters (└─, ├─) for visual hierarchy
        - Include distances and times for evacuations
        - Prioritize by urgency (immediate/urgent/high)
        - Assign specific roles to each helper
        - Keep each line under 80 characters
        - Use emojis for quick visual scanning

        ## PART 2: reasoning (Detailed Analysis)
        Provide comprehensive reasoning covering:

        1. **Threat Analysis:**
           - Primary dangers and their movement/evolution
           - Which assets are most vulnerable and why
           - Time-critical factors influencing decisions

        2. **Evacuation Strategy:**
           - Why specific evacuation zones were chosen for each asset
           - Route selection rationale (distance vs. safety vs. capacity)
           - Priority ordering justification

        3. **Helper Deployment Logic:**
           - Why each helper was chosen for their role
           - Coordination between multiple helpers
           - Backup plans if helpers are unavailable

        4. **Risk Mitigation:**
           - How the plan addresses high-risk scenarios
           - Contingencies for route blockages or zone capacity issues
           - Special considerations for sensitive assets

        5. **Timeline Justification:**
           - Why specific timeframes were assigned
           - Dependencies between evacuation steps
           - Critical path analysis

        ## General Requirements:
        1. **Prioritize Evacuation:** Identify all assets at High or Medium risk
           - Do NOT include EVACUATION_ZONE assets in evacuation list!

        2. **Assign Optimal Evacuation Zones:** Consider:
           - Distance and travel time (prefer closer for urgent)
           - Zone capacity and features
           - Danger proximity (NEVER assign to zones near dangers)
           - Route feasibility (prefer "feasible" over "challenging")
           - Multiple assets can share zones if appropriate

        3. **Identify Critical Assets:** Assess sensitive materials and determine protection needs

        4. **Strategic Helper Deployment:** Assign specific, actionable roles

        5. **Quality Score:** Self-assess effectiveness (0.0-1.0)
        """  # nosec
    else:
        prompt += """

        Generate an evacuation plan with a schematic and detailed reasoning:

        1. **plan_schematic:** Visual tree-style action plan with priorities, distances, and specific actions
        2. **reasoning:** Detailed analysis of threats, strategy, and decision-making
        3. **Prioritize Evacuation:** Identify all High/Medium risk assets (NOT evacuation zones!)
        4. **Assign helpers** with specific roles
        5. **Quality score** (0.0-1.0) based on effectiveness
        """

    # Add feedback if this is a retry
    if evaluation_feedback:
        prompt += f"""

        PREVIOUS EVALUATION FEEDBACK:
        {evaluation_feedback}

        Please improve the plan based on this feedback. Pay special attention to addressing the specific concerns raised.
        """

    # Generate plan
    proposed_plan = llm.invoke(prompt)

    return {"proposed_plan": proposed_plan, "retry_count": retry_count}
