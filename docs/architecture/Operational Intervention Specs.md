# **Operational Intervention Specifications**

## **1\. The Pilot Dashboard**

### **1.1 Emergency Controls**

* **Global Kill Switch:** A prominent button that forces all ACTIVE UOWs into PAUSED state.  
* **Selective Termination:** Ability to kill a specific branch of a topology.

### **1.2 The Override Interface**

When a Guard blocks or a Zombie triggers, the Pilot sees:

* **Violation Details:** Rule violated and raw telemetry.  
* **Action Buttons:**  
  * WAIVE: One-time pass (Proceed Once).  
  * RETRY: Re-submit as Soft Timeout.  
  * REFINE: Pass to Librarian to adjust the rule permanently.  
  * CLARIFY: Provide a string to break an Ambiguity Lock.

## **2\. Mandatory Metadata**

Every manual override requires the Pilot to select or type a **Reason Code**. This metadata is sent to the Librarian to close the "Continuous Learning" loop.

## **3\. Refinement Approval**

A dedicated tab for the Pilot to review **Refinement Proposals**. The UI must show a "Diff" of the template changes before approval.