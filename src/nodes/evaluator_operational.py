# src/nodes/evaluator_operational.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from ..config import OPERATIONAL_TEMPERATURE, OPERATIONAL_THRESHOLD
from ..state import GraphState, OperationalEvaluation


def evaluate_operational(state: GraphState) -> Dict[str, Any]:
    """
    OPERATIONAL EVALUATOR - Strict focus on saving lives and minimizing casualties.

    This is the MOST IMPORTANT evaluator with the highest standards.
    Approval threshold: {OPERATIONAL_THRESHOLD}
    Weight in final score: {OPERATIONAL_WEIGHT*100:.0f}%
    """

    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=OPERATIONAL_TEMPERATURE,
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(OperationalEvaluation)

    # Get context
    proposed_plan = state["proposed_plan"]
    risk_assessments = state["risk_assessments"]
    route_details = state.get("route_details", [])
    assets = state["assets"]
    dangers = state["dangers"]

    # Build evaluation prompt
    prompt = f"""
You are the CHIEF OPERATIONAL OFFICER for emergency response. Your SOLE priority is saving lives and minimizing casualties. You are STRICT and have ZERO tolerance for safety gaps.

PROPOSED EVACUATION PLAN:
- Assets to evacuate: {proposed_plan.assets_to_evacuate}
- Evacuation zone assignments: {proposed_plan.evacuation_zone_assignments}
- Helper assets: {proposed_plan.helpers}
- Plan schematic: {proposed_plan.plan_schematic}
- Reasoning: {proposed_plan.reasoning}
- Self-assessed quality: {proposed_plan.plan_quality_score}

RISK ASSESSMENTS:
{[{"asset": r.asset_id, "danger": r.danger_id, "distance_km": r.distance_km, "risk": r.risk_level} for r in risk_assessments]}

ROUTE DETAILS:
{[{"asset": r["asset_id"], "zone": r.get("safe_place_id"), "distance_km": r.get("route_distance_km"), "time_min": r.get("estimated_time_minutes"), "feasibility": r.get("feasibility")} for r in route_details] if route_details else "No route data"}

ALL ASSETS:
{[{"id": a.id, "type": a.type, "comments": a.comments} for a in assets]}

ALL DANGERS:
{[{"id": d.id, "type": d.type, "severity": getattr(d, 'severity', 'unknown'), "comments": d.comments} for d in dangers]}

EVALUATION CRITERIA (Score 0.0-1.0):

1. **Completeness (35%):**
   - Are ALL high-risk assets evacuated or protected?
   - Are ALL medium-risk assets addressed?
   - Cross-check: List each high/medium risk asset and verify it's in the plan
   - List any missing assets as CRITICAL GAPS

2. **Safety (30%):**
   - Are evacuation routes actually feasible within the proposed timeframe?
   - Are evacuation zones far enough from active dangers?
   - Are helpers positioned effectively and safely?
   - Check if any evacuation zones are themselves at risk

3. **Timeline Realism (20%):**
   - Can evacuations realistically happen in proposed timeframes?
   - Are there sufficient resources (vehicles, personnel, fuel)?
   - Are there bottlenecks or conflicts (multiple assets to same zone simultaneously)?
   - Is the priority ordering logical?

4. **Acceptable Losses (15%):**
   - If sacrificing low-value assets saves high-value ones, that's acceptable
   - Clearly identify what losses are acceptable and why
   - Prioritize: Human life > Critical infrastructure > Regular assets > Low-value assets
   - Are we over-investing in protecting low-value assets?

APPROVAL THRESHOLD: {OPERATIONAL_THRESHOLD} or higher (STRICT)

SCORING GUIDE:
- 0.9-1.0: Excellent, comprehensive coverage of all risks
- {OPERATIONAL_THRESHOLD}-0.9: Good, all critical risks addressed, minor improvements possible → APPROVE
- 0.5-{OPERATIONAL_THRESHOLD}: Significant gaps, missing high-risk assets → REJECT
- <0.5: Critical safety failures, lives at risk → REJECT

Be STRICT. This is life-or-death. If in doubt, REJECT and demand improvements.

Provide:
- **quality_score**: Your honest, strict assessment
- **feedback**: Detailed analysis of strengths and weaknesses
- **critical_gaps**: Specific missing elements that MUST be fixed (with asset IDs)
- **acceptable_losses**: What we can afford to lose to save more important targets
- **approved**: True only if score >= {OPERATIONAL_THRESHOLD} AND no critical safety gaps
"""

    # Evaluate
    evaluation = llm.invoke(prompt)

    print(
        f"🚨 Operational Evaluation: {evaluation.quality_score:.2f} - {'✅ APPROVED' if evaluation.approved else '❌ REJECTED'}"
    )
    if evaluation.critical_gaps:
        print(f"   Critical gaps: {len(evaluation.critical_gaps)}")

    return {"operational_evaluation": evaluation}
