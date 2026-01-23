# Database Module

The database module provides all data persistence and access functionality for the Chameleon Workflow Engine.

## Overview

This module handles all database interactions using **SQLAlchemy ORM** (Object-Relational Mapping). It defines the database schema through SQLAlchemy models and provides a Data Access Object (DAO) interface through the `DatabaseManager` class for safe, consistent database operations.

## Architecture

### Models

The database schema is defined through five main SQLAlchemy models:

#### WorkflowModel
Represents the `wf_workflows` table. Stores the core workflow information.

**Fields:**
- `id` (String, PK): Unique workflow identifier
- `name` (String): Workflow name
- `description` (Text, nullable): Workflow description
- `status` (String): Workflow status (default: "created")
- `created_at` (DateTime): Creation timestamp (UTC)
- `updated_at` (DateTime): Last update timestamp (UTC)

#### WorkflowModelAttribute
Represents the `wf_workflow_attributes` table. Stores key-value attributes associated with workflows.

**Fields:**
- `id` (String, PK): Unique attribute identifier
- `workflow_id` (String): Foreign reference to workflow
- `key` (String): Attribute key name
- `value` (Text, nullable): Attribute value
- `description` (Text, nullable): Attribute description
- `context` (Text, nullable): Execution context (e.g., "system")
- `created_at` (DateTime): Creation timestamp (UTC)
- `updated_at` (DateTime): Last update timestamp (UTC)

#### WorkflowInteraction
Represents the `wf_workflow_interactions` table. Stores interaction records within workflows.

**Fields:**
- `id` (String, PK): Unique interaction identifier
- `workflow_id` (String): Foreign reference to workflow
- `interaction_type` (String): Type of interaction
- `name` (String): Interaction name
- `description` (Text, nullable): Interaction description
- `created_at` (DateTime): Creation timestamp (UTC)
- `updated_at` (DateTime): Last update timestamp (UTC)

#### WorkflowInteractionComponent
Represents the `wf_workflow_interaction_components` table. Stores components that participate in workflow interactions.

**Fields:**
- `id` (String, PK): Unique component identifier
- `interaction_id` (String): Foreign reference to interaction
- `role_id` (String): Foreign reference to role
- `direction` (String): Component direction ('input' or 'output')
- `name` (String): Component name
- `description` (Text, nullable): Component description
- `created_at` (DateTime): Creation timestamp (UTC)
- `updated_at` (DateTime): Last update timestamp (UTC)

#### WorkflowRole
Represents the `wf_workflow_roles` table. Stores roles that can be assigned in workflows.

**Fields:**
- `id` (String, PK): Unique role identifier
- `name` (String): Role name
- `type` (String): Role type
- `description` (Text, nullable): Role description
- `created_at` (DateTime): Creation timestamp (UTC)
- `updated_at` (DateTime): Last update timestamp (UTC)

### DatabaseManager Class

Central data access object providing all CRUD operations and business logic for workflow management.

#### Getters
- `get_workflow(workflow_id)` - Retrieve a single workflow by ID
- `get_all_workflows()` - Retrieve all workflows
- `get_workflow_attributes(workflow_id)` - Retrieve all attributes for a workflow
- `get_workflow_attribute(workflow_id, key)` - Retrieve a specific attribute by key
- `get_workflow_interactions(workflow_id)` - Retrieve all interactions for a workflow
- `get_workflow_interaction(workflow_id, interaction_id)` - Retrieve a specific interaction
- `get_workflow_interaction_components(interaction_id)` - Retrieve all components for an interaction
- `get_workflow_interaction_component(interaction_id, role_id)` - Retrieve a specific component
- `get_workflow_interaction_components_by_role(interaction_id, role_id)` - Retrieve components by role
- `get_workflow_roles()` - Retrieve all workflow roles
- `get_workflow_role(role_id)` - Retrieve a specific role by ID

#### Setters / Creators
- `create_workflow(workflow_id, name, description)` - Create a new workflow
- `create_workflow_attribute(workflow_id, key, value, description, context)` - Create a new attribute
- `create_workflow_interaction(workflow_id, interaction_id, interaction_type, name, description)` - Create an interaction
- `create_workflow_interaction_component(interaction_id, role_id, direction, name, description)` - Create a component
- `create_workflow_role(role_id, name, type, description)` - Create a new role
- `delete_workflow(workflow_id)` - Delete a workflow by ID
- `delete_workflow_attribute(workflow_id, key)` - Delete a workflow attribute
- `delete_workflow_interaction(workflow_id, interaction_id)` - Delete an interaction
- `delete_workflow_interaction_component(interaction_id, role_id)` - Delete a component
- `delete_workflow_role(role_id)` - Delete a role

