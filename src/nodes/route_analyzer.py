# src/nodes/route_analyzer.py

from typing import Any, Dict, List, Optional

from ..state import Asset, GraphState
from ..tools import calculate_distance, calculate_route_distance


def find_asset_by_id(assets: List[Asset], asset_id: str) -> Optional[Asset]:
    """Helper to find asset by ID"""
    for asset in assets:
        if asset.id == asset_id:
            return asset
    return None


def find_nearest_safe_location(
    asset_lat: float, asset_lon: float, safe_places: List[Asset]
) -> Optional[tuple]:
    """
    Find the nearest safe location for evacuation.

    Args:
        asset_lat, asset_lon: Asset coordinates
        safe_places: List of SafePlace assets

    Returns:
        (safe_place_id, distance_km, route_distance_km) or None
    """
    if not safe_places:
        return None

    best_safe_place = None
    min_distance = float("inf")
    route_distance = None

    for safe_place in safe_places:
        # Calculate straight-line distance first
        straight_distance = calculate_distance(
            asset_lat, asset_lon, safe_place.location["lat"], safe_place.location["lon"]
        )

        if straight_distance < min_distance:
            """
            We are doing this because straight-line distance difference from the route distance
            is only relevant after some kms.
            """
            # Calculate actual route distance for the closest candidate
            try:
                actual_route = calculate_route_distance(
                    asset_lat,
                    asset_lon,
                    safe_place.location["lat"],
                    safe_place.location["lon"],
                )
                min_distance = straight_distance
                route_distance = actual_route
                best_safe_place = safe_place.id
            except NotImplementedError:
                # Fallback to Haversine if OSRM not implemented
                min_distance = straight_distance
                route_distance = straight_distance
                best_safe_place = safe_place.id

    return (best_safe_place, min_distance, route_distance) if best_safe_place else None


def analyze_evacuation_routes(state: GraphState) -> Dict[str, Any]:
    """
    Calculate actual road distances and evacuation times for high-risk assets.

    This node runs after risk analysis to provide realistic evacuation routing.
    It only processes assets with high or medium risk levels.

    For each at-risk asset, it:
    1. Identifies nearest safe location
    2. Calculates actual route distance (vs straight-line)
    3. Estimates evacuation time
    4. Provides route feasibility assessment

    Args:
        state: Current graph state with risk assessments

    Returns:
        Updated state with route_details list
    """

    assets = state["assets"]
    risk_assessments = state["risk_assessments"]

    # Filter for high and medium risk assets
    at_risk = [r for r in risk_assessments if r.risk_level in ["high", "medium"]]

    # Identify safe places from assets
    safe_places = [a for a in assets if a.type == "SafePlace"]

    route_details = []

    for risk in at_risk:
        asset = find_asset_by_id(assets, risk.asset_id)
        if not asset:
            continue

        asset_lat = asset.location["lat"]
        asset_lon = asset.location["lon"]

        # Find nearest safe location
        safe_location_info = find_nearest_safe_location(
            asset_lat, asset_lon, safe_places
        )

        if safe_location_info:
            safe_place_id, straight_distance, route_distance = safe_location_info

            # Estimate evacuation time
            # Assumptions:
            # - Average speed: 40 km/h in emergency (accounting for traffic, caution)
            # - Add 10 minutes for preparation/loading
            travel_time_hours = route_distance / 40.0
            travel_time_minutes = (travel_time_hours * 60) + 10

            # Calculate route efficiency (how much longer than straight line)
            route_efficiency = (
                (route_distance / straight_distance) if straight_distance > 0 else 1.0
            )

            route_detail = {
                "asset_id": asset.id,
                "asset_type": asset.type,
                "risk_level": risk.risk_level,
                "safe_place_id": safe_place_id,
                "straight_distance_km": round(straight_distance, 2),
                "route_distance_km": round(route_distance, 2),
                "estimated_time_minutes": round(travel_time_minutes, 1),
                "route_efficiency": round(
                    route_efficiency, 2
                ),  # 1.0 = perfect, >1.5 = winding route
                "feasibility": _assess_route_feasibility(
                    route_distance, travel_time_minutes
                ),
            }
        else:
            # No safe place found - use fallback assessment
            route_detail = {
                "asset_id": asset.id,
                "asset_type": asset.type,
                "risk_level": risk.risk_level,
                "safe_place_id": None,
                "straight_distance_km": None,
                "route_distance_km": None,
                "estimated_time_minutes": None,
                "route_efficiency": None,
                "feasibility": "no_safe_location",
            }

        route_details.append(route_detail)

    return {"route_details": route_details}


def _assess_route_feasibility(route_distance_km: float, time_minutes: float) -> str:
    """
    Assess if evacuation route is feasible given the circumstances.

    Returns:
        "feasible", "challenging", or "critical"
    """
    # Feasible: < 30 minutes, reasonable distance
    if time_minutes < 30 and route_distance_km < 20:
        return "feasible"

    # Challenging: 30-60 minutes or 20-50km
    elif time_minutes < 60 and route_distance_km < 50:
        return "challenging"

    # Critical: > 60 minutes or > 50km
    else:
        return "critical"
