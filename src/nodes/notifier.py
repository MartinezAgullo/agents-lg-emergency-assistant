# src/nodes/notifier.py

from typing import Any, Dict

from ..state import GraphState
from ..tools import send_pushover_notification


def send_notifications(state: GraphState) -> Dict[str, Any]:
    """
    Send push notifications with the final evacuation plan.

    Uses Pushover to send alerts to emergency coordinators with
    the approved evacuation plan details.

    Note: Sends the concise schematic, NOT the detailed reasoning.
    """

    proposed_plan = state["proposed_plan"]

    # Prepare notification message with schematic (not reasoning)
    message = f"""🚨 EMERGENCY EVACUATION PLAN APPROVED



{proposed_plan.plan_schematic}

📍 ASSETS TO EVACUATE ({len(proposed_plan.assets_to_evacuate)}):
{', '.join(proposed_plan.assets_to_evacuate) if proposed_plan.assets_to_evacuate else 'None'}

🚑 HELPER ASSETS ({len(proposed_plan.helpers)}):
{', '.join(proposed_plan.helpers) if proposed_plan.helpers else 'None'}

📊 QUALITY SCORE: {proposed_plan.plan_quality_score:.2f}

⚠️ EXECUTE IMMEDIATELY - Lives at risk
View full reasoning at command center
"""

    # Send notification via Pushover
    try:
        success = send_pushover_notification(
            message=message,
            title="🚨 Emergency Evacuation Plan",
            priority=1,  # High priority
            sound="siren",  # Use urgent sound
        )

        return {
            "final_plan": proposed_plan,
            "notifications_sent": success,
            "error": None if success else "Failed to send notifications",
        }

    except Exception as e:
        return {
            "final_plan": proposed_plan,
            "notifications_sent": False,
            "error": f"Notification error: {str(e)}",
        }
