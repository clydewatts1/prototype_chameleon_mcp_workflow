# 🦎 Chameleon MCP Workflow Engine

A production-grade Model Context Protocol (MCP) workflow engine for orchestrating AI agent workflows with dynamic context injection, attribute-driven branching, and runtime model orchestration.

**Latest Release**: Phase 3 Complete
- ✅ Dynamic Context Injection (DCI) with model orchestration
- ✅ Frontend Real-Time Integration (REST API + WebSocket)
- ✅ Semantic Guards with attribute-driven branching
- ✅ Zombie actor detection and cleanup
- ✅ 11/11 DCI tests passing

## 🎯 Overview

The Chameleon Workflow Engine provides constitutional AI workflow orchestration featuring:

- **Dynamic Context Injection (DCI)**: Runtime LLM model override, system prompt injection, knowledge fragment injection
- **Semantic Guards**: Attribute-driven conditional branching with mutation support
- **Model Orchestration**: Whitelist-based provider routing (OpenAI, Anthropic, Google, xAI)
- **Two-Tier Architecture**: Tier 1 (Templates) / Tier 2 (Instances) with complete isolation
- **REST API + WebSocket**: Real-time workflow monitoring and intervention
- **Zombie Detection**: TAU role cleanup of stale actors
- **Constitutional Design**: Actor-blind roles, atomic traceability, silent failure protocol

Perfect for: Multi-agent orchestration, complex workflows, AI system governance, runtime context modification

## 📦 Project Structure

```
prototype_chameleon_mcp_workflow/
├── chameleon_workflow_engine/      # FastAPI workflow engine
│   ├── server.py                   # Main server, REST/WebSocket endpoints
│   ├── engine.py                   # Orchestration core with DCI
│   ├── semantic_guard.py           # Guard evaluation with mutations
│   ├── provider_router.py          # LLM model routing & whitelist
│   ├── SERVER_PROMPT.md            # Developer guide
│   └── README.md                   # Engine documentation
│
├── database/                       # SQLAlchemy ORM (Tier 1 + 2)
│   ├── models_template.py          # Template (blueprint) models
│   ├── models_instance.py          # Instance (runtime) models
│   ├── manager.py                  # DatabaseManager class
│   ├── enums.py                    # Type enumerations
│   ├── README.md                   # Architecture details
│   └── __init__.py                 # Exports
│
├── docs/
│   ├── architecture/
│   │   ├── Workflow_Constitution.md # Core design (DO NOT CHANGE)
│   │   ├── Database_Schema_Specification.md
│   │   ├── Role_Behavior_Specs.md
│   │   ├── UOW_Lifecycle_Specs.md
│   │   ├── Guard_Behavior_Specifications.md
│   │   └── Dynamic_Context_Injection_Specs.md
│   └── user_guide.md               # End-user documentation
│
├── tools/
│   ├── workflow_manager.py         # YAML import/export + DOT graphs
│   └── README_WORKFLOW_MONITOR.md  # Monitoring tool
│
├── tests/
│   ├── test_dci_logic.py          # DCI mutation tests (11/11 passing)
│   ├── test_schema_generation.py  # Database schema tests
│   ├── test_engine.py             # Engine core tests
│   └── test_*.py                  # Additional tests
│
├── common/                        # Utilities
│   ├── config.py                  # Environment configuration
│   └── README.md                  # Configuration guide
│
├── examples/                      # Sample workflows
│   └── *_workflow.yml             # YAML workflow definitions
│
├── requirements.txt               # Python dependencies
├── pyproject.toml                # Project metadata
├── setup.py                      # Package setup
├── verify_setup.py               # Setup verification
├── CONTRIBUTING.md               # Contribution guidelines
└── TODO.md                        # Future work items
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip / venv
- Text editor or IDE

### Setup (5 minutes)

```bash
# 1. Clone and enter directory
git clone https://github.com/clydewatts1/prototype_chameleon_mcp_workflow.git
cd prototype_chameleon_mcp_workflow

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
# or
venv\Scripts\Activate.ps1         # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env              # Linux/macOS
# or
Copy-Item .env.example .env       # Windows PowerShell
# Edit .env with your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

# 5. Verify installation
python verify_setup.py
```

### Run the Server

```bash
# Start the workflow engine (FastAPI)
python -m chameleon_workflow_engine.server

