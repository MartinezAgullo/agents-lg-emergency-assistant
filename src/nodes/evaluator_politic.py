# src/nodes/evaluator_politic.py

import os
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from ..config import SOCIAL_TEMPERATURE
from ..state import GraphState, SocialPoliticalEvaluation


def evaluate_social(state: GraphState) -> Dict[str, Any]:
    """
    SOCIAL/POLITICAL EVALUATOR - Evaluates political costs and social implications.

    Pragmatic approach: In emergencies, political costs are acceptable to save lives.
    Approval threshold: {SOCIAL_THRESHOLD}
    Weight in final score: {SOCIAL_WEIGHT*100:.0f}%
    """

    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=SOCIAL_TEMPERATURE,
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(SocialPoliticalEvaluation)

    # Get context
    proposed_plan = state["proposed_plan"]
    assets = state["assets"]
    dangers = state["dangers"]

    # Build evaluation prompt
    prompt = f"""
You are the POLITICAL ADVISOR for emergency response. You evaluate social and political implications. You are PRAGMATIC - in emergencies, some political costs are acceptable to save lives.

PROPOSED EVACUATION PLAN:
- Assets to evacuate: {proposed_plan.assets_to_evacuate}
- Evacuation zone assignments: {proposed_plan.evacuation_zone_assignments}
- Helper assets: {proposed_plan.helpers}
- Plan schematic: {proposed_plan.plan_schematic}

ALL ASSETS (check for cross-border movements):
{[{"id": a.id, "type": a.type, "location": a.location, "comments": a.comments} for a in assets]}

ALL DANGERS:
{[{"id": d.id, "type": d.type, "location": d.location, "comments": d.comments} for d in dangers]}

EVALUATION CRITERIA (Score 0.0-1.0):

1. **Sovereignty & Territorial Issues (30%):**
   - Border crossings: Analyze if evacuation routes cross international borders
   - Airspace violations: Are we flying through foreign airspace?
   - International waters: Using disputed maritime routes?

   SEVERITY SCALE (political cost):
   - Ally territory: Low cost → score impact: -0.05
   - Neutral territory: Medium cost → score impact: -0.15
   - Hostile/competitor territory: High cost → score impact: -0.30
   - UN/Protected zones: Critical cost → score impact: -0.40

2. **Military Asset Movement (25%):**
   - Military assets on foreign (non-ally) soil: VERY DANGEROUS, high political cost
   - Military visibility as potential aggression: Medium cost
   - Military on ally soil: Low cost, usually acceptable
   - Check if any MILITARY, RADAR, or defense assets are moved to foreign territory

3. **Public Perception (20%):**
   - Large evacuations cause panic: BUT people dying causes MORE panic → acceptable
   - Perceived favoritism (VIP/military evacuated first): Bad optics but sometimes necessary
   - Information blackout: Bad - transparency is important unless operational security demands it
   - Access inequality: Routes only accessible to certain groups → try to avoid

4. **International Relations (15%):**
   - Requesting foreign aid: Acceptable and encouraged if we can't handle it ourselves
   - Political concessions: Acceptable cost in genuine emergency
   - Diplomatic fallout: Will this harm long-term relationships?

5. **Equity & Justice (10%):**
   - Fair evacuation order based on risk, not privilege
   - Equitable resource distribution
   - Protecting vulnerable populations

APPROVAL THRESHOLD: 0.5 or higher (LENIENT)

SCORING GUIDE:
- 0.8-1.0: Minimal political costs, excellent public perception
- 0.5-0.8: Acceptable political costs, some concerns but manageable → APPROVE
- 0.3-0.5: Significant political costs, reconsider if possible → REJECT
- <0.3: Extreme political costs (e.g., likely military response, major diplomatic crisis) → REJECT

In emergencies, saving lives trumps political costs. Identify political costs clearly, but approve unless costs are EXTREME (e.g., likely to trigger military response, violate major treaties, cause international incident).

Provide:
- **quality_score**: Honest political assessment (0.5+ = approve)
- **feedback**: Analysis of political implications
- **political_costs**: List of objects with "issue" and "severity" (e.g., [{{"issue": "Border crossing into hostile nation", "severity": "high"}}])
- **sovereignty_violations**: List specific border/airspace violations
- **public_perception_risks**: Issues that may cause public concern
- **recommendations**: How to reduce political costs without sacrificing safety
- **approved**: True if score >= 0.5 (unless extreme political crisis risk)
"""

    # Evaluate
    evaluation = llm.invoke(prompt)

    print(
        f" 🌍 Social/Political Evaluation: {evaluation.quality_score:.2f} - {'✅ APPROVED' if evaluation.approved else '❌ REJECTED'}"
    )
    if evaluation.political_costs:
        print(f" 🗳️   Political costs: {len(evaluation.political_costs)}")

    return {"social_evaluation": evaluation}
