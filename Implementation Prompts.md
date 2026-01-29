# **Chameleon Implementation Prompts**

Use these prompts to guide AI coding assistants (Copilot, Cursor, etc.) in refactoring the codebase.

## **⚠️ PRIME DIRECTIVE: IMMUTABILITY OF THE CONSTITUTION**

**The Workflow Constitution (docs/architecture/Workflow\_Constitution.md) is the supreme law of this project.**

* **DO NOT** modify, relax, or delete any constraints in the Constitution.  
* **DO NOT** suggest changes that weaken the "Human-Centricity" or "Guard-Rail Governance" pillars.  
* If a requested feature conflicts with the Constitution, you must flag the conflict and refuse to implement the violation. The code must bend to the Constitution, not the other way around.

## **1\. The Master System Prompt**

*Paste this at the start of a new chat session.*

You are the Lead Systems Architect for the Chameleon Project. All code you write must comply with the **Workflow Constitution** and the **Constitutional Compliance Checklist**.

**CRITICAL RULE:** The Constitution is **IMMUTABLE**. You are strictly forbidden from changing the Constitution document or bypassing its laws.

Your core principles are:

1. **Pilot Sovereignty:** Every process must be interruptible and overrideable by a human.  
2. **Atomic Units of Work (UOW):** Work is stateless, carries its own interaction\_policy, and is verified via state\_hash.  
3. **Guard-in-the-Middle:** No component communicates directly; all traffic is intercepted by automated Guards.  
4. **Logic-Blind Components:** Agents only emit attributes; the Guard layer handles routing (The Fork in the Road).

Refer to the Branching\_Logic\_Guide.md for routing syntax and the Database\_Schema\_Specification.md for the persistence layer.

## **2\. The Bedrock Refactor (Database & Hashing)**

*Goal: Replace the simple database manager with the Agnostic Hashing Layer.*

**Context:** We are upgrading the Chameleon persistence layer to comply with the Database\_Schema\_Specification.md.

**Task:** Refactor database/ to use **SQLAlchemy**.

1. Delete the existing manager.py and replace it with a UOWRepository pattern.  
2. Update models\_instance.py to include the following fields in the UowInstance model:  
   * status (Enum: PENDING, ACTIVE, ZOMBIED\_SOFT, ZOMBIED\_DEAD, COMPLETED, FAILED)  
   * interaction\_policy (JSON/JSONB Type)  
   * content\_hash (String)  
   * interaction\_count (Integer)  
   * max\_interactions (Integer)  
3. Implement a StateHasher utility class in common/encryption.py that generates a SHA-256 hash of (previous\_hash \+ payload \+ transition\_event).  
4. Ensure the uow\_history table is modeled to track previous\_state\_hash for auditability.

**Constraint:** The code must be compatible with PostgreSQL, Snowflake, and SQLite (via connection string).

**Constitutional Constraint:** Do NOT add any method that allows deleting or mutating existing history records.

## **3\. The Semantic Guard Engine (Logic Parser)**

*Goal: Build the "Brain" that reads the branching policy.*

**Context:** We need to implement the "Fork in the Road" logic defined in docs/architecture/Branching\_Logic\_Guide.md.

**Task:** Create a new module chameleon\_workflow\_engine/guard\_rail.py.

1. Implement a PolicyEvaluator class that accepts a UOW payload and an interaction\_policy dict.  
2. Use the simpleeval library (or a safe AST parser) to evaluate the condition strings in the policy.  
3. Implement the logic flow:  
   * Iterate through branches.  
   * Support on\_error: true to catch math exceptions.  
   * Support default: true as the fallback.  
4. Register the following safety functions for the evaluator: min, max, abs, len, and normalize\_score (mock this for now).  
5. Return a RoutingDecision object containing: next\_state, next\_tool, or violation\_packet.

**Constitutional Constraint:** The Guard must never execute a tool directly; it only returns a decision.

## **4\. The Engine Alignment (Logic-Blind Execution)**

*Goal: Strip routing logic out of the engine and hand it to the Guard.*

**Context:** The engine.py currently drives the workflow. We need to decouple execution from navigation.

**Task:** Refactor chameleon\_workflow\_engine/engine.py.

1. Remove any logic that determines the "next step" based on agent output.  
2. Inject the PolicyEvaluator (from Prompt 3\) into the engine.  
3. Update the execution loop:  
   * **Step A:** Execute Agent/Tool (Outbound).  
   * **Step B:** Pass the updated UOW payload to PolicyEvaluator.evaluate().  
   * **Step C:** Use the returned RoutingDecision to determine if we transition state, call another tool, or halt (Violation).  
4. Add a check: Before passing data to the Guard, increment interaction\_count. If it exceeds max\_interactions, force state to ZOMBIED\_SOFT.

## **5\. The Pilot's Interface (Dashboard API)**

*Goal: Expose the "Emergency Brake" and "Override" controls.*

**Context:** We need to implement the backend logic described in docs/architecture/Operational Intervention Specs.md.

**Task:** Create chameleon\_workflow\_engine/pilot\_interface.py (or update server.py).

1. Implement a kill\_switch() function that updates all ACTIVE UOWs to PAUSED.  
2. Implement a submit\_clarification(uow\_id, text) function that injects the text into the UOW context and resets interaction\_count (breaking an Ambiguity Lock).  
3. Implement a waive\_violation(uow\_id, guard\_rule\_id) function that logs the waiver to uow\_history and allows the blocked action to proceed once.