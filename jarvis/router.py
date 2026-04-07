"""
Multi-Endpoint LLM Router
Routes requests to appropriate Ollama endpoint based on configuration.
Handles failover, health checks, and load balancing.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
from loguru import logger
from langchain_community.llms import Ollama
from langchain_core.callbacks import CallbackManager

from jarvis.config import ConfigManager, EndpointConfig, OllamaModelConfig


@dataclass
class EndpointHealth:
    """Health status of an LLM endpoint."""
    endpoint_name: str
    is_healthy: bool
    last_check: datetime
    response_time_ms: float = 0.0
    error_message: Optional[str] = None


class MultiEndpointRouter:
    """Routes LLM requests to appropriate local Ollama endpoints."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get()
        self.config_manager = config_manager
        self._health_cache: Dict[str, EndpointHealth] = {}
        self._llm_cache: Dict[str, Ollama] = {}
        logger.info(f"MultiEndpointRouter initialized with {len(self.config.endpoints)} endpoints")
    
    async def health_check(self, endpoint: EndpointConfig) -> EndpointHealth:
        """Check if an endpoint is healthy."""
        cache_key = endpoint.name
        
        # Check if cache is still valid
        if cache_key in self._health_cache:
            cached = self._health_cache[cache_key]
            age = (datetime.now() - cached.last_check).total_seconds()
            if age < endpoint.healthcheck_interval:
                return cached
        
        # Perform actual health check
        health = EndpointHealth(
            endpoint_name=endpoint.name,
            is_healthy=False,
            last_check=datetime.now()
        )
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient(timeout=endpoint.timeout) as client:
                response = await client.get(f"{endpoint.url}/api/tags")
                health.response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    health.is_healthy = True
                    logger.debug(f"✓ Endpoint {endpoint.name} is healthy ({health.response_time_ms:.1f}ms)")
                else:
                    health.error_message = f"HTTP {response.status_code}"
                    logger.warning(f"✗ Endpoint {endpoint.name} returned {response.status_code}")
        
        except Exception as e:
            health.error_message = str(e)
            logger.warning(f"✗ Endpoint {endpoint.name} health check failed: {e}")
        
        self._health_cache[cache_key] = health
        return health
    
    async def get_healthy_endpoint(self, preferred_endpoint_name: Optional[str] = None) -> Optional[EndpointConfig]:
        """Get a healthy endpoint, with preference for specified endpoint."""
        endpoints = self.config.endpoints
        
        # Check all endpoints in parallel
        health_checks = await asyncio.gather(
            *[self.health_check(ep) for ep in endpoints],
            return_exceptions=True
        )
        
        # Prefer specified endpoint if healthy
        if preferred_endpoint_name:
            for ep, health in zip(endpoints, health_checks):
                if ep.name == preferred_endpoint_name and isinstance(health, EndpointHealth) and health.is_healthy:
                    return ep
        
        # Fall back to any healthy endpoint
        for ep, health in zip(endpoints, health_checks):
            if isinstance(health, EndpointHealth) and health.is_healthy:
                return ep
        
        # If nothing is healthy, return first endpoint anyway (will fail gracefully)
        logger.error("No healthy endpoints found!")
        return endpoints[0] if endpoints else None
    
    def get_llm(self, model_name: str, endpoint_url: str, **kwargs) -> Ollama:
        """Get or create an Ollama LLM instance."""
        cache_key = f"{endpoint_url}:{model_name}"
        
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        try:
            llm = Ollama(
                base_url=endpoint_url,
                model=model_name,
                **kwargs
            )
            self._llm_cache[cache_key] = llm
            logger.debug(f"Created LLM instance: {model_name} on {endpoint_url}")
            return llm
        
        except Exception as e:
            logger.error(f"Failed to create LLM instance: {e}")
            raise
    
    def get_routed_llm(self, agent_name: str, **kwargs) -> tuple[Ollama, EndpointConfig]:
        """Get an LLM instance routed based on agent configuration."""
        agent_config = self.config_manager.get_agent(agent_name)
        endpoint_config = self.config_manager.get_endpoint(agent_config.endpoint_name)
        
        # Find the model config
        model_config = next(
            (m for m in endpoint_config.models if m.name == agent_config.model_name),
            None
        )
        
        if not model_config:
            raise ValueError(f"Model {agent_config.model_name} not found on endpoint {agent_config.endpoint_name}")
        
        # Merge configurations
        llm_kwargs = {
            'temperature': agent_config.temperature or model_config.temperature,
            'top_p': model_config.top_p,
            **kwargs
        }
        
        llm = self.get_llm(agent_config.model_name, endpoint_config.url, **llm_kwargs)
        return llm, endpoint_config
    
    async def parallel_route(
        self,
        tasks: List[tuple[str, str, Dict[str, Any]]],  # [(agent, task_id, kwargs), ...]
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Route multiple tasks in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def execute_task(agent_name: str, task_id: str, kwargs: Dict[str, Any]):
            async with semaphore:
                try:
                    # This is a placeholder - actual execution happens in agents
                    logger.info(f"Routing task {task_id} to agent {agent_name}")
                    return {"task_id": task_id, "status": "routed"}
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    return {"task_id": task_id, "status": "failed", "error": str(e)}
        
        coroutines = [execute_task(agent, tid, kwargs) for agent, tid, kwargs in tasks]
        results_list = await asyncio.gather(*coroutines, return_exceptions=True)
        
        for result in results_list:
            if isinstance(result, Exception):
                logger.error(f"Task execution failed: {result}")
            else:
                results[result["task_id"]] = result
        
        return results
    
    def clear_caches(self):
        """Clear internal caches."""
        self._health_cache.clear()
        self._llm_cache.clear()
        logger.info("Router caches cleared")
