# Database Package Documentation

## Overview

The Chameleon Workflow Engine database package implements a production-grade, **air-gapped two-tier architecture** using SQLAlchemy ORM. This design ensures complete isolation between template blueprints and runtime instances.

## Architecture

### Two-Tier Design

1. **Tier 1: The Meta-Store (Templates)**
   - Read-only blueprints
   - Source of truth for workflow structures
   - Used only during instantiation phase
   - 5 tables: Template_Workflows, Template_Roles, Template_Interactions, Template_Components, Template_Guardians

2. **Tier 2: The Instance-Store (Runtime)**
   - Read/write runtime engine
   - Self-contained execution environment
   - Complete independence from Tier 1 after instantiation
   - 12 tables: Instance_Context, Local_Workflows, Local_Roles, Local_Interactions, Local_Components, Local_Guardians, Local_Actors, Local_Actor_Role_Assignments, Local_Role_Attributes, UnitsOfWork, UOW_Attributes, Interaction_Logs

### Key Design Principles

1. **Separate Declarative Bases**: Each tier uses its own `declarative_base()` to prevent cross-contamination
2. **UUID Primary Keys**: All primary keys use UUIDs generated Python-side via `default=uuid.uuid4`
3. **Strict Isolation**: Every Tier 2 table includes an `instance_id` column
4. **AI Introspection**: Every table and column includes comments matching specifications
5. **Database Agnosticism**: Standard SQLAlchemy types (JSON, not JSONB)

## Module Structure

```
database/
├── __init__.py           # Package exports
├── enums.py             # All enumeration types
├── models_template.py   # Tier 1 models
├── models_instance.py   # Tier 2 models
└── manager.py           # DatabaseManager class
```

## Usage

### Basic Setup

```python
from database import DatabaseManager

# Initialize with both tiers
manager = DatabaseManager(
    template_url="sqlite:///templates.db",
    instance_url="sqlite:///instance.db"
)

# Create schemas
manager.create_template_schema()
manager.create_instance_schema()
```

### Creating Template Blueprints (Tier 1)

```python
from database import Template_Workflows, Template_Roles, RoleType

with manager.get_template_session() as session:
    # Create workflow blueprint
    workflow = Template_Workflows(
        name="Invoice_Approval",
        description="Invoice approval workflow",
        version=1
    )
    session.add(workflow)
    session.flush()
    
    # Create roles
    alpha_role = Template_Roles(
        workflow_id=workflow.workflow_id,
        name="Invoice_Creator",
        role_type=RoleType.ALPHA.value
    )
    session.add(alpha_role)
```

### Creating Runtime Instances (Tier 2)

```python
from database import Instance_Context, Local_Workflows, Local_Actors, ActorType

with manager.get_instance_session() as session:
    # Create instance context
    instance = Instance_Context(
        name="Finance_Department",
        status=InstanceStatus.ACTIVE.value
    )
    session.add(instance)
    session.flush()
    
    # Clone workflow from template
    local_workflow = Local_Workflows(
        instance_id=instance.instance_id,
        original_workflow_id=template_workflow_id,  # Reference to Tier 1
        name="Invoice_Approval",
        version=1,
        is_master=True
    )
    session.add(local_workflow)
    
    # Create actors
    actor = Local_Actors(
        instance_id=instance.instance_id,
        identity_key="user@company.com",
        name="John Doe",
        type=ActorType.HUMAN.value
    )
    session.add(actor)
```

## Enumerations

### RoleType
- `ALPHA`: The Origin - instantiates Base UOW
- `BETA`: The Processor - decomposes into Child UOWs
- `OMEGA`: The Terminal - reconciles and finalizes
- `EPSILON`: The Physician - error handling
- `TAU`: The Chronometer - timeout management

### GuardianType
- `CERBERUS`: Three-headed synchronization check
- `PASS_THRU`: Identity-only validation
- `CRITERIA_GATE`: Data-driven threshold enforcement
- `DIRECTIONAL_FILTER`: Attribute-based routing

### ActorType
- `HUMAN`: Human operator
- `AI_AGENT`: AI agent
- `SYSTEM`: Automated system role

### InstanceStatus
- `ACTIVE`: Operational
- `PAUSED`: Temporarily suspended
- `ARCHIVED`: Historical record

## Key Features

### Recursive Workflows

Roles can spawn child workflows via the `linked_local_workflow_id` field:

```python
recursive_role = Local_Roles(
    local_workflow_id=parent_workflow_id,
    name="SubProcess_Handler",
    is_recursive_gateway=True,
    linked_local_workflow_id=child_workflow_id  # Points to another Local_Workflow
)
```

### Memory Hierarchy

The `Local_Role_Attributes` table supports both:
- **Global Blueprints**: `actor_id = NULL` (shared knowledge)
- **Personal Playbooks**: `actor_id = <specific actor>` (private knowledge)

```python
# Global Blueprint
global_memory = Local_Role_Attributes(
    instance_id=instance_id,
    role_id=role_id,
    actor_id=None,  # NULL = shared
    key="approval_threshold",
    value={"amount": 10000}
)

# Personal Playbook
personal_memory = Local_Role_Attributes(
    instance_id=instance_id,
    role_id=role_id,
    actor_id=actor_id,  # Specific actor
    key="preferences",
    value={"notification": "email"}
)
```

### Child Tracking in UnitsOfWork

The `UnitsOfWork` table includes fields for Cerberus synchronization:

```python
parent_uow = UnitsOfWork(
    instance_id=instance_id,
    local_workflow_id=workflow_id,
    current_interaction_id=interaction_id,
    child_count=5,           # Total children spawned
    finished_child_count=3   # Children completed
)
```

## Testing

Run the validation tests:

```bash
python tests/test_schema_generation.py
```

Run the example usage:

```bash
python tests/example_usage.py
```

## References

- **DATABASE_SCHEMA_SPEC.md**: Complete schema specification
- **WORKFLOW_CONSTITUTION.md**: Business logic and relationships
- **Constitution Article V**: Role type definitions
- **Constitution Article III**: Memory hierarchy
- **Constitution Article XIII**: Recursive workflow rules
