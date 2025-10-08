# src/config.py

"""
Configuration parameters for the Emergency Assistant multi-evaluator system.

Adjust these values to tune the evaluation behavior:
- Weights: How much each evaluator contributes to final score (must sum to 1.0)
- Thresholds: Minimum score for each evaluator to approve (0.0-1.0)
- Max retries: How many times the proposer can iterate before giving up
"""

# ==================== RETRY CONFIGURATION ====================

MAX_RETRIES = 4  # Maximum number of plan improvement iterations


# ==================== EVALUATOR WEIGHTS ====================
# These determine how much each evaluator contributes to the weighted final score
# Must sum to 1.0

OPERATIONAL_WEIGHT = 0.60  # Most important - saving lives
SOCIAL_WEIGHT = 0.20  # Secondary - political implications
ECONOMIC_WEIGHT = 0.20  # Secondary - cost and resources

# Validation
assert (
    abs((OPERATIONAL_WEIGHT + SOCIAL_WEIGHT + ECONOMIC_WEIGHT) - 1.0) < 0.001
), "Evaluator weights must sum to 1.0"


# ==================== EVALUATOR THRESHOLDS ====================
# Minimum score required for each evaluator to approve the plan (0.0-1.0)
# Lower threshold = more lenient, higher threshold = more strict

OPERATIONAL_THRESHOLD = 0.70  # STRICT - operational safety is critical
SOCIAL_THRESHOLD = 0.50  # LENIENT - political costs acceptable in emergencies
ECONOMIC_THRESHOLD = 0.50  # LENIENT - high costs acceptable in emergencies


# ==================== LLM TEMPERATURE SETTINGS ====================
# Temperature controls randomness in LLM responses
# Lower = more consistent/strict, Higher = more creative/flexible

OPERATIONAL_TEMPERATURE = 0.2  # Very consistent for safety evaluations
SOCIAL_TEMPERATURE = 0.4  # Moderate for nuanced political analysis
ECONOMIC_TEMPERATURE = 0.3  # Moderate for cost analysis
META_TEMPERATURE = 0.3  # Moderate for synthesis
PROPOSER_TEMPERATURE = 0.7  # Higher for creative planning


# ==================== HELPER FUNCTIONS ====================


def get_evaluator_config():
    """Get all evaluator configuration as a dictionary"""
    return {
        "operational": {
            "weight": OPERATIONAL_WEIGHT,
            "threshold": OPERATIONAL_THRESHOLD,
            "temperature": OPERATIONAL_TEMPERATURE,
        },
        "social": {
            "weight": SOCIAL_WEIGHT,
            "threshold": SOCIAL_THRESHOLD,
            "temperature": SOCIAL_TEMPERATURE,
        },
        "economic": {
            "weight": ECONOMIC_WEIGHT,
            "threshold": ECONOMIC_THRESHOLD,
            "temperature": ECONOMIC_TEMPERATURE,
        },
        "max_retries": MAX_RETRIES,
    }


def format_weights_display():
    """Format weights as percentages for display"""
    return {
        "operational": f"{OPERATIONAL_WEIGHT*100:.0f}%",
        "social": f"{SOCIAL_WEIGHT*100:.0f}%",
        "economic": f"{ECONOMIC_WEIGHT*100:.0f}%",
    }
