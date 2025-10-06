# src/graph.py

from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from .nodes.analyzer import analyze_risks
from .nodes.evaluator import evaluate_plan
from .nodes.notifier import send_notifications
from .nodes.parser import parse_input
from .nodes.proposer import propose_plan
from .state import GraphState


def should_retry_plan(
    state: GraphState,
) -> Literal["approved", "needs_improvement", "max_retries_reached"]:
    """Decide if the plan needs improvement based on quality score and retry count"""
    if state["proposed_plan"].plan_quality_score >= 0.7:
        return "approved"
    elif state["retry_count"] < 3:
        return "needs_improvement"
    else:
        return "max_retries_reached"


def create_emergency_graph() -> StateGraph:
    """Create and configure the emergency response graph"""

    # Initialize the graph
    graph_builder = StateGraph(GraphState)

    # Add nodes
    graph_builder.add_node("parser", parse_input)
    graph_builder.add_node("analyzer", analyze_risks)
    graph_builder.add_node("proposer", propose_plan)
    graph_builder.add_node("evaluator", evaluate_plan)
    graph_builder.add_node("notifier", send_notifications)

    # Define normal edges
    graph_builder.add_edge("parser", "analyzer")
    graph_builder.add_edge("analyzer", "proposer")
    graph_builder.add_edge("proposer", "evaluator")

    # Conditional edge: after evaluator
    graph_builder.add_conditional_edges(
        "evaluator",
        should_retry_plan,
        {
            "approved": "notifier",  # OK
            "needs_improvement": "proposer",  # Not OK, improve
            "max_retries_reached": "notifier",  # Not OK, but stop trying
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
