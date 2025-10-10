# Emergency Assistant 🚨

An AI-powered agentic system for intelligent decision-making in emergency scenarios, built with LangGraph.

## 🎯 Overview

Emergency Assistant analyzes threats (fires, storms, terrorist attacks), and automatically generates evacuation plans for critical assets (data centers, energy plants, radar stations). The system uses a multi-agent approach with an **Evaluator-Optimizer pattern** to ensure high-quality emergency response plans.

## ✨ Key Features

- 🤖 **Multi-Agent Architecture**: Parser → Analyzer → Proposer → Evaluator workflow
- 📍 **Geospatial Risk Assessment**: Calculates threat proximity and risk levels for each asset
- 🔄 **Self-Improving Plans**: Iterative plan refinement until quality threshold is met
   - Several sub evaluators specialists
- 📲 **Push Notifications**: Real-time alerts via [Pushover](https://pushover.net/)
- 💾 **Persistent Checkpoints**: SQLite-based state management for reliability
- 📊 **Full Observability**: Integrated LangSmith tracing
- 🧱 **LLM Injection Firewall**: Protects against malicious external prompts
<!-- - 🎨 **Interactive UI**: Gradio interface with map visualization -->

## 🏗️ Architecture

```
              ┌────────────────────────────────────────┐
              │                 Parser                 │
              └────────────────────────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────┐
              │                 Analyzer               │
              └────────────────────────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────┐
              │             RouteAnalyzer              │
              └────────────────────────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────┐
              │                 Proposer               │
              │     (generates an initial or revised plan) │
              └────────────────────────────────────────┘
                                  │
             ┌────────────────────┴────────────────────┐
             │                   │                     │
             ▼                   ▼                     ▼
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Operational_Eval   │ │    Social_Eval     │ │   Economic_Eval    │
│  (strict ≥ 0.6)    │ │  (lenient ≥ 0.5)   │ │  (lenient ≥ 0.5)   │
└────────────────────┘ └────────────────────┘ └────────────────────┘
             │                   │                     │
             └───────────────────┴─────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────┐
              │             Meta_Evaluator             │
              │  (synthesis of the three evaluations)  │
              └────────────────────────────────────────┘
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
        ┌────────────────────────┐  ┌────────────────────────┐
        │        Notifier        │  │        Proposer        │
        │ (plan approved, alert) │  │ (retries with improvements) │
        └────────────────────────┘  └────────────────────────┘
                         │                 │
                         └───────► Iterative Cycle ◄───────┘

```

## 🚀 Quick Start

```bash
# Install dependencies with uv
uv sync

# for test
uv run python tests/test_yaml.py
uv run python tests/test_firewall.py
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
│   ├── config.py
│   ├── firewall.py
│   ├── graph.py
│   ├── nodes
│   │   ├── analyzer.py
│   │   ├── evaluator_economic.py
│   │   ├── evaluator_meta.py
│   │   ├── evaluator_operational.py
│   │   ├── evaluator_politic.py
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
Gradio interface before loading an scenario:
    <figure style="margin: 0;">
        <img src="https://github.com/MartinezAgullo/agents-lg-emergency-assistant/blob/main/data/gradio_0_empty.png" alt="Gradio interface" style="width: 100%; max-width: 400px; display: block;">
    </figure>

Evacuation routes for an emergency scenario:
    <figure style="margin: 0;">
        <img src="https://github.com/MartinezAgullo/agents-lg-emergency-assistant/blob/main/data/gradio_a_maps.png" alt="Routes" style="width: 100%; max-width: 400px; display: block;">
    </figure>


## 📝 License

GNU General Public License (GPL) 3.0

---

 <!-- tree -I "__pycache__|agents_crewai_tactical_multimodal.egg-info|__init__.py|inputs|uv.lock|README.md|tests|*.log|*.db*|*.png|*.PNG" -->
