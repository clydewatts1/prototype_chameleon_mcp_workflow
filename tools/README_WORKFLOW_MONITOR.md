# Workflow Monitor Dashboard

## Overview

The Workflow Monitor Dashboard is a real-time control room for the Chameleon Workflow Engine, built with Streamlit. It provides operators with comprehensive visibility into workflow execution, UOW (Units of Work) status, and system health.

## Features

### 1. Sidebar Configuration
- **Database Connection**: Input field for SQLAlchemy connection string (defaults to local SQLite)
- **Instance Selector**: Dropdown to select from all active workflow instances
- **Auto-Refresh**: Toggle to enable automatic dashboard refresh with configurable interval (5-60 seconds)
- **Manual Refresh**: Button to refresh data on demand

### 2. Key Metrics Dashboard (The "HUD")
Real-time metrics displayed as large, easy-to-read cards:
- **Active UOWs**: Total count of `IN_PROGRESS` + `PENDING` UOWs
- **Completed**: Total successfully completed UOWs
- **Failed**: Total failed UOWs (displayed in red for critical alerts)
- **Zombies**: UOWs with stale heartbeats (timeout detection)

### 3. Graph Visualization (The "Map")
Interactive workflow topology visualization using Graphviz:
- **Nodes**: 
  - Roles displayed as boxes with color-coded borders by type (ALPHA=green, BETA=blue, OMEGA=black, EPSILON=orange, TAU=purple)
  - Interactions displayed as ellipses
- **Edges**: Components shown as labeled arrows indicating data flow direction
- **Dynamic Coloring**:
  - Roles with locked UOWs → Blue fill
  - Interactions with Pending UOWs → Yellow fill (with count in label)
  - Interactions with Failed UOWs → Red fill

### 4. Data Tables (The "Manifest")
Three comprehensive data views:
- **Active Work**: Table showing all `IN_PROGRESS` UOWs with:
  - UOW ID (truncated)
  - Workflow name
  - Current interaction
  - Status
  - Duration since last heartbeat (in seconds)
  
- **Queue Depths**: Table showing pending work per interaction:
  - Workflow name
  - Interaction name
  - Count of pending UOWs
  
- **History Log**: Latest 50 entries from `Instance_UOW_History` showing:
  - Log ID
  - Timestamp
  - UOW ID
  - Role involved
  - Interaction involved

## Installation

### Prerequisites
```bash
# Install required dependencies
pip install -r requirements.txt
```

The following packages are required (already in requirements.txt):
- `streamlit>=1.28.0`
- `streamlit-autorefresh>=1.0.0`
- `graphviz>=0.20.0`
- `sqlalchemy>=2.0.0`

### System Requirements
- Python 3.9+
- Graphviz system package (for visualization)

On Ubuntu/Debian:
```bash
sudo apt-get install graphviz
```

On macOS:
```bash
brew install graphviz
```

## Usage

### Basic Usage
```bash
# Run with default database (sqlite:///chameleon_instance.db)
streamlit run tools/workflow_monitor.py
```

### With Custom Database
```bash
# Using command-line argument
streamlit run tools/workflow_monitor.py -- --db-url "sqlite:///path/to/your/instance.db"

# Using environment variable (future enhancement)
export CHAMELEON_INSTANCE_DB="sqlite:///path/to/your/instance.db"
streamlit run tools/workflow_monitor.py
```

### Using the Dashboard
1. **Select Instance**: Use the sidebar dropdown to choose which workflow instance to monitor
2. **View Metrics**: Check the key metrics cards at the top for system health
3. **Inspect Graph**: Examine the workflow topology to see where UOWs are queued or stuck
4. **Review Tables**: Drill into specific UOWs and their execution history
5. **Enable Auto-Refresh**: Toggle auto-refresh for continuous monitoring

## Architecture

### Source of Truth
The dashboard queries data directly from the Tier 2 (Instance) database using:
- `database/manager.py`: Database connection management
- `database/models_instance.py`: Instance tier data models
- `database/enums.py`: Status and type enumerations

### Read-Only Design
The dashboard performs **read-only** queries for optimal performance and safety. It does not modify workflow state.

### Performance Considerations
- Uses SQLAlchemy for efficient database queries
- Implements session management for proper connection handling
- Optimized queries with appropriate JOINs and aggregations
- Minimal data transfer through selective column queries

## Troubleshooting

### Empty Dashboard
If you see "No workflow instances found":
1. Verify the database connection string is correct
2. Ensure the instance database has been initialized
3. Check that at least one workflow instance has been instantiated

### Graphviz Not Found
If visualization fails:
1. Install system Graphviz package (see Installation section)
2. Verify `dot` command is in PATH: `which dot`
3. Restart the dashboard after installation

### Connection Errors
If database connection fails:
1. Check the connection string format
2. Verify the database file exists (for SQLite)
3. Ensure proper permissions for database access
4. Check for file locks if database is in use

## Development

### Testing
Create a test database with sample data:
```bash
python /tmp/test_monitor_data.py
```

Test dashboard functions without UI:
```bash
python /tmp/test_monitor_functions.py
```

### Adding New Metrics
To add new metrics:
1. Define query function in `get_uow_metrics()` or create new function
2. Update `render_metrics()` to display the new metric
3. Add appropriate help text and formatting

### Customizing Visualizations
To modify graph appearance:
1. Edit `generate_workflow_graph()` function
2. Adjust node shapes, colors, and styles in the Graphviz DOT generation
3. Modify dynamic coloring logic based on UOW states

## Future Enhancements

Potential improvements for future versions:
- [ ] Drill-down views for individual UOWs
- [ ] Real-time alerting for failed/zombie UOWs
- [ ] Historical trend charts
- [ ] Actor performance metrics
- [ ] Export/download capabilities for data tables
- [ ] Dark mode support
- [ ] Multi-instance comparison view
- [ ] Integration with workflow engine API for administrative actions

## References

- [Chameleon Workflow Engine Documentation](../../docs/)
- [Database Schema Documentation](../../database/README.md)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Graphviz Documentation](https://graphviz.org/)
