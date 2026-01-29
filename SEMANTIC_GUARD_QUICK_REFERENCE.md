# Semantic Guard - Quick Reference Guide

## Expression Syntax

### Operators (Arithmetic & Comparison)

```
Arithmetic:    +, -, *, /, %
Comparison:    <, >, <=, >=, ==, !=
Boolean:       and, or, not
Grouping:      ( ... )
```

### Examples

```python
# Arithmetic
amount + 100                           # 150 + 100 = 250
amount * 1.1                           # 100 * 1.1 = 110
amount / 1000                          # 100000 / 1000 = 100
amount % 10                            # 27 % 10 = 7

# Comparison
amount > 50000                         # TRUE if amount is over 50K
priority <= 5                          # TRUE if priority is 5 or less
status == "PENDING"                    # TRUE if status is "PENDING"

# Boolean
(amount > 50000) and (priority > 5)   # TRUE if both conditions met
(amount > 100000) or (vip == True)    # TRUE if either condition met
not flagged                            # TRUE if flagged is False

# Grouping
((amount * 1.1) + tax) > threshold    # Calculation with precedence
(a > 5 and b < 10) or c == True       # Complex Boolean
```

## Functions

### Pre-loaded Functions (14 total)

```python
# Math Functions
abs(-5)                    → 5
min(10, 5, 8)             → 5
max(10, 5, 8)             → 10
round(3.14159, 2)         → 3.14
floor(3.9)                → 3
ceil(3.1)                 → 4
sqrt(16)                  → 4.0
pow(2, 3)                 → 8

# String/Type Functions
len([1, 2, 3])            → 3
str(123)                  → "123"
int("123")                → 123
float("3.14")             → 3.14

# Logic Functions
sum([1, 2, 3])            → 6
all([True, True])         → True
any([False, True])        → True
```

### Custom Functions

```python
# Registration
from semantic_guard import register_custom_function

def normalize_score(score):
    return max(0, min(1, score / 100))

register_custom_function("normalize_score", normalize_score)

# Usage in Policy
condition: "normalize_score(raw_score) > 0.5"
```

## YAML Policy Structure

### Minimal Policy

```yaml
guardians:
  - name: RoutingGuard
    type: CRITERIA_GATE
    component: MainProcessor
    attributes:
      interaction_policy:
        branches:
          - condition: "amount > 10000"
            next_interaction: "HighValue"
            action: ROUTE
```

### Complete Policy with All Features

```yaml
guardians:
  - name: AdvancedRouter
    type: CRITERIA_GATE
    component: Processor
    attributes:
      interaction_policy:
        # Named branches for clarity
        branches:
          # Branch 1: Main condition
          - name: "high_value_path"
            condition: "amount > 50000"
            next_interaction: "HighValueProcessing"
            action: ROUTE
            on_error: false
          
          # Branch 2: Complex Boolean logic
          - name: "urgent_path"
            condition: "(priority > 7 and amount > 10000) or flagged"
            next_interaction: "UrgentProcessing"
            action: ROUTE
            on_error: false
          
          # Branch 3: With functions
          - name: "approval_path"
            condition: "max(score, previous_score) < 0.3"
            next_interaction: "QuickApproval"
            action: ROUTE
            on_error: false
          
          # Branch 4: Error handler
          - name: "error_recovery"
            condition: "1 == 1"
            next_interaction: "ErrorPath"
            action: ROUTE
            on_error: true
        
        # Default fallback
        default:
          next_interaction: "StandardProcessing"
          action: ROUTE
```

## Common Patterns

### 1. Amount-Based Routing

```yaml
condition: |
  (amount > 100000) or
  (amount > 50000 and risk_score > 5) or
  (amount > 10000 and internal_user)
```

### 2. Risk-Based Routing

```yaml
condition: |
  (risk_score * 10) > threshold and
  not trusted_user
```

### 3. Normalized Score Routing

```yaml
# First register function
register_custom_function("normalize", lambda x: max(0, min(1, x/100)))

# Then use in policy
condition: |
  normalize(raw_score) > 0.5 and
  normalize(risk_score) < 0.8
```

### 4. Multi-Factor Decision

```yaml
condition: |
  ((amount / 10000) + (count * 5) + (risk_score * 2)) > 10 and
  not excluded_category
```

### 5. Tiered Processing

```yaml
branches:
  - condition: "amount > 100000"
    next_interaction: "PremiumTier"
  - condition: "amount > 50000"
    next_interaction: "StandardTier"
  - condition: "amount > 10000"
    next_interaction: "BasicTier"
```

### 6. Error Handling with Fallback

```yaml
branches:
  - condition: "undefined_variable > 10"
    next_interaction: "MainPath"
  - condition: "1 == 1"
    next_interaction: "ErrorPath"
    on_error: true
default:
  next_interaction: "FallbackPath"
```

