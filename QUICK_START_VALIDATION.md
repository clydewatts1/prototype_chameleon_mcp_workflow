# Quick Start Guide - Workflow Validation & Examples

## What Was Implemented

✅ **Workflow Topology Validation** - All 10 Constitutional requirements enforced  
✅ **Example YAML Workflows** - Valid and invalid examples for testing  
✅ **Comprehensive Test Suite** - 17 tests covering all validation rules  
✅ **Complete Documentation** - Usage guides and reference materials

## Quick Commands

### Import a Workflow
```bash
python tools/workflow_manager.py -i -f examples/invoice_processing_workflow.yml
```

### Validate a Workflow (automatic during import)
All workflows are automatically validated against Constitutional requirements when imported.

### Export a Workflow
```bash
python tools/workflow_manager.py -w "Invoice_Processing" -e
```

### Generate Visual Graph
```bash
python tools/workflow_manager.py -w "Invoice_Processing" --graph
# Requires Graphviz to render:
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

## Example Files

### Valid Workflow
- **`examples/invoice_processing_workflow.yml`** - Complete working example

### Invalid Workflows (for testing validation)
- **`examples/invalid_no_alpha.yml`** - Missing ALPHA role
- **`examples/invalid_beta_no_strategy.yml`** - BETA without strategy
- **`examples/invalid_omega_no_cerberus.yml`** - OMEGA without CERBERUS guardian

## Validation Rules (R1-R10)

Every workflow must have:
1. ✅ Exactly **one ALPHA** role (The Origin)
2. ✅ Exactly **one OMEGA** role (The Terminal)
3. ✅ Exactly **one EPSILON** role (The Physician)
4. ✅ Exactly **one TAU** role (The Chronometer)
5. ✅ All **BETA roles** must have strategy (HOMOGENEOUS or HETEROGENEOUS)
6. ✅ All **components** must have valid direction (INBOUND or OUTBOUND)
7. ✅ All **interactions** must have at least one producer and one consumer
8. ✅ **EPSILON INBOUND** components must have guardians (Ate Guard)
9. ✅ **OMEGA INBOUND** components must have **CERBERUS** guardian
10. ✅ **ALPHA** must have OUTBOUND, **OMEGA** must have INBOUND

## Testing

Run all validation tests:
```bash
python -m pytest tests/test_workflow_validation.py -v
```

Expected result: **17 passed** in ~3-4 seconds

## Documentation

- **`examples/README.md`** - Complete usage guide for example workflows
- **`VALIDATION_IMPLEMENTATION_SUMMARY.md`** - Detailed implementation summary
- **`docs/architecture/Workflow_Import_Requirements.md`** - Full validation specification
- **`TODO.md`** - Updated with completed tasks

## Architecture

### Validation Flow
```
YAML File → Import → Parse Entities → Create in Session
                                           ↓
                                    Validate Topology
                                           ↓
                              Pass ✓         Fail ✗
                                ↓              ↓
                            Commit         Rollback
                                          (no data saved)
```

### Key Files
- **`tools/workflow_manager.py`** - Contains `_validate_workflow_topology()` method
- **`tests/test_workflow_validation.py`** - Test suite (17 tests)
- **`database/models_template.py`** - Template tier models
- **`database/enums.py`** - Role types and other enumerations

## Error Messages

All validation errors cite the specific Constitutional Article violated:

```
✗ Violation of Article V: Workflow must have exactly one ALPHA role (The Origin). Found: 0
✗ Violation of Article V.2: BETA role 'Processor' must have a valid strategy (HOMOGENEOUS or HETEROGENEOUS). Found: None
✗ Violation of Article VI (The Cerberus Mandate): Component 'Finalizer_From_Queue' connects to OMEGA role (INBOUND) and must have a CERBERUS guardian. Found: PASS_THRU
```

## Minimal Valid Workflow Template

```yaml
workflow:
  name: "My_Workflow"
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

## Status

✅ **Implementation Complete**  
✅ **All Tests Passing** (17/17)  
✅ **Documentation Complete**  
✅ **Production Ready**

---

For detailed information, see `VALIDATION_IMPLEMENTATION_SUMMARY.md` or `examples/README.md`.
