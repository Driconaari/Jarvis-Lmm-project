"""Jarvis Multi-LLM Orchestrator Package"""

__version__ = "1.0.0"
__author__ = "Jarvis Team"
__description__ = "Local multi-LLM collaborative workflow orchestrator"

from jarvis.config import ConfigManager, get_config_manager
from jarvis.router import MultiEndpointRouter
from jarvis.orchestrator import Orchestrator, WorkflowContext, ArtifactManager
from jarvis.base_agent import BaseAgent, AgentOutput

__all__ = [
    "ConfigManager",
    "get_config_manager",
    "MultiEndpointRouter",
    "Orchestrator",
    "WorkflowContext",
    "ArtifactManager",
    "BaseAgent",
    "AgentOutput",
]
