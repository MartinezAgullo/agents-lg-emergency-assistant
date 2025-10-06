# src/tools.py

import math
import os
from typing import Optional

import requests
from langchain.agents import Tool
from langsmith import traceable

from .state import Asset, Danger

# ==================== DISTANCE CALCULATION ====================


@traceable(name="calculate_distance")
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the haversine formula.
    Note: From 20kms the straight-line distance becomes notably different from the haversine distance.

    Args:
        lat1, lon1: Latitude and longitude of first point (in degrees)
        lat2, lon2: Latitude and longitude of second point (in degrees)

    Returns:
        Distance in kilometers
    """
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in kilometers
    earth_radius_km = 6371.0

    return earth_radius_km * c


@traceable(name="calculate_route_distance")
def calculate_route_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, provider: str = "osrm"
) -> float:
    """
    Calculate actual road/walking distance between two points using routing APIs.

    This function will be implemented in the future to provide realistic evacuation
    route distances instead of straight-line distances.

    Providers under consideration:
    - osrm (Open Source Routing Machine) <--- MOST PROBABLY WE WILL BE USING THIS
    - google_maps (Google Maps Distance Matrix API)
    - graphhopper
    - valhalla

    Args:
        lat1, lon1: Start point coordinates
        lat2, lon2: End point coordinates
        provider: Routing service to use

    Returns:
        Route distance in kilometers

    TODO: Implement routing API integration
    """
    raise NotImplementedError(
        "Route distance calculation not yet implemented. Use calculate_distance() for now."
    )


# ==================== RISK ASSESSMENT ====================

# Risk thresholds by danger type (in kilometers)
RISK_THRESHOLDS = {
    "Fire": {"high": 2.0, "medium": 5.0},
    "Heavy_Storm": {"high": 5.0, "medium": 15.0},
    "Terrorist": {"high": 1.0, "medium": 3.0},
    "Flood": {"high": 3.0, "medium": 8.0},
}


@traceable(name="assess_risk_level")
def assess_risk_level(
    distance_km: float,
    danger_type: str,
    asset: Optional[Asset] = None,
    danger: Optional[Danger] = None,
) -> str:
    """
    Assess risk level based on distance, danger type, and optional contextual information.

    Deterministic mode (no comments):
    - Uses predefined thresholds based on danger type and distance

    TO DO in future: LLM-enhanced mode (when comments are present):
    - Considers asset.comments for vulnerability context
    - Considers danger.comments for additional threat details
    - Considers danger.severity for threat intensity
    - Uses LLM to make nuanced risk assessment

    Args:
        distance_km: Distance between asset and danger
        danger_type: Type of danger (Fire, Heavy_Storm, Terrorist, Flood)
        asset: Optional Asset object with comments field
        danger: Optional Danger object with comments and severity fields

    Returns:
        Risk level: "high", "medium", or "low"
    """
    # Check if we should use LLM-enhanced assessment
    has_comments = (asset and hasattr(asset, "comments") and asset.comments) or (
        danger and hasattr(danger, "comments") and danger.comments
    )

    if has_comments:
        return _assess_risk_with_llm(distance_km, danger_type, asset, danger)
    else:
        return _assess_risk_deterministic(distance_km, danger_type, danger)


def _assess_risk_deterministic(
    distance_km: float, danger_type: str, danger: Optional[Danger] = None
) -> str:
    """
    Deterministic risk assessment based on distance thresholds.

    Takes into account danger severity if available to adjust thresholds.
    """
    # Get base thresholds for this danger type
    thresholds = RISK_THRESHOLDS.get(danger_type, {"high": 3.0, "medium": 10.0})

    # Adjust thresholds based on danger severity if available
    if danger and hasattr(danger, "severity") and danger.severity:
        severity_multipliers = {
            "low": 0.7,  # Reduce thresholds (less dangerous)
            "medium": 1.0,  # Keep standard thresholds
            "high": 1.5,  # Increase thresholds (more dangerous)
        }
        multiplier = severity_multipliers.get(danger.severity.lower(), 1.0)
        thresholds = {k: v * multiplier for k, v in thresholds.items()}

    # Classify risk based on adjusted thresholds
    if distance_km < thresholds["high"]:
        return "high"
    elif distance_km < thresholds["medium"]:
        return "medium"
    else:
        return "low"


def _assess_risk_with_llm(
    distance_km: float,
    danger_type: str,
    asset: Optional[Asset],
    danger: Optional[Danger],
) -> str:
    """
    LLM-enhanced risk assessment considering contextual comments.

    This function uses an LLM to make nuanced risk assessments when additional
    context is available through comments fields. The LLM considers:

    - Base distance and danger type (deterministic baseline)
    - Asset comments: vulnerability factors, asset importance, special conditions
    - Danger comments: threat evolution, environmental factors, spread patterns
    - Danger severity: intensity multiplier for the threat

    The LLM provides reasoning-based risk classification that goes beyond simple
    distance thresholds, accounting for real-world complexity.

    Example scenarios where LLM helps:
    - Asset comment: "Contains flammable materials" + nearby fire → elevated risk
    - Danger comment: "Strong winds pushing fire northeast" + asset location → directional risk
    - Asset comment: "Underground bunker, flood-resistant" + flood nearby → reduced risk

    Args:
        distance_km: Distance between asset and danger
        danger_type: Type of danger
        asset: Asset with optional comments
        danger: Danger with optional comments and severity

    Returns:
        Risk level: "high", "medium", or "low"

    TODO: Implement LLM-based risk assessment with structured output
    TODO: Create prompt template that includes:
          - Deterministic baseline risk
          - Asset context from comments
          - Danger context from comments and severity
          - Request for final risk classification with reasoning
    TODO: Use .with_structured_output() to ensure valid risk level output
    TODO: Add caching/memoization for identical assessments
    """
    # Placeholder: Fall back to deterministic for now
    # In future implementation, this will call an LLM with structured output

    # Get baseline deterministic risk
    baseline_risk = _assess_risk_deterministic(distance_km, danger_type, danger)

    # TODO: Replace with actual LLM call
    # llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(RiskAssessmentOutput)
    # prompt = f"""
    # Assess risk level considering:
    # - Distance: {distance_km} km
    # - Danger type: {danger_type}
    # - Baseline risk: {baseline_risk}
    # - Asset context: {asset.comments if asset else "None"}
    # - Danger context: {danger.comments if danger else "None"}
    # - Danger severity: {danger.severity if danger and hasattr(danger, 'severity') else "medium"}
    #
    # Provide final risk level: high, medium, or low
    # """
    # enhanced_risk = llm.invoke(prompt)
    # return enhanced_risk.risk_level

    return baseline_risk


