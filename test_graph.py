#!/usr/bin/env python3
"""
Test script for the Emergency Assistant graph.

This script runs the complete graph workflow end-to-end using the actors.json file.
It's useful for debugging and validating the graph logic before building the UI.

Usage:
    python test_graph.py
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "emergency-assistant-test"

from src.graph import compile_graph
from src.state import GraphState
from langgraph.checkpoint.sqlite import SqliteSaver


def load_actors_data(filepath: str = "data/actors.json") -> dict:
    """Load actors data from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_state_summary(state: GraphState, step: str):
    """Print a summary of the current state"""
    print(f"\n📊 State after: {step}")
    print("-" * 80)
    
    if state.get("error"):
        print(f"❌ Error: {state['error']}")
        return
    
    if state.get("assets"):
        print(f"✅ Assets parsed: {len(state['assets'])}")
        for asset in state['assets']:
            print(f"   - {asset.id} ({asset.type})")
    
    if state.get("dangers"):
        print(f"✅ Dangers parsed: {len(state['dangers'])}")
        for danger in state['dangers']:
            severity = f" [{danger.severity}]" if hasattr(danger, 'severity') and danger.severity else ""
            print(f"   - {danger.id} ({danger.type}){severity}")
    
    if state.get("risk_assessments"):
        print(f"\n🎯 Risk Assessments: {len(state['risk_assessments'])}")
        high_risks = [r for r in state['risk_assessments'] if r.risk_level == "high"]
        medium_risks = [r for r in state['risk_assessments'] if r.risk_level == "medium"]
        low_risks = [r for r in state['risk_assessments'] if r.risk_level == "low"]
        
        print(f"   - High risk: {len(high_risks)}")
        print(f"   - Medium risk: {len(medium_risks)}")
        print(f"   - Low risk: {len(low_risks)}")
        
        if high_risks:
            print("\n   High-risk situations:")
            for risk in high_risks:
                print(f"     • {risk.asset_id} ← {risk.danger_id} ({risk.distance_km:.2f} km)")
    
    if state.get("proposed_plan"):
        plan = state['proposed_plan']
        print(f"\n📋 Proposed Plan (Quality: {plan.plan_quality_score:.2f})")
        print(f"   - Assets to evacuate: {len(plan.assets_to_evacuate)}")
        if plan.assets_to_evacuate:
            for asset_id in plan.assets_to_evacuate:
                print(f"     • {asset_id}")
        print(f"   - Helper assets: {len(plan.helpers)}")
        if plan.helpers:
            for helper_id in plan.helpers:
                print(f"     • {helper_id}")
        print(f"   - Reasoning: {plan.reasoning[:150]}...")
    
    if state.get("evaluation_feedback"):
        print(f"\n💭 Evaluator Feedback:")
        print(f"   {state['evaluation_feedback'][:200]}...")
    
    if state.get("retry_count"):
        print(f"\n🔄 Retry count: {state['retry_count']}")
    
    if state.get("final_plan"):
        print(f"\n✅ Final Plan Approved!")
        print(f"   Quality Score: {state['final_plan'].plan_quality_score:.2f}")
    
    if state.get("notifications_sent") is not None:
        status = "✅ Sent" if state['notifications_sent'] else "❌ Failed"
        print(f"\n📲 Notifications: {status}")


def main():
    print_section("🚨 EMERGENCY ASSISTANT - GRAPH TEST")
    
    # Load test data
    print("\n📁 Loading actors data from data/actors.json...")
    try:
        actors_data = load_actors_data()
        print(f"✅ Loaded {len(actors_data['assets'])} assets and {len(actors_data['dangers'])} dangers")
    except FileNotFoundError:
        print("❌ Error: data/actors.json not found!")
        print("   Please ensure the file exists in the data/ directory")
        return
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Setup checkpointer (use context manager)
    print("\n💾 Setting up SQLite checkpointer...")
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_path = str(checkpoint_dir / "test_emergency.db")
    print("✅ Checkpointer ready")
    
    # Compile graph (checkpointer will be used inside context manager)
    print("\n🔧 Compiling emergency response graph...")
    graph = compile_graph(checkpointer=None)  # We'll add checkpointer in the stream context
    print("✅ Graph compiled successfully")
    print("   Graph visualization saved to: data/emergency_graph.png")
    
    # Prepare initial state
    print_section("🚀 RUNNING GRAPH")
    
    initial_state: GraphState = {
        "raw_input": actors_data,
        "assets": [],
        "dangers": [],
        "risk_assessments": [],
        "proposed_plan": None,
        "evaluation_feedback": None,
        "retry_count": 0,
        "final_plan": None,
        "notifications_sent": False,
        "error": None
    }
    
    # Configuration for the graph execution
    config = {
        "configurable": {
            "thread_id": "test-run-1"
        }
    }
    
    # Run the graph and stream results
    print("\n▶️  Executing graph...\n")
    
    try:
        step_count = 0
        
        # Use checkpointer context manager for the execution
        with SqliteSaver.from_conn_string(checkpoint_path) as checkpointer:
            # Recompile graph with checkpointer
            graph_with_checkpoint = compile_graph(checkpointer=checkpointer)
            
            for event in graph_with_checkpoint.stream(initial_state, config, stream_mode="values"):
                step_count += 1
                
                # Determine which node just executed based on state changes
                if step_count == 1:
                    current_step = "START"
                elif event.get("assets") and not event.get("risk_assessments"):
                    current_step = "Parser"
                elif event.get("risk_assessments") and not event.get("proposed_plan"):
                    current_step = "Analyzer"
                elif event.get("proposed_plan") and not event.get("evaluation_feedback"):
                    current_step = "Proposer"
                elif event.get("evaluation_feedback"):
                    current_step = "Evaluator"
                elif event.get("final_plan") or event.get("notifications_sent") is not None:
                    current_step = "Notifier"
                else:
                    current_step = f"Step {step_count}"
                
                print_state_summary(event, current_step)
            
            print_section("✅ GRAPH EXECUTION COMPLETE")
            
            # Get final state
            final_state = graph_with_checkpoint.get_state(config)
        
        print("\n📊 Final Statistics:")
        print(f"   Total steps executed: {step_count}")
        print(f"   Total retries: {final_state.values.get('retry_count', 0)}")
        
        if final_state.values.get('final_plan'):
            final_plan = final_state.values['final_plan']
            print(f"\n🎯 Final Plan Summary:")
            print(f"   - Quality Score: {final_plan.plan_quality_score:.2f}")
            print(f"   - Assets evacuated: {len(final_plan.assets_to_evacuate)}")
            print(f"   - Helpers deployed: {len(final_plan.helpers)}")
            print(f"   - Notifications sent: {'Yes' if final_state.values.get('notifications_sent') else 'No'}")
        
        print("\n💡 View detailed traces in LangSmith:")
        print("   https://smith.langchain.com/")
        
    except Exception as e:
        print(f"\n❌ Error during graph execution: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print_section("🏁 TEST COMPLETE")


if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set them in your .env file")
        exit(1)
    
    main()

