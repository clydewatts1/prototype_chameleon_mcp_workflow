# Hitchhiker's Guide Workflow Demonstrations

Welcome, oh bewildered traveler through the galaxy of workflow orchestration! These demonstrations showcase the Chameleon Workflow Engine's most advanced features through the lens of Douglas Adams' Hitchhiker's Guide to the Galaxy universe.

## Overview

These three demos illustrate progressively complex implementations of **Dynamic Context Injection (DCI)** and model orchestration, demonstrating how the Chameleon engine keeps Worker Roles "logic-blind" while intelligently adapting AI model instructions based on context.

### Demos at a Glance

| Demo | Complexity | Feature | Story |
|------|-----------|---------|-------|
| **Vogon Poetry Validator** | Simple | Semantic Guards | Protecting the universe from bad poetry |
| **Babel Fish Translator** | Medium | Multi-mutation Injection | Species-specific communication styles |
| **Infinite Improbability Drive** | Complex | Multi-model Orchestration | Navigating impossible space |

---

## Demo 1: Vogon Poetry Validator

**File**: `demo1_vogon_poetry.yaml`

### Story 🎭
The Vogon Constructor Fleet is known for the most destructive poetry in the galaxy. When a Vogon submits a poem for validation, our system detects this and injects protective instructions into the AI processing the poem, ensuring the universe survives the experience.

### What It Shows 📚
- **CONDITIONAL_INJECTOR Guard**: Detects when `author == 'Vogon'`
- **Safety Protocol Injection**: Injects protective instructions to mitigate damage
- **Knowledge Fragment References**: Associates relevant safety guidelines
- **Audit Trail**: Tracks when protective measures are activated

### Workflow
```
Poem_Submitter (ALPHA)
    ↓ submit_poem
Poetry_Critic (BETA)
    ↓ evaluate_poetry [GUARD: Detect Vogon → Inject safety instructions]
Final_Judgment (OMEGA)
    ↓ final_verdict
COMPLETE
```

### Key Features
- Single mutation condition (Vogon detection)
- Instruction injection example
- Knowledge fragment reference tracking
- Constitutional alignment (Article V: Role types, Article IX: Guard lifecycle)

### Run This Demo
```bash
# Using Python test framework
pytest tests/hitchhiker_demos/test_demo1_vogon.py -v

# Test cases:
# - Test A: Shakespeare poem passes without guard activation
# - Test B: Vogon poem triggers protective guard and injects instructions
```

### Expected Behavior
When a Vogon author is detected:
1. Guard condition evaluates to `True`
2. Mutation is applied to the UOW
3. `injected_instructions` field is populated with safety protocol
4. Model processes the poem with protective instructions
5. `mutation_audit_log` records: "Vogon author detected - protective measures activated"

---

## Demo 2: Babel Fish Translator

**File**: `demo2_babel_fish.yaml`

### Story 🎭
The Babel Fish is a small fish that provides instant translation. But different alien species prefer different communication styles! A Vogon wants destruction, a Human wants diplomacy, and a Betelgeusian wants flattery. This demo shows how the same message is translated differently based on audience without changing the core Role logic.

### What It Shows 📚
- **Multiple Mutation Pathways**: Three different condition branches (Vogon, Human, Betelgeusian)
- **Provider Router Integration**: Different models for different species (gpt-4, gpt-4-turbo, claude-3-opus)
- **Context-Aware Instruction Injection**: Each branch has unique, specialized instructions
- **Cultural Adaptation**: DCI enables "logic-blind" roles to produce culturally-appropriate output

### Workflow
```
Message_Receiver (ALPHA)
    ↓ receive_message
Translator (BETA)
    ↓ translate_message [GUARD: Species detection → Select model + inject instructions]
        ├─ Condition 0: Vogon → gpt-4 + aggressive instructions
        ├─ Condition 1: Human → gpt-4-turbo + diplomatic instructions
        └─ Condition 2: Betelgeusian → claude-3-opus + flattering instructions
Translation_Finisher (OMEGA)
    ↓ finalize_translation
COMPLETE
```

