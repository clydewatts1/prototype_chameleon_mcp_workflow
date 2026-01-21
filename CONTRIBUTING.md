# Contributing to Chameleon MCP Workflow

Thank you for your interest in contributing! This project leverages modern AI-assisted development tools to enhance productivity and code quality.

## 🤖 AI-Assisted Development

This project is designed to work seamlessly with AI coding assistants:

### GitHub Copilot

GitHub Copilot provides intelligent code completions and suggestions.

**Setup:**
1. Install the GitHub Copilot extension in your IDE (VS Code, JetBrains, etc.)
2. Sign in with your GitHub account
3. Start coding - Copilot will suggest completions automatically

**Best Practices:**
- Write clear function signatures and docstrings - Copilot uses these for context
- Use descriptive variable names
- Break complex functions into smaller, well-documented pieces
- Leverage Copilot Chat for code explanations and refactoring suggestions

### Claude

Use Claude (Anthropic's AI assistant) for complex reasoning, architecture decisions, and code review.

**Use Cases:**
- Architecture design and system planning
- Complex algorithm development
- Code review and optimization suggestions
- Documentation writing
- Debugging assistance

**Best Practices:**
- Provide Claude with complete context about the problem
- Ask for explanations, not just code
- Use Claude to review your code before committing
- Request multiple approaches to solve complex problems

### Antigravity

Because every serious project needs a little fun:

```python
import antigravity
```

This Python easter egg opens the classic XKCD comic about Python. It's a reminder to:
- Keep coding fun and light-hearted
- Embrace Python's philosophy
- Take breaks when needed

## 🛠️ Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/prototype_chameleon_mcp_workflow.git
   cd prototype_chameleon_mcp_workflow
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install with dev tools
   ```

4. **Verify Setup**
   ```bash
   python verify_setup.py
   ```

## 📝 Code Style

This project uses:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

Run before committing:
```bash
# Format code
black .

# Check linting
ruff check .

# Type check
mypy chameleon_workflow_engine mcp_workflow_server streamlit_client
```

## 🧪 Testing

Write tests for new features:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chameleon_workflow_engine --cov=mcp_workflow_server --cov=streamlit_client

# Run specific test
pytest tests/test_workflow_engine.py
```

## 📦 Project Structure

```
prototype_chameleon_mcp_workflow/
├── chameleon_workflow_engine/    # Core workflow orchestration
│   ├── __init__.py              # Module with architecture docs
│   └── server.py                # FastAPI server
├── mcp_workflow_server/          # MCP protocol interface
│   ├── __init__.py              # MCP server module
│   └── server.py                # MCP implementation
├── streamlit_client/             # Web UI
│   ├── __init__.py              # Client module
│   └── app.py                   # Streamlit app
└── tests/                        # Test files
```

## 🔄 Workflow

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Use GitHub Copilot for code completion
   - Consult Claude for architecture decisions
   - Write clear, documented code
   - Add tests for new features

3. **Test Your Changes**
   ```bash
   # Run verification
   python verify_setup.py
   
   # Run tests
   pytest
   
   # Check code quality
   black --check .
   ruff check .
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test updates
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a Pull Request on GitHub with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots for UI changes
   - Test results

## 🎯 Areas for Contribution

- **Workflow Engine**: Add new workflow patterns and execution strategies
- **MCP Server**: Enhance MCP protocol implementation
- **Streamlit Client**: Improve UI/UX and add visualizations
- **Documentation**: Improve guides and API docs
- **Tests**: Increase test coverage
- **Examples**: Add example workflows and use cases

## 💡 Getting Help

- Review existing code and documentation
- Ask GitHub Copilot for code explanations
- Use Claude for complex problem-solving
- Open an issue for bugs or questions
- Join discussions in pull requests

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Keep discussions professional
- Embrace diverse perspectives

## 🙏 Attribution

When using AI tools:
- GitHub Copilot and Claude significantly assist development
- Human review and approval are required for all code
- AI suggestions are treated as recommendations, not requirements
- Final responsibility for code quality rests with human developers

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Happy Contributing! 🦎✨**

*Built with ❤️ and AI assistance from GitHub Copilot and Claude*
