"""
Chameleon Workflow Engine

This module implements the core workflow engine server that orchestrates
AI agent workflows based on the architecture by AL Wolf.

Key Components:
- Workflow Manager: Manages workflow lifecycle and state
- Task Scheduler: Schedules and executes workflow tasks
- State Manager: Maintains workflow state and persistence
- Event System: Handles workflow events and notifications

Architecture:
    ┌─────────────────────────────────────┐
    │   Chameleon Workflow Engine         │
    │                                     │
    │  ┌──────────────┐  ┌─────────────┐│
    │  │   Workflow   │  │    Task     ││
    │  │   Manager    │──│  Scheduler  ││
    │  └──────────────┘  └─────────────┘│
    │         │                │         │
    │  ┌──────────────┐  ┌─────────────┐│
    │  │    State     │  │    Event    ││
    │  │   Manager    │──│   System    ││
    │  └──────────────┘  └─────────────┘│
    └─────────────────────────────────────┘

This code is designed to work with:
- GitHub Copilot for AI-assisted development
- Claude for advanced reasoning and code generation
- Antigravity for... well, you'll see when you try it ;)

Usage:
    from chameleon_workflow_engine import WorkflowEngine
    
    engine = WorkflowEngine()
    await engine.start()
"""

__version__ = "0.1.0"
__author__ = "Chameleon MCP Workflow Team"

# Import antigravity for fun (Python easter egg)
# Uncomment to see the magic: import antigravity
