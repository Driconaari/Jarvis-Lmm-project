"""
Jarvis Configuration Management
Loads and validates configuration from YAML files with environment overrides.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from pydantic import BaseModel, Field, validator
from loguru import logger


class OllamaModelConfig(BaseModel):
    """Configuration for a single Ollama model instance."""
    name: str = Field(..., description="Model name (e.g., 'mistral:7b')")
    endpoint: str = Field(..., description="Ollama endpoint URL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    context_window: int = Field(default=8192, description="Model's context window size")
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if not v.startswith('http'):
            raise ValueError('Endpoint must start with http:// or https://')
        return v.rstrip('/')


class EndpointConfig(BaseModel):
    """Configuration for a local LLM endpoint (Ollama server)."""
    name: str = Field(..., description="Endpoint identifier (e.g., 'endpoint1')")
    url: str = Field(..., description="Base URL of the Ollama server")
    models: List[OllamaModelConfig] = Field(default_factory=list)
    timeout: int = Field(default=120, description="Request timeout in seconds")
    healthcheck_interval: int = Field(default=30, description="Health check interval in seconds")
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith('http'):
            raise ValueError('URL must start with http:// or https://')
        return v.rstrip('/')


class AgentConfig(BaseModel):
    """Configuration for a specialized agent."""
    name: str = Field(..., description="Agent identifier")
    role: str = Field(..., description="Agent role/responsibility")
    model_name: str = Field(..., description="Model to use (must exist in endpoints)")
    endpoint_name: str = Field(..., description="Endpoint to route to")
    system_prompt: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_retries: int = Field(default=3)
    timeout: int = Field(default=60)
    parallel_workers: int = Field(default=1, description="Number of parallel instances")


class WorkspaceConfig(BaseModel):
    """Configuration for output workspace."""
    git_repo: str = Field(default="./output", description="Output repo directory")
    artifacts_dir: str = Field(default="artifacts", description="Directory for generated artifacts")
    max_context_tokens: int = Field(default=8000, description="Max tokens to preserve in context")
    auto_commit: bool = Field(default=True, description="Auto-commit changes after each phase")
    review_before_execute: bool = Field(default=True, description="Show diffs before applying changes")


class JarvisConfig(BaseModel):
    """Main configuration for Jarvis orchestrator."""
    version: str = Field(default="1.0.0")
    
    # Endpoints
    endpoints: List[EndpointConfig] = Field(..., description="Local LLM endpoints")
    
    # Agents
    agents: Dict[str, AgentConfig] = Field(..., description="Agent configurations by name")
    
    # Workspace
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    
    # Global settings
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)
    
    @validator('agents')
    def validate_agents(cls, agents, values):
        """Ensure all referenced endpoints and models exist."""
        if 'endpoints' not in values:
            return agents
            
        endpoints = values['endpoints']
        available_models = {}
        
        for endpoint in endpoints:
            for model in endpoint.models:
                available_models[model.name] = endpoint.url
        
        for agent_name, agent in agents.items():
            if agent.model_name not in available_models:
                raise ValueError(f"Agent {agent_name} references unknown model {agent.model_name}")
            
            endpoint = next((e for e in endpoints if e.name == agent.endpoint_name), None)
            if not endpoint:
                raise ValueError(f"Agent {agent_name} references unknown endpoint {agent.endpoint_name}")
        
        return agents


class ConfigManager:
    """Manages loading and caching of Jarvis configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or "config/jarvis_config.yaml")
        self._config: Optional[JarvisConfig] = None
        logger.info(f"ConfigManager initialized with path: {self.config_path}")
    
    def load(self) -> JarvisConfig:
        """Load configuration from YAML file."""
        if self._config is not None:
            return self._config
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        self._config = JarvisConfig(**config_dict)
        logger.info(f"Configuration loaded: {len(self._config.endpoints)} endpoints, {len(self._config.agents)} agents")
        
        return self._config
    
    def get(self) -> JarvisConfig:
        """Get configuration (load if not already loaded)."""
        if self._config is None:
            self.load()
        return self._config
    
    def reload(self) -> JarvisConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load()
    
    def get_agent(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent."""
        config = self.get()
        if agent_name not in config.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        return config.agents[agent_name]
    
    def get_endpoint(self, endpoint_name: str) -> EndpointConfig:
        """Get configuration for a specific endpoint."""
        config = self.get()
        for endpoint in config.endpoints:
            if endpoint.name == endpoint_name:
                return endpoint
        raise ValueError(f"Unknown endpoint: {endpoint_name}")
    
    def get_model_endpoint(self, model_name: str) -> str:
        """Get endpoint URL for a specific model."""
        config = self.get()
        for endpoint in config.endpoints:
            for model in endpoint.models:
                if model.name == model_name:
                    return endpoint.url
        raise ValueError(f"Unknown model: {model_name}")


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get or create global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager
