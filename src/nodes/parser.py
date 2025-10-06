# src/nodes/parser.py

from typing import Any, Dict

from ..firewall import validate_input
from ..state import Asset, Danger, GraphState


def parse_input(state: GraphState) -> Dict[str, Any]:
    """
    Parse and validate the raw input containing assets and dangers.
    Converts raw JSON data into structured Pydantic models for downstream processing.
    """
    raw_input = state["raw_input"]

    # Step 1: Security validation with AI firewall
    is_valid, error_message, sanitized_data = validate_input(raw_input)

    if not is_valid:
        # Firewall blocked the input
        return {"assets": [], "dangers": [], "error": error_message}

    # Step 2: Parse validated data into Pydantic models
    try:
        # Parse assets
        assets = [Asset(**asset_data) for asset_data in raw_input.get("assets", [])]

        # Parse dangers
        dangers = [
            Danger(**danger_data) for danger_data in raw_input.get("dangers", [])
        ]

        return {"assets": assets, "dangers": dangers, "error": None}

    except Exception as e:
        return {
            "assets": [],
            "dangers": [],
            "error": f"Failed to parse input: {str(e)}",
        }
