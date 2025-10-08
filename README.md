# Emergency Assistant 🚨

An AI-powered agentic system for intelligent decision-making in emergency scenarios, built with LangGraph.

## 🎯 Overview

Emergency Assistant analyzes threats (fires, storms, terrorist attacks) and automatically generates evacuation plans for critical assets (data centers, energy plants, radar stations). The system uses a multi-agent approach with an **Evaluator-Optimizer pattern** to ensure high-quality emergency response plans.

## ✨ Key Features

- 🤖 **Multi-Agent Architecture**: Parser → Analyzer → Proposer → Evaluator workflow
- 📍 **Geospatial Risk Assessment**: Calculates threat proximity and risk levels for each asset
- 🔄 **Self-Improving Plans**: Iterative plan refinement until quality threshold is met
- 📲 **Push Notifications**: Real-time alerts via [Pushover](https://pushover.net/)
- 💾 **Persistent Checkpoints**: SQLite-based state management for reliability
- 📊 **Full Observability**: Integrated LangSmith tracing
- 🧱 **LLM Injection Firewall**: Protects against malicious external promptss
<!-- - 🎨 **Interactive UI**: Gradio interface with map visualization -->

## 🏗️ Architecture

```
START → Parser → Analyzer → RouteAnalyzer → Proposer → Evaluator → [Plan OK?]
                                                            ↓ No
                                                         Proposer (retry)
                                                            ↓ Yes
                                                         Notifier → END
```

## 🚀 Quick Start

```bash
# Install dependencies with uv
uv sync

# for test
uv run python tests/test_graph.py


# Run the application
uv run python main.py
```

## 📁 Project Structure
Proposed project scaffolding
```
/emergency_assistant
├── checkpoints
├── data
│   ├── actors_japan.yaml
│   └── actors_valencia.yaml
├── main.py
├── pyproject.toml
├── src
│   ├── firewall.py
│   ├── graph.py
│   ├── nodes
│   │   ├── analyzer.py
│   │   ├── evaluator.py
│   │   ├── notifier.py
│   │   ├── parser.py
│   │   ├── proposer.py
│   │   └── route_analyzer.py
│   ├── state.py
│   └── tools.py
└── tests
    ├── test_firewall.py
    ├── test_graph.py
    └── test_yaml.py
```
## Interface
    <figure style="margin: 0;">
        <img src="https://github.com/MartinezAgullo/agents-lg-emergency-assistant/blob/main/data/gradio_0_empty.png" alt="Gradio interface" style="width: 100%; max-width: 400px; display: block;">
    </figure>

The evacuation routes are displayed as well
    <figure style="margin: 0;">
        <img src="https://github.com/MartinezAgullo/agents-lg-emergency-assistant/blob/main/data/gradio_a_maps.png" alt="Gradio interface" style="width: 100%; max-width: 400px; display: block;">
    </figure>


## 📝 License

GNU General Public License (GPL) 3.0

---

 <!-- tree -I "__pycache__|agents_crewai_tactical_multimodal.egg-info|__init__.py|inputs|uv.lock|README.md|tests|*.log|*.db*|*.png|*.PNG" -->
