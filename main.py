#!/usr/bin/env python3
"""
Emergency Assistant - Gradio Interface

Web interface for the emergency response AI system using LangGraph.
Provides interactive map visualization and plan generation.
"""

import os
from pathlib import Path
from typing import Any, Dict

import folium
import gradio as gr
from dotenv import load_dotenv
from folium.plugins import MarkerCluster
from gradio_folium import Folium
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph import compile_graph
from src.state import GraphState

# Load environment variables
load_dotenv()

# Setup LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "emergency-assistant"

# Map configuration
ORIGIN_COORDS = (39.4699, -0.3763)  # Valencia, Spain


# ==================== GRAPH EXECUTION ====================


def run_emergency_response(actors_data: str) -> Dict[str, Any]:
    """
    Execute the emergency response graph with the provided input.

    Args:
        actors_data: YAML or JSON string with assets and dangers

    Returns:
        Dictionary with execution results
    """
    try:
        # Prepare initial state (parser will handle YAML/JSON conversion)
        initial_state: GraphState = {
            "raw_input": actors_data,  # Pass as string - parser handles it
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

    except Exception as e:
        return {"success": False, "state": None, "error": f"Execution error: {str(e)}"}


# ==================== UI FORMATTERS ====================


def format_risk_assessments(risk_assessments, make_clickable=False) -> str:
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
            if make_clickable:
                output += f"- `{r.asset_id}` threatened by `{r.danger_id}` ({r.distance_km:.2f} km)\n"
            else:
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

    # Filter out evacuation zones from the assets_to_evacuate list
    assets_to_evacuate_filtered = [
        asset_id
        for asset_id in plan.assets_to_evacuate
        if not asset_id.startswith("evacuation_zone")
    ]

    output += f"#### Assets to Evacuate ({len(assets_to_evacuate_filtered)})\n"

    # Show evacuation zone assignments if available
    if plan.evacuation_zone_assignments:
        for asset_id in assets_to_evacuate_filtered:
            zone_id = plan.evacuation_zone_assignments.get(asset_id, "Not assigned")
            output += f"- {asset_id} → **{zone_id}**\n"
    else:
        for asset_id in assets_to_evacuate_filtered:
            output += f"- {asset_id}\n"

    output += f"\n#### Helper Assets ({len(plan.helpers)})\n"
    for helper_id in plan.helpers:
        output += f"- {helper_id}\n"

    return output


# ==================== MAP CREATION ====================
def create_empty_map():
    """Create an empty Folium map centered on Valencia"""
    m = folium.Map(location=ORIGIN_COORDS, zoom_start=10, tiles="cartodbdark_matter")
    return m


def create_map_centered_on_item(state: Dict[str, Any], item_id: str, zoom: int = 15):
    """Create a map centered on a specific asset or danger"""
    assets = state.get("assets", [])
    dangers = state.get("dangers", [])

    # Find the item by ID
    target = None
    for asset in assets:
        if asset.id == item_id:
            target = asset
            break

    if not target:
        for danger in dangers:
            if danger.id == item_id:
                target = danger
                break

    if not target:
        return create_map_with_data(state)  # Fallback to normal map

    # Create map centered on target
    center_lat = target.location["lat"]
    center_lon = target.location["lon"]

    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=zoom, tiles="cartodbdark_matter"
    )

    # Add all markers (same as before)
    cluster = MarkerCluster().add_to(m)
    final_plan = state.get("final_plan")

    # Add assets
    for asset in assets:
        lat = asset.location["lat"]
        lon = asset.location["lon"]

        popup_html = f"<b>{asset.type}</b><br>ID: {asset.id}<br>"
        if asset.comments:
            popup_html += f"Comments: {asset.comments}<br>"
        if hasattr(asset, "timestamp") and asset.timestamp:
            popup_html += f"Time: {asset.timestamp}"

        if asset.type in ["SafePlace", "EVACUATION_ZONE"]:
            color = "green"
            icon = "home"
        elif final_plan and asset.id in final_plan.assets_to_evacuate:
            color = "orange"
            icon = "exclamation-sign"
        else:
            color = "blue"
            icon = "info-sign"

        # Highlight the target item
        if asset.id == item_id:
            icon = folium.Icon(color=color, icon=icon, icon_color="yellow")
        else:
            icon = folium.Icon(color=color, icon=icon)

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=icon,
        ).add_to(cluster)

    # Add dangers
    for danger in dangers:
        lat = danger.location["lat"]
        lon = danger.location["lon"]
        severity = getattr(danger, "severity", "unknown")

        popup_html = (
            f"<b>{danger.type}</b><br>ID: {danger.id}<br>Severity: {severity}<br>"
        )
        if danger.comments:
            popup_html += f"Comments: {danger.comments}<br>"
        if hasattr(danger, "timestamp") and danger.timestamp:
            popup_html += f"Time: {danger.timestamp}"

        # Highlight the target item
        if danger.id == item_id:
            icon = folium.Icon(
                color="red", icon="exclamation-sign", icon_color="yellow"
            )
        else:
            icon = folium.Icon(color="red", icon="exclamation-sign")

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=icon,
        ).add_to(cluster)

    # Draw evacuation routes if plan exists
    if final_plan and final_plan.evacuation_zone_assignments:
        for asset_id, zone_id in final_plan.evacuation_zone_assignments.items():
            asset = next((a for a in assets if a.id == asset_id), None)
            zone = next((a for a in assets if a.id == zone_id), None)

            if asset and zone:
                folium.PolyLine(
                    locations=[
                        [asset.location["lat"], asset.location["lon"]],
                        [zone.location["lat"], zone.location["lon"]],
                    ],
                    color="yellow",
                    weight=3,
                    opacity=0.7,
                    popup=f"Evacuation route: {asset_id} → {zone_id}",
                ).add_to(m)

    return m