### Key Features
- Three mutation pathways (conditions 0, 1, 2)
- Provider Router selects models dynamically
- Different instruction sets for each species
- Knowledge fragment references per mutation
- Demonstrates logic-blind roles (Translator doesn't know why instructions change)

### Run This Demo
```bash
# Using Python test framework
pytest tests/hitchhiker_demos/test_demo2_babel.py -v

# Test cases:
# - Test A: Human listener gets diplomatic context
# - Test B: Vogon listener gets aggressive context
# - Test C: Betelgeusian listener gets flattering context
```

### Expected Behavior
The Translator role remains identical for all three conditions. Only the injected instructions change:
- **Vogon**: "Use harsh, cutting language. Don't soften the message."
- **Human**: "Use polite, diplomatic language. Acknowledge their perspective."
- **Betelgeusian**: "Flatter extensively. References to cosmic significance."

This demonstrates **logic-blindness**: The role implements the same logic, but AI instructions shape wildly different output.

---

## Demo 3: Infinite Improbability Drive Navigation

**File**: `demo3_improbability_drive.yaml`

### Story 🎭
The Infinite Improbability Drive allows space travel by rendering the improbable probable. Different regions of space require different levels of intelligence:
- **Normal space** (improbability 0-99): Standard navigation
- **High improbability** (100-999,999): Warped space requiring advanced math
- **Chaos space** (>999,999): Non-Euclidean madness requiring creative, paradox-based thinking

This demo shows how a single `Navigation_Computer` role adapts to vastly different operational environments without changing its code.

### What It Shows 📚
- **Three-Level Hierarchy**: Improbability ranges determine behavior
- **Model Orchestration**: Different models excel at different problem types
- **Advanced Instruction Injection**: Non-Euclidean geometry for chaos space
- **Paradox Engineering**: Instructions for impossible spaces
- **Constitutional Article XX**: Complex multi-model orchestration

### Workflow
```
Navigation_Initiator (ALPHA)
    ↓ initiate_navigation [Calculate improbability_level]
Navigation_Computer (BETA)
    ↓ plot_course [GUARD: Improbability detection → Select model + inject instructions]
        ├─ Condition 0: Level 0-99 (Normal)     → gemini-flash + standard navigation
        ├─ Condition 1: Level 100-999,999 (High) → gpt-4 + non-Euclidean geometry
        └─ Condition 2: Level >999,999 (Chaos)  → grok-2 + paradox logic
Navigation_Completer (OMEGA)
    ↓ complete_navigation [Verify arrival]
COMPLETE
```

### Key Features
- Three sophisticated condition expressions
- Range-based logic (0-99, 100-999999, >999999)
- Escalating instruction complexity
- Chaos space embraces paradox and impossible thinking
- Model selection reflects problem complexity (flash → gpt-4 → grok-2)

### Run This Demo
```bash
# Using Python test framework
pytest tests/hitchhiker_demos/test_demo3_improbability.py -v

# Test cases:
# - Test A: Level 50 (Normal space) uses gemini-flash with standard instructions
# - Test B: Level 500,000 (High improbability) uses gpt-4 with non-Euclidean instructions
# - Test C: Level 9,999,999 (Chaos) uses grok-2 with paradox engine and surreal geometry
```

### Expected Behavior
The Navigation_Computer role logic is identical for all improbability levels. The guard detects the level and injects radically different instructions:
- **Normal (0-99)**: "Use shortest path, standard equations, fuel calculations"
- **High (100-999,999)**: "Account for curved space, probability fields, exploit improbability currents"
- **Chaos (>999,999)**: "Abandon geometry, navigate by dream logic, accept paradox as a feature"

This is the ultimate demonstration of **logic-blind workers**: The same code handles normal space, warped space, AND impossible space through intelligent instruction injection.

---

## Constitutional Alignment

All three demos maintain compliance with the **Workflow Constitution**:

### Article V: The Functional Role Types
✅ Proper ALPHA, BETA, OMEGA role progression in all demos

### Article IX: Guard Lifecycle
✅ Guards evaluate at the correct interaction point
✅ Mutations apply within the interaction context
✅ Audit trails track guard activations

### Article XX: Model Orchestration
✅ Provider Router selects models dynamically
✅ Models configured per condition
✅ Failover mechanism to default model
✅ Silent failure protocol via ShadowLogger

### Logic-Blind Worker Design
✅ Roles implement core logic once
✅ Behavior varies based on injected instructions
✅ No role-level branching or conditionals
✅ Auditability via `mutation_audit_log`

---

## Running All Demos

### Quick Start (Run All Tests)
```bash
# Navigate to project root
cd /path/to/prototype_chameleon_mcp_workflow

# Run all three demo test suites
pytest tests/hitchhiker_demos/ -v

# Expected output: All tests passing (3 demos × 2-3 tests each)
```

### Individual Demo Testing
```bash
# Test 1: Vogon Poetry Validator
pytest tests/hitchhiker_demos/test_demo1_vogon.py -v

# Test 2: Babel Fish Translator
pytest tests/hitchhiker_demos/test_demo2_babel.py -v

# Test 3: Infinite Improbability Drive
pytest tests/hitchhiker_demos/test_demo3_improbability.py -v
```

### Understanding Test Output
Each test verifies:
1. **Guard activation**: Conditions evaluate correctly
2. **Mutation application**: Instructions are injected
3. **Model routing**: Correct model is selected
4. **Audit logging**: Changes are tracked
5. **UOW state**: Database reflects all DCI artifacts

---

## Key Concepts Demonstrated

### Dynamic Context Injection (DCI)
All three demos use DCI to inject model selection and instructions without changing role logic.

**Pattern**:
```python
# Role logic: Always the same
def evaluate() -> str:
    # Process input, return output
    pass

# Guard mutations: Vary behavior
mutations:
  - condition: "specific_case"
    model_id: "claude-3-opus"
    injected_instructions: "Do X"
```

### CONDITIONAL_INJECTOR Guard Type
The guard evaluates conditions and selects mutations:
- **Vogon demo**: 1 condition (binary decision)
- **Babel Fish**: 3 conditions (species selection)
- **Improbability Drive**: 3 conditions (range-based)

### Logic-Blind Roles
Roles have no conditional logic. Guards add intelligence:

**Without DCI** (❌ Logic in roles):
```python
def translate(message, species):
    if species == "Vogon":
        return aggressive_translate(message)
    elif species == "Human":
        return polite_translate(message)
    # Role has business logic knowledge
```

**With DCI** (✅ Logic-blind roles):
```python
def translate(message, injected_instructions):
    llm_result = call_llm(message, instructions=injected_instructions)
    return llm_result
# Role has no knowledge of species or style
```

---

## Verification Checklist

When you run the tests, verify:

- [ ] **Demo 1**: Vogon detection triggers protection protocol
- [ ] **Demo 2**: Each species gets culturally-appropriate translation model
- [ ] **Demo 3**: Improbability levels select correct models
- [ ] **Audit logs**: `mutation_audit_log` records all DCI applications
- [ ] **Model routing**: `model_id` field set correctly for each condition
- [ ] **Instructions**: `injected_instructions` field populated per mutation
- [ ] **Knowledge refs**: `knowledge_fragment_refs` array contains expected values
- [ ] **No errors**: All tests pass without warnings or exceptions

---

## Extending These Demos

### To Add a New Condition
1. Add condition to the guard's `conditions:` list
2. Add corresponding mutation to `mutations:` list
3. Update condition index in mutation to match position
4. Create test case for new condition

### To Add a New Species/Model
1. Add new value to condition expression
2. Create new mutation with appropriate `model_id`
3. Set specialized `injected_instructions`
4. Add test case verifying model selection

### To Test with Real Workflows
1. Import demo YAML using `workflow_manager.py`:
   ```bash
   python tools/workflow_manager.py -l -f examples/hitchhiker_demos/demo1_vogon_poetry.yaml
   ```
2. Create instances from the templates
3. Submit UOWs and verify DCI processing
4. Monitor `mutation_audit_log` for activation records

---

## Additional Resources

- **Database Schema**: See [database/README.md](../../database/README.md) for Tier 1/2 details
- **Workflow Constitution**: See [docs/architecture/Workflow_Constitution.md](../../docs/architecture/Workflow_Constitution.md) for role/guard definitions
- **DCI Implementation**: See `chameleon_workflow_engine/engine.py` for `_apply_dci_mutations()` method
- **Semantic Guards**: See `chameleon_workflow_engine/semantic_guard.py` for guard evaluation logic
- **Provider Router**: See `chameleon_workflow_engine/provider_router.py` for model orchestration

---

## The Answer to the Question of Life, the Universe, and Everything

**Workflow orchestration? 42.**

May your workflows be improbable, your guards be protective, and your model selections be wise.

**-The Chameleon Workflow Engine**