# Or with uvicorn for more control
uvicorn chameleon_workflow_engine.server:app --reload --port 8000
```

API Endpoints:
- **REST API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/ws/monitor

## 🏗️ Architecture Highlights

### Dynamic Context Injection (DCI)

Modify execution context at runtime without changing role templates:

```python
# CONDITIONAL_INJECTOR guard in workflow YAML
guardians:
  - name: "Premium_Model_Gate"
    type: "CONDITIONAL_INJECTOR"
    scope: "pre_execution"
    rules:
      - condition: "credit_score < 100"
        action: "mutate"
        payload:
          model_override: "gpt-4"
          instructions: "Apply strict verification for risky cases"
          knowledge_fragments: ["credit_risk_policies_v2"]
```

**Result**: When credit_score < 100, the UOW automatically uses gpt-4 with injected instructions and knowledge fragments.

### Two-Tier Database Architecture

**Tier 1 (Templates)**: Read-only workflow blueprints
- Template_Workflows, Template_Roles, Template_Interactions, etc.
- Managed via YAML import/export in `tools/workflow_manager.py`
- Reusable across multiple instances

**Tier 2 (Instances)**: Runtime execution data
- Local_Workflows, Local_Roles, UnitsOfWork, etc.
- Complete isolation per instance
- Mutable state during execution

### Semantic Guards

Attribute-driven conditional logic:

```yaml
guardians:
  - name: "Amount_Gate"
    type: "CRITERIA_GATE"
    condition: "amount > 10000 && department != 'Finance'"
    action: "mutate"
    payload:
      approval_required: true
      escalation_level: "manager"
```

Supports: PASS_THRU, CRITERIA_GATE, DIRECTIONAL_FILTER, CONDITIONAL_INJECTOR

### Model Orchestration

Automatic provider routing with whitelist security:

```python
from chameleon_workflow_engine.provider_router import ProviderRouter

router = ProviderRouter()
config = router.get_model_config("gpt-4")
# Returns: {
#   "model_id": "gpt-4",
#   "provider": "openai",
#   "model": "gpt-4",
#   "is_whitelisted": True,
#   "is_failover": False
# }
```

Supported models:
- **OpenAI**: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- **Anthropic**: claude-3-opus, claude-3-sonnet, claude-3-haiku
- **Google**: gemini-pro, gemini-1.5-pro, gemini-flash
- **xAI**: grok-2, grok-3

## 🛠️ Workflow Manager (CLI)

Manage workflow templates from the command line:

### Export to YAML

```bash
# Export workflow definition
python tools/workflow_manager.py -w "Invoice_Approval" -e

# Export with custom filename
python tools/workflow_manager.py -w "Invoice_Approval" -e -f custom_name.yml
```

### Import from YAML

```bash
# Import and update workflow
python tools/workflow_manager.py -l -f invoice_approval.yml

# Re-importing deletes and recreates the workflow (cascade delete)
```

### Generate Topology Graph

```bash
# Export as DOT graph
python tools/workflow_manager.py -w "Invoice_Approval" --graph

# Render to PNG (requires Graphviz)
dot -Tpng workflow_Invoice_Approval.dot -o workflow.png
```

**Key Features**:
- Name-based entity references (not UUIDs) for easy editing
- Transactional imports with automatic rollback on error
- Visual topology graphs for documentation

## 📚 Module Documentation

Each module has detailed README:

- [**chameleon_workflow_engine/**](chameleon_workflow_engine/) - Server, engine, guards, routing
- [**database/**](database/) - ORM models, Tier 1/2 architecture, enums
- [**common/**](common/) - Configuration management
- [**tools/**](tools/) - Workflow manager, monitoring utilities
- [**examples/**](examples/) - Sample workflow YAML files

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_dci_logic.py -v

# Run with coverage
pytest --cov=chameleon_workflow_engine --cov=database
```

**Test Coverage**:
- ✅ DCI mutation logic (11 tests passing)
- ✅ Semantic guard evaluation
- ✅ Database schema isolation
- ✅ Provider router validation
- ✅ REST API endpoints
- ✅ WebSocket integration

## 🔑 Key Concepts

### Unit of Work (UOW)
Atomic task representing work to be done by an actor. Tracks status, heartbeat, execution context (model, instructions, knowledge).

### Role Types
- **ALPHA**: Origin - creates initial UOWs
- **BETA**: Processor - decomposes work into child UOWs
- **OMEGA**: Terminal - reconciles results
- **EPSILON**: Physician - error recovery
- **TAU**: Chronometer - zombie detection and cleanup

### Guardian Types
- **PASS_THRU**: Identity validation
- **CRITERIA_GATE**: Threshold-based branching
- **DIRECTIONAL_FILTER**: Attribute-based routing
- **CONDITIONAL_INJECTOR**: Runtime context mutation (NEW)

