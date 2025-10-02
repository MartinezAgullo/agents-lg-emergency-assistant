# Emergency Assistant 🚨

An AI-powered agentic system for intelligent decision-making in emergency scenarios, built with LangGraph.

## 🎯 Overview

Emergency Assistant analyzes threats (fires, storms, terrorist attacks) and automatically generates evacuation plans for critical assets (data centers, energy plants, radar stations). The system uses a multi-agent approach with an **Evaluator-Optimizer pattern** to ensure high-quality emergency response plans.

## ✨ Key Features

- 🤖 **Multi-Agent Architecture**: Parser → Analyzer → Proposer → Evaluator workflow
- 📍 **Geospatial Risk Assessment**: Calculates threat proximity and risk levels for each asset
- 🔄 **Self-Improving Plans**: Iterative plan refinement until quality threshold is met
- 📲 **Push Notifications**: Real-time alerts via Pushover
- 💾 **Persistent Checkpoints**: SQLite-based state management for reliability
- 📊 **Full Observability**: Integrated LangSmith tracing
- 🎨 **Interactive UI**: Gradio interface with map visualization

## 🏗️ Architecture

```
START → Parser → Analyzer → Proposer → Evaluator → [Plan OK?]
                                            ↓ No
                                         Proposer (retry with feedback)
                                            ↓ Yes
                                         Notifier → END
```

## 🚀 Quick Start

```bash
# Install dependencies with uv
uv sync

# Run the application
uv run python src/main.py
```

## 📁 Project Structure

```
/emergency_assistant
├── /src
│   ├── main.py           # Gradio entry point
│   ├── graph.py          # LangGraph definition
│   ├── /nodes            # Agent nodes (parser, analyzer, proposer, evaluator, notifier)
│   ├── tools.py          # Pushover, distance calculator, etc.
│   ├── state.py          # State schema
│   └── models.py         # Pydantic models
├── /data
│   └── actors.json       # Assets and dangers input
├── /checkpoints          # SQLite persistence
└── /prompts
    └── prompts.yaml      # System prompts
```

## 📝 License

GNU General Public License (GPL) 3.0

---

