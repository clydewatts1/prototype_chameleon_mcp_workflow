# 🦎 Chameleon MCP Workflow

A Model Context Protocol (MCP) workflow server for orchestrating AI agent workflows. Based on a workflow architecture by AL Wolf.

## 🎯 Overview

The Chameleon MCP Workflow project provides infrastructure for orchestrating AI agent workflows.

This project is designed to work seamlessly with:
- 🤖 **GitHub Copilot** - AI pair programming assistant
- 🧠 **Claude** - Advanced AI reasoning and code generation
- 🚀 **Antigravity** - Python's secret weapon (try `import antigravity`!)

## 📁 Project Structure

```
prototype_chameleon_mcp_workflow/
├── chameleon_workflow_engine/    # Workflow engine server
│   ├── __init__.py              # Module initialization
│   ├── server.py                # FastAPI-based workflow engine
│   └── SERVER_PROMPT.md         # Developer guidance for server.py
├── database/                     # Database module
│   ├── __init__.py              # Package exports
│   ├── README.md                # Database documentation
│   ├── models_template.py        # Tier 1 template models
│   ├── models_instance.py        # Tier 2 instance models
│   ├── manager.py               # DatabaseManager
│   └── enums.py                 # Database enumerations
├── common/                       # Common utilities
│   ├── README.md                # Configuration documentation
│   └── config.py                # Configuration management
├── tools/                        # CLI utilities
│   ├── __init__.py              # Module initialization
│   └── workflow_manager.py       # Workflow template management CLI
├── tests/                        # Test files
├── requirements.txt              # Project dependencies
├── pyproject.toml               # Modern Python project configuration
├── setup.py                     # Package setup script
└── verify_setup.py              # Setup verification script
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Virtual environment tool (venv, conda, etc.)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/clydewatts1/prototype_chameleon_mcp_workflow.git
   cd prototype_chameleon_mcp_workflow
   ```

2. **Create a virtual environment**
   ```bash
   # Using venv
   python -m venv venv
   
   # Activate on Linux/Mac
   source venv/bin/activate
   
   # Activate on Windows
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   # Install all required packages
   pip install -r requirements.txt
   
   # Or install in development mode with optional dev tools
   pip install -e ".[dev]"
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your configuration
   nano .env  # or use your preferred editor
   ```

5. **Verify your setup**
   ```bash
   # Run the verification script to check everything is working
   python verify_setup.py
   ```
   
   This will check:
   - All dependencies are installed
   - Project structure is correct
   - Workflow engine API is functional
   - Python modules can be imported

### Running the Components

#### 1. Start the Workflow Engine Server

The workflow engine is the core orchestration server built with FastAPI.

```bash
# Start the workflow engine
python -m chameleon_workflow_engine.server

# Or with uvicorn directly
uvicorn chameleon_workflow_engine.server:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

#### 2. Verify your setup

## 🏗️ Component Architecture

### Chameleon Workflow Engine

The workflow engine is built with FastAPI and provides REST API endpoints for:
- Creating workflow definitions
- Executing workflows
- Monitoring workflow status
- Managing workflow lifecycle

**Key Features:**
- Asynchronous workflow execution
- State management and persistence
- Event-driven architecture
- RESTful API interface
- Zombie actor detection and cleanup (TAU role)
- UOW heartbeat monitoring

See [chameleon_workflow_engine/SERVER_PROMPT.md](chameleon_workflow_engine/SERVER_PROMPT.md) for detailed developer guidance on the workflow engine server.

### Database Module

The database module provides comprehensive data persistence using SQLAlchemy ORM with an air-gapped architecture:
- **Tier 1 Models** - Template/blueprint definitions for workflow schemas
- **Tier 2 Models** - Runtime instance data with strict isolation
- **DatabaseManager** class for managing both tiers
- Support for SQLite, PostgreSQL, MySQL, and other SQLAlchemy-compatible databases

**Key Features:**
- Complete air-gapped template and instance separation
- Automatic schema creation and management
- Comprehensive enums for workflow types and roles
- Full support for recursive workflows and memory hierarchy

See [database/README.md](database/README.md) for detailed documentation.

### Common Module

The common module provides shared utilities:
- **Configuration management** through the `Config` class
- Environment variable loading from `.env` files
- Type-safe getters for strings, integers, and booleans
- Centralized configuration constants

See [common/README.md](common/README.md) for usage examples.

### Workflow Manager CLI

The workflow manager is a command-line tool for managing Workflow Templates (Tier 1 Meta-Store). It provides three main features:

**1. YAML Export** - Export workflow blueprints to human-readable YAML files:
```bash
# Export a workflow to YAML
python tools/workflow_manager.py -w "MyWorkflow" -e

# Export with custom filename
python tools/workflow_manager.py -w "MyWorkflow" -e -f my_custom_name.yml
```

**2. YAML Import/Load** - Import and update workflow blueprints from YAML:
```bash
# Import a workflow from YAML
python tools/workflow_manager.py -l -f workflow_MyWorkflow.yml

# Re-importing will delete and recreate the workflow (cascade delete)
python tools/workflow_manager.py -l -f modified_workflow.yml
```

**3. DOT Graph Export** - Generate visual workflow topology graphs:
```bash
# Export workflow as DOT graph
python tools/workflow_manager.py -w "MyWorkflow" --graph

# Export with custom filename
python tools/workflow_manager.py -w "MyWorkflow" --graph -f my_graph.dot

# Render the graph to PNG (requires Graphviz)
dot -Tpng workflow_MyWorkflow.dot -o workflow_MyWorkflow.png
```

**Key Features:**
- **Name-based references** - YAML uses entity names as identifiers instead of UUIDs for easy editing
- **Cascade delete** - Re-importing a workflow automatically deletes the old version
- **Transactional integrity** - All import operations use database transactions with automatic rollback on failure
- **Visual topology** - DOT graphs show roles (circles), interactions (hexagons), and guardians (double octagons)

**YAML Structure:**
The exported YAML follows a hierarchical structure with all entities nested under the workflow:
- `workflow` - Main workflow definition with name, description, version, and AI context
- `roles` - Functional agents (ALPHA, BETA, OMEGA, EPSILON, TAU)
- `interactions` - Waiting areas/queues between roles
- `components` - Directional connections between roles and interactions
- `guardians` - Logic gates attached to components

Components and Guardians reference other entities by name (e.g., `role_name`, `component_name`), making the YAML easy to edit by hand and reload.

## 🔧 Development with AI Tools

This project is designed to work with modern AI-assisted development tools:

### GitHub Copilot
- Enable Copilot in your IDE (VS Code, JetBrains, etc.)
- Use Copilot for code completion and suggestions
- Leverage Copilot Chat for code explanations and refactoring

### Claude
- Use Claude for architecture design and complex problem solving
- Leverage Claude's code review capabilities
- Ask Claude for implementation guidance and best practices

### Antigravity
Because every serious Python project needs a little fun:
```python
import antigravity  # Opens XKCD comic about Python
```

## 📦 Dependencies

### Core Dependencies
- **mcp[cli]** - Model Context Protocol implementation
- **fastapi** - Modern web framework for the workflow engine
- **uvicorn** - ASGI server for FastAPI
- **streamlit** - Web UI framework
- **pydantic** - Data validation and settings management
- **pydantic-settings** - Settings management
- **httpx** - Async HTTP client
- **aiohttp** - Async HTTP support
- **python-dotenv** - Environment variable management
- **loguru** - Logging and monitoring
- **sqlalchemy** - ORM for database operations
- **teradatasqlalchemy** - Teradata database support
- **jinja2** - Template rendering
- **PyYAML** - YAML configuration file support

### Development Dependencies
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage reporting
- **ruff** - Fast Python linter
- **black** - Code formatter
- **mypy** - Static type checker

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chameleon_workflow_engine --cov=database

# Run specific test file
pytest tests/test_workflow_engine.py
```

## 🛠️ Development Workflow

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes with AI assistance**
   - Use GitHub Copilot for code completion
   - Consult Claude for architecture decisions
   - Run linters and formatters regularly

3. **Test your changes**
   ```bash
   python verify_setup.py
   pytest
   ruff check .
   black --check .
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

## 📖 API Documentation

### Workflow Engine API

Once the workflow engine is running, visit:
- Interactive API Docs: `http://localhost:8000/docs`
- Alternative API Docs: `http://localhost:8000/redoc`

### Example API Usage

```python
import httpx

# Create a workflow
response = httpx.post(
    "http://localhost:8000/workflows",
    json={
        "name": "My Workflow",
        "description": "A sample workflow",
        "steps": ["step1", "step2", "step3"]
    }
)
workflow = response.json()

# Execute the workflow
workflow_id = workflow["id"]
response = httpx.post(f"http://localhost:8000/workflows/{workflow_id}/execute")

# Check workflow status
response = httpx.get(f"http://localhost:8000/workflows/{workflow_id}")
status = response.json()
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Based on workflow architecture by AL Wolf
- Built with assistance from GitHub Copilot and Claude
- Inspired by the MCP protocol for AI assistant integration

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review the component architecture in each module's `__init__.py`

---

**Happy Orchestrating! 🦎✨**
