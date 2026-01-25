# Configuration Module

This module provides a simple and flexible way to manage environment variables through the `Config` class.

## Setup

### 1. Install Dependencies

Add `python-dotenv` to your project dependencies:

```bash
pip install python-dotenv
```

Or add it to `requirements.txt`:
```
python-dotenv
```

### 2. Create a .env File

Create a `.env` file in the project root directory with your configuration variables:

```env
# Application Configuration
DEBUG=True
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
DB_POOL_SIZE=10

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0

# MCP Server Configuration
MCP_SERVER_PORT=9000
```

## Usage

### Basic Import

```python
from common.config import Config

config = Config()  # Automatically loads .env from project root
```

### Getting String Values

```python
database_url = config.get("DATABASE_URL")
# With default value
log_level = config.get("LOG_LEVEL", default="INFO")
```

### Getting Integer Values

```python
port = config.get_int("API_PORT", default=8000)
pool_size = config.get_int("DB_POOL_SIZE", default=5)
```

### Getting Boolean Values

Supported true values: `true`, `1`, `yes`, `on` (case-insensitive)

```python
debug_mode = config.get_bool("DEBUG", default=False)
enable_feature = config.get_bool("ENABLE_FEATURE")
```

### Custom .env Path

If your `.env` file is in a non-standard location:

```python
config = Config(env_file="/path/to/.env")
```

## Examples

```python
from common.config import Config

# Initialize config
config = Config()

# Get various types of configuration
app_debug = config.get_bool("DEBUG", default=False)
api_port = config.get_int("API_PORT", default=8000)
api_host = config.get("API_HOST", default="localhost")
db_url = config.get("DATABASE_URL")

print(f"Running on {api_host}:{api_port}")
print(f"Debug mode: {app_debug}")
print(f"Database: {db_url}")
```

## Best Practices

1. **Never commit `.env` files** - Add `.env` to your `.gitignore`
2. **Use sensible defaults** - Always provide defaults for optional variables
3. **Type safety** - Use the appropriate getter method for your variable type
4. **Documentation** - Document required environment variables in your code
5. **Validation** - Validate critical configuration values at application startup

## Error Handling

```python
try:
    max_connections = config.get_int("MAX_CONNECTIONS", default=10)
except ValueError:
    print("MAX_CONNECTIONS must be a valid integer")
```

## Module-Level Constants

The config module provides commonly used configuration constants at module level:

```python
from common.config import DATABASE_URL

# DATABASE_URL is pre-loaded from environment variable or defaults to:
# "sqlite:///./chameleon_workflow.db"
```

This allows for convenient import of configuration values without instantiating the `Config` class.