### Components
Connections between roles and interactions with optional guardians for conditional logic.

## 🤝 Contributing

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Check [TODO.md](TODO.md) for planned work
3. **DO NOT modify** [Workflow_Constitution.md](docs/architecture/Workflow_Constitution.md)
4. Update tests for any code changes
5. Run linters before committing:
   ```bash
   ruff check .
   black .
   mypy chameleon_workflow_engine database
   ```

## 📋 Development Checklist

Before committing:
- [ ] Code follows project patterns
- [ ] Tests pass: `pytest`
- [ ] Linting passes: `ruff check .`
- [ ] Formatting: `black .`
- [ ] Type checking: `mypy chameleon_workflow_engine database`
- [ ] Docs updated if needed
- [ ] No changes to Workflow_Constitution.md (unless deliberate design change)

## 🔐 Environment Variables

Create `.env` file with:

```env
# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSy...

# Database
TEMPLATE_DB_URL=sqlite:///templates.db
INSTANCE_DB_URL=sqlite:///instance.db

# Server
WORKFLOW_ENGINE_HOST=0.0.0.0
WORKFLOW_ENGINE_PORT=8000

# Logging
LOG_LEVEL=INFO
```

## 📖 Key Documentation

**Start Here**:
1. [README.md](README.md) (you are here)
2. [Workflow_Constitution.md](docs/architecture/Workflow_Constitution.md) - Core design
3. [Database_Schema_Specification.md](docs/architecture/Database_Schema_Specification.md) - Data model
4. [SERVER_PROMPT.md](chameleon_workflow_engine/SERVER_PROMPT.md) - Server development

**For Specific Topics**:
- [Dynamic Context Injection](docs/architecture/Dynamic_Context_Injection_Specs.md)
- [Guard Behavior](docs/architecture/Guard_Behavior_Specifications.md)
- [Role Behavior](docs/architecture/Role_Behavior_Specs.md)
- [UOW Lifecycle](docs/architecture/UOW_Lifecycle_Specs.md)

## 🎓 Example: Create a Simple Workflow

```yaml
workflow:
  name: "Simple_Approval"
  description: "A basic approval workflow"
  version: 1

roles:
  - name: "Requester"
    role_type: "ALPHA"
    
  - name: "Approver"
    role_type: "BETA"
    
  - name: "Finalizer"
    role_type: "OMEGA"

interactions:
  - name: "Approval_Queue"
  - name: "Decision_Queue"

components:
  - role: "Requester"
    interaction: "Approval_Queue"
    direction: "OUTBOUND"
    
  - role: "Approver"
    interaction: "Approval_Queue"
    direction: "INBOUND"
    
  - role: "Approver"
    interaction: "Decision_Queue"
    direction: "OUTBOUND"
    
  - role: "Finalizer"
    interaction: "Decision_Queue"
    direction: "INBOUND"
```

Import and use:
```bash
python tools/workflow_manager.py -l -f simple_approval.yml
```

## 🐛 Troubleshooting

**Server won't start**:
```bash
# Check port availability
netstat -ano | findstr :8000  # Windows
lsof -i :8000                # Linux/macOS

# Check environment variables
python -c "from common.config import Config; Config()"
```

**Database errors**:
```bash
# Reset databases (development only)
rm templates.db instance.db
python verify_setup.py
```

**Import tests fail**:
```bash
# Ensure venv is activated
python -c "import chameleon_workflow_engine; print('OK')"
```

## 📞 Support

- **Issues**: Open GitHub issue with error details
- **Questions**: Check module READMEs and architecture docs
- **API Help**: Visit http://localhost:8000/docs when server is running

## ✨ Features Implemented

### Phase 3 Complete
- ✅ REST API endpoints for workflow management
- ✅ WebSocket support for real-time updates
- ✅ Dynamic Context Injection (DCI) with model override
- ✅ Semantic Guard mutations for context modification
- ✅ Provider Router for multi-model orchestration
- ✅ Whitelist-based security for model selection
- ✅ Fallback/failover protocol for invalid models
- ✅ Comprehensive test suite (11/11 tests passing)

### Available Now
- Database Tier 1/Tier 2 architecture
- Workflow template YAML export/import
- Topology graph visualization
- Zombie actor detection (TAU role)
- UOW heartbeat monitoring
- Attribute-driven branching
- Silent failure protocol with logging

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- Architecture by AL Wolf
- Built with GitHub Copilot and Claude
- Inspired by MCP protocol for AI integration

---

**Happy Orchestrating! 🦎✨**
