# **Testing Strategy & Quality Assurance Specifications**

This document establishes the testing protocols required to verify that the Chameleon Workflow Engine adheres to its Constitution and Architectural Specifications. It serves as the "Definition of Done" for the Implementation Phase.

## **1\. The Testing Philosophy**

**"Trust but Verify"**

Every Architectural Specification must have a corresponding automated test. If a feature (e.g., The Ate Path) is defined in the docs but not verified in the test suite, it is considered **non-existent**.

### **1.1 Test Infrastructure**

* **Framework:** pytest (Standard Python testing framework).  
* **Database:** In-memory SQLite (sqlite:///:memory:) for fast, isolated execution of integration tests.  
* **Fixtures:** All tests must utilize the DatabaseManager to ensure strict transactional isolation between test cases.

## **2\. Test Levels (The Pyramid)**

### **2.1 Level 1: Unit Tests (The Components)**

**Focus:** Individual functions and logic blocks in isolation.

**Target Areas:**

* **Guard Logic:** Verify CRITERIA\_GATE passes/fails correctly based on inputs. Verify TTL\_CHECK math.  
* **Schema Validation:** Verify workflow\_manager.py rejects invalid YAML (e.g., missing Alpha role) with specific error messages.  
* **Atomic Versioning:** Verify the "Diff Calculator" correctly identifies changes between two JSON blobs.

### **2.2 Level 2: Integration Tests (The Engine)**

**Focus:** The interaction between the ChameleonEngine controller and the Database.

**Target Areas:**

* **Instantiation:** Does instantiate\_workflow create the correct number of rows in Instance\_Roles?  
* **Locking Mechanics:** If Actor A checks out UOW X, does checkout\_work for Actor B return null?  
* **State Transitions:** Does submit\_work successfully move status from IN\_PROGRESS to COMPLETED?

### **2.3 Level 3: System Tests (The Workflows)**

**Focus:** End-to-End execution of a lifecycle using real YAML templates.

**Target Areas:**

* **The Vertical Slice:** A full "Happy Path" run from Alpha ![][image1] Beta ![][image1] Omega.  
* **The Ate Path:** Intentionally submitting bad data to trigger a Guard failure and verifying routing to Epsilon.  
* **The Zombie Protocol:** Manually manipulating timestamps to simulate a timeout and verifying Tau detection.

## **3\. The Vertical Slice Protocol (The First Milestone)**

The primary objective of the AI Code Agent is to implement and pass the **Vertical Slice Test**.

**Test Scenario: tests/e2e/test\_vertical\_slice.py**

1. **Setup:** Load tools/complete\_workflow\_example.yaml into the DB.  
2. **Instantiate:** Call engine.instantiate\_workflow(). Verify Alpha UOW exists.  
3. **Step 1 (Alpha):** Simulate Alpha Role (or system) spawning the work.  
4. **Step 2 (Beta Checkout):** Actor Processor\_01 calls checkout\_work("Processor\_Role").  
   * *Assert:* UOW is returned. Status is IN\_PROGRESS. Locked by Processor\_01.  
5. **Step 3 (Beta Submit):** Actor Processor\_01 calls submit\_work(result={...}).  
   * *Assert:* Status is COMPLETED. History log contains the update.  
6. **Step 4 (Completion):** Verify UOW is sitting in the queue for the next step (or Omega).

## **4\. Constitutional Verification Matrix**

The AI Agent must ensure the following "Laws" are covered by tests:

| Article / Spec | Test Case Name | Success Condition |
| :---- | :---- | :---- |
| **Article I (Isolation)** | test\_actor\_lock\_exclusivity | Actor B cannot modify Actor A's locked token. |
| **Article XI (Ate Path)** | test\_guard\_failure\_routing | Failed token moves to Epsilon Interaction, not next Role. |
| **Article XI (Chronos)** | test\_zombie\_timeout\_detection | Old IN\_PROGRESS token is flagged by Tau. |
| **Atomic Versioning** | test\_history\_immutability | Every submit\_work call adds a new row to Instance\_UOW\_History. |
| **Topology Rules** | test\_bipartite\_validation | YAML Import fails if Role connects directly to Role. |

## **5\. Mocking Strategy**

* **Database:** Do **NOT** mock the database logic for Engine tests. Use the real SQLite engine via DatabaseManager. The logic is too dependent on SQL transactions/locking to mock safely.  
* **External Systems:** Mock any HTTP calls (e.g., if an "Auto Role" calls an external API).  
* **Time:** Mock datetime.now() to reliably test Timeouts and TTL Guards.

## **6\. Instructions for AI Implementation**

When implementing tests, follow this sequence:

1. **Create Fixtures:** Set up conftest.py with a reusable db\_session and loaded\_workflow\_template.  
2. **Implement Vertical Slice:** Write the happy path first to prove the engine connects.  
3. **Implement Guard Tests:** Verify the filtering logic.  
4. **Implement Edge Cases:** Timeouts, Locks, Errors.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAAt0lEQVR4XmNgGAWjgDpAQUGBQ05OLk1UVJQHXY4cwCgvL98KNNAYXYIsADIIaGAvkMmCLkcOYAR6twBoaByIjSIDlBAA2iRJClZSUgKaJTcfyJ6soqLCBzZIXFycGyhQDcSzSMVAw3YA6a9A3Aw0kB3FhaQAWVlZE6Ahq6WlpWXQ5UgCQAOEgQYtVlRUlEeXIxkADcoChnMEujjJAJRogYZNlZGRkUaXIwcwqqur84JodIlRMMAAAJV7J+RoCL8jAAAAAElFTkSuQmCC>