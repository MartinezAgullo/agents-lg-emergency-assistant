# src/graph.py

from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from .config import MAX_RETRIES
from .nodes.analyzer import analyze_risks
from .nodes.evaluator_economic import evaluate_economic
from .nodes.evaluator_meta import evaluate_meta
from .nodes.evaluator_operational import evaluate_operational
from .nodes.evaluator_social import evaluate_social
from .nodes.notifier import send_notifications
from .nodes.parser import parse_input
from .nodes.proposer import propose_plan
from .nodes.route_analyzer import analyze_evacuation_routes
from .state import GraphState


def should_retry_plan(
    state: GraphState,
) -> Literal["approved", "needs_improvement", "max_retries_reached"]:
    """
    Decide if the plan needs improvement based on meta-evaluation.

    Plan is approved ONLY if all three evaluators approved.
    """
    meta_eval = state.get("meta_evaluation")

    if not meta_eval:
        # Safety fallback - if no meta evaluation exists, retry
        return "needs_improvement"

    if meta_eval.overall_approved:
        return "approved"
    elif state["retry_count"] < MAX_RETRIES:
        return "needs_improvement"
    else:
        return "max_retries_reached"


def create_emergency_graph() -> StateGraph:
    """
    Create and configure the emergency response graph with parallel evaluators.

    Graph structure:
        Parser → Analyzer → RouteAnalyzer → Proposer
                                               ↓
                        ┌──────────────────────┼──────────────────────┐
                        ↓                      ↓                       ↓
                Operational_Eval       Social_Eval            Economic_Eval
                        ↓                      ↓                       ↓
                        └──────────────────────┼───────────────────────┘
                                               ↓
                                         Meta_Evaluator
                                               ↓
                                      [All approved?]
                                  Yes ↓          ↓ No
                                  Notifier    Proposer (retry)
    """

    # Initialize the graph
    graph_builder = StateGraph(GraphState)

    # Add nodes
    graph_builder.add_node("parser", parse_input)
    graph_builder.add_node("analyzer", analyze_risks)
    graph_builder.add_node("route_analyzer", analyze_evacuation_routes)
    graph_builder.add_node("proposer", propose_plan)

    # Three parallel evaluators
    graph_builder.add_node("evaluator_operational", evaluate_operational)
    graph_builder.add_node("evaluator_social", evaluate_social)
    graph_builder.add_node("evaluator_economic", evaluate_economic)

    # Meta-evaluator synthesizes results
    graph_builder.add_node("evaluator_meta", evaluate_meta)

    graph_builder.add_node("notifier", send_notifications)

    # Define linear edges
    graph_builder.add_edge("parser", "analyzer")
    graph_builder.add_edge("analyzer", "route_analyzer")
    graph_builder.add_edge("route_analyzer", "proposer")

    # Parallel evaluation: proposer → three evaluators
    graph_builder.add_edge("proposer", "evaluator_operational")
    graph_builder.add_edge("proposer", "evaluator_social")
    graph_builder.add_edge("proposer", "evaluator_economic")

    # All three evaluators → meta-evaluator
    graph_builder.add_edge("evaluator_operational", "evaluator_meta")
    graph_builder.add_edge("evaluator_social", "evaluator_meta")
    graph_builder.add_edge("evaluator_economic", "evaluator_meta")

    # Conditional edge: after meta-evaluator
    graph_builder.add_conditional_edges(
        "evaluator_meta",
        should_retry_plan,
        {
            "approved": "notifier",  # All three evaluators approved
            "needs_improvement": "proposer",  # At least one evaluator rejected
            "max_retries_reached": "notifier",  # Give up after 4 retries
        },
    )

    # Final edge
    graph_builder.add_edge("notifier", END)

    # Set entry point
    graph_builder.set_entry_point("parser")

    return graph_builder


def compile_graph(checkpointer: SqliteSaver = None):
    """Compile the graph with optional checkpointer for persistence"""
    from pathlib import Path

    graph_builder = create_emergency_graph()

    if checkpointer:
        graph = graph_builder.compile(checkpointer=checkpointer)
    else:
        graph = graph_builder.compile()

    # Generate and save graph visualization
    try:
        graph_image = graph.get_graph().draw_mermaid_png()

        # Ensure data directory exists
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)

        # Save the graph image
        output_path = data_dir / "emergency_graph.png"
        with open(output_path, "wb") as f:
            f.write(graph_image)

        print(f"✅ Graph visualization saved to: {output_path}")
    except Exception as e:
        print(f"⚠️ Could not generate graph visualization: {e}")

    return graph
