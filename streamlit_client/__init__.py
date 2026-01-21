"""
Streamlit Client for Chameleon Workflow Engine

This module provides a web-based user interface for interacting with the
Chameleon Workflow Engine using Streamlit.

Features:
- Visual workflow builder
- Workflow execution monitoring
- Real-time status updates
- Interactive workflow debugging
- Workflow history and analytics

UI Components:
    ┌─────────────────────────────────────┐
    │   Streamlit Client Dashboard        │
    │                                     │
    │  ┌──────────────┐  ┌─────────────┐│
    │  │   Workflow   │  │  Execution  ││
    │  │   Builder    │  │   Monitor   ││
    │  └──────────────┘  └─────────────┘│
    │         │                │         │
    │  ┌──────────────┐  ┌─────────────┐│
    │  │   Status     │  │  Analytics  ││
    │  │  Dashboard   │  │   & Logs    ││
    │  └──────────────┘  └─────────────┘│
    └─────────────────────────────────────┘

Streamlit provides:
- Rapid UI development
- Reactive components
- Built-in data visualization
- Easy deployment

Development Environment:
- GitHub Copilot: Assists with Streamlit component creation
- Claude: Helps design UX and complex interactions
- Antigravity: For when you need to float away from bugs :)

Usage:
    # Start the Streamlit app
    streamlit run streamlit_client/app.py
    
    # Or with custom port
    streamlit run streamlit_client/app.py --server.port 8501
"""

__version__ = "0.1.0"
__author__ = "Chameleon MCP Workflow Team"
