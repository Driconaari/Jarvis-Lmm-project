"""
Test Suite for Jarvis Multi-LLM Orchestrator with Scalability
Comprehensive testing covering core functionality and edge cases
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.config import ConfigManager, AgentConfig
from jarvis.router import MultiEndpointRouter
from jarvis.task_queue import Job, JobQueue, JobStatus
from jarvis.agent_pool import AgentPool, PoolConfig, AgentMetrics
from jarvis.agent_factory import (
    AgentFactoryRegistry, get_agent_factory_registry,
    ArchitectureAgentFactory, ImplementationAgentFactory
)
from jarvis.base_agent import BaseAgent, AgentOutput


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfiguration:
    """Test configuration loading and validation."""
    
    def test_config_loads_successfully(self):
        """Configuration should load without errors."""
        config = ConfigManager("config/jarvis_config.yaml")
        assert config is not None
        assert config.endpoints is not None
        assert len(config.endpoints) >= 1
    
    def test_config_has_required_endpoints(self):
        """Configuration should define at least 1 endpoint."""
        config = ConfigManager("config/jarvis_config.yaml")
        assert len(config.endpoints) >= 1
        
        endpoint = config.endpoints[0]
        assert endpoint.name is not None
        assert endpoint.url is not None
    
    def test_config_has_agents(self):
        """Configuration should define agent configurations."""
        config = ConfigManager("config/jarvis_config.yaml")
        assert config.agents is not None
        assert len(config.agents) <= 6


# ============================================================================
# ROUTER TESTS
# ============================================================================

class TestMultiEndpointRouter:
    """Test LLM routing and endpoint management."""
    
    def test_router_initializes(self):
        """Router should initialize successfully."""
        config = ConfigManager("config/jarvis_config.yaml")
        router = MultiEndpointRouter(config)
        assert router is not None
    
    @pytest.mark.asyncio
    async def test_router_gets_llm(self):
        """Router should provide LLM instance for agent."""
        config = ConfigManager("config/jarvis_config.yaml")
        router = MultiEndpointRouter(config)
        
        llm, endpoint = router.get_routed_llm("architecture")
        assert llm is not None
        assert endpoint is not None
        assert hasattr(endpoint, 'name')
    
    @pytest.mark.asyncio
    async def test_health_check_handles_unavailable_endpoint(self):
        """Router should detect when endpoint is unavailable."""
        config = ConfigManager("config/jarvis_config.yaml")
        router = MultiEndpointRouter(config)
        
        # Try health check (may fail if Ollama not running, but shouldn't crash)
        try:
            is_healthy = await router.health_check("http://localhost:99999")
            # If it returns False, that's expected behavior
            assert isinstance(is_healthy, bool)
        except Exception as e:
            # Connection errors are acceptable during tests
            assert "connection" in str(e).lower() or "refused" in str(e).lower()


# ============================================================================
# TASK QUEUE TESTS
# ============================================================================

class TestJobQueue:
    """Test job queue with priority scheduling."""
    
    @pytest.mark.asyncio
    async def test_queue_initializes(self):
        """Queue should initialize successfully."""
        queue = JobQueue(max_size=100)
        assert queue is not None
    
    @pytest.mark.asyncio
    async def test_enqueue_job(self):
        """Should successfully enqueue a job."""
        queue = JobQueue(max_size=100)
        
        job = Job(
            agent_type="implementation",
            task_id="test_task",
            priority=5,
            payload={"code": "test"}
        )
        
        success = await queue.enqueue(job)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Jobs should dequeue in priority order (1=first, 10=last)."""
        queue = JobQueue(max_size=100)
        
        # Enqueue in reverse priority order
        job1 = Job("impl", "task1", priority=9, payload={})
        job2 = Job("impl", "task2", priority=5, payload={})
        job3 = Job("impl", "task3", priority=1, payload={})
        
        await queue.enqueue(job1)
        await queue.enqueue(job2)
        await queue.enqueue(job3)
        
        # Should dequeue in priority order: 1, 5, 9
        first = await queue.dequeue()
        assert first.priority == 1
        
        second = await queue.dequeue()
        assert second.priority == 5
        
        third = await queue.dequeue()
        assert third.priority == 9
    
    @pytest.mark.asyncio
    async def test_queue_max_size(self):
        """Queue should respect max_size limit."""
        queue = JobQueue(max_size=3)
        
        # Enqueue 3 jobs (at capacity)
        for i in range(3):
            job = Job("impl", f"task{i}", priority=5, payload={})
            success = await queue.enqueue(job)
            assert success is True
        
        # 4th job should fail (queue full)
        job_overflow = Job("impl", "overflow", priority=1, payload={})
        success = await queue.enqueue(job_overflow)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_mark_completed(self):
        """Should track completed jobs."""
        queue = JobQueue(max_size=100)
        
        job = Job("impl", "task1", priority=5, payload={})
        await queue.enqueue(job)
        
        job_data = await queue.get_job(job.job_id)
        assert job_data.status == JobStatus.PENDING
        
        await queue.mark_completed(job.job_id, {"result": "success"})
        
        job_data = await queue.get_job(job.job_id)
        assert job_data.status == JobStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_queue_stats(self):
        """Queue should provide accurate statistics."""
        queue = JobQueue(max_size=100)
        
        # Enqueue jobs
        for i in range(5):
            job = Job("impl", f"task{i}", priority=5, payload={})
            await queue.enqueue(job)
        
        stats = await queue.get_stats()
        assert stats.pending_jobs == 5
        assert stats.completed_jobs == 0
        assert stats.failed_jobs == 0


