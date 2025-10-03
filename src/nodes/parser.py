# src/nodes/parser.py

from typing import Dict, Any
from ..state import GraphState, Asset, Danger


def parse_input(state: GraphState) -> Dict[str, Any]:
    """
    Parse and validate the raw input containing assets and dangers.
    Converts raw JSON data into structured Pydantic models for downstream processing.
    """
    raw_input = state["raw_input"]
    
    try:
        # Parse assets
        assets = [Asset(**asset_data) for asset_data in raw_input.get("assets", [])]
        
        # Parse dangers
        dangers = [Danger(**danger_data) for danger_data in raw_input.get("dangers", [])]
        
        return {
            "assets": assets,
            "dangers": dangers,
            "error": None
        }
    
    except Exception as e:
        return {
            "assets": [],
            "dangers": [],
            "error": f"Failed to parse input: {str(e)}"
        }