def create_map_with_data(state: Dict[str, Any]):
    """Create a Folium map with assets, dangers, and evacuation routes"""
    assets = state.get("assets", [])
    dangers = state.get("dangers", [])
    final_plan = state.get("final_plan")
    route_details = state.get("route_details") or []

    # # DEBUG: Print what we have
    # print(f"🔍 DEBUG - Route details count: {len(route_details)}")
    # if route_details:
    #     print(f"🔍 DEBUG - First route: {route_details[0]}")
    #     print(f"🔍 DEBUG - Has geometry: {'route_geometry' in route_details[0]}")

    # print(f"🔍 DEBUG - Final plan exists: {final_plan is not None}")
    # if final_plan:
    #     print(f"🔍 DEBUG - Evacuation assignments: {final_plan.evacuation_zone_assignments}")
    # ### end

    if not assets and not dangers:
        return create_empty_map()

    # Calculate map center
    all_lats = [a.location["lat"] for a in assets] + [
        d.location["lat"] for d in dangers
    ]
    all_lons = [a.location["lon"] for a in assets] + [
        d.location["lon"] for d in dangers
    ]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=11, tiles="cartodbdark_matter"
    )

    # Add markers with clustering
    cluster = MarkerCluster().add_to(m)

    # Add assets (blue markers)
    for asset in assets:
        lat = asset.location["lat"]
        lon = asset.location["lon"]

        # Build popup
        popup_html = f"""
        <b>{asset.type}</b><br>
        ID: {asset.id}<br>
        """
        if asset.comments:
            popup_html += f"Comments: {asset.comments}<br>"
        if hasattr(asset, "timestamp") and asset.timestamp:
            popup_html += f"Time: {asset.timestamp}"

        # Determine color based on type and evacuation status
        if asset.type in ["SafePlace", "EVACUATION_ZONE"]:
            color = "green"
            icon = "home"
        elif final_plan and asset.id in final_plan.assets_to_evacuate:
            color = "orange"  # Assets to evacuate
            icon = "exclamation-sign"
        else:
            color = "blue"
            icon = "info-sign"

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon=icon),
        ).add_to(cluster)

    # Add dangers (red markers)
    for danger in dangers:
        lat = danger.location["lat"]
        lon = danger.location["lon"]
        severity = getattr(danger, "severity", "unknown")

        # Build popup
        popup_html = f"""
        <b>{danger.type}</b><br>
        ID: {danger.id}<br>
        Severity: {severity}<br>
        """
        if danger.comments:
            popup_html += f"Comments: {danger.comments}<br>"
        if hasattr(danger, "timestamp") and danger.timestamp:
            popup_html += f"Time: {danger.timestamp}"

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="red", icon="exclamation-sign"),
        ).add_to(cluster)

    # Draw evacuation routes if plan exists
    if final_plan and final_plan.evacuation_zone_assignments:
        for asset_id, zone_id in final_plan.evacuation_zone_assignments.items():
            # Find route details for this asset
            route_detail = next(
                (r for r in route_details if r["asset_id"] == asset_id), None
            )

            if route_detail and route_detail.get("route_geometry"):
                # Draw actual OSRM route (curved road path)
                folium.PolyLine(
                    locations=route_detail["route_geometry"],  # Actual road path!
                    color="yellow",
                    weight=4,
                    opacity=0.8,
                    popup=f"Evacuation route: {asset_id} → {zone_id}<br>Distance: {route_detail['route_distance_km']} km<br>Time: {route_detail['estimated_time_minutes']} min",
                ).add_to(m)

    # Fit bounds to show all markers
    if all_lats and all_lons:
        m.fit_bounds([[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]])

    return m


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
            "",  # ← NEW: reasoning
            Folium(create_empty_map()),
            gr.update(choices=[], visible=False),
        )

    # Run graph
    result = run_emergency_response(actors_json)

    if not result["success"]:
        return (
            f"❌ Error: {result['error']}",
            "",
            "",
            "",
            "",  # ← NEW: reasoning
            Folium(create_empty_map()),
            gr.update(choices=[], visible=False),
        )

    state = result["state"]

    # Format outputs
    risk_text = format_risk_assessments(
        state.get("risk_assessments", []), make_clickable=True
    )
    route_text = format_route_details(state.get("route_details", []))

    # Split plan and reasoning
    final_plan = state.get("final_plan")
    plan_text = format_evacuation_plan(final_plan)
    reasoning_text = (
        f"**Reasoning:**\n\n{final_plan.reasoning}"
        if final_plan and final_plan.reasoning
        else "No reasoning available"
    )

    # Status message
    if state.get("error"):
        status = f"⚠️ Completed with errors: {state['error']}"
    elif state.get("notifications_sent"):
        status = "✅ Emergency plan generated and notifications sent!"
    else:
        status = "✅ Emergency plan generated (notifications not sent)"

    # Create map
    map_obj = create_map_with_data(state)

    # Collect all IDs for the dropdown
    all_ids = []
    for asset in state.get("assets", []):
        all_ids.append(asset.id)
    for danger in state.get("dangers", []):
        all_ids.append(danger.id)

    # Sort alphabetically
    all_ids.sort()

    return (
        status,
        risk_text,
        route_text,
        plan_text,
        reasoning_text,  # ← NEW: separate reasoning
        Folium(map_obj),
        gr.update(choices=all_ids, visible=True, value=None),
    )


