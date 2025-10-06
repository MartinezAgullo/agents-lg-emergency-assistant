#!/usr/bin/env python3
"""
Emergency Assistant - Gradio Interface

Web interface for the emergency response AI system using LangGraph.
Provides interactive map visualization and plan generation.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

import gradio as gr
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph import compile_graph
from src.state import GraphState

# Load environment variables
load_dotenv()

# Setup LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "emergency-assistant"


# ==================== GRAPH EXECUTION ====================


def run_emergency_response(actors_json: str) -> Dict[str, Any]:
    """
    Execute the emergency response graph with the provided input.

    Args:
        actors_json: JSON string with assets and dangers

    Returns:
        Dictionary with execution results
    """
    try:
        # Parse input
        actors_data = json.loads(actors_json)

        # Prepare initial state
        initial_state: GraphState = {
            "raw_input": actors_data,
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
        checkpoint_path = str(checkpoint_dir / "gradio_emergency.db")

        # Execute graph
        with SqliteSaver.from_conn_string(checkpoint_path) as checkpointer:
            graph = compile_graph(checkpointer=checkpointer)

            config = {
                "configurable": {"thread_id": f"gradio-run-{os.urandom(4).hex()}"}
            }

            # Run to completion
            final_state = None
            for state in graph.stream(initial_state, config, stream_mode="values"):
                final_state = state

            return {
                "success": True,
                "state": final_state,
                "error": final_state.get("error") if final_state else None,
            }

    except json.JSONDecodeError as e:
        return {"success": False, "state": None, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "state": None, "error": f"Execution error: {str(e)}"}


# ==================== UI FORMATTERS ====================


def format_risk_assessments(risk_assessments) -> str:
    """Format risk assessments for display"""
    if not risk_assessments:
        return "No risk assessments available"

    high = [r for r in risk_assessments if r.risk_level == "high"]
    medium = [r for r in risk_assessments if r.risk_level == "medium"]
    low = [r for r in risk_assessments if r.risk_level == "low"]

    output = "### Risk Assessment Summary\n\n"
    output += f"- **High Risk:** {len(high)}\n"
    output += f"- **Medium Risk:** {len(medium)}\n"
    output += f"- **Low Risk:** {len(low)}\n\n"

    if high:
        output += "#### High-Risk Situations:\n"
        for r in high:
            output += f"- `{r.asset_id}` threatened by `{r.danger_id}` ({r.distance_km:.2f} km)\n"

    return output


def format_route_details(route_details) -> str:
    """Format evacuation route details for display"""
    if not route_details:
        return "No route analysis available"

    output = "### Evacuation Routes\n\n"

    for route in route_details:
        output += f"#### {route['asset_id']}\n"
        output += f"- **Risk Level:** {route['risk_level']}\n"

        if route.get("safe_place_id"):
            output += f"- **Destination:** {route['safe_place_id']}\n"
            output += f"- **Route Distance:** {route['route_distance_km']} km\n"
            output += f"- **Estimated Time:** {route['estimated_time_minutes']} min\n"
            output += f"- **Feasibility:** {route['feasibility']}\n"
        else:
            output += "- **Status:** No safe location found\n"

        output += "\n"

    return output


def format_evacuation_plan(plan) -> str:
    """Format evacuation plan for display"""
    if not plan:
        return "No plan generated"

    output = "### Evacuation Plan\n\n"
    output += f"**Quality Score:** {plan.plan_quality_score:.2f}\n\n"

    output += f"#### Assets to Evacuate ({len(plan.assets_to_evacuate)})\n"
    for asset_id in plan.assets_to_evacuate:
        output += f"- {asset_id}\n"

    output += f"\n#### Helper Assets ({len(plan.helpers)})\n"
    for helper_id in plan.helpers:
        output += f"- {helper_id}\n"

    output += f"\n#### Reasoning\n{plan.reasoning}\n"

    return output


def create_map_html(state: Dict[str, Any]) -> str:
    """Create an interactive map with Leaflet.js"""

    assets = state.get("assets", [])
    dangers = state.get("dangers", [])

    if not assets and not dangers:
        return "<p>No data to display</p>"

    # Calculate map center
    all_lats = [a.location["lat"] for a in assets] + [
        d.location["lat"] for d in dangers
    ]
    all_lons = [a.location["lon"] for a in assets] + [
        d.location["lon"] for d in dangers
    ]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ height: 500px; width: 100%; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([{center_lat}, {center_lon}], 11);

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);

            // Asset markers (blue)
            var assetIcon = L.icon({{
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            }});

            // Danger markers (red)
            var dangerIcon = L.icon({{
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            }});

            // SafePlace markers (green)
            var safePlaceIcon = L.icon({{
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            }});
    """

    # Add assets
    for asset in assets:
        lat = asset.location["lat"]
        lon = asset.location["lon"]
        icon = "safePlaceIcon" if asset.type == "SafePlace" else "assetIcon"
        popup = f"<b>{asset.type}</b><br>{asset.id}<br>{asset.description}"
        html += f"""
            L.marker([{lat}, {lon}], {{icon: {icon}}})
                .addTo(map)
                .bindPopup("{popup}");
        """

    # Add dangers
    for danger in dangers:
        lat = danger.location["lat"]
        lon = danger.location["lon"]
        severity = getattr(danger, "severity", "unknown")
        popup = f"<b>{danger.type}</b><br>{danger.id}<br>Severity: {severity}<br>{danger.description}"
        html += f"""
            L.marker([{lat}, {lon}], {{icon: dangerIcon}})
                .addTo(map)
                .bindPopup("{popup}");
        """

    html += """
        </script>
    </body>
    </html>
    """

    return html


