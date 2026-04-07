"""
Agent Factory Pattern for Jarvis
Dynamically creates agent instances on demand
"""

from typing import Type, Optional, Dict, Any
from abc import ABC, abstractmethod
from loguru import logger

from jarvis.base_agent import BaseAgent
from jarvis.config import AgentConfig, LLMConfig


class AgentFactory(ABC):
    """Abstract base for agent factories."""
    
    @abstractmethod
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        """Create an agent instance."""
        pass
    
    @abstractmethod
    def get_agent_type(self) -> str:
        """Return the agent type this factory creates."""
        pass


class ArchitectureAgentFactory(AgentFactory):
    """Factory for ArchitectureAgent."""
    
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        from agents.architecture_agent import ArchitectureAgent
        return ArchitectureAgent(llm, config)
    
    def get_agent_type(self) -> str:
        return "architecture"


class TechLeadAgentFactory(AgentFactory):
    """Factory for TechLeadAgent."""
    
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        from agents.tech_lead_agent import TechLeadAgent
        return TechLeadAgent(llm, config)
    
    def get_agent_type(self) -> str:
        return "tech_lead"


class ImplementationAgentFactory(AgentFactory):
    """Factory for ImplementationAgent."""
    
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        from agents.implementation_agent import ImplementationAgent
        return ImplementationAgent(llm, config)
    
    def get_agent_type(self) -> str:
        return "implementation"


class TestingAgentFactory(AgentFactory):
    """Factory for TestingAgent."""
    
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        from agents.testing_agent import TestingAgent
        return TestingAgent(llm, config)
    
    def get_agent_type(self) -> str:
        return "testing"


class DocumentationAgentFactory(AgentFactory):
    """Factory for DocumentationAgent."""
    
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        from agents.documentation_agent import DocumentationAgent
        return DocumentationAgent(llm, config)
    
    def get_agent_type(self) -> str:
        return "documentation"


class DeploymentAgentFactory(AgentFactory):
    """Factory for DeploymentAgent."""
    
    async def create_agent(self, llm: Any, config: AgentConfig) -> BaseAgent:
        from agents.deployment_agent import DeploymentAgent
        return DeploymentAgent(llm, config)
    
    def get_agent_type(self) -> str:
        return "deployment"


class AgentFactoryRegistry:
    """Registry of available agent factories."""
    
    def __init__(self):
        """Initialize with all built-in factories."""
        self._factories: Dict[str, AgentFactory] = {}
        
        # Register built-in factories
        for factory_class in [
            ArchitectureAgentFactory,
            TechLeadAgentFactory,
            ImplementationAgentFactory,
            TestingAgentFactory,
            DocumentationAgentFactory,
            DeploymentAgentFactory,
        ]:
            factory = factory_class()
            self._factories[factory.get_agent_type()] = factory
            logger.debug(f"Registered factory: {factory.get_agent_type()}")
    
    def register_factory(self, agent_type: str, factory: AgentFactory) -> None:
        """Register a custom agent factory."""
        self._factories[agent_type] = factory
        logger.info(f"Registered custom factory for agent type: {agent_type}")
    
    async def create_agent(
        self,
        agent_type: str,
        llm: Any,
        config: AgentConfig
    ) -> Optional[BaseAgent]:
        """Create an agent of the specified type."""
        factory = self._factories.get(agent_type)
        
        if not factory:
            logger.error(f"No factory registered for agent type: {agent_type}")
            return None
        
        try:
            agent = await factory.create_agent(llm, config)
            logger.debug(f"Created {agent_type} agent instance")
            return agent
        
        except Exception as e:
            logger.error(f"Failed to create {agent_type} agent: {e}", exc_info=True)
            return None
    
    def list_factories(self) -> list:
        """List all registered agent types."""
        return list(self._factories.keys())
    
    def has_factory(self, agent_type: str) -> bool:
        """Check if factory is registered for agent type."""
        return agent_type in self._factories


# Global registry instance
_global_registry: Optional[AgentFactoryRegistry] = None


def get_agent_factory_registry() -> AgentFactoryRegistry:
    """Get or create the global agent factory registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentFactoryRegistry()
    return _global_registry


async def create_agent(
    agent_type: str,
    llm: Any,
    config: AgentConfig
) -> Optional[BaseAgent]:
    """
    Convenience function to create an agent using the global registry.
    
    Args:
        agent_type: Type of agent to create (e.g., "implementation")
        llm: LLM instance to use
        config: Agent configuration
    
    Returns:
        Agent instance or None if creation failed
    
    Example:
        ```python
        from jarvis.agent_factory import create_agent
        
        agent = await create_agent("implementation", llm, config)
        if agent:
            result = await agent.execute({"task": "..."})
        ```
    """
    registry = get_agent_factory_registry()
    return await registry.create_agent(agent_type, llm, config)
