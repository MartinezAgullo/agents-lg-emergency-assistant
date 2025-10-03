# src/nodes/notifier.py

from typing import Dict, Any
from ..state import GraphState
from ..tools import send_pushover_notification


def send_notifications(state: GraphState) -> Dict[str, Any]:
    """
    Send push notifications with the final evacuation plan.
    
    Uses Pushover to send alerts to emergency coordinators with
    the approved evacuation plan details.
    """
    
    proposed_plan = state["proposed_plan"]
    
    # Prepare notification message
    message = f"""🚨 EMERGENCY EVACUATION PLAN APPROVED

📍 ASSETS TO EVACUATE:
{', '.join(proposed_plan.assets_to_evacuate) if proposed_plan.assets_to_evacuate else 'None'}

🚑 HELPER ASSETS DEPLOYED:
{', '.join(proposed_plan.helpers) if proposed_plan.helpers else 'None'}

📊 PLAN QUALITY SCORE: {proposed_plan.plan_quality_score:.2f}

💡 REASONING:
{proposed_plan.reasoning}

⚠️ Take immediate action according to this plan.
"""
    
    # Send notification via Pushover
    try:
        success = send_pushover_notification(
            message=message,
            title="Emergency Evacuation Plan",
            priority=1  # High priority
        )
        
        return {
            "final_plan": proposed_plan,
            "notifications_sent": success,
            "error": None if success else "Failed to send notifications"
        }
    
    except Exception as e:
        return {
            "final_plan": proposed_plan,
            "notifications_sent": False,
            "error": f"Notification error: {str(e)}"
        }