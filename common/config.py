import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration class that reads environment variables from .env file."""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize Config and load environment variables from .env file.
        
        Args:
            env_file: Path to .env file. If None, looks for .env in project root.
        """
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env"
        else:
            env_file = Path(env_file)
        
        if env_file.exists():
            load_dotenv(env_file)
        else:
            print(f"Warning: .env file not found at {env_file}")

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if variable not found
            
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)

    @staticmethod
    def get_int(key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Get an environment variable as an integer.
        
        Args:
            key: Environment variable name
            default: Default value if variable not found
            
        Returns:
            Environment variable value as int or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be an integer, got '{value}'")

    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """
        Get an environment variable as a boolean.
        
        Args:
            key: Environment variable name
            default: Default value if variable not found
            
        Returns:
            Environment variable value as bool or default
        """
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")


# Load environment variables once at import so module-level constants work
_config = Config()

# --- Standardized Database Configurations ---
# Shared by Server, Tools, and Tests
TEMPLATE_DB_URL = Config.get("TEMPLATE_DB_URL", "sqlite:///template.db")
INSTANCE_DB_URL = Config.get("INSTANCE_DB_URL", "sqlite:///instance.db")
PHASE3_DB_URL = Config.get("PHASE3_DB_URL", "sqlite:///phase3.db")