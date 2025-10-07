"""
Test script for YAML input parsing.

Usage:
    python test_yaml.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph import compile_graph
from src.state import GraphState

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "emergency-assistant-yaml-test"


def load_yaml_file(filepath: str = "data/actors_japan.yaml") -> str:
    """Load YAML file as string"""
    with open(filepath, "r") as f:
        return f.read()


def main():
    print("=" * 80)
    print("🚨 TESTING YAML INPUT")
    print("=" * 80)

    # Load YAML string
    print("\n📁 Loading YAML from data/actors_japan.yaml...")
    try:
        yaml_content = load_yaml_file()
        print(f"✅ Loaded {len(yaml_content)} characters")
    except FileNotFoundError:
        print("❌ Error: data/actors_japan.yaml not found!")
        return

    # Prepare state with YAML string
    initial_state: GraphState = {
        "raw_input": yaml_content,  # Pass YAML string directly
        "assets": [],
        "dangers": [],
        "risk_assessments": [],
        "route_details": None,
        "proposed_plan": None,
        "evaluation_feedback": None,
        "retry_count": 0,
        "final_plan": None,
        "notifications_sent": False,
        "error": None,
    }

    # Setup checkpointer
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_path = str(checkpoint_dir / "test_yaml.db")

    # Execute graph
    print("\n🔧 Executing graph...\n")

    with SqliteSaver.from_conn_string(checkpoint_path) as checkpointer:
        graph = compile_graph(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "yaml-test-1"}}

        final_state = None
        step_count = 0

        for state in graph.stream(initial_state, config, stream_mode="values"):
            step_count += 1
            final_state = state

            # Print progress
            if state.get("error"):
                print(f"❌ Error: {state['error']}")
                break

            if state.get("assets"):
                print(
                    f"✅ Step {step_count}: Parsed {len(state['assets'])} assets and {len(state.get('dangers', []))} dangers"
                )

            if state.get("risk_assessments"):
                high = [r for r in state["risk_assessments"] if r.risk_level == "high"]
                print(
                    f"✅ Step {step_count}: Risk analysis complete - {len(high)} high-risk situations"
                )

            if state.get("route_details"):
                print(
                    f"✅ Step {step_count}: Route analysis complete - {len(state['route_details'])} routes calculated"
                )

            if state.get("final_plan"):
                print(
                    f"✅ Step {step_count}: Final plan approved (Quality: {state['final_plan'].plan_quality_score:.2f})"
                )

    print("\n" + "=" * 80)
    print("📊 YAML TEST COMPLETE")
    print("=" * 80)

    if final_state:
        if final_state.get("error"):
            print(f"\n❌ Test failed: {final_state['error']}")
        else:
            print("\n✅ Successfully processed YAML input!")
            print(f"   Assets parsed: {len(final_state.get('assets', []))}")
            print(f"   Dangers parsed: {len(final_state.get('dangers', []))}")
            if final_state.get("final_plan"):
                plan = final_state["final_plan"]
                print(f"   Assets to evacuate: {len(plan.assets_to_evacuate)}")
                print(f"   Helpers: {len(plan.helpers)}")


if __name__ == "__main__":
    required_vars = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        exit(1)

    main()