#### Process Functions
- `update_workflow_status(workflow_id, new_status)` - Update workflow processing status
- `update_workflow_attribute(workflow_id, key, new_value)` - Update attribute value
- `update_workflow_interaction(workflow_id, interaction_id, new_name, new_description)` - Update interaction details
- `update_workflow_role(role_id, new_name, new_type, new_description)` - Update role details

## Usage

### Initialization

```python
from database.workflow import DatabaseManager

# Initialize with default database URL from config
db_manager = DatabaseManager()

# Or specify custom database URL
db_manager = DatabaseManager(database_url="sqlite:///custom.db")
```

### Creating Records

```python
# Create a workflow
workflow = db_manager.create_workflow(
    workflow_id="wf_001",
    name="My Workflow",
    description="A sample workflow"
)

# Create a workflow attribute
attribute = db_manager.create_workflow_attribute(
    workflow_id="wf_001",
    key="priority",
    value="high",
    description="Workflow priority",
    context="system"
)

# Create a workflow role
role = db_manager.create_workflow_role(
    role_id="role_001",
    name="Processor",
    type="agent",
    description="Processes workflow data"
)

# Create a workflow interaction
interaction = db_manager.create_workflow_interaction(
    workflow_id="wf_001",
    interaction_id="int_001",
    interaction_type="data_processing",
    name="Process Data",
    description="Main data processing step"
)

# Create an interaction component
component = db_manager.create_workflow_interaction_component(
    interaction_id="int_001",
    role_id="role_001",
    direction="input",
    name="Data Input",
    description="Input data for processing"
)
```

### Querying Records

```python
# Get single workflow
workflow = db_manager.get_workflow("wf_001")

# Get all workflows
all_workflows = db_manager.get_all_workflows()

# Get workflow attributes
attributes = db_manager.get_workflow_attributes("wf_001")

# Get specific attribute
attr = db_manager.get_workflow_attribute("wf_001", "priority")

# Get all roles
roles = db_manager.get_workflow_roles()

# Get specific role
role = db_manager.get_workflow_role("role_001")

# Get workflow interactions
interactions = db_manager.get_workflow_interactions("wf_001")

# Get specific interaction
interaction = db_manager.get_workflow_interaction("wf_001", "int_001")

# Get interaction components
components = db_manager.get_workflow_interaction_components("int_001")

# Get components by role
components_by_role = db_manager.get_workflow_interaction_components_by_role("int_001", "role_001")
```

### Updating Records

```python
# Update workflow status
db_manager.update_workflow_status("wf_001", "active")

# Update attribute value
db_manager.update_workflow_attribute("wf_001", "priority", "medium")

# Update interaction
db_manager.update_workflow_interaction(
    workflow_id="wf_001",
    interaction_id="int_001",
    new_name="Enhanced Processing",
    new_description="Updated processing logic"
)

# Update role
db_manager.update_workflow_role(
    role_id="role_001",
    new_name="Data Processor",
    new_type="enhanced_agent"
)
```

### Deleting Records

```python
# Delete workflow
db_manager.delete_workflow("wf_001")

# Delete attribute
db_manager.delete_workflow_attribute("wf_001", "priority")

# Delete interaction
db_manager.delete_workflow_interaction("wf_001", "int_001")

# Delete component
db_manager.delete_workflow_interaction_component("int_001", "role_001")

# Delete role
db_manager.delete_workflow_role("role_001")
```

## Configuration

Database configuration is managed through the `common.config` module. The database URL can be set via:
- Environment variables
- Configuration file
- Direct instantiation parameter

Supported databases:
- SQLite (default, with thread-safety enabled)
- PostgreSQL
- MySQL
- Other SQLAlchemy-supported databases

## Error Handling

All database operations are wrapped with proper session management using context managers. The `DatabaseManager` handles:
- Transaction commits on success
- Transaction rollbacks on errors
- Proper session cleanup

## Database Setup

Tables are automatically created on first initialization if they don't exist:

```python
db_manager = DatabaseManager()
# Tables are created automatically via Base.metadata.create_all()
```
