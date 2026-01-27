# Chameleon Workflow Engine - Example Agents

This directory contains example agents demonstrating the flexibility of the Chameleon Workflow Engine during the Pilot Phase. These agents interact with the workflow engine to process work items using different modalities: Human, AI (LLM), and Automated.

## Overview

The example agents work with the `mixed_agent_workflow.yaml` workflow, which chains three distinct processing roles:

1. **AI Agent** (`ai_agent.py`) - Uses Ollama to analyze and summarize text
2. **Auto Agent** (`auto_agent.py`) - Performs deterministic calculations
3. **Human Agent** (`human_agent.py`) - Provides human-in-the-loop approval

## Prerequisites

### General Requirements
- Python 3.9+
- Chameleon Workflow Engine server running (see main README)
- Required Python packages: `requests`

### AI Agent Additional Requirements
- Ollama installed and running: https://ollama.ai
- LLM model downloaded (default: llama3)
  ```bash
  ollama pull llama3
  ```

## Quick Start

### 1. Import the Workflow

First, import the mixed agent workflow into the database:

```bash
python tools/workflow_manager.py -l -f tools/mixed_agent_workflow.yaml
```

### 2. Get Role IDs

You'll need the role UUIDs for each agent. Query the database to find them:

```python
# Example using SQLite CLI
sqlite3 instance.db "SELECT role_id, name FROM Local_Roles WHERE name IN ('AI_Analyzer', 'Auto_Calculator', 'Human_Approver');"
```

Or use a database browser to inspect the `Local_Roles` table.

### 3. Start the Workflow Engine Server

```bash
python -m chameleon_workflow_engine.server
# Or
uvicorn chameleon_workflow_engine.server:app --reload --port 8000
```

### 4. Start the Agents

Open three separate terminal windows and start each agent:

**Terminal 1 - AI Agent:**
```bash
python examples/ai_agent.py --role-id <AI_Analyzer_role_id>
```

**Terminal 2 - Auto Agent:**
```bash
python examples/auto_agent.py --role-id <Auto_Calculator_role_id>
```

**Terminal 3 - Human Agent:**
```bash
python examples/human_agent.py --role-id <Human_Approver_role_id>
```

### 5. Instantiate a Workflow and Add Work

Use the API to create a workflow instance and inject work:

```bash
# Instantiate the workflow
curl -X POST http://localhost:8000/workflow/instantiate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "<workflow_template_id>",
    "initial_context": {
      "input_text": "The quick brown fox jumps over the lazy dog. This is a test of the Chameleon Workflow Engine."
    },
    "instance_name": "Demo Workflow Instance",
    "instance_description": "Testing the mixed agent workflow"
  }'
```

The workflow will automatically progress through the agents:
1. AI Agent picks up the work, generates a summary, and submits it
2. Auto Agent receives the summarized work, calculates a score, and submits it
3. Human Agent receives the work with both AI summary and Auto score for approval
4. Upon approval, the Archiver role completes the workflow

## Agent Details

### AI Agent (`ai_agent.py`)

**Purpose:** Analyze input text using Ollama LLM to generate summaries.

**Key Features:**
- Polls for work from the AI_Analyzer role
- Calls Ollama API for text generation
- Gracefully handles Ollama offline scenarios
- Reports failures to the workflow engine

**Command-line Options:**
```bash
python examples/ai_agent.py --help
```

**Example Usage:**
```bash
# Basic usage
python examples/ai_agent.py --role-id <UUID>

# Custom Ollama instance and model
python examples/ai_agent.py --role-id <UUID> --ollama-url http://remote-host:11434 --model mistral

# Custom polling interval
python examples/ai_agent.py --role-id <UUID> --poll-interval 10
```

### Auto Agent (`auto_agent.py`)

**Purpose:** Perform deterministic calculations on processed work items.

**Key Features:**
- Polls for work from the Auto_Calculator role
- Calculates scores based on AI summary characteristics
- Simulates processing time (configurable)
- Provides detailed calculation metadata

