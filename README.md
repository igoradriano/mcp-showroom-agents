# MCP Showroom Agents

Multi-agent customer journey demo built with OpenAI Agents, MCP tools, Streamlit, and PostgreSQL.

This project simulates a car dealership experience with specialized agents for reception, sales, and maintenance. The user interacts through a Streamlit chat UI while the agents call MCP tools exposed by a local Python server.

## Why This Project Matters

This repository is designed as an Agentic AI portfolio case study. It demonstrates:

- multi-agent orchestration with domain-specific handoffs
- MCP server integration for tool calling
- a conversational UI built with Streamlit
- real data access for dealership inventory and customer lookup
- separation between orchestration, tool layer, and interface

## Architecture

### Application flow

1. The user sends a message through the Streamlit interface.
2. The reception agent decides whether to answer directly or hand off to a specialist.
3. Specialist agents call MCP tools exposed by the local server.
4. The MCP server queries PostgreSQL and returns structured data to the agent runtime.
5. The final answer is rendered back in the chat interface.

### Agents

- Reception agent: first contact, triage, and handoff routing
- Sales agent: inventory discovery, dealership lookup, seller lookup, visit scheduling
- Maintenance agent: customer lookup, owned vehicle context, service scheduling

### Main files

- [streamlit_agents/app_core.py](streamlit_agents/app_core.py): shared Streamlit app logic, agent setup, and MCP runtime integration
- [streamlit_agents/chat_multi_agent.py](streamlit_agents/chat_multi_agent.py): main portfolio app
- [servers/server_agente_atendente.py](servers/server_agente_atendente.py): MCP tool server and database access layer

## Project Structure

```text
.
|-- arquivos/
|   `-- novadrive.png
|-- servers/
|   `-- server_agente_atendente.py
|-- streamlit_agents/
|   |-- app_core.py
|   `-- chat_multi_agent.py
|-- .env.example
|-- .gitignore
|-- README.md
|-- ingestion.py
`-- requirements.txt
```

## Setup

### Requirements

- Python 3.11+
- Access to the Python dependencies in [requirements.txt](requirements.txt)
- An OpenAI API key

### Environment

Copy `.env.example` to `.env` and set your OpenAI key.

Notes:

- The OpenAI key is private and must never be committed.
- The PostgreSQL connection values included in `.env.example` are intentionally public for this demo project.
- The MCP server also supports environment variable overrides for the database configuration.

### Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run the app

```powershell
streamlit run streamlit_agents/chat_multi_agent.py
```

The app starts a local MCP server process internally with:

```powershell
mcp run servers/server_agente_atendente.py
```

## Current Demo Boundaries

- Inventory, dealership, seller, and customer information are backed by PostgreSQL queries.
- Scheduling tools currently simulate a successful booking instead of persisting a real appointment.
- The Streamlit app exposes a single public entrypoint for a cleaner portfolio structure.

## Validation

Minimal validation currently included in the repository:

- dependency installation from [requirements.txt](requirements.txt)
- Python syntax compilation for [servers](servers/server_agente_atendente.py) and [streamlit_agents](streamlit_agents/chat_multi_agent.py)

Recommended local check:

```powershell
python -m compileall servers streamlit_agents
```

## Portfolio Positioning

This project should be presented as a technical demo of agentic orchestration rather than a full production system. The strongest signals for recruiters are:

- clear agent responsibilities
- visible MCP tool usage
- modular separation between UI, orchestration, and tools
- explicit documentation of what is real versus simulated in the workflow

## Next Improvements

- add lightweight automated tests for the MCP tool layer
- normalize dependency management and lock the runtime version
- add screenshots or a short GIF to the README
- initialize GitHub Actions checks for pull requests
