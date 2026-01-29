# **Database Agnosticism Validation Plan**

## **1\. Objective**

To ensure the UOWRepository interface and StateHasher utility function correctly and consistently across disparate database engines (SQLite, PostgreSQL, Snowflake, Databricks, Teradata) as mandated by the **Workflow Constitution**.

## **2\. UOWRepository Interface Requirements**

The abstract base class (ABC) must define the following methods, which every driver adapter must implement:

class UOWRepository(ABC):  
    @abstractmethod  
    def create(self, uow\_data: dict) \-\> str: ...  
      
    @abstractmethod  
    def get(self, uow\_id: str) \-\> dict: ...  
      
    @abstractmethod  
    def update\_state(self, uow\_id: str, new\_state: str, payload: dict, interaction\_policy: dict \= None) \-\> None: ...  
      
    @abstractmethod  
    def append\_history(self, uow\_id: str, event: str, previous\_hash: str) \-\> None: ...

### **2.1 Driver-Specific Challenges & Solutions**

| Database | Challenge | Solution |
| :---- | :---- | :---- |
| **SQLite** | No native JSON type (stored as TEXT). | Adapter must serialize/deserialize JSON on read/write. |
| **PostgreSQL** | Native JSONB. | Adapter passes dicts directly to driver (psycopg2/asyncpg). |
| **Snowflake** | VARIANT column type. | Adapter handles snowflake.connector specific object mapping. |
| **Databricks** | STRUCT/MAP complex types. | Adapter maps Python dicts to PySpark/ODBC equivalents. |

## **3\. StateHasher Consistency Strategy**

The StateHasher is critical for **Atomic Traceability**. It must produce the exact same SHA-256 hash regardless of how the database returns the data (e.g., a JSON string from SQLite vs. a Python dict from Postgres).

**Normalization Protocol:**

1. **Input:** Receive payload (Dict or String).  
2. **Normalization:** Sort keys alphabetically. Remove whitespace.  
3. **Encoding:** Convert to UTF-8 bytes.  
4. **Hashing:** SHA-256.

## **4\. Testing Strategy**

### **4.1 Integration Test Suite**

* **In-Memory SQLite:** Runs on every commit. Validates standard SQL logic.  
* **Mocked Enterprise Drivers:** Uses unittest.mock to simulate Snowflake/Postgres return types (variants, binary json) to verify the Adapter handles them correctly without a live DB connection.

### **4.2 Verifiability**

* **Hash Test:** Assert that StateHasher(sqlite\_data) \== StateHasher(snowflake\_data).