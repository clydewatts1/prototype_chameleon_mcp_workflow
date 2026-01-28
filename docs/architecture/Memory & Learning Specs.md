# **Memory & Learning Specifications**

## **1\. The Learning Loop**

Input: Shadow Logs \+ Observation Stream \-\> Librarian Analysis \-\> Refinement Proposal \-\> Pilot Approval \-\> Template Update.

## **2\. Refinement Proposals**

The Librarian cannot modify system logic directly. It must issue a **Refinement Proposal**:

* **Source:** The specific UOW IDs that triggered the observation.  
* **Delta:** The proposed change to the YAML template or Guard rules.  
* **Risk Assessment:** Guard-validated simulation of the new rule.

## **3\. Ambiguity Lock Intelligence**

When a Pilot resolves an Ambiguity Lock by providing a "Clarification String," the Librarian indexes this interaction.

* The next time a similar UOW is generated, the clarification is injected into the prompt context to prevent a repeat lock.

## **4\. Sandbox Validation**

All learned heuristics must pass through a **Constitutional Guard Simulation** (Sandbox) to ensure the "learned" logic doesn't bypass existing safety rails.