"""
Scalable Orchestrator with Auto-Scaling Capabilities
Enhanced orchestrator supporting job queues and dynamic agent pools.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from loguru import logger

from jarvis.orchestrator import Orchestrator, WorkflowContext
from jarvis.task_queue import Job, JobQueue, JobStatus
from jarvis.agent_pool import AgentPool, PoolConfig
from jarvis.config import ConfigManager
from jarvis.agent_factory import get_agent_factory_registry


@dataclass
class ScalabilityConfig:
    """Configuration for the scalable orchestrator."""
    enable_job_queue: bool = True
    enable_auto_scaling: bool = True
    max_queue_size: int = 1000
    refresh_interval_seconds: int = 5
    
    # Per-agent-type scaling
    implementation_pool_config: PoolConfig = None
    default_pool_config: PoolConfig = None
    
    def __post_init__(self):
        """Initialize default configs."""
        if self.implementation_pool_config is None:
            self.implementation_pool_config = PoolConfig(
                agent_type="implementation",
                min_agents=2,
                max_agents=10,
                scale_up_threshold=0.7,
                scale_down_threshold=0.2,
            )
        if self.default_pool_config is None:
            self.default_pool_config = PoolConfig(
                agent_type="default",
                min_agents=1,
                max_agents=5,
                scale_up_threshold=0.75,
                scale_down_threshold=0.15,
            )


class ScalableOrchestrator(Orchestrator):
    """Enhanced orchestrator with job queue and auto-scaling."""
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 scalability_config: Optional[ScalabilityConfig] = None):
        super().__init__(config_path)
        
        self.scalability_config = scalability_config or ScalabilityConfig()
        self.job_queue = JobQueue(self.scalability_config.max_queue_size)
        self.agent_pools: Dict[str, AgentPool] = {}
        self._worker_tasks: List[asyncio.Task] = []
        self._stats_task: Optional[asyncio.Task] = None
        self._job_available_event = asyncio.Event()  # Signal when job is available
        
        logger.info("ScalableOrchestrator initialized with auto-scaling")
    
    def setup_agent_pool(self, agent_type: str, pool_config: Optional[PoolConfig] = None):
        """Setup an agent pool for specific agent type."""
        if pool_config is None:
            # Use default config based on agent type
            if agent_type == "implementation":
                pool_config = self.scalability_config.implementation_pool_config
            else:
                pool_config = self.scalability_config.default_pool_config
        
        pool = AgentPool(self.job_queue, pool_config)
        self.agent_pools[agent_type] = pool
        logger.info(f"Agent pool setup for {agent_type}")
    
    async def submit_job(self, 
                        agent_type: str,
                        task_data: Dict[str, Any],
                        priority: int = 5,
                        max_retries: int = 3) -> Job:
        """Submit a new job to the queue."""
        job = Job(
            agent_type=agent_type,
            task_id=task_data.get("task_id", "unknown"),
            priority=priority,
            payload=task_data,
            max_retries=max_retries,
        )
        
        success = await self.job_queue.enqueue(job)
        if success:
            logger.info(f"Job {job.job_id} submitted for {agent_type} (priority: {priority})")
            # Signal workers that a new job is available
            self._job_available_event.set()
        else:
            logger.error(f"Failed to enqueue job {job.job_id} (queue full)")
        
        return job
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        job = await self.job_queue.get_job(job_id)
        if job:
            return job.to_dict()
        return None
    
    async def start_worker_pool(self, agent_type: str, num_workers: int = 2):
        """Start worker processes for an agent type."""
        if agent_type not in self.agent_pools:
            self.setup_agent_pool(agent_type)
        
        pool = self.agent_pools[agent_type]
        
        # Get agent configuration and LLM routing
        agent_config = self.config.agents.get(agent_type)
        if not agent_config:
            logger.error(f"No configuration found for agent type: {agent_type}")
            return
        
        # Get LLM routed for this agent
        llm, endpoint = self.router.get_routed_llm(agent_type)
        logger.debug(f"Agent {agent_type} routed to {endpoint.name}")
        
        # Get factory registry
        factory_registry = get_agent_factory_registry()
        
        # Create initial worker agents using factory
        for i in range(num_workers):
            try:
                # Create new agent instance dynamically
                agent = await factory_registry.create_agent(agent_type, llm, agent_config)
                
                if agent:
                    agent_id = await pool.add_agent(agent)
                    logger.info(f"Worker {i+1}/{num_workers} ({agent_id}) spawned for {agent_type}")
                else:
                    logger.error(f"Failed to create agent for worker {i+1}/{num_workers}")
            
            except Exception as e:
                logger.error(f"Error spawning worker {i+1}/{num_workers}: {e}", exc_info=True)
        
        # Start auto-scaler
        if self.scalability_config.enable_auto_scaling:
            await pool.start_auto_scaler(
                llm=llm,
                agent_config=agent_config,
                factory_registry=factory_registry,
                agent_type=agent_type
            )
        
        # Start worker loop
        worker_task = asyncio.create_task(
            self._worker_loop(agent_type, pool)
        )
        self._worker_tasks.append(worker_task)
        
        logger.info(f"Worker pool started for {agent_type} with {num_workers} workers")
    
    async def _worker_loop(self, agent_type: str, pool: AgentPool):
        """Main loop for worker processes."""
        logger.info(f"Worker loop started for {agent_type}")
        
        while True:
            try:
                # Get next job from queue (with timeout to avoid blocking forever)
                job = await asyncio.wait_for(
                    self.job_queue.dequeue(),
                    timeout=5.0  # Wake up every 5 seconds max
                )
                
                if job and job.agent_type == agent_type:
                    # Get available agent
                    agent_id = await pool.get_available_agent()
                    
                    if agent_id:
                        # Execute job
                        success = await pool.execute_job(job, agent_id)
                        
                        if not success and job.attempt < job.max_retries:
                            # Re-queue for retry
                            job.attempt += 1
                            job.status = JobStatus.RETRYING
                            await self.job_queue.enqueue(job)
                            logger.info(f"Job {job.job_id} requeued (attempt {job.attempt})")
                    else:
                        # Requeue - no available agents (back of queue)
                        await self.job_queue.enqueue(job)
                        await asyncio.sleep(0.5)  # Brief pause before retrying
                else:
                    if job:
                        await self.job_queue.enqueue(job)
            
            except asyncio.TimeoutError:
                # Timeout is normal - means no jobs available
                # Check if we should exit
                continue
            
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(2)  # Back off on errors
    
    async def start_stats_monitor(self):
        """Start periodic stats reporting."""
        if self._stats_task and not self._stats_task.done():
            logger.warning("Stats monitor already running")
            return
        
        self._stats_task = asyncio.create_task(self._stats_loop())
    
    async def _stats_loop(self):
        """Loop that periodically reports stats."""
        while True:
            try:
                await asyncio.sleep(self.scalability_config.refresh_interval_seconds)
                
                logger.info("=" * 60)
                logger.info("SCALABLE ORCHESTRATOR STATS")
                logger.info("=" * 60)
                
                queue_stats = await self.job_queue.get_stats()
                logger.info(f"Queue: {queue_stats.pending_jobs} pending, "
                          f"{queue_stats.running_jobs} running, "
                          f"{queue_stats.completed_jobs} completed, "
                          f"{queue_stats.failed_jobs} failed")
                logger.info(f"Performance: avg {queue_stats.average_job_time:.2f}s/job, "
                          f"{queue_stats.throughput_jobs_per_minute:.2f} jobs/min")
                
                for agent_type, pool in self.agent_pools.items():
                    stats = await pool.get_pool_stats()
                    logger.info(f"{agent_type}: {stats['total_agents']} agents "
                              f"({stats['idle_agents']} idle, {stats['busy_agents']} busy)")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats loop error: {e}")
    
    async def stop_all_workers(self):
        """Gracefully stop all worker pools."""
        logger.info("Stopping all worker pools...")
        
        # Stop auto-scalers
        for pool in self.agent_pools.values():
            await pool.stop_auto_scaler()
        
        # Stop worker tasks
        for task in self._worker_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop stats monitor
        if self._stats_task:
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass
        
        logger.info("All worker pools stopped")
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        queue_stats = await self.job_queue.get_stats()
        pools_stats = {}
        
        for agent_type, pool in self.agent_pools.items():
            pools_stats[agent_type] = await pool.get_pool_stats()
        
        return {
            "timestamp": asyncio.get_event_loop().time(),
            "queue": {
                "pending": queue_stats.pending_jobs,
                "running": queue_stats.running_jobs,
                "completed": queue_stats.completed_jobs,
                "failed": queue_stats.failed_jobs,
                "max_depth": queue_stats.max_queue_depth,
                "average_job_time": queue_stats.average_job_time,
                "throughput_jobs_per_minute": queue_stats.throughput_jobs_per_minute,
            },
            "pools": pools_stats,
        }
