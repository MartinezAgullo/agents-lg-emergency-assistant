# src/nodes/evaluator_meta.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from ..state import GraphState, MetaEvaluation


def evaluate_meta(state: GraphState) -> Dict[str, Any]:
    """
    META-EVALUATOR - Synthesizes feedback from all three specialist evaluators.

    Combines operational, social, and economic evaluations into coherent feedback.
    Plan approved ONLY if ALL three evaluators approved.
    """

    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(MetaEvaluation)

    # Get evaluations from state
    operational_eval = state["operational_evaluation"]
    social_eval = state["social_evaluation"]
    economic_eval = state["economic_evaluation"]
    retry_count = state.get("retry_count", 0)
    proposed_plan = state["proposed_plan"]

    # Build meta-evaluation prompt
    prompt = f"""
You are the CHIEF COORDINATOR synthesizing feedback from three specialist evaluators.

OPERATIONAL EVALUATOR (Weight: 60%, Threshold: 0.6, STRICT):
- Score: {operational_eval.quality_score:.3f}
- Approved: {operational_eval.approved}
- Feedback: {operational_eval.feedback}
- Critical Gaps: {operational_eval.critical_gaps}
- Acceptable Losses: {operational_eval.acceptable_losses}

SOCIAL/POLITICAL EVALUATOR (Weight: 20%, Threshold: 0.5, LENIENT):
- Score: {social_eval.quality_score:.3f}
- Approved: {social_eval.approved}
- Feedback: {social_eval.feedback}
- Political Costs: {[{"issue": pc.issue, "severity": pc.severity} for pc in social_eval.political_costs]}
- Sovereignty Violations: {social_eval.sovereignty_violations}
- Public Perception Risks: {social_eval.public_perception_risks}
- Recommendations: {social_eval.recommendations}

ECONOMIC EVALUATOR (Weight: 20%, Threshold: 0.5, LENIENT):
- Score: {economic_eval.quality_score:.3f}
- Approved: {economic_eval.approved}
- Feedback: {economic_eval.feedback}
- Estimated Cost: {economic_eval.estimated_total_cost}
- Resource Constraints: {economic_eval.resource_constraints}
- Cost-Benefit: {economic_eval.cost_benefit_analysis}
- Recommendations: {economic_eval.recommendations}

CURRENT RETRY: {retry_count + 1}/4

YOUR TASKS:

1. **Overall Approval:**
   - Plan is approved ONLY if ALL three evaluators approved
   - Set overall_approved = True only if all three approved

2. **Calculate Weighted Score:**
   - (Operational × 0.6) + (Social × 0.2) + (Economic × 0.2)
   - This is informational but approval requires ALL three

3. **Synthesize Feedback:**
   Create ONE coherent improvement message for the proposer:

   Structure:
   - **START WITH OPERATIONAL** (most critical - lives at stake)
     * List critical gaps with specific asset IDs
     * Safety concerns that MUST be addressed

   - **THEN POLITICAL CONCERNS** (important but secondary to safety)
     * Sovereignty violations and political costs
     * Suggestions to reduce political impact

   - **FINALLY ECONOMIC** (optimize costs without sacrificing safety)
     * Resource constraints
     * Cost-reduction opportunities

   Keep it clear and actionable. This goes directly to the proposer.

4. **Priority Improvements:**
   Numbered list of specific actions, prioritized by importance:
   - Format: "1. [CRITICAL] Evacuate asset_x threatened by danger_y (0.5km)"
   - Format: "2. [HIGH] Avoid border crossing by rerouting asset_z to zone_w"
   - Format: "3. [MEDIUM] Optimize helper deployment to reduce costs"

   Order: Critical safety issues → High-priority concerns → Medium optimizations

5. **Conflicting Requirements:**
   If evaluators contradict each other, note it:
   - Example: "Operational wants more helpers, Economic wants cost reduction"
   - Suggest resolution: "Prioritize safety: deploy helpers but optimize routes to offset cost"

   Usually operational safety should override economic/political concerns in emergencies.

PRINCIPLES:
- Saving lives comes first (operational priority)
- Political costs are acceptable if necessary to save lives
- Economic costs are acceptable if necessary to save lives
- But we should minimize political/economic costs when possible without sacrificing safety

Keep synthesized_feedback concise, specific, and actionable.
"""

    # Generate meta-evaluation
    meta_eval = llm.invoke(prompt)

    # Calculate weighted score for the plan
    weighted_score = (
        operational_eval.quality_score * 0.6
        + social_eval.quality_score * 0.2
        + economic_eval.quality_score * 0.2
    )

    # Override meta score with calculated weighted score
    meta_eval.overall_quality_score = weighted_score

    print(
        f"📊 Meta-Evaluation: {meta_eval.overall_quality_score:.2f} - {'✅ ALL APPROVED' if meta_eval.overall_approved else '❌ NEEDS IMPROVEMENT'}"
    )

    # Update plan with final quality score
    updated_plan = proposed_plan.model_copy(
        update={"plan_quality_score": meta_eval.overall_quality_score}
    )

    # Prepare detailed feedback for state
    detailed_feedback = f"""
{'='*60}
MULTI-EVALUATOR ASSESSMENT (Retry {retry_count + 1}/4)
{'='*60}

🚨 OPERATIONAL (60% weight, ≥0.6): {operational_eval.quality_score:.2f} - {'✅ APPROVED' if operational_eval.approved else '❌ REJECTED'}
🌍 SOCIAL/POLITICAL (20% weight, ≥0.5): {social_eval.quality_score:.2f} - {'✅ APPROVED' if social_eval.approved else '❌ REJECTED'}
💰 ECONOMIC (20% weight, ≥0.5): {economic_eval.quality_score:.2f} - {'✅ APPROVED' if economic_eval.approved else '❌ REJECTED'}

📊 OVERALL: {meta_eval.overall_quality_score:.2f} - {'✅ ALL APPROVED' if meta_eval.overall_approved else '❌ NEEDS IMPROVEMENT'}

{'='*60}
SYNTHESIZED FEEDBACK
{'='*60}
{meta_eval.synthesized_feedback}

PRIORITY IMPROVEMENTS:
{chr(10).join(meta_eval.priority_improvements)}

{f"⚠️  CONFLICTING REQUIREMENTS:{chr(10)}{chr(10).join(meta_eval.conflicting_requirements)}" if meta_eval.conflicting_requirements else ""}

{'='*60}
DETAILED EVALUATOR FEEDBACK
{'='*60}

🚨 OPERATIONAL DETAILS:
{operational_eval.feedback}

Critical Gaps:
{chr(10).join(f"  • {gap}" for gap in operational_eval.critical_gaps) if operational_eval.critical_gaps else "  None"}

Acceptable Losses:
{chr(10).join(f"  • {loss}" for loss in operational_eval.acceptable_losses) if operational_eval.acceptable_losses else "  None"}

---

🌍 SOCIAL/POLITICAL DETAILS:
{social_eval.feedback}

Political Costs:
{chr(10).join(f"  • {pc}" for pc in social_eval.political_costs) if social_eval.political_costs else "  None"}

Sovereignty Violations:
{chr(10).join(f"  • {v}" for v in social_eval.sovereignty_violations) if social_eval.sovereignty_violations else "  None"}

Public Perception Risks:
{chr(10).join(f"  • {r}" for r in social_eval.public_perception_risks) if social_eval.public_perception_risks else "  None"}

Recommendations:
{chr(10).join(f"  • {rec}" for rec in social_eval.recommendations) if social_eval.recommendations else "  None"}

---

💰 ECONOMIC DETAILS:
{economic_eval.feedback}

Estimated Cost: {economic_eval.estimated_total_cost}

Resource Constraints:
{chr(10).join(f"  • {c}" for c in economic_eval.resource_constraints) if economic_eval.resource_constraints else "  None"}

Cost-Benefit Analysis:
{economic_eval.cost_benefit_analysis}

Recommendations:
{chr(10).join(f"  • {rec}" for rec in economic_eval.recommendations) if economic_eval.recommendations else "  None"}
"""

    return {
        "proposed_plan": updated_plan,
        "meta_evaluation": meta_eval,
        "evaluation_feedback": detailed_feedback,
        "retry_count": retry_count + 1,
    }