def load_example_file(filepath: str = "data/actors_japan.yaml") -> str:
    """Load example actors file (YAML or JSON)"""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to empty YAML
        return "assets: []\ndangers: []"


# ==================== GRADIO APP ====================


def create_interface():
    """Create the Gradio interface"""

    with gr.Blocks(title="Emergency Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🚨 Emergency Response Assistant
        AI-powered emergency decision-making system using LangGraph
        """)

        # Top row: Input and Map side by side (EQUAL HEIGHT)
        with gr.Row(equal_height=True):
            # Left column: Input data
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Input Data")

                input_json = gr.Code(
                    label="Emergency Scenario (YAML or JSON)",
                    language="yaml",
                    lines=30,  # ← INCREASED from 20 to 30
                    max_lines=30,  # ← INCREASED from 20 to 30
                    value=load_example_file(),
                )

                with gr.Row():
                    submit_btn = gr.Button(
                        "🚀 Generate Plan", variant="primary", size="lg"
                    )
                    clear_btn = gr.Button("🔄 Clear", size="lg")
                    load_example_btn = gr.Button("📁 Load Example", size="lg")

                status_output = gr.Markdown(label="Status")

            # Right column: Map visualization (EQUAL HEIGHT)
            with gr.Column(scale=1):
                gr.Markdown("### 🗺️ Map Visualization")
                map_output = Folium(create_empty_map(), height=600)  # ← ADD HEIGHT

                # Zoom controls
                with gr.Row():
                    zoom_dropdown = gr.Dropdown(
                        choices=[],
                        label="🔍 Zoom to Location",
                        interactive=True,
                        visible=False,
                    )
                    zoom_level = gr.Slider(
                        minimum=10,
                        maximum=18,
                        value=15,
                        step=1,
                        label="Zoom Level",
                        visible=False,
                    )

        # Second row: Route Analysis and Risk/Plan (TWO COLUMNS)
        with gr.Row():
            # Left column: Route Analysis
            with gr.Column(scale=1):
                gr.Markdown("### 🛣️ Route Analysis")
                route_output = gr.Markdown(label="Evacuation Routes")

            # Right column: Risk Assessment + Evacuation Plan
            with gr.Column(scale=1):
                gr.Markdown("### 🎯 Risk Assessment")
                risk_output = gr.Markdown(label="Risk Summary")

                gr.Markdown("### 📋 Evacuation Plan")
                plan_output = gr.Markdown(label="Final Plan")

        # Third row: Reasoning (FULL WIDTH)
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 💭 Reasoning")
                reasoning_output = gr.Markdown(label="Plan Reasoning")

        # Collapsible instructions
        with gr.Accordion("ℹ️ How to Use", open=False):
            gr.Markdown("""
            ### Input Format
            Provide YAML or JSON with `assets` and `dangers` arrays:

            **Asset Types:** RADAR, DATA_CENTER, ENERGY_PLANT, HOSPITAL, FIREMEN, POLICE, MILITARY, CCT_AMBULANCE, EVACUATION_ZONE

            **Danger Types:** FIRE, HEAVY_STORM, TERRORIST, FLOOD, EARTHQUAKE

            **Required Fields:**
            - `id`: Unique identifier
            - `type`: Asset or danger type
            - `location`: Object with `lat` and `lon`

            **Optional Fields:**
            - `comments`: Additional context
            - `severity`: Low, Medium, High, Critical
            - `timestamp`: When recorded
            - `source`: Data source
            - `tags`: Array of tags

            ### System Features
            - ✅ Parses YAML/JSON automatically
            - ✅ Validates input through AI firewall
            - ✅ Analyzes risks by proximity and type
            - ✅ Calculates evacuation routes
            - ✅ Generates optimized plans
            - ✅ Sends Pushover notifications

            ### Map Legend
            - 🔵 Blue markers: Assets (protected resources)
            - 🟢 Green markers: Safe places / Evacuation zones
            - 🔴 Red markers: Dangers (threats)
            - 🟡 Yellow lines: Evacuation routes

            View detailed traces in [LangSmith](https://smith.langchain.com/)
            """)

        # Event handlers
        current_state = gr.State(value={})

        def handle_zoom(item_id, zoom_val, state_data):
            """Handle zoom to specific location"""
            if not item_id or not state_data:
                return Folium(create_empty_map())
            return Folium(
                create_map_centered_on_item(state_data, item_id, int(zoom_val))
            )

        submit_btn.click(
            fn=process_emergency,
            inputs=[input_json],
            outputs=[
                status_output,
                risk_output,
                route_output,
                plan_output,
                reasoning_output,  # ← NEW OUTPUT
                map_output,
                zoom_dropdown,
            ],
        ).then(fn=lambda result: result, inputs=[input_json], outputs=[current_state])

        # Zoom functionality
        zoom_dropdown.change(
            fn=lambda item_id, zoom_val: handle_zoom(
                item_id, zoom_val, run_emergency_response(input_json.value)["state"]
            )
            if item_id
            else gr.update(),
            inputs=[zoom_dropdown, zoom_level],
            outputs=[map_output],
        )

        clear_btn.click(
            fn=lambda: (
                "",
                "",
                "",
                "",
                "",  # ← NEW: reasoning output
                Folium(create_empty_map()),
                gr.update(choices=[], visible=False),
            ),
            inputs=[],
            outputs=[
                status_output,
                risk_output,
                route_output,
                plan_output,
                reasoning_output,  # ← NEW OUTPUT
                map_output,
                zoom_dropdown,
            ],
        )

        load_example_btn.click(
            fn=lambda: load_example_file("data/actors_japan.yaml"),
            inputs=[],
            outputs=[input_json],
        )

    return app


# ==================== MAIN ====================


def main():
    """Launch the Gradio application"""
    import signal
    import sys

    def signal_handler(sig, frame):
        print("\n\n" + "=" * 80)
        print("🛑 Program closed by user (Ctrl+C)")
        print("=" * 80)
        print("👋 Goodbye!\n")
        sys.exit(0)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

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
    print("🗺️  Map: Folium with dark theme")
    print("🌐 Opening browser...")
    print("\n💡 Press Ctrl+C to stop the server\n")

    try:
        app.launch(
            server_name="127.0.0.1", server_port=7860, share=False, show_error=True
        )
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("🛑 Program closed by user (Ctrl+C)")
        print("=" * 80)
        print("👋 Goodbye!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
