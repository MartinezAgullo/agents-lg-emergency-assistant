# src/nodes/evaluator_economic.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from ..config import ECONOMIC_TEMPERATURE
from ..state import EconomicEvaluation, GraphState


def evaluate_economic(state: GraphState) -> Dict[str, Any]:
    """
    ECONOMIC EVALUATOR - Evaluates cost-effectiveness and resource feasibility.

    Pragmatic approach: High costs acceptable in emergencies, but flag prohibitive costs.
    Approval threshold: {ECONOMIC_THRESHOLD}
    Weight in final score: {ECONOMIC_WEIGHT*100:.0f}%
    """

    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=ECONOMIC_TEMPERATURE,
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(EconomicEvaluation)

    # Get context
    proposed_plan = state["proposed_plan"]
    route_details = state.get("route_details", [])
    assets = state["assets"]

    # Build evaluation prompt
    prompt = f"""
You are the ECONOMIC ADVISOR for emergency response. You evaluate cost-effectiveness and resource feasibility. You are PRAGMATIC - in emergencies, higher costs are acceptable, but you flag when costs become prohibitive or resources are unavailable.

PROPOSED EVACUATION PLAN:
- Assets to evacuate: {proposed_plan.assets_to_evacuate}
- Helper assets: {proposed_plan.helpers}
- Plan schematic: {proposed_plan.plan_schematic}

ROUTE DETAILS (distances and times):
{[{"asset": r["asset_id"], "zone": r.get("safe_place_id"), "distance_km": r.get("route_distance_km"), "time_min": r.get("estimated_time_minutes"), "feasibility": r.get("feasibility")} for r in route_details] if route_details else "No route data"}

ALL ASSETS (check for high-value assets):
{[{"id": a.id, "type": a.type, "comments": a.comments} for a in assets]}

EVALUATION CRITERIA (Score 0.0-1.0):

1. **Resource Availability (40%):**
   - Fuel: Enough for all evacuation routes? (Estimate: 1L per km for trucks, 10L per km for heavy vehicles)
   - Vehicles: Sufficient trucks/helicopters/transport for all assets?
   - Personnel: Enough helpers/drivers/coordinators to execute simultaneously?
   - Identify any resource constraints that make the plan infeasible

2. **Direct Costs (30%):**
   - Transportation costs (fuel, vehicle wear, pilot fees)
   - Helper deployment (overtime, hazard pay, equipment)
   - Provide rough total estimate: "Low ($50K-250K)", "Moderate ($250K-1M)", "High ($1M-5M)", "Very High (>$5M)"

3. **Asset Value vs Cost (20%):**
   - Is cost proportional to value being saved?
   - Are we spending $1M to save a $10K asset? (Flag this)
   - Are we under-investing in high-value assets?
   - Cost per life/asset saved

4. **Economic Impact (10%):**
   - Business disruption (evacuated data centers = service outage, hospitals = health crisis)
   - Regional economic impact
   - Recovery costs and timeline

APPROVAL THRESHOLD: 0.5 or higher (LENIENT)

SCORING GUIDE:
- 0.8-1.0: Cost-effective, resources readily available
- 0.5-0.8: Higher costs or some resource constraints, but acceptable → APPROVE
- 0.3-0.5: Very high costs or significant resource shortages → REJECT
- <0.3: Economically catastrophic or resources physically unavailable → REJECT

Only reject if:
- Resources are PHYSICALLY unavailable (not enough fuel/vehicles exist)
- Cost is catastrophically disproportionate to value saved
- There's a much cheaper alternative achieving same safety

Provide:
- **quality_score**: Economic feasibility assessment (0.5+ = approve)
- **feedback**: Cost analysis and resource availability
- **estimated_total_cost**: Rough estimate ("Moderate", "$500K-1M", etc.)
- **resource_constraints**: Specific shortages (e.g., "Need 50 trucks, only 30 available")
- **cost_benefit_analysis**: Brief assessment of value vs cost
- **recommendations**: Practical ways to reduce costs without sacrificing safety
- **approved**: True if score >= 0.5 (unless resources physically unavailable)
"""

    # Evaluate
    evaluation = llm.invoke(prompt)

    print(
        f" 💰 Economic Evaluation: {evaluation.quality_score:.2f} - {'✅ APPROVED' if evaluation.approved else '❌ REJECTED'}"
    )
    #  print(f"   Estimated cost: {evaluation.estimated_total_cost}")

    return {"economic_evaluation": evaluation}
