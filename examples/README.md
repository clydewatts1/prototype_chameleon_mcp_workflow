# Example Workflows

This directory contains example workflow YAML files for the Chameleon MCP Workflow Engine.

## Valid Workflows

### invoice_processing_workflow.yml
A complete, valid invoice processing workflow that demonstrates all Constitutional requirements:
- **1 ALPHA role**: `Invoice_Creator` - Creates the base invoice UOW
- **1 OMEGA role**: `Invoice_Reconciler` - Final reconciliation with CERBERUS guardian
- **1 EPSILON role**: `Error_Handler` - Handles explicit data errors (Ate Path)
- **1 TAU role**: `Timeout_Manager` - Manages stale tokens and zombie actors
- **2 BETA roles**:
  - `Invoice_Validator` with HOMOGENEOUS strategy
  - `Senior_Approver` with HETEROGENEOUS strategy
- **5 Interactions**: Validation, Approval, Reconciliation, Error, and Timeout queues
- **Proper guardians**: Cerberus guard on OMEGA inbound, Ate guard on EPSILON inbound
- **Valid topology**: All interactions have producers and consumers

This workflow can be imported to demonstrate a working end-to-end process:
```bash
python tools/workflow_manager.py -i -f examples/invoice_processing_workflow.yml
```

## Invalid Workflows (for testing)

These workflows intentionally violate Constitutional rules to demonstrate validation:

### invalid_no_alpha.yml
**Violates R1**: Missing ALPHA role (The Origin)
- Demonstrates that workflows without an ALPHA role are rejected
- Error: "Violation of Article V: Workflow must have exactly one ALPHA role"

### invalid_beta_no_strategy.yml
**Violates R5**: BETA role without decomposition strategy
- Demonstrates that BETA roles must specify HOMOGENEOUS or HETEROGENEOUS strategy
- Error: "Violation of Article V.2: BETA role must have a valid strategy"

### invalid_omega_no_cerberus.yml
**Violates R9**: OMEGA INBOUND component without CERBERUS guardian
- Demonstrates the Cerberus Mandate requirement
- Error: "Violation of Article VI (The Cerberus Mandate)"

## Usage

### Import a Workflow
```bash
python tools/workflow_manager.py -i -f examples/invoice_processing_workflow.yml
```

### Export a Workflow
```bash
python tools/workflow_manager.py -w "Invoice_Processing" -e
```

### Generate DOT Graph
```bash
python tools/workflow_manager.py -w "Invoice_Processing" --graph
dot -Tpng workflow_Invoice_Processing.dot -o workflow_Invoice_Processing.png
```

### List All Workflows
```bash
python tools/workflow_manager.py -l
```

### Delete a Workflow
```bash
python tools/workflow_manager.py -w "Invoice_Processing" -d
```

## Validation Rules

All workflows are validated against the following Constitutional requirements:

1. **R1**: Exactly one ALPHA role (The Origin)
2. **R2**: Exactly one OMEGA role (The Terminal)
3. **R3**: Exactly one EPSILON role (The Physician)
4. **R4**: Exactly one TAU role (The Chronometer)
5. **R5**: All BETA roles must have valid strategy (HOMOGENEOUS or HETEROGENEOUS)
6. **R6**: All components must have valid direction (INBOUND or OUTBOUND)
7. **R7**: All interactions must have at least one producer and one consumer
8. **R8**: EPSILON INBOUND components must have guardians (The Ate Guard)
9. **R9**: OMEGA INBOUND components must have CERBERUS guardian (The Cerberus Mandate)
10. **R10**: ALPHA must have OUTBOUND, OMEGA must have INBOUND

See `docs/architecture/Workflow_Import_Requirements.md` for complete validation specifications.

## Creating Your Own Workflows

When creating a new workflow YAML, ensure:

1. **Include all five role types**: ALPHA, OMEGA, EPSILON, TAU, and any BETA roles needed
2. **Define BETA strategies**: Specify HOMOGENEOUS or HETEROGENEOUS for each BETA role
3. **Create interactions**: Define holding areas between roles
4. **Connect with components**: Use INBOUND (to role) and OUTBOUND (from role) directions
5. **Add guardians**: Especially on EPSILON and OMEGA INBOUND components
6. **Validate topology**: Ensure every interaction has both producers and consumers

### Minimal Valid Workflow Template

```yaml
workflow:
  name: "My_Workflow"
  description: "Description here"
  version: 1

  roles:
    - name: "Origin"
      role_type: "ALPHA"
    - name: "Processor"
      role_type: "BETA"
      strategy: "HOMOGENEOUS"
    - name: "Terminal"
      role_type: "OMEGA"
    - name: "Error_Handler"
      role_type: "EPSILON"
    - name: "Timeout_Manager"
      role_type: "TAU"

  interactions:
    - name: "Work_Queue"
    - name: "Final_Queue"
    - name: "Error_Queue"

  components:
    - name: "Origin_To_Work"
      role: "Origin"
      interaction: "Work_Queue"
      direction: "OUTBOUND"
    - name: "Processor_From_Work"
      role: "Processor"
      interaction: "Work_Queue"
      direction: "INBOUND"
    - name: "Processor_To_Final"
      role: "Processor"
      interaction: "Final_Queue"
      direction: "OUTBOUND"
    - name: "Terminal_From_Final"
      role: "Terminal"
      interaction: "Final_Queue"
      direction: "INBOUND"
      guardian:
        name: "Cerberus_Guard"
        type: "CERBERUS"
    - name: "Processor_To_Error"
      role: "Processor"
      interaction: "Error_Queue"
      direction: "OUTBOUND"
    - name: "Error_From_Queue"
      role: "Error_Handler"
      interaction: "Error_Queue"
      direction: "INBOUND"
      guardian:
        name: "Ate_Guard"
        type: "PASS_THRU"
```

## Testing

These examples are used in the test suite:
```bash
python -m pytest tests/test_workflow_validation.py -v
```

All 17 validation tests should pass, demonstrating that:
- Valid workflows import successfully
- Invalid workflows are rejected with appropriate error messages
- Database rollback prevents partial workflow creation on validation failure