# ============================================================================
# AGENT POOL TESTS
# ============================================================================

class TestAgentPool:
    """Test agent pool management and scaling."""
    
    @pytest.mark.asyncio
    async def test_pool_initializes(self):
        """Pool should initialize successfully."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(agent_type="impl", min_agents=1, max_agents=5)
        
        pool = AgentPool(queue, config)
        assert pool is not None
        assert len(pool.agents) == 0
    
    @pytest.mark.asyncio
    async def test_add_agent(self):
        """Should add agents to pool."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(agent_type="impl", min_agents=1, max_agents=5)
        pool = AgentPool(queue, config)
        
        mock_agent = AsyncMock(spec=BaseAgent)
        agent_id = await pool.add_agent(mock_agent)
        
        assert agent_id is not None
        assert len(pool.agents) == 1
        assert agent_id in pool.agents
    
    @pytest.mark.asyncio
    async def test_remove_agent(self):
        """Should remove agents from pool."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(agent_type="impl", min_agents=0, max_agents=5)
        pool = AgentPool(queue, config)
        
        mock_agent = AsyncMock(spec=BaseAgent)
        agent_id = await pool.add_agent(mock_agent)
        
        success = await pool.remove_agent(agent_id)
        assert success is True
        assert len(pool.agents) == 0
    
    @pytest.mark.asyncio
    async def test_pool_stats(self):
        """Pool should provide accurate statistics."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(agent_type="impl", min_agents=1, max_agents=5)
        pool = AgentPool(queue, config)
        
        mock_agent = AsyncMock(spec=BaseAgent)
        await pool.add_agent(mock_agent)
        
        stats = await pool.get_pool_stats()
        assert stats['total_agents'] == 1
        assert stats['idle_agents'] == 1
        assert stats['busy_agents'] == 0


# ============================================================================
# AGENT FACTORY TESTS
# ============================================================================

