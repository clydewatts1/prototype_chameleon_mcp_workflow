#!/usr/bin/env python
"""
Environment verification script for Chameleon MCP Workflow project.

This script checks that all dependencies are installed correctly and
that the basic infrastructure is working.

Usage:
    python verify_setup.py
"""

import sys
import importlib.util


def check_module(module_name: str, display_name: str = None) -> bool:
    """Check if a module can be imported"""
    display = display_name or module_name
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            print(f"✓ {display}")
            return True
        else:
            print(f"✗ {display} - not found")
            return False
    except Exception as e:
        print(f"✗ {display} - error: {e}")
        return False


def check_project_structure() -> bool:
    """Check if project directories exist"""
    import os
    
    required_dirs = [
        "chameleon_workflow_engine",
        "mcp_workflow_server", 
        "streamlit_client"
    ]
    
    all_present = True
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"✓ {dir_name}/ directory exists")
        else:
            print(f"✗ {dir_name}/ directory missing")
            all_present = False
    
    return all_present


def check_documentation_files() -> bool:
    """Check if required documentation files exist"""
    import os
    
    required_docs = [
        "docs/architecture/Workflow_Constitution.md",
        "docs/architecture/Database_Schema_Specification.md",
    ]
    
    all_present = True
    for doc_path in required_docs:
        if os.path.isfile(doc_path):
            print(f"✓ {doc_path} exists")
        else:
            print(f"✗ {doc_path} missing")
            all_present = False
    
    return all_present


def test_workflow_engine() -> bool:
    """Test if the workflow engine API works"""
    try:
        from chameleon_workflow_engine.server import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print("✓ Workflow Engine API is functional")
            return True
        else:
            print(f"✗ Workflow Engine API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Workflow Engine API test failed: {e}")
        return False


def test_antigravity() -> bool:
    """Test the antigravity easter egg (for fun)"""
    try:
        import antigravity
        print("✓ Antigravity is available (Python easter egg - XKCD 353)")
        return True
    except ImportError:
        print("✗ Antigravity not available")
        return False
    except Exception:
        # Browser opening may fail in some environments
        print("✓ Antigravity is available (browser opening may have failed)")
        return True


def main():
    """Main verification function"""
    print("=" * 60)
    print("Chameleon MCP Workflow - Environment Verification")
    print("=" * 60)
    print()
    
    # Check Python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 9):
        print("⚠ Warning: Python 3.9 or higher is recommended")
    print()
    
    # Check core dependencies
    print("Checking core dependencies...")
    core_deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("streamlit", "Streamlit"),
        ("mcp", "MCP"),
        ("pydantic", "Pydantic"),
        ("httpx", "HTTPX"),
        ("loguru", "Loguru"),
    ]
    
    all_deps_ok = all(check_module(mod, display) for mod, display in core_deps)
    print()
    
    # Check project structure
    print("Checking project structure...")
    structure_ok = check_project_structure()
    print()
    
    # Check documentation files
    print("Checking documentation files...")
    docs_ok = check_documentation_files()
    print()
    
    # Check project modules
    print("Checking project modules...")
    project_modules = [
        ("chameleon_workflow_engine", "Chameleon Workflow Engine"),
        ("mcp_workflow_server", "MCP Workflow Server"),
        ("streamlit_client", "Streamlit Client"),
    ]
    
    modules_ok = all(check_module(mod, display) for mod, display in project_modules)
    print()
    
    # Test workflow engine
    print("Testing workflow engine...")
    engine_ok = test_workflow_engine()
    print()
    
    # Test antigravity
    print("Testing Python easter eggs...")
    antigravity_ok = test_antigravity()
    print()
    
    # Summary
    print("=" * 60)
    if all_deps_ok and structure_ok and docs_ok and modules_ok and engine_ok:
        print("✅ All checks passed! Your environment is ready.")
        print()
        print("Next steps:")
        print("1. Start the workflow engine: python -m chameleon_workflow_engine.server")
        print("2. Start the Streamlit client: streamlit run streamlit_client/app.py")
        print("3. Visit http://localhost:8501 to use the UI")
        print()
        print("For GitHub Copilot: Enable in your IDE")
        print("For Claude: Use via API or Anthropic Console")
        if antigravity_ok:
            print("For Antigravity: Try 'import antigravity' for a surprise! 🚀")
        return 0
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print()
        print("To fix dependency issues:")
        print("  pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
