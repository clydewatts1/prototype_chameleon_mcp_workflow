# **Operational Intervention Specifications**

This document establishes the protocols for **Manual Override** and **System Intervention**. It defines how authorized Administrators can intervene in active workflows to resolve deadlocks, data corruption, or logic failures while maintaining the system's audit integrity.

## **1\. The Principle of "Break-Glass" (The Pragmatic Clause)**

**Core Rule:** While Article I mandates "Total Isolation" for standard execution, **System Administrators** are granted "Break-Glass" privileges to manipulate UOWs directly.

**Constraint:** Every intervention is an **Auditable Event**. The Administrator **must** provide a reason\_for\_intervention (text justification) which is permanently appended to the UOW's lineage. "Silent" edits are strictly forbidden.

## **2\. Intervention Capabilities**

### **2.1 Force Unlock (The Jaws of Life)**

**Problem:** An Actor (e.g., a Kubernetes Pod) crashed while holding a transactional lock on a UOW in an Interaction. The lock lease has not yet expired, but the system is stalled.

**Action:**

* **Target:** Specific UOW ID in a specific Interaction.  
* **Operation:** FORCE\_RELEASE.  
* **Result:** The lock is legally broken. The UOW state is reset from IN\_PROGRESS to PENDING, making it visible to other Actors immediately.  
* **Audit Log:** "Lock broken by Admin![][image1]  
  | Reason: Actor pod![][image1]  
  crash loop."

### **2.2 Data Surgery (The Scalpel)**

**Problem:** A UOW contains invalid data (e.g., a typo in an email address or a negative currency value) that prevents it from passing a **Criteria Guard**, causing an infinite "Ate Path" loop.

**Action:**

* **Target:** Specific UOW ID.  
* **Operation:** PATCH\_ATTRIBUTES.  
* **Result:** The Administrator injects a JSON patch to modify specific fields.  
* **Version Control:** The system **archives** the pre-surgery state as a "Corrupt Version" and creates a new "Patched Version" in the lineage.  
* **Audit Log:** "Attributes patched by Admin![][image1]  
  | Reason: Fix typo in customer\_id."

### **2.3 Teleportation (The Detour)**

**Problem:** A UOW is stuck in the wrong queue (e.g., sent to Dead\_Letter due to a config error) or needs to skip a broken step.

**Action:**

* **Target:** Specific UOW ID.  
* **Operation:** MOVE\_TOKEN.  
* **Source:** Current Interaction ID.  
* **Destination:** Target Interaction ID.  
* **Result:** The UOW is atomically removed from Source and inserted into Destination.  
* **Audit Log:** "Token moved from![][image2]  
  to![][image3]  
  by Admin![][image1]  
  | Reason: Retry after hotfix."

### **2.4 State Forcing (The Gavel)**

**Problem:** A UOW is stuck in IN\_PROGRESS but the work is actually done (e.g., external API call succeeded but callback failed).

**Action:**

* **Target:** Specific UOW ID.  
* **Operation:** SET\_STATUS.  
* **Result:** Force status to COMPLETED or FAILED.  
* **Audit Log:** "Status forced to COMPLETED by Admin![][image1]  
  | Reason: Manual reconciliation of external state."

## **3\. The Admin Actor (Identity Specification)**

To perform these actions, the request must come from a specialized identity.

* **Role Type:** SYSTEM\_ADMIN (A reserved Role Type not used in standard workflows).  
* **Access Control:** This role bypasses standard **Guards**. It interacts directly with the **Persistence Layer** via the **Management API**.  
* **Throttle:** Operations are rate-limited to prevent accidental bulk-corruption (e.g., "Select All \-\> Delete").

## **4\. Safety Interlocks**

1. **Quiescence Requirement:** Before performing **Data Surgery** or **Teleportation**, the UOW must be in a PENDING or FAILED state. You cannot patch a UOW that is currently locked (IN\_PROGRESS) by another active Actor. You must FORCE\_UNLOCK it first.  
2. **Lineage Preservation:** The UOW ID must never change. The history must show the continuous timeline, including the moment the Admin intervened.

## **5\. Audit Performance & Configuration**

To balance the "Law of Immutable Audit" (Article XVII) with system performance, the engine implements a **Tiered Audit Strategy**.

### **5.1 Intervention vs. Execution Logs**

* **Intervention Events (Admin Actions):** These are **Low-Frequency / High-Risk**.  
  * **Strategy:** Strict Synchronous Write.  
  * **Constraint:** The intervention *must* fail if the audit log cannot be written. Security takes precedence over performance here.  
