# Pilot Phase Delivery: Mixed Agent Workflow Demo

## 🎯 Objective
Demonstrate the flexibility of the Chameleon Workflow Engine by creating a complete example workflow that chains three distinct agent types: AI (LLM-powered), Automated (deterministic), and Human (interactive).

## 📦 Deliverables

### 1. Workflow Definition
**File**: `tools/mixed_agent_workflow.yaml`

A production-ready workflow template featuring:
- **Alpha Role** (Initiator): System-triggered workflow start
- **Beta Roles** (3 types):
  - AI_Analyzer: LLM-powered text analysis via Ollama
  - Auto_Calculator: Deterministic score calculation
  - Human_Approver: Interactive approval/rejection
- **Omega Role** (Archiver): Final workflow completion
- **Epsilon Role** (Error_Handler): Error remediation
- **Tau Role** (Timeout_Manager): Automated timeout handling

**Validation Status**: ✅ Passes all constitution checks (Articles IV, V, VI, XI)

### 2. Example Agent Implementations

#### AI Agent (`examples/ai_agent.py`)
- **Purpose**: Demonstrate AI-powered processing using Ollama
- **Features**:
  - Polls for work from AI_Analyzer role
  - Calls Ollama API for text summarization
  - Handles offline scenarios gracefully (reports failures)
  - Configurable model selection
- **Command Line**: `python examples/ai_agent.py --role-id <UUID> [--ollama-url URL] [--model MODEL]`

#### Auto Agent (`examples/auto_agent.py`)
- **Purpose**: Demonstrate automated deterministic processing
- **Features**:
  - Polls for work from Auto_Calculator role
  - Calculates scores based on AI summary characteristics
  - Simulates processing time (configurable delay)
  - Provides detailed calculation metadata
- **Command Line**: `python examples/auto_agent.py --role-id <UUID> [--processing-delay SECONDS]`

#### Human Agent (`examples/human_agent.py`)
- **Purpose**: Demonstrate human-in-the-loop processing
- **Features**:
  - Polls for work from Human_Approver role
  - Interactive console interface
  - Displays UOW attributes in readable format
  - Requires reasoning for rejections
- **Command Line**: `python examples/human_agent.py --role-id <UUID>`

### 3. Setup and Documentation

#### Setup Helper (`examples/setup_demo.py`)
- **Purpose**: Simplify deployment and testing
- **Features**:
  - Validates workflow is imported
  - Retrieves and displays role IDs
  - Provides copy-paste commands for running agents
  - Shows example curl command for workflow instantiation

#### Examples README (`examples/README.md`)
- Quick start guide with setup helper
- Detailed agent documentation
- Troubleshooting section
- Architecture notes and workflow diagram
- Command-line reference

## 🏗️ Architecture Highlights

### Data Flow
```
Alpha (Initiator)
    ↓ Initial_Queue
AI_Analyzer (Ollama)
    ↓ AI_Analysis_Queue
Auto_Calculator (Deterministic)
    ↓ Calculation_Queue
Human_Approver (Interactive)
    ↓ Approval_Queue
Omega (Archiver)
```

### Error Handling
- Failed UOWs route to Error_Queue
- Epsilon role handles remediation
- Agents can report failures via `/workflow/failure` endpoint

### Guardians
- **PASS_THRU**: Most pipeline stages (rapid transit)
- **CRITERIA_GATE**: Human approval status check
- **CERBERUS**: Omega role synchronization (Article VI)

## 🧪 Testing & Validation

### Workflow Validation
✅ Article IV: All interactions have producers and consumers  
✅ Article V: Exactly one role of each type (Alpha, Omega, Epsilon, Tau)  
✅ Article VI: Omega role has CERBERUS guardian  
✅ Article XI: TAU role present for timeout management

### Code Quality
✅ Formatted with Black (Python code style)  
✅ Validated with Ruff (linting)  
✅ Code review completed  
✅ All help text corrected

## 🚀 Quick Start

```bash
# 1. Install dependencies (if needed)
pip install -r requirements.txt

# 2. Import the workflow
python tools/workflow_manager.py -i -f tools/mixed_agent_workflow.yaml

# 3. Get setup instructions with role IDs
python examples/setup_demo.py

# 4. Start the workflow engine (in a terminal)
python -m chameleon_workflow_engine.server

# 5. Start the agents (in separate terminals, using role IDs from step 3)
python examples/ai_agent.py --role-id <AI_Analyzer_UUID>
python examples/auto_agent.py --role-id <Auto_Calculator_UUID>
python examples/human_agent.py --role-id <Human_Approver_UUID>

# 6. Instantiate a workflow instance (use curl command from step 3 output)
curl -X POST http://localhost:8000/workflow/instantiate \
  -H "Content-Type: application/json" \
  -d '{"template_id": "...", "initial_context": {"input_text": "Your text here"}}'

# 7. Watch the agents process the work!
```

## 📚 Key Files

| File | Purpose |
|------|---------|
| `tools/mixed_agent_workflow.yaml` | Workflow template definition |
| `examples/ai_agent.py` | AI-powered agent (Ollama) |
| `examples/auto_agent.py` | Automated deterministic agent |
| `examples/human_agent.py` | Interactive human agent |
| `examples/setup_demo.py` | Setup helper script |
| `examples/README.md` | Comprehensive documentation |

## 🎓 Learning Outcomes

This demo showcases:

1. **Multi-Modal Processing**: AI, automated, and human agents working together
2. **MCP Architecture**: Stateless agents polling for work
3. **Workflow Constitution**: Proper role types, guardians, and validation
4. **Error Handling**: Failures route to Epsilon role for remediation
5. **Graceful Degradation**: AI agent reports failures when Ollama is offline
6. **Production Patterns**: Heartbeats, transactional locking, atomic versioning

## 🔧 Customization

### Adding a New Agent Type
1. Define a new Beta role in the YAML
2. Add corresponding interaction and components
3. Create a new agent script following the existing pattern
4. Update setup_demo.py to include the new role

### Modifying the Workflow
1. Edit `tools/mixed_agent_workflow.yaml`
2. Re-import: `python tools/workflow_manager.py -i -f tools/mixed_agent_workflow.yaml`
3. Get new role IDs: `python examples/setup_demo.py`

### Using Different AI Models
The AI agent supports any Ollama model:
```bash
python examples/ai_agent.py --role-id <UUID> --model mistral
python examples/ai_agent.py --role-id <UUID> --model codellama
```

## 🐛 Troubleshooting

### "Cannot connect to Ollama"
- Install Ollama: https://ollama.ai
- Start Ollama: `ollama serve`
- Download a model: `ollama pull llama3`

### "No work available"
- Ensure workflow instance is created (step 6 above)
- Check that previous agents in the chain have completed
- Verify server is running

### "Role ID not provided"
- Run `python examples/setup_demo.py` to get role IDs
- The role IDs change each time the workflow is imported

## 📈 Next Steps

1. **Scale Up**: Run multiple instances of each agent for parallel processing
2. **Custom Workflows**: Create domain-specific workflows (invoice processing, document review, etc.)
3. **Monitoring**: Add logging and metrics to track agent performance
4. **Deployment**: Containerize agents for production deployment

## 📄 License

See the main repository LICENSE file.

---

**Created**: January 2026  
**Version**: Pilot Phase Demo v1.0  
**Status**: Production Ready ✅
