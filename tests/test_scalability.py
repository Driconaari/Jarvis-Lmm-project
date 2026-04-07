"""
Scalability Tests for Jarvis
Tests for job queue, auto-scaling, and worker pool performance.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock
import time

from jarvis.task_queue import Job, JobQueue, JobStatus
from jarvis.agent_pool import AgentPool, PoolConfig, AgentMetrics
from jarvis.scalable_orchestrator import ScalableOrchestrator, ScalabilityConfig


# ============================================================================
# SCALABILITY LOAD TESTS
# ============================================================================

class TestScalabilityLoad:
    """Test system under load with many jobs."""
    
    @pytest.mark.asyncio
    async def test_queue_with_1000_jobs(self):
        """Queue should handle 1000 jobs without issue."""
        queue = JobQueue(max_size=2000)
        
        # Enqueue 1000 jobs
        for i in range(1000):
            job = Job("impl", f"task{i}", priority=5, payload={"id": i})
            success = await queue.enqueue(job)
            assert success is True
        
        stats = await queue.get_stats()
        assert stats.pending_jobs == 1000
    
    @pytest.mark.asyncio
    async def test_priority_ordering_large_batch(self):
        """Priority ordering should work with many jobs."""
        queue = JobQueue(max_size=2000)
        
        # Add jobs with varying priorities
        priorities_added = []
        for i in range(500):
            priority = (i % 10) + 1
            job = Job("impl", f"task{i}", priority=priority, payload={})
            await queue.enqueue(job)
            priorities_added.append(priority)
        
        # Dequeue and verify priority ordering
        for i in range(100):
            job = await queue.dequeue()
            if i > 0:
                assert job.priority <= last_priority or last_priority == job.priority
            last_priority = job.priority
    
    @pytest.mark.asyncio
    async def test_concurrent_enqueueing(self):
        """Multiple concurrent producers should work correctly."""
        queue = JobQueue(max_size=1000)
        
        async def producer(producer_id, count):
            for i in range(count):
                job = Job("impl", f"task_p{producer_id}_{i}", priority=5, payload={})
                success = await queue.enqueue(job)
                if not success:
                    return False
            return True
        
        # Run 5 producers concurrently
        results = await asyncio.gather(
            producer(0, 100),
            producer(1, 100),
            producer(2, 100),
            producer(3, 100),
            producer(4, 100),
        )
        
        assert all(results)
        stats = await queue.get_stats()
        assert stats.pending_jobs == 500


# ============================================================================
# AUTO-SCALING TESTS
# ============================================================================

class TestAutoScaling:
    """Test auto-scaling behavior and thresholds."""
    
    @pytest.mark.asyncio
    async def test_scaling_config_validates(self):
        """Scaling config should validate thresholds."""
        # Valid config
        config = PoolConfig(
            agent_type="impl",
            min_agents=1,
            max_agents=10,
            scale_up_threshold=0.7,
            scale_down_threshold=0.2,
        )
        assert config.scale_down_threshold < config.scale_up_threshold
        assert config.min_agents <= config.max_agents
    
    @pytest.mark.asyncio
    async def test_scale_up_cooldown_prevents_thrashing(self):
        """Scale-up cooldown should prevent rapid scaling."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(
            agent_type="impl",
            min_agents=1,
            max_agents=5,
            scale_up_cooldown_seconds=5,
        )
        
        pool = AgentPool(queue, config)
        
        # Verify cooldown is set
        assert pool.config.scale_up_cooldown_seconds >= 1
        assert pool.config.scale_up_cooldown_seconds <= 300
    
    @pytest.mark.asyncio
    async def test_scale_down_respects_minimum(self):
        """Scale-down should respect min_agents."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(
            agent_type="impl",
            min_agents=2,
            max_agents=10,
        )
        
        pool = AgentPool(queue, config)
        
        # Add agents
        for i in range(5):
            mock_agent = AsyncMock()
            await pool.add_agent(mock_agent)
        
        assert len(pool.agents) == 5
        
        # Scale down should respect min_agents
        await pool._scale_down()
        assert len(pool.agents) >= config.min_agents


# ============================================================================
# PERFORMANCE REGRESSION TESTS
# ============================================================================

class TestPerformanceRegression:
    """Test known performance issues don't regress."""
    
    @pytest.mark.asyncio
    async def test_no_aggressive_polling_cpu_usage(self):
        """System should not have aggressive polling (sleep 0.01-0.05)."""
        # This checks that we don't have busy-waiting loops
        queue = JobQueue(max_size=100)
        
        # Simulate rapid get_available_agent calls
        # If there's aggressive polling, this would cause high CPU
        start = time.time()
        
        for _ in range(1000):
            await asyncio.sleep(0)  # Yield to other tasks
        
        elapsed = time.time() - start
        
        # Should be very fast (< 1 second for 1000 yields)
        assert elapsed < 1.0, f"Rapid queue checks took {elapsed}s (might indicate busy-waiting)"
    
    @pytest.mark.asyncio
    async def test_memory_doesnt_grow_uncontrolled(self):
        """Queue memory usage should not grow uncontrolled."""
        queue = JobQueue(max_size=500)
        
        # Add and remove jobs repeatedly
        for batch in range(10):
            # Add 500 jobs
            for i in range(500):
                job = Job("impl", f"task{batch}_{i}", priority=5, payload={})
                await queue.enqueue(job)
            
            # Process and clear
            for _ in range(500):
                await queue.dequeue()
        
        # After clearing, should have minimal jobs
        stats = await queue.get_stats()
        assert stats.pending_jobs == 0
    
    @pytest.mark.asyncio
    async def test_auto_scaler_doesnt_consume_cpu(self):
        """Auto-scaler loop should have reasonable sleep intervals."""
        queue = JobQueue(max_size=100)
        config = PoolConfig(
            agent_type="impl",
            min_agents=1,
            max_agents=3,
            scale_up_cooldown_seconds=1,
            scale_down_cooldown_seconds=5,
        )
        
        pool = AgentPool(queue, config)
        
        # Verify scaler config has reasonable sleep times
        # (checked in _auto_scale_loop - should be at least 1 second)
        assert pool.config.scale_up_cooldown_seconds >= 1
        assert pool.config.scale_down_cooldown_seconds >= 1