# ==================== GRADIO INTERFACE ====================


def process_emergency(actors_json: str):
    """Main processing function for Gradio interface"""

    # Validate input
    if not actors_json or actors_json.strip() == "":
        return (
            "Error: Please provide input data",
            "",
            "",
            "",
            "<p>No map available</p>",
        )

    # Run graph
    result = run_emergency_response(actors_json)

    if not result["success"]:
        return (f"Error: {result['error']}", "", "", "", "<p>Execution failed</p>")

    state = result["state"]

    # Format outputs
    risk_text = format_risk_assessments(state.get("risk_assessments", []))
    route_text = format_route_details(state.get("route_details", []))
    plan_text = format_evacuation_plan(state.get("final_plan"))

    # Status message
    if state.get("error"):
        status = f"⚠️ Completed with errors: {state['error']}"
    elif state.get("notifications_sent"):
        status = "✅ Emergency plan generated and notifications sent!"
    else:
        status = "✅ Emergency plan generated (notifications not sent)"

    # Create map
    map_html = create_map_html(state)

    return status, risk_text, route_text, plan_text, map_html


def load_example_file(filepath: str = "data/actors_with_safeplaces.json") -> str:
    """Load example actors file"""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except FileNotFoundError:
        return json.dumps({"assets": [], "dangers": []}, indent=2)


# ==================== GRADIO APP ====================


def create_interface():
    """Create the Gradio interface"""

    with gr.Blocks(title="Emergency Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🚨 Emergency Response Assistant

        AI-powered emergency decision-making system using LangGraph.
        Upload or paste your emergency scenario data to generate an evacuation plan.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Input Data")

                input_json = gr.Code(
                    label="Emergency Scenario (JSON)",
                    language="json",
                    lines=15,
                    value=load_example_file(),
                )

                with gr.Row():
                    submit_btn = gr.Button(
                        "🚀 Generate Plan", variant="primary", size="lg"
                    )
                    clear_btn = gr.Button("🔄 Clear", size="lg")
                    load_example_btn = gr.Button("📁 Load Example", size="lg")

                status_output = gr.Markdown(label="Status")

            with gr.Column(scale=1):
                gr.Markdown("### Map Visualization")
                map_output = gr.HTML(label="Interactive Map")

        with gr.Row():
            with gr.Column():
                risk_output = gr.Markdown(label="Risk Assessment")

            with gr.Column():
                route_output = gr.Markdown(label="Evacuation Routes")

        with gr.Row():
            plan_output = gr.Markdown(label="Evacuation Plan")

        gr.Markdown("""
        ---
        ### How to Use

        1. **Input Format:** Provide JSON with `assets` and `dangers` arrays
        2. **Asset Types:** DataCenter, EnergyPlant, SafePlace, etc.
        3. **Danger Types:** Fire, Heavy_Storm, Terrorist, Flood
        4. **Optional Fields:** Add `comments` and `severity` for enhanced analysis
        5. **Safe Places:** Include SafePlace assets for route calculation

        The system will:
        - Analyze risks based on proximity and threat type
        - Calculate evacuation routes to safe locations
        - Generate an optimized evacuation plan
        - Send notifications via Pushover (if configured)

        View detailed traces in [LangSmith](https://smith.langchain.com/)
        """)

        # Event handlers
        submit_btn.click(
            fn=process_emergency,
            inputs=[input_json],
            outputs=[status_output, risk_output, route_output, plan_output, map_output],
        )

        clear_btn.click(
            fn=lambda: ("", "", "", "", "<p>No map</p>"),
            inputs=[],
            outputs=[status_output, risk_output, route_output, plan_output, map_output],
        )

        load_example_btn.click(fn=load_example_file, inputs=[], outputs=[input_json])

    return app


# ==================== MAIN ====================


def main():
    """Launch the Gradio application"""

    # Check environment variables
    required_vars = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set them in your .env file")
        return

    # Create and launch interface
    app = create_interface()

    print("\n" + "=" * 80)
    print("🚨 EMERGENCY ASSISTANT - Starting Gradio Interface")
    print("=" * 80)
    print("\n📊 LangSmith Project: emergency-assistant")
    print("💾 Checkpoints: checkpoints/gradio_emergency.db")
    print("🌐 Opening browser...\n")

    app.launch(server_name="127.0.0.1", server_port=7860, share=False, show_error=True)


if __name__ == "__main__":
    main()
