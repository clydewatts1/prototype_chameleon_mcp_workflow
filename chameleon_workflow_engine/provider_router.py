"""
Provider Router for Dynamic Context Injection (DCI).

This module handles LLM model resolution, provider mapping, and failover logic
for the Chameleon Workflow Engine. It maps abstract model IDs to concrete provider
configurations and handles credential management.

Constitutional Reference: Article XX (Model Orchestration & DCI)
"""

import os
from typing import Dict, Optional
from loguru import logger


class ProviderRouter:
    """
    Routes model requests to appropriate LLM providers with failover support.
    
    Responsibilities:
    - Map model IDs (e.g., "gpt-4o", "claude-3-sonnet") to provider names
    - Validate model_override against whitelist
    - Provide failover models when primary is unavailable
    - Return provider configuration for API client construction
    
    Note: This is a prototype stub. Production version would integrate with
    environment-based configuration and API credential management.
    """
    
    def __init__(self):
        """Initialize provider router with model mapping."""
        # Model ID -> Provider mapping (expandable via environment config)
        self.model_provider_map = {
            # OpenAI models
            "gpt-4o": "openai",
            "gpt-4-turbo": "openai",
            "gpt-4": "openai",
            "gpt-3.5-turbo": "openai",
            
            # Anthropic models
            "claude-3-opus": "anthropic",
            "claude-3-sonnet": "anthropic",
            "claude-3-haiku": "anthropic",
            
            # Google models
            "gemini-pro": "google",
            "gemini-flash": "google",
            
            # xAI models
            "grok-1-pro": "xai",
            
            # Default/fallback
            "default": "gemini-flash",
        }
        
        # Whitelist of allowed models (prevents arbitrary model injection)
        self.model_whitelist = set(self.model_provider_map.keys())
        
        # Safe failover model (fast, cheap, reliable)
        self.failover_model_id = "gemini-flash"
    
    def resolve_model(self, model_id: str) -> Dict[str, str]:
        """
        Resolve model ID to provider configuration.
        
        Args:
            model_id: Abstract model identifier (e.g., "gpt-4o", "claude-3-sonnet")
        
        Returns:
            Dictionary with 'provider' and 'model' keys:
            {
                'provider': 'openai',  # Provider name
                'model': 'gpt-4o'      # Actual model name
            }
        
        Example:
            >>> router = ProviderRouter()
            >>> router.resolve_model("gpt-4o")
            {'provider': 'openai', 'model': 'gpt-4o'}
        """
        if model_id not in self.model_provider_map:
            logger.warning(
                f"Model ID '{model_id}' not found in provider map. "
                f"Using failover model '{self.failover_model_id}'."
            )
            model_id = self.failover_model_id
        
        provider = self.model_provider_map[model_id]
        
        return {
            'provider': provider,
            'model': model_id
        }
    
    def get_failover_model(self, model_id: str) -> str:
        """
        Get safe failover model when requested model is unavailable.
        
        This method is called when:
        - Model ID fails whitelist validation
        - Provider API returns error (rate limit, invalid key, etc.)
        - Model ID is not in the provider map
        
        Args:
            model_id: The model that failed
        
        Returns:
            Failover model ID (default: "gemini-flash")
        
        Example:
            >>> router = ProviderRouter()
            >>> router.get_failover_model("invalid-model-999")
            'gemini-flash'
        """
        logger.info(
            f"Initiating failover for model '{model_id}'. "
            f"Using safe default: '{self.failover_model_id}'"
        )
        return self.failover_model_id
    
    def validate_model_whitelist(self, model_id: str) -> bool:
        """
        Validate that model ID is in the allowed whitelist.
        
        Security check to prevent injection of arbitrary model names
        that could bypass cost controls or access unauthorized APIs.
        
        Args:
            model_id: Model ID to validate
        
        Returns:
            True if model is whitelisted, False otherwise
        
        Example:
            >>> router = ProviderRouter()
            >>> router.validate_model_whitelist("gpt-4o")
            True
            >>> router.validate_model_whitelist("malicious-model")
            False
        """
        is_valid = model_id in self.model_whitelist
        
        if not is_valid:
            logger.warning(
                f"Model ID '{model_id}' failed whitelist validation. "
                f"Allowed models: {sorted(self.model_whitelist)}"
            )
        
        return is_valid
    
    def get_provider_credentials(self, provider: str) -> Optional[str]:
        """
        Retrieve API credentials for a provider.
        
        NOTE: Prototype stub. Production version would use secure credential
        management (e.g., AWS Secrets Manager, HashiCorp Vault).
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
        
        Returns:
            API key from environment, or None if not found
        
        Example:
            >>> router = ProviderRouter()
            >>> key = router.get_provider_credentials("openai")
            >>> # Returns value of OPENAI_API_KEY env var
        """
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "xai": "XAI_API_KEY",
        }
        
        env_var = env_var_map.get(provider)
        if not env_var:
            logger.warning(f"No credential mapping for provider '{provider}'")
            return None
        
        api_key = os.getenv(env_var)
        if not api_key:
            logger.warning(
                f"API key not found for provider '{provider}'. "
                f"Expected environment variable: {env_var}"
            )
        
        return api_key
    
    def get_model_config(self, model_id: str) -> Dict[str, any]:
        """
        Get complete configuration for a model including provider and credentials.
        
        This is the primary method called by the engine during UOW execution.
        
        Args:
            model_id: Model ID to configure
        
        Returns:
            Complete model configuration:
            {
                'model_id': 'gpt-4o',
                'provider': 'openai',
                'api_key': 'sk-...',
                'is_whitelisted': True,
                'is_failover': False
            }
        
        Example:
            >>> router = ProviderRouter()
            >>> config = router.get_model_config("gpt-4o")
            >>> # Returns full config dict ready for API client
        """
        is_whitelisted = self.validate_model_whitelist(model_id)
        is_failover = False
        
        # If not whitelisted, use failover
        if not is_whitelisted:
            model_id = self.get_failover_model(model_id)
            is_failover = True
        
        # Resolve to provider
        resolved = self.resolve_model(model_id)
        provider = resolved['provider']
        
        # Get credentials
        api_key = self.get_provider_credentials(provider)
        
        return {
            'model_id': model_id,
            'provider': provider,
            'api_key': api_key,
            'is_whitelisted': is_whitelisted,
            'is_failover': is_failover
        }


# Global singleton instance for use across the engine
_provider_router: Optional[ProviderRouter] = None


def get_provider_router() -> ProviderRouter:
    """
    Get or create global ProviderRouter instance.
    
    Returns:
        Singleton ProviderRouter instance
    
    Example:
        >>> from chameleon_workflow_engine.provider_router import get_provider_router
        >>> router = get_provider_router()
        >>> config = router.resolve_model("gpt-4o")
    """
    global _provider_router
    if _provider_router is None:
        _provider_router = ProviderRouter()
    return _provider_router


def initialize_provider_router(router: ProviderRouter) -> None:
    """
    Initialize the global provider router (for testing or custom configuration).
    
    Args:
        router: Custom ProviderRouter instance
    
    Example:
        >>> custom_router = ProviderRouter()
        >>> initialize_provider_router(custom_router)
    """
    global _provider_router
    _provider_router = router
