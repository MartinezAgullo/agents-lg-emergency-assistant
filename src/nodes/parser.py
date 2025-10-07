# src/nodes/parser.py

from typing import Any, Dict

import yaml

from ..firewall import validate_input
from ..state import Asset, Danger, GraphState


def parse_input(state: GraphState) -> Dict[str, Any]:
    """
    Parse and validate the raw input containing assets and dangers.

    Supports both JSON (dict) and YAML string inputs.
    First applies AI firewall security checks, then converts raw data
    into structured Pydantic models for downstream processing.
    """
    raw_input = state["raw_input"]

    # Handle YAML string input
    if isinstance(raw_input, str):
        try:
            raw_input = yaml.safe_load(raw_input)
        except yaml.YAMLError as e:
            return {
                "assets": [],
                "dangers": [],
                "error": f"Invalid YAML format: {str(e)}",
            }

    if not isinstance(raw_input, dict):
        return {
            "assets": [],
            "dangers": [],
            "error": f"Invalid input type: expected dict, got {type(raw_input).__name__}",
        }

    # Step 1: Security validation with AI firewall
    is_valid, error_message, sanitized_data = validate_input(raw_input)

    if not is_valid:
        # Firewall blocked the input
        return {"assets": [], "dangers": [], "error": error_message}

    # Step 2: Parse validated data into Pydantic models
    try:
        # Parse assets - normalize keys to lowercase
        assets = []
        for asset_data in sanitized_data.get("assets", []):
            # Create a copy with lowercase keys
            asset_dict = {k.lower(): v for k, v in asset_data.items()}
            assets.append(Asset(**asset_dict))

        # Parse dangers - normalize keys to lowercase
        dangers = []
        for danger_data in sanitized_data.get("dangers", []):
            # Create a copy with lowercase keys
            danger_dict = {k.lower(): v for k, v in danger_data.items()}
            dangers.append(Danger(**danger_dict))

        return {"assets": assets, "dangers": dangers, "error": None}

    except Exception as e:
        return {
            "assets": [],
            "dangers": [],
            "error": f"Failed to parse input: {str(e)}",
        }
