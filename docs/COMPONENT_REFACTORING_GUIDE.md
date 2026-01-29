# Component Refactoring Guide: From Logic-Aware to Logic-Blind

## Purpose
This guide provides step-by-step instructions for converting existing "logic-aware" components (that contain routing decisions) into "logic-blind" components (that only emit attributes). This is the foundation of the Chameleon Workflow Engine's Guard-in-the-Middle architecture.

---

## Table of Contents
1. [The Problem: Logic-Aware Components](#the-problem-logic-aware-components)
2. [The Solution: Logic-Blind Pattern](#the-solution-logic-blind-pattern)
3. [Refactoring Process](#refactoring-process)
4. [Real-World Examples](#real-world-examples)
5. [Testing Your Refactored Code](#testing-your-refactored-code)
6. [Common Pitfalls](#common-pitfalls)

---

## The Problem: Logic-Aware Components

### ❌ Anti-Pattern: Component Decides Routing

```python
class InvoiceApprovalAgent:
    """
    BAD EXAMPLE: This component knows about workflow topology.
    It makes routing decisions internally.
    """
    
    def execute(self, uow: UnitsOfWork) -> str:
        # Calculate approval requirements
        amount = uow.attributes["invoice_amount"]
        department = uow.attributes["department"]
        
        # ❌ PROBLEM: Component contains routing logic
        if amount > 50000:
            return "ExecutiveApproval"  # High-value path
        elif department == "Finance":
            return "FinanceManagerApproval"  # Department-specific
        else:
            return "StandardApproval"  # Default path
```

### Why This Is Bad

1. **Tight Coupling:** Component knows about downstream interactions
2. **Testing Difficulty:** Must mock entire workflow to test logic
3. **Inflexibility:** Changing routing requires code changes
4. **Guard Bypass:** Routing happens without Guard authorization
5. **Constitutional Violation:** Violates Article IX (The Fork in the Road)

---

## The Solution: Logic-Blind Pattern

### ✅ Correct Pattern: Component Emits Attributes

```python
class InvoiceApprovalAgent:
    """
    GOOD EXAMPLE: This component only emits attributes.
    Guard layer handles routing decisions.
    """
    
    def execute(self, uow: UnitsOfWork) -> Dict[str, Any]:
        # Calculate approval requirements
        amount = uow.attributes["invoice_amount"]
        department = uow.attributes["department"]
        
        # ✅ SOLUTION: Only emit attributes, no routing decisions
        return {
            "invoice_amount": amount,
            "department": department,
            "requires_executive_approval": amount > 50000,
            "is_finance_department": department == "Finance"
        }
```

### Routing Handled by Guardian

```yaml
# In workflow YAML definition
guardians:
  - name: InvoiceApprovalRouter
    type: DIRECTIONAL_FILTER
    component: InvoiceApprovalAgent
    attributes:
      interaction_policy:
        branches:
          # High-value path
          - condition: "invoice_amount > 50000"
            action: ROUTE
            next_interaction: "ExecutiveApproval"
          
          # Department-specific path
          - condition: "is_finance_department and invoice_amount > 10000"
            action: ROUTE
            next_interaction: "FinanceManagerApproval"
          
          # Default path
          - default: true
            action: ROUTE
            next_interaction: "StandardApproval"
```

### Benefits

1. **Loose Coupling:** Component doesn't know about workflow topology
2. **Easy Testing:** Test only attribute calculation logic
3. **Flexibility:** Change routing without code changes (YAML only)
4. **Guard Enforcement:** All routing goes through Guard authorization
5. **Constitutional Compliance:** Follows Article IX

---

## Refactoring Process

### Step 1: Identify Routing Logic

**Look for these patterns:**

```python
# Pattern 1: If/else chains returning interaction names
if condition1:
    return "Interaction1"
elif condition2:
    return "Interaction2"

# Pattern 2: Switch statements or dictionaries
routing_map = {
    "high": "HighPriorityPath",
    "low": "LowPriorityPath"
}
return routing_map[priority]

# Pattern 3: Calling next component directly
if score > threshold:
    return next_component.execute(uow)

# Pattern 4: String concatenation for interaction names
return f"{category}Processing"
```

### Step 2: Extract Decision Variables

**Identify the data used for routing decisions:**

```python
# Before refactoring, list all decision variables:
decision_vars = {
    "amount": uow.attributes["invoice_amount"],
    "department": uow.attributes["department"],
    "urgency": uow.attributes["priority"],
    "approver_available": check_approver_status()
}
```

### Step 3: Convert to Attribute Emission

**Replace routing logic with attribute return:**

```python
# BEFORE (Logic-Aware)
def execute(self, uow):
    amount = uow.attributes["invoice_amount"]
    if amount > 50000:
        return "ExecutiveApproval"
    else:
        return "StandardApproval"

# AFTER (Logic-Blind)
def execute(self, uow):
    amount = uow.attributes["invoice_amount"]
    return {
        "invoice_amount": amount,
        "requires_executive_approval": amount > 50000
    }
```

### Step 4: Move Routing to Guardian

**Create interaction_policy in Guardian definition:**

```yaml
guardians:
  - name: ApprovalRouter
    type: DIRECTIONAL_FILTER
    component: InvoiceApprovalAgent
    attributes:
      interaction_policy:
        branches:
          - condition: "requires_executive_approval"
            next_interaction: "ExecutiveApproval"
          - default: true
            next_interaction: "StandardApproval"
```

### Step 5: Update Tests

**Before: Tests verify routing decisions**
```python
def test_high_value_routing():
    uow = create_uow(amount=60000)
    result = agent.execute(uow)
    assert result == "ExecutiveApproval"  # ❌ Tests routing
```

**After: Tests verify attributes only**
```python
def test_high_value_attributes():
    uow = create_uow(amount=60000)
    result = agent.execute(uow)
    assert result["invoice_amount"] == 60000  # ✅ Tests attributes
    assert result["requires_executive_approval"] is True
```

---

## Real-World Examples

### Example 1: Risk Scoring Agent

#### Before Refactoring (Logic-Aware)

```python
class RiskScoringAgent:
    """Anti-pattern: Contains routing logic"""
    
    def execute(self, uow: UnitsOfWork) -> str:
        # Calculate risk score
        transaction_amount = uow.attributes["amount"]
        customer_history = self.fetch_customer_history(uow.attributes["customer_id"])
        
        risk_score = self.calculate_risk(transaction_amount, customer_history)
        
        # ❌ Routing logic embedded in component
        if risk_score > 0.9:
            return "FraudInvestigation"
        elif risk_score > 0.6:
            return "ManualReview"
        elif customer_history["is_vip"]:
            return "VIPProcessing"
        else:
            return "AutoApproval"
    
    def calculate_risk(self, amount, history):
        # Complex risk calculation
        base_score = amount / 100000
        history_multiplier = 1.0 - (history["successful_transactions"] * 0.01)
        return min(base_score * history_multiplier, 1.0)
```

#### After Refactoring (Logic-Blind)

```python
class RiskScoringAgent:
    """Correct pattern: Only emits attributes"""
    
    def execute(self, uow: UnitsOfWork) -> Dict[str, Any]:
        # Calculate risk score
        transaction_amount = uow.attributes["amount"]
        customer_history = self.fetch_customer_history(uow.attributes["customer_id"])
        
        risk_score = self.calculate_risk(transaction_amount, customer_history)
        
        # ✅ Only emit attributes, no routing decisions
        return {
            "risk_score": risk_score,
            "transaction_amount": transaction_amount,
            "is_high_risk": risk_score > 0.9,
            "requires_manual_review": risk_score > 0.6,
            "is_vip_customer": customer_history["is_vip"],
            "customer_trust_score": 1.0 - history_multiplier
        }
    
    def calculate_risk(self, amount, history):
        # Same complex risk calculation
        base_score = amount / 100000
        history_multiplier = 1.0 - (history["successful_transactions"] * 0.01)
        return min(base_score * history_multiplier, 1.0)
```

#### Guardian Configuration

```yaml
guardians:
  - name: RiskBasedRouter
    type: DIRECTIONAL_FILTER
    component: RiskScoringAgent
    attributes:
      interaction_policy:
        branches:
          # Fraud investigation path
          - condition: "is_high_risk"
            action: ROUTE
            next_interaction: "FraudInvestigation"
          
          # Manual review path
          - condition: "requires_manual_review and not is_vip_customer"
            action: ROUTE
            next_interaction: "ManualReview"
          
          # VIP fast-track
          - condition: "is_vip_customer and risk_score < 0.7"
            action: ROUTE
            next_interaction: "VIPProcessing"
          
          # Auto-approval
          - default: true
            action: ROUTE
            next_interaction: "AutoApproval"
```

---

### Example 2: Document Classification Agent

#### Before Refactoring (Logic-Aware)

```python
class DocumentClassifier:
    """Anti-pattern: Mixed concerns"""
    
    def execute(self, uow: UnitsOfWork) -> str:
        document_text = uow.attributes["document_content"]
        
        # Classification logic
        doc_type = self.classify_document(document_text)
        confidence = self.get_confidence()
        language = self.detect_language(document_text)
        
        # ❌ Complex routing logic
        if confidence < 0.5:
            return "HumanClassification"
        elif doc_type == "contract" and language == "legal_english":
            return "LegalReview"
        elif doc_type == "invoice":
            if self.extract_amount(document_text) > 10000:
                return "HighValueInvoiceProcessing"
            else:
                return "StandardInvoiceProcessing"
        elif doc_type == "medical":
            return "HIPAAComplianceCheck"
        else:
            return "GeneralProcessing"
    
    def classify_document(self, text):
        # ML classification logic
        return self.ml_model.predict(text)
```

#### After Refactoring (Logic-Blind)

```python
class DocumentClassifier:
    """Correct pattern: Clean separation of concerns"""
    
    def execute(self, uow: UnitsOfWork) -> Dict[str, Any]:
        document_text = uow.attributes["document_content"]
        
        # Classification logic (unchanged)
        doc_type = self.classify_document(document_text)
        confidence = self.get_confidence()
        language = self.detect_language(document_text)
        
        # Extract relevant attributes
        attributes = {
            "document_type": doc_type,
            "classification_confidence": confidence,
            "language": language,
            "is_low_confidence": confidence < 0.5,
            "is_legal_document": doc_type == "contract" and language == "legal_english",
            "is_medical_document": doc_type == "medical"
        }
        
        # For invoices, extract amount
        if doc_type == "invoice":
            amount = self.extract_amount(document_text)
            attributes["invoice_amount"] = amount
            attributes["is_high_value_invoice"] = amount > 10000
        
        # ✅ Return all attributes, no routing
        return attributes
    
    def classify_document(self, text):
        # Same ML classification logic
        return self.ml_model.predict(text)
```

#### Guardian Configuration

```yaml
guardians:
  - name: DocumentRouter
    type: DIRECTIONAL_FILTER
    component: DocumentClassifier
    attributes:
      interaction_policy:
        branches:
          # Low confidence requires human
          - condition: "is_low_confidence"
            action: ROUTE
            next_interaction: "HumanClassification"
          
          # Legal review path
          - condition: "is_legal_document"
            action: ROUTE
            next_interaction: "LegalReview"
          
          # High-value invoice path
          - condition: "document_type == 'invoice' and is_high_value_invoice"
            action: ROUTE
            next_interaction: "HighValueInvoiceProcessing"
          
          # Standard invoice path
          - condition: "document_type == 'invoice'"
            action: ROUTE
            next_interaction: "StandardInvoiceProcessing"
          
          # Medical/HIPAA path
          - condition: "is_medical_document"
            action: ROUTE
            next_interaction: "HIPAAComplianceCheck"
          
          # Default path
          - default: true
            action: ROUTE
            next_interaction: "GeneralProcessing"
```

---

## Testing Your Refactored Code

### Test Structure: Before vs. After

#### Before Refactoring (Testing Routing)

```python
class TestRiskScoringAgent:
    """Tests couple component logic with routing decisions"""
    
    def test_high_risk_routes_to_fraud_investigation(self):
        # ❌ Test verifies routing behavior
        agent = RiskScoringAgent()
        uow = create_high_risk_uow()
        
        result = agent.execute(uow)
        assert result == "FraudInvestigation"
    
    def test_vip_customer_routes_to_vip_processing(self):
        # ❌ Test verifies routing behavior
        agent = RiskScoringAgent()
        uow = create_vip_customer_uow()
        
        result = agent.execute(uow)
        assert result == "VIPProcessing"
```

#### After Refactoring (Testing Attributes)

```python
class TestRiskScoringAgent:
    """Tests focus on attribute calculation only"""
    
    def test_high_risk_attributes_emitted(self):
        # ✅ Test verifies attribute calculation
        agent = RiskScoringAgent()
        uow = create_high_risk_uow(amount=100000, history={"successful_transactions": 0})
        
        result = agent.execute(uow)
        
        assert result["risk_score"] > 0.9
        assert result["is_high_risk"] is True
        assert result["requires_manual_review"] is True
    
    def test_vip_customer_attributes_emitted(self):
        # ✅ Test verifies attribute calculation
        agent = RiskScoringAgent()
        uow = create_vip_customer_uow(customer_history={"is_vip": True})
        
        result = agent.execute(uow)
        
        assert result["is_vip_customer"] is True
        assert "customer_trust_score" in result
```

### Guardian Testing (Separate)

```python
class TestRiskBasedRouter:
    """Tests Guardian routing logic separately"""
    
    def test_high_risk_routes_to_fraud_investigation(self):
        # Test Guardian policy evaluation
        guard = SemanticGuard()
        policy = load_guardian_policy("RiskBasedRouter")
        attributes = {
            "risk_score": 0.95,
            "is_high_risk": True,
            "requires_manual_review": True
        }
        
        result = guard.evaluate_policy(policy, attributes)
        
        assert result.success is True
        assert result.next_interaction == "FraudInvestigation"
```

---

## Common Pitfalls

### Pitfall 1: Hidden Routing Logic

```python
# ❌ WRONG: Hidden routing in helper method
class Agent:
    def execute(self, uow):
        category = self.categorize(uow)
        return self._route_by_category(category)  # Hidden routing!
    
    def _route_by_category(self, category):
        return f"{category}Processing"  # Still routing logic!
```

**Fix:** Emit category as attribute
```python
# ✅ CORRECT: Category is just an attribute
class Agent:
    def execute(self, uow):
        category = self.categorize(uow)
        return {"category": category}  # Pure attribute
```

---

### Pitfall 2: Boolean Flags That Imply Routes

```python
# ❌ QUESTIONABLE: Flag names imply routing
return {
    "should_go_to_executive_approval": amount > 50000,
    "needs_fraud_investigation": risk > 0.9
}
```

**Better:** Use descriptive attributes
```python
# ✅ BETTER: Attributes describe state, not destination
return {
    "requires_executive_approval": amount > 50000,
    "is_high_risk": risk > 0.9,
    "amount": amount,
    "risk_score": risk
}
```

---

### Pitfall 3: Calling Other Components

```python
# ❌ WRONG: Component calls next component directly
class ComponentA:
    def execute(self, uow):
        result = self.process(uow)
        if result["needs_review"]:
            return ComponentB().execute(uow)  # Direct call!
        return result
```

**Fix:** Let Guard orchestrate
```python
# ✅ CORRECT: Return attributes, let Guard route
class ComponentA:
    def execute(self, uow):
        result = self.process(uow)
        return {
            "needs_review": result["needs_review"],
            "processing_complete": True
        }
```

---

### Pitfall 4: Incomplete Attribute Sets

```python
# ❌ WRONG: Conditional attribute emission
def execute(self, uow):
    attrs = {"base_score": self.score(uow)}
    if attrs["base_score"] > 0.5:
        attrs["high_risk"] = True  # Only set sometimes!
    return attrs
```

**Fix:** Always emit all attributes
```python
# ✅ CORRECT: Consistent attribute schema
def execute(self, uow):
    base_score = self.score(uow)
    return {
        "base_score": base_score,
        "high_risk": base_score > 0.5,  # Always present
        "low_risk": base_score <= 0.5   # Always present
    }
```

---

## Refactoring Checklist

### ✅ Before Submitting PR

- [ ] **No routing decisions in component code**
  - No if/else returning interaction names
  - No string concatenation for interaction names
  - No direct calls to other components

- [ ] **Component returns Dict[str, Any]**
  - Return type is dictionary, not string
  - All decision variables included in return value
  - Attribute names are descriptive (not "flag1", "flag2")

- [ ] **Guardian policy created**
  - YAML file includes interaction_policy
  - All branches map to actual interactions
  - Default branch included
  - Error branch included (if needed)

- [ ] **Tests updated**
  - Tests verify attribute calculation, not routing
  - Guardian routing tested separately
  - Edge cases covered (null values, missing attributes)

- [ ] **Documentation updated**
  - Component docstring describes attributes emitted
  - Guardian policy documented in YAML comments
  - README includes routing diagram (if complex)

---

## Quick Reference

### Convert This Pattern

| Before (Logic-Aware) | After (Logic-Blind) |
|---------------------|---------------------|
| `return "InteractionName"` | `return {"attribute": value}` |
| `if x: return "A" else: return "B"` | `return {"x": x}` |
| `next_component.execute(uow)` | `return attributes` |
| `routing_map[key]` | `return {"key": key}` |

### Remember

1. **Components emit**, Guardians route
2. **Attributes describe**, policies decide
3. **Test calculation**, not navigation
4. **YAML changes**, not code deploys

---

## Additional Resources

- **Constitution:** [docs/architecture/Workflow_Constitution.md](../architecture/Workflow_Constitution.md#article-ix-the-fork-in-the-road)
- **Branching Guide:** [docs/architecture/Branching Logic Guide.md](../architecture/Branching%20Logic%20Guide.md)
- **Semantic Guard:** [chameleon_workflow_engine/semantic_guard.py](../../chameleon_workflow_engine/semantic_guard.py)
- **Example Agents:** [examples/example_agents/](../../examples/example_agents/)

---

**Last Updated:** January 29, 2026  
**Version:** 1.0.0  
**Status:** Active