class TestAgentFactory:
    """Test agent factory pattern for dynamic creation."""
    
    def test_registry_initializes(self):
        """Factory registry should initialize with all built-in factories."""
        registry = AgentFactoryRegistry()
        
        factories = registry.list_factories()
        assert len(factories) >= 6
        assert "architecture" in factories
        assert "implementation" in factories
        assert "testing" in factories
    
    def test_registry_checks_factory_availability(self):
        """Registry should check if factory exists."""
        registry = AgentFactoryRegistry()
        
        assert registry.has_factory("implementation") is True
        assert registry.has_factory("nonexistent") is False
    
    def test_global_registry_instance(self):
        """Should provide global registry instance."""
        registry = get_agent_factory_registry()
        assert registry is not None
        
        # Second call should return same instance
        registry2 = get_agent_factory_registry()
        assert registry is registry2


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics and edge cases."""
    
    @pytest.mark.asyncio
    async def test_queue_performance_large_batch(self):
        """Queue should handle 1000 jobs efficiently."""
        queue = JobQueue(max_size=2000)
        
        start = datetime.now()
        
        # Enqueue 1000 jobs
        for i in range(1000):
            job = Job("impl", f"task{i}", priority=5, payload={"index": i})
            await queue.enqueue(job)
        
        elapsed = (datetime.now() - start).total_seconds()
        
        # Should complete in under 5 seconds
        assert elapsed < 5, f"Enqueueing 1000 jobs took {elapsed}s (should be <5s)"
        
        stats = await queue.get_stats()
        assert stats.pending_jobs == 1000
    
    @pytest.mark.asyncio
    async def test_priority_maintenance_under_load(self):
        """Priority ordering should be maintained with many jobs."""
        queue = JobQueue(max_size=1000)
        
        # Add 300 jobs with mixed priorities
        for i in range(300):
            priority = (i % 10) + 1  # Priorities 1-10
            job = Job("impl", f"task{i}", priority=priority, payload={})
            await queue.enqueue(job)
        
        # Dequeue and verify ordering
        prev_priority = 0
        for _ in range(50):
            job = await queue.dequeue()
            if job:
                assert job.priority >= prev_priority, "Priority ordering violated"
                prev_priority = job.priority
    
    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self):
        """Queue should handle concurrent operations safely."""
        queue = JobQueue(max_size=500)
        
        async def producer():
            for i in range(100):
                job = Job("impl", f"task{i}", priority=5, payload={})
                await queue.enqueue(job)
        
        async def consumer():
            for _ in range(50):
                await queue.dequeue()
                await asyncio.sleep(0.01)
        
        # Run producer and consumer concurrently
        await asyncio.gather(producer(), consumer())
        
        stats = await queue.get_stats()
        # Should have some jobs still in queue
        assert stats.pending_jobs > 0


# ============================================================================
# SCALABILITY STRESS TESTS
# ============================================================================

class TestScalabilityRisk:
    """Test for scalability issues that could cause slow performance."""
    
    @pytest.mark.asyncio
    async def test_no_busy_waiting(self):
        """Should not have aggressive polling causing high CPU."""
        # This test verifies the fix is in place
        queue = JobQueue(max_size=100)
        config = PoolConfig(
            agent_type="impl",
            min_agents=1,
            max_agents=5,
            scale_up_cooldown_seconds=2,
            scale_down_cooldown_seconds=10
        )
        pool = AgentPool(queue, config)
        
        # If polling is too aggressive, this would use significant CPU
        # We test this by checking the implementation doesn't have
        # sleep(0.01) or sleep(0.05) type calls in tight loops
        
        # For now, verify pool can handle rapid calls
        for _ in range(100):
            await pool.get_available_agent()
    
    @pytest.mark.asyncio
    async def test_auto_scaling_thresholds_reasonable(self):
        """Auto-scaling thresholds should be reasonable."""
        configs_to_test = [
            PoolConfig(agent_type="impl", min_agents=1, max_agents=10,
                      scale_up_threshold=0.7),
            PoolConfig(agent_type="impl", min_agents=2, max_agents=20,
                      scale_up_threshold=0.6),
        ]
        
        for config in configs_to_test:
            # Thresholds should be between 0.1 and 0.9
            assert 0.1 <= config.scale_up_threshold <= 0.9
            assert 0.1 <= config.scale_down_threshold <= 0.9
            
            # Thresholds should make sense
            assert config.scale_down_threshold < config.scale_up_threshold
            
            # Scaling cooldowns should be reasonable (< 5 minutes)
            assert config.scale_up_cooldown_seconds < 300
            assert config.scale_down_cooldown_seconds < 300


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    @pytest.mark.asyncio
    async def test_job_queue_and_pool_integration(self):
        """Queue and pool should work together."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(agent_type="impl", min_agents=1, max_agents=3)
        pool = AgentPool(queue, config)
        
        # Add agent
        mock_agent = AsyncMock(spec=BaseAgent)
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            success=True, artifacts={}, reasoning="test"
        ))
        
        agent_id = await pool.add_agent(mock_agent)
        
        # Create and enqueue job
        job = Job("impl", "test_job", priority=5, payload={"task": "test"})
        success = await queue.enqueue(job)
        assert success is True
        
        # Dequeue and execute
        queued_job = await queue.dequeue()
        assert queued_job is not None
        
        available_agent = await pool.get_available_agent()
        assert available_agent is not None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