* **Lineage Events (The Resulting Trace):** These are **High-Frequency**.  
  * **Strategy:** Asynchronous / Eventual Consistency.  
  * **Constraint:** Can be offloaded to a separate "Cold Store" or message queue (e.g., Kafka/SQS) to prevent blocking the main workflow engine.

### **5.2 Configuration Levels (AUDIT\_LEVEL)**

System Administrators can configure the verbosity of the data payload logging to manage storage/performance burdens:

1. **STRICT (Default):** Full payload snapshots of pre- and post-intervention states.  
   * *Cost:* High Storage, Higher Latency.  
   * *Use Case:* Financial/Compliance workflows where every byte must be legally traceable.  
2. **DIFFERENTIAL:** Logs only the *diff* (patch) of the changes.  
   * *Cost:* Medium Storage, Medium Latency.  
   * *Use Case:* Standard business logic. Provides traceability without duplicating the entire UOW state.  
3. **METADATA\_ONLY:** Logs *who* intervened, *why*, and *when*, but not the full data payload modification.  
   * *Cost:* Low Storage, Low Latency.  
   * *Use Case:* High-throughput non-critical tasks.  
   * *Warning:* Makes precise "Data Surgery" reversal difficult as the previous state is not explicitly archived in the log.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAtCAYAAAATDjfFAAABhUlEQVR4Xu3bsUrDUBQG4BYUdFQEoaTtrZviIAScHDu4ODn6AO4ugs/h7gu4Ojg6Objq7iC4+QJF67mQwjV0EuLi98GhyX9D558T0usBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/D9VVW2ORqP78Xg8b+ZxcRb5Q9x/Nvlbc/0cc1r+BwAAfyCXsihol0vyq8inRdSP7Ho4HO4XGQAAHcslbBbF7KgMU0prkd9FvlPmcX8SZ+dlBgBAh6KA1VHMbuNypZVPI/8qsyyyi2XbOAAAutGP8nXT3q5lebsW815mg8FgK7KXmN0yBwCgI1HUNqJ8PU0mk+32WeSvubSVWUrpuNm6/djGAQDQkShfZzHzdp7lYlZ+cFDX9WpkH1HuDsvnAADoUH4dGiVs1s6rqlrPr0MXHxzE717etqWUDtrPAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/M43Rds2xuVsIu4AAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAtCAYAAAATDjfFAAADmElEQVR4Xu3bPWidVRgH8JQo+C1Ra0ia23tvGiyiWxQsOIkiDjroImjxC0QoOChF0EWEgiiCFHWqSgZpxYKDuEiHYJeOKrgpVBCCgougoEv8P7nnhTeXgGOS8vvBw3vOc857zh0fzrnvzAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADA3jUcDn9ObO4QF+bn56+fng8AwC6oAm0wGDw2lTvd7wMAsEvqFC3F2cbhw4eXq7+4uHhbPZN7ZftMAAB2RQqzRxIfJBZGo9EzKdzmpsbfSnycOJ/xHxJPpv3JcHKV+lHi3cTFNvdk4rvEU4lXkzpQ43nn26x7Lu0Lab/ZX3/aYDC4J/Ner/Wrn+d7iUvdeO2RtV6u35HnQ5VLey357w8dOnRr2tek/WXSszW2vLx8R/pnE28kvujWAQDYN1LErHena1Uo9YZmq3hKEbSU/KlKZN6Lc3NzN6e/MGynconjrch6PO2nu5fT30zx9FwKpppfBd1VeZ7oTvDanCqkqrhbT/dAy1VhVfmtIi3PP2tOtatAq4JvdXX16jwfHo/Hw9q77XG27VEF6D/t3a8Sv7b2h4mTWxsDAOwnKWI2uo8LUgS93XLjpaWla6udIunBiv477RTr63p2uep3hV/rb6b/aJ53Jv7o8s2BvPts9rilzR0njnWDVWR1J3Fp/5V1Vlv7TOL3jH2e5wu9+cfqxK21TyUut3YVe/8mLrU1topCAIB9pQqrfj9F1EqKn29649sKs7JTETdsV5ht/K688/7M5Er0dOLH3tSau94VZKXWT6z1xn9JLGSduTw/W1lZuamuO6t98ODBG7p5i4uL17X317p85mwMJ1eq7yT+rqJxej4AwL5RRU4VOL3UbPo/9YupYbtS7KuCqH+a1nJneqdy5+qasuUvJs5Pzf0tc+7v+nVNOux95FB7tqvYJzLvtcFgcHfl6xSt27f2Svt4m3/m6NGjN85MCsTuZO/5xKVhu87NGvcOJ9emAABXljrlms71T7n66hTsyJEjt/dz7f2tDwA6KZwuJxaqXf9Hy5xPZ7ZfV85263QfEnQDtfdO+4/H4/mWn+3/T676078JAID/kWLtgdHki9P70j7pqhIAYA+qk7X6v1ydjNV15fQ4AAB7xGg0eqk+KpjOAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABwJfgPCOW6p6IX9r0AAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAtCAYAAAATDjfFAAAEz0lEQVR4Xu3cXcjeYxwH8Htt5P191l6e+36ebVpGOXgUQkkUJ9IoykuKtCIHQ2pSTuRAapGivORAXk4lYWWlWK28RRQrNFtLHCgOiPn+nvv6z9/fThATn0/9ut6v/3U/R7+u/30/oxEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADA328ymexJ7GvxTZWzs7Nb1q5de8xw7kG0KGe6vMrhAADAf966deuOTpL2xtzc3LKuL+1tiZ/78w6m+fn5Q5KwXTDsBwD4X0hidmri61SX9Pp2JH7sTQMA4GBJYvZQPzlbvXr1sWl/NTMzc+bKlStXpf5kYmfivsQDNd7W3Tkej29OeU3i9rZ8UeqfJjYl3ur2TP3DxMP1rJpTfbX/7Ozs+4mrs8/Fvbk70r4+5faUp6XckHgk8V6NtzM9mHU3pHyx9kx82a2PxWm/O5me951Vq1ad0hv7ncx5JnFH4sZq101e6udUvW72Uv8k57gt5et1zjp36psTO3t7bO/V6zzv1meo83f9AAB/WpKLrxOvJZZXJGE5rDd2T+vfU8lLEpDrWv+G1K/tzduX9nzK7/pr16xZc3LKD1qSV8ncC73xz/OsV7Pu+GXLlh1ZfW2PJ5IUranEqSVMNyW2J57NlCWZc1fqm7tELO2L0v6p1SvB+6qeVfumvqPqbWx92rcmrmmfo/qXTKaf+epJS9JSbq3+Vl/Yt332V+bm5tI1ubvOUmeqsfSdUXtWPftsrL3a867vklsAgL9kMv2xweZhf6cSuIy/NGwnIVnd9bU9fnNT1/ovrbHM/SLl1iRZa3tjdTtW637o+lqCV337krSd35v7fZcItfZLXWKZ8t609/TqC9+9a4nUt21JJYsvt3qt/2jSErTRNGl7tndzuLBXq9dZdmbf5/s/wkjfrnpWq1cCOF9JZ+pbE7sTH6fvym4+AMCf1n5w8FkSqZXDsU7dYFV07fpxQiUxvfHTkrxsacnKtq5/NH01Wa8z99+6NXX7VXveVo1KeFasWHFSqy/caLX6QlLWnvdQ1SuhO8C8hWQu+92f8um036j+tJ9K/cOlS5ceNThXt/fTbd7wZnBX4pb0nzdYtzjnPKLN+TyxfNxu8SqZS8I37p7dWb9+/aH9NgDAHzYzM3N6S172vwYdyvjm/m3aaHoj9XiSvMPrViljz9Xt1Hj6qvLtblL2fCzteoe4q+vL8y6rdenblPnnVl/KR0fttWX6P66ykqxxe+WafS6p5CnlWb15/VuwXfW9toxfldg4mSaTdaP2U+KZlpDt7ea3NfWduk1V79/EtVee2yoBrSQy9d3dmkoIx7++El54Zsor6jn1d6z+rLu3kriq53OeUOfu1gMA/G0qeRr2lSQsJ6ZYPOxPArN8uKZuydr8/apd/f2+WNxu0X6zb7uB29/XTzCrPty75BzftWStXst+1vW3fxGyZdSSv0733OHZD/R5Rr+esywanOe4WtO1AQBo2nfI9iYJXDc7/QXphm4s9QsTT0ymP164c3SARBMAgH9AkrE3E9vG4/FTw7H2Xbgnq0xCd/ZwHACAf4H2v982DvsBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPi3+QVW6RzZnAy0QgAAAABJRU5ErkJggg==>