**Calculation Algorithm:**
- Base score: length of AI summary × 10
- Bonus: +50 per important keyword (urgent, critical, important, priority, essential)
- Penalty: -25 if summary is very short (< 50 chars)

**Command-line Options:**
```bash
python examples/auto_agent.py --help
```

**Example Usage:**
```bash
# Basic usage
python examples/auto_agent.py --role-id <UUID>

# Adjust processing delay
python examples/auto_agent.py --role-id <UUID> --processing-delay 2

# Custom server
python examples/auto_agent.py --role-id <UUID> --base-url http://remote-host:8000
```

### Human Agent (`human_agent.py`)

**Purpose:** Provide human-in-the-loop approval for workflow decisions.

**Key Features:**
- Polls for work from the Human_Approver role
- Displays UOW attributes in human-readable format
- Interactive console prompts for approval/rejection
- Requires reasoning for rejections

**Command-line Options:**
```bash
python examples/human_agent.py --help
```

**Example Usage:**
```bash
# Basic usage
python examples/human_agent.py --role-id <UUID>

# Custom polling interval
python examples/human_agent.py --role-id <UUID> --poll-interval 10

# Custom server
python examples/human_agent.py --role-id <UUID> --base-url http://remote-host:8000
```

**Interactive Controls:**
- `y` or `yes` - Approve the work
- `n` or `no` - Reject the work (requires reasoning)
- `q` - Quit the agent

## Workflow Diagram

```
┌─────────────┐
│   Initiator │ (Alpha Role - System)
│   (Alpha)   │
└──────┬──────┘
       │ Initial Queue
       ▼
┌─────────────┐
│ AI_Analyzer │ (Beta Role - Ollama Agent)
│   (Beta)    │ Summarizes input text
└──────┬──────┘
       │ AI Analysis Queue
       ▼
┌─────────────────┐
│ Auto_Calculator │ (Beta Role - Auto Agent)
│     (Beta)      │ Calculates score from summary
└────────┬────────┘
         │ Calculation Queue
         ▼
┌──────────────────┐
│ Human_Approver   │ (Beta Role - Human Agent)
│     (Beta)       │ Reviews and approves/rejects
└────────┬─────────┘
         │ Approval Queue
         ▼
┌─────────────┐
│  Archiver   │ (Omega Role - System)
│   (Omega)   │ Final archival
└─────────────┘
```

## Troubleshooting

### "Role ID not provided" Error
All agents require the `--role-id` parameter. Use the workflow manager to import the workflow, then query the database for role UUIDs.

### AI Agent: "Cannot connect to Ollama"
- Ensure Ollama is running: `ollama serve`
- Check the Ollama URL is correct (default: http://localhost:11434)
- Verify the model is downloaded: `ollama list`

### No Work Available
- Ensure the workflow has been instantiated via the API
- Check that the workflow instance is active
- Verify that previous agents in the chain have completed their work

### Connection Errors
- Ensure the Chameleon server is running on the specified URL
- Check firewall settings if using remote servers
- Verify the base URL includes the protocol (http:// or https://)

## Architecture Notes

These agents follow the **Model Context Protocol (MCP)** architecture:
- Agents are stateless and poll for work
- Work is locked when checked out (PENDING → ACTIVE)
- Heartbeats prevent zombie detection
- Failures are reported to the Epsilon (Error Handler) role

For more details, see:
- `docs/architecture/Interface_MCP_Specs.md` - API specifications
- `chameleon_workflow_engine/server.py` - Server implementation
- `tools/mixed_agent_workflow.yaml` - Workflow definition

## Next Steps

1. **Extend the Workflow:** Add more roles or modify the YAML to create custom workflows
2. **Build Custom Agents:** Use these examples as templates for domain-specific agents
3. **Deploy at Scale:** Run multiple instances of each agent for parallel processing
4. **Add Monitoring:** Integrate logging and metrics to track agent performance

## Contributing

Found a bug or have an improvement? Please submit an issue or pull request!

## License

See the main repository LICENSE file.