## UOW Attributes

### Reserved Attributes (Always Available)

```python
uow_id                  # UUID as string
child_count             # Total children spawned
finished_child_count    # Children completed
status                  # Current status (ACTIVE, COMPLETED, etc.)
parent_id               # Parent UOW UUID as string
```

### Custom Attributes (From UOW_Attributes table)

```python
amount                  # Monetary value
priority                # Priority level
risk_score              # Risk assessment
flagged                 # Boolean flag
category                # Category string
count                   # Counter
# ... any other attributes added by ALPHA role
```

## Engine Integration

### Enable Semantic Guard (Default)

```python
result = engine._evaluate_interaction_policy(
    session=session,
    uow=uow,
    outbound_components=components,
    use_semantic_guard=True,  # Use advanced routing
)
```

### Disable for Backward Compatibility

```python
result = engine._evaluate_interaction_policy(
    session=session,
    uow=uow,
    outbound_components=components,
    use_semantic_guard=False,  # Use simple DSL
)
```

## Error Handling

### Silent Failure Protocol

1. **Error occurs** during condition evaluation
2. **Error logged** to Shadow Logger with:
   - Timestamp
   - UOW ID
   - Branch number
   - Condition
   - Available variables
   - Error message
3. **Execution continues** to next branch
4. **on_error branch** evaluated if marked
5. **Default used** if no match

### Example: Undefined Variable

```yaml
branches:
  - condition: "undefined_var > 10"
    next_interaction: "MainPath"
    on_error: false  # Don't use this for error recovery
  - condition: "1 == 1"
    next_interaction: "ErrorRecovery"
    on_error: true   # Use this if error occurs above
```

**Result:** 
- If `undefined_var` is defined → First branch evaluated
- If `undefined_var` is undefined → Error logged, second branch (on_error) evaluated

## Testing

### Run All Tests

```bash
pytest tests/test_semantic_guard.py -v
```

### Run Integration Tests

```bash
pytest tests/test_engine_semantic_guard_integration.py -v
```

### Run Specific Test

```bash
pytest tests/test_semantic_guard.py::TestSemanticGuardEvaluation::test_arithmetic_expressions -v
```

### Check Test Results

```bash
pytest tests/test_semantic_guard.py -v --tb=short
```

## Debugging

### Get Shadow Logs

```python
from chameleon_workflow_engine.semantic_guard import get_shadow_logs

# All errors
errors = get_shadow_logs()

# Errors for specific UOW
errors = get_shadow_logs(uow_id="550e8400-e29b-41d4-a716-446655440000")

# Errors with specific level
errors = get_shadow_logs(level="ERROR")

# Print errors
for error in errors:
    print(f"UOW: {error['uow_id']}")
    print(f"Condition: {error['condition']}")
    print(f"Error: {error['error_message']}")
```

## Common Mistakes

### ❌ Wrong: Undefined Variable

```yaml
condition: "my_variable > 10"  # Error if my_variable not in UOW attributes
```

✅ **Fix:** Add attribute to UOW first

```python
UOW_Attributes(uow_id=uow.uow_id, key="my_variable", value=50).save(session)
```

### ❌ Wrong: Bitwise Operator

```yaml
condition: "amount >> 2"  # ERROR: >> not allowed
condition: "amount ** 2"  # ERROR: ** not allowed
```

✅ **Fix:** Use allowed operators

```yaml
condition: "amount / 4"   # Use division instead
condition: "pow(amount, 2)"  # Use pow() function
```

### ❌ Wrong: Function Typo

```yaml
condition: "sqrt(amount)"  # ERROR if function not registered
```

✅ **Fix:** Register or use correct name

```python
register_custom_function("sqrt", math.sqrt)
```

### ❌ Wrong: Missing Parentheses

```yaml
condition: "a > 10 and b < 5 or c == true"  # Ambiguous precedence
```

✅ **Fix:** Be explicit with parentheses

```yaml
condition: "(a > 10 and b < 5) or c == true"
```

## Performance Tips

1. **Use simple conditions when possible**
   - `amount > 10000` is faster than complex nested expressions

2. **Register frequently-used functions once**
   - Register at startup, not per-evaluation

3. **Cache compiled policies** (future enhancement)
   - Expressions could be compiled once and reused

4. **Keep attribute count reasonable**
   - Fewer attributes = faster hashing

5. **Use specific conditions**
   - Avoid overly broad conditions that match everything

## Reference

- **Full Documentation:** `docs/SEMANTIC_GUARD_IMPLEMENTATION.md`
- **Example Workflow:** `tools/semantic_guard_example.yaml`
- **Test Suite:** `tests/test_semantic_guard.py`
- **Engine Integration:** `chameleon_workflow_engine/engine.py` (lines 854-1217)
