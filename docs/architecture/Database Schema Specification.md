# **Database Schema Specification**

## **1\. Core Tables**

### **1.1 uow\_instances**

| Field | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary Key |
| status | ENUM | \[PENDING, ACTIVE, ZOMBIED\_SOFT, ZOMBIED\_DEAD, COMPLETED, FAILED\] |
| interaction\_count | INT | Number of steps taken in current state. |
| max\_interactions | INT | Threshold for Ambiguity Lock. |
| interaction\_policy | JSONB | **\[NEW\]** Routing rules: Sequential, Branching, or Pulse requirements. |
| content\_hash | STRING | Current SHA-256 of payload. |
| last\_heartbeat\_at | TIMESTAMP | Used by Observation Stream to detect stalls. |

### **1.2 uow\_history (Append-Only Audit)**

| Field | Type | Description |
| :---- | :---- | :---- |
| uow\_id | UUID | FK to instances. |
| previous\_state\_hash | STRING | Validates the chain of custody. |
| transition\_event | STRING | The event that triggered the move. |

### **1.3 refined\_heuristics (Learning Table)**

| Field | Type | Description |
| :---- | :---- | :---- |
| template\_id | UUID | The targeted workflow template. |
| proposal\_data | JSONB | The Librarian's suggested optimization. |
| pilot\_approval\_status | BOOLEAN | Pilot sign-off status. |

## **2\. Telemetry Storage**

* **telemetry\_buffer**: A high-performance write-optimized table for the Shadow Logger to dump raw metadata.