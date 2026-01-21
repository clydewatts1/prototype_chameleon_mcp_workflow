# 🦎 Chameleon MCP Workflow

A Model Context Protocol (MCP) workflow server for orchestrating AI agent workflows. Based on a workflow architecture by AL Wolf.

## 🎯 Overview

The Chameleon MCP Workflow project provides infrastructure for orchestrating AI agent workflows with three main components:

1. **Chameleon Workflow Engine** - Core workflow orchestration server
2. **MCP Workflow Server** - MCP protocol interface for AI assistants
3. **Streamlit Client** - Web-based UI for workflow management

This project is designed to work seamlessly with:
- 🤖 **GitHub Copilot** - AI pair programming assistant
- 🧠 **Claude** - Advanced AI reasoning and code generation
- 🚀 **Antigravity** - Python's secret weapon (try `import antigravity`!)

## 📁 Project Structure

```
prototype_chameleon_mcp_workflow/
├── chameleon_workflow_engine/    # Workflow engine server
│   ├── __init__.py              # Module initialization with architecture docs
│   └── server.py                # FastAPI-based workflow engine
├── mcp_workflow_server/          # MCP protocol server
│   ├── __init__.py              # MCP server module
│   └── server.py                # MCP protocol implementation
├── streamlit_client/             # Web UI client
│   ├── __init__.py              # Streamlit client module
│   └── app.py                   # Streamlit application
├── requirements.txt              # Project dependencies
├── pyproject.toml               # Modern Python project configuration
├── setup.py                     # Package setup script
├── .env.example                 # Environment variables template
└── README.md                    # This file
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

#### 2. Start the MCP Workflow Server

The MCP server provides a standardized interface for AI assistants.

```bash
# Start the MCP server
python -m mcp_workflow_server.server
```

The MCP server will connect to the workflow engine at `http://localhost:8000`

#### 3. Start the Streamlit Client

The Streamlit client provides a web-based UI for workflow management.

```bash
# Start the Streamlit app
streamlit run streamlit_client/app.py

# Or with custom port
streamlit run streamlit_client/app.py --server.port 8501
```

The UI will be available at: `http://localhost:8501`

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

### MCP Workflow Server

The MCP server implements the Model Context Protocol, enabling AI assistants like Claude to:
- Discover available workflow capabilities
- Execute workflows programmatically
- Query workflow state and results
- Integrate with the broader AI ecosystem

**MCP Capabilities:**
- **Resources**: Workflow definitions and templates
- **Tools**: Workflow operations (create, execute, monitor)
- **Prompts**: Pre-defined workflow patterns

### Streamlit Client

The Streamlit client provides an intuitive web interface for:
- Visual workflow creation
- Real-time execution monitoring
- Workflow analytics and history
- Interactive debugging

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
- **httpx** - Async HTTP client
- **python-dotenv** - Environment variable management

### Development Dependencies
- **pytest** - Testing framework
- **ruff** - Fast Python linter
- **black** - Code formatter
- **mypy** - Static type checker

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chameleon_workflow_engine --cov=mcp_workflow_server --cov=streamlit_client

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