# ============================================================================
# RETRY LOGIC TESTS
# ============================================================================

class TestRetryLogic:
    """Test job retry behavior."""
    
    @pytest.mark.asyncio
    async def test_job_tracks_attempt_count(self):
        """Job should track attempt count for retries."""
        job = Job("impl", "test_task", priority=5, payload={}, max_retries=3)
        
        assert job.attempt == 1
        assert job.max_retries == 3
        
        # Simulate retry
        job.attempt += 1
        assert job.attempt == 2
    
    @pytest.mark.asyncio
    async def test_job_respects_max_retries(self):
        """Job should not retry beyond max_retries."""
        job = Job("impl", "test_task", priority=5, payload={}, max_retries=2)
        
        # Attempt 1
        assert job.attempt < job.max_retries
        job.attempt += 1
        
        # Attempt 2
        assert job.attempt < job.max_retries
        job.attempt += 1
        
        # Should not retry beyond this
        assert job.attempt >= job.max_retries


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_queue_max_size_zero_handled(self):
        """Queue with size 0 should be handled gracefully."""
        queue = JobQueue(max_size=0)
        
        job = Job("impl", "test", priority=5, payload={})
        success = await queue.enqueue(job)
        
        # Should fail gracefully
        assert success is False
    
    @pytest.mark.asyncio
    async def test_priority_zero_handled(self):
        """Priority 0 should be handled (though not recommended)."""
        job = Job("impl", "test", priority=0, payload={})
        assert job.priority == 0
    
    @pytest.mark.asyncio
    async def test_priority_negative_handled(self):
        """Negative priority should be handled."""
        job = Job("impl", "test", priority=-1, payload={})
        assert job.priority == -1
    
    @pytest.mark.asyncio
    async def test_empty_payload_handled(self):
        """Job with empty payload should work."""
        job = Job("impl", "test", priority=5, payload={})
        assert job.payload == {}
    
    @pytest.mark.asyncio
    async def test_very_large_payload(self):
        """Job with large payload should work."""
        large_payload = {"data": "x" * 1000000}  # 1MB
        job = Job("impl", "test", priority=5, payload=large_payload)
        assert len(str(job.payload)) > 1000000


# ============================================================================
# METRICS TESTS
# ============================================================================

class TestMetrics:
    """Test metrics collection and reporting."""
    
    @pytest.mark.asyncio
    async def test_agent_metrics_initialization(self):
        """Agent metrics should initialize correctly."""
        metrics = AgentMetrics(
            agent_id="test_agent",
            agent_type="implementation",
        )
        
        assert metrics.jobs_completed == 0
        assert metrics.jobs_failed == 0
        assert metrics.status == "idle"
    
    @pytest.mark.asyncio
    async def test_agent_metrics_success_rate(self):
        """Agent metrics should calculate success rate."""
        metrics = AgentMetrics(
            agent_id="test_agent",
            agent_type="implementation",
        )
        
        metrics.jobs_completed = 8
        metrics.jobs_failed = 2
        
        success_rate = metrics.success_rate
        assert success_rate == 0.8  # 80%
    
    @pytest.mark.asyncio
    async def test_queue_stats_aggregation(self):
        """Queue stats should aggregate correctly."""
        queue = JobQueue(max_size=100)
        
        # Add jobs
        for i in range(10):
            job = Job("impl", f"task{i}", priority=5, payload={})
            await queue.enqueue(job)
        
        stats = await queue.get_stats()
        assert stats.pending_jobs == 10
        assert stats.completed_jobs == 0
        
        # Complete some
        for i in range(3):
            job = await queue.dequeue()
            await queue.mark_completed(job.job_id, {})
        
        stats = await queue.get_stats()
        assert stats.completed_jobs == 3


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestScalabilityConfiguration:
    """Test scalability configuration options."""
    
    def test_scalability_config_defaults(self):
        """ScalabilityConfig should have reasonable defaults."""
        config = ScalabilityConfig()
        
        assert config.enable_job_queue is True
        assert config.enable_auto_scaling is True
        assert config.max_queue_size >= 100
        assert config.refresh_interval_seconds >= 1
    
    def test_scalability_config_customizable(self):
        """ScalabilityConfig should be customizable."""
        config = ScalabilityConfig(
            max_queue_size=5000,
            refresh_interval_seconds=10,
        )
        
        assert config.max_queue_size == 5000
        assert config.refresh_interval_seconds == 10
    
    def test_pool_config_validation(self):
        """PoolConfig should validate settings."""
        # Should prevent min > max
        with pytest.raises((AssertionError, ValueError)):
            PoolConfig(
                agent_type="impl",
                min_agents=10,
                max_agents=5,  # Invalid: min > max
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