# ==================== PUSHOVER NOTIFICATIONS ====================


@traceable(name="send_pushover_notification")
def send_pushover_notification(
    message: str,
    title: str = "Emergency Alert",
    priority: int = 0,
    sound: str = "pushover",
) -> bool:
    """
    Send a push notification via Pushover.

    Args:
        message: Notification text
        title: Notification title
        priority: -2 (silent) to 2 (emergency bypass, requires acknowledgment)
        sound: Notification sound (pushover, bike, bugle, cashregister, classical,
               cosmic, falling, gamelan, incoming, intermission, magic, mechanical,
               pianobar, siren, spacealarm, tugboat, alien, climb, persistent, echo, updown)

    Returns:
        True if sent successfully, False otherwise
    """
    pushover_token = os.getenv("PUSHOVER_TOKEN")
    pushover_user = os.getenv("PUSHOVER_USER")
    pushover_url = "https://api.pushover.net/1/messages.json"

    if not pushover_token or not pushover_user:
        print("⚠️ Pushover credentials not found in environment variables")
        return False

    data = {
        "token": pushover_token,
        "user": pushover_user,
        "message": message,
        "title": title,
        "priority": priority,
        "sound": sound,
    }

    # If priority=2 (emergency), require acknowledgment
    if priority == 2:
        data["retry"] = 30  # Retry every 30 seconds
        data["expire"] = 1800  # Expire after half hour

    try:
        response = requests.post(pushover_url, data=data, timeout=10)

        if response.status_code == 200:
            print(f"✅ Pushover notification sent: {title}")
            return True
        else:
            print(f"❌ Pushover API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Pushover error: {e}")
        return False


def _push_wrapper(text: str) -> str:
    """Wrapper function for LangChain Tool integration"""
    success = send_pushover_notification(
        message=text,
        title="Emergency Assistant",
        priority=1,  # High priority by default
    )
    return (
        "Notification sent successfully" if success else "Failed to send notification"
    )


# LangChain Tool for agent integration
tool_push = Tool(
    name="send_push_notification",
    func=_push_wrapper,
    description="Send a high-priority push notification for emergency alerts. Use this to notify coordinators about critical situations.",
)
