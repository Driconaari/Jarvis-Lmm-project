"""
Agent Pool Management with Auto-Scaling
Maintains pool of agents and dynamically scales based on workload.
"""

import asyncio
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

from jarvis.task_queue import Job, JobQueue, QueueStats
from jarvis.base_agent import BaseAgent


@dataclass
class PoolConfig:
    """Configuration for agent pool auto-scaling."""
    agent_type: str = ""
    min_agents: int = 1
    max_agents: int = 10
    scale_up_threshold: float = 0.7  # Queue filling 70% triggers scale-up
    scale_down_threshold: float = 0.2  # Queue below 20% triggers scale-down
    scale_up_cooldown_seconds: int = 5
    scale_down_cooldown_seconds: int = 30
    idle_timeout_seconds: int = 60  # Auto-shutdown idle agents
    metrics_window_seconds: int = 60  # Window for performance metrics


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    agent_id: str
    agent_type: str
    created_at: datetime = field(default_factory=datetime.now)
    jobs_completed: int = 0
    jobs_failed: int = 0
    total_processing_time: float = 0.0
    average_job_time: float = 0.0
    last_job_time: datetime = field(default_factory=datetime.now)
    status: str = "idle"  # idle, processing
    
    @property
    def is_idle(self, timeout_seconds: int = 60) -> bool:
        """Check if agent has been idle too long."""
        return (datetime.now() - self.last_job_time).total_seconds() > timeout_seconds
    
    @property
    def success_rate(self) -> float:
        """Job success rate."""
        total = self.jobs_completed + self.jobs_failed
        return self.jobs_completed / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "average_job_time": self.average_job_time,
            "success_rate": f"{self.success_rate * 100:.1f}%",
            "status": self.status,
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds(),
        }


class AgentPool:
    """Pool of agents with auto-scaling capabilities."""
    
    def __init__(self, job_queue: JobQueue, pool_config: PoolConfig):
        self.config = pool_config
        self.job_queue = job_queue
        self.agents: Dict[str, BaseAgent] = {}
        self.metrics: Dict[str, AgentMetrics] = {}
        self.agent_locks: Dict[str, asyncio.Lock] = {}
        self._scaler_task: Optional[asyncio.Task] = None
        self._last_scale_up_time = datetime.now()
        self._last_scale_down_time = datetime.now()
        self._running_agents = set()
        
        # For dynamic agent creation
        self._llm = None
        self._agent_config = None
        self._factory_registry = None
        self._agent_type = None
        
        logger.info(f"AgentPool created for {pool_config.agent_type} "
                   f"(min: {pool_config.min_agents}, max: {pool_config.max_agents})")
    
    async def add_agent(self, agent: BaseAgent) -> str:
        """Add an agent to the pool."""
        agent_id = f"{self.config.agent_type}_{len(self.agents)}"
        self.agents[agent_id] = agent
        self.metrics[agent_id] = AgentMetrics(
            agent_id=agent_id,
            agent_type=self.config.agent_type
        )
        self.agent_locks[agent_id] = asyncio.Lock()
        logger.info(f"Agent {agent_id} added (pool now has {len(self.agents)} agents)")
        return agent_id
    
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from pool."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            if agent_id in self.metrics:
                del self.metrics[agent_id]
            if agent_id in self.agent_locks:
                del self.agent_locks[agent_id]
            self._running_agents.discard(agent_id)
            logger.info(f"Agent {agent_id} removed (pool now has {len(self.agents)} agents)")
            return True
        return False
    
    async def get_available_agent(self) -> Optional[str]:
        """Get next available agent for processing."""
        # Prefer idle agents
        for agent_id, agent in self.agents.items():
            if agent_id not in self._running_agents:
                return agent_id
        return None
    
    async def execute_job(self, job: Job, agent_id: str) -> bool:
        """Execute a job on specified agent."""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not found in pool")
            return False
        
        agent = self.agents[agent_id]
        metrics = self.metrics[agent_id]
        
        async with self.agent_locks[agent_id]:
            try:
                self._running_agents.add(agent_id)
                metrics.status = "processing"
                
                # Execute with timeout
                start_time = datetime.now()
                result = await asyncio.wait_for(
                    agent.execute({"job_id": job.job_id, **job.payload}),
                    timeout=job.timeout_seconds
                )
                
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Update metrics
                metrics.jobs_completed += 1
                metrics.total_processing_time += elapsed
                metrics.average_job_time = metrics.total_processing_time / metrics.jobs_completed
                metrics.last_job_time = datetime.now()
                metrics.status = "idle"
                
                # Mark job completed
                await self.job_queue.mark_completed(job.job_id, result)
                logger.debug(f"Agent {agent_id} completed job {job.job_id} in {elapsed:.2f}s")
                
                return True
            
            except asyncio.TimeoutError:
                metrics.jobs_failed += 1
                metrics.status = "idle"
                error = f"Job timeout after {job.timeout_seconds}s"
                await self.job_queue.mark_failed(job.job_id, error)
                logger.error(f"Agent {agent_id} job {job.job_id} timeout: {error}")
                return False
            
            except Exception as e:
                metrics.jobs_failed += 1
                metrics.status = "idle"
                error = f"Job error: {str(e)}"
                await self.job_queue.mark_failed(job.job_id, error)
                logger.error(f"Agent {agent_id} job {job.job_id} failed: {e}")
                return False
            
            finally:
                self._running_agents.discard(agent_id)
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        queue_stats = await self.job_queue.get_stats()
        agents_metrics = [self.metrics[aid].to_dict() for aid in self.agents]
        
        return {
            "agent_type": self.config.agent_type,
            "total_agents": len(self.agents),
            "idle_agents": len(self.agents) - len(self._running_agents),
            "busy_agents": len(self._running_agents),
            "queue_stats": {
                "pending": queue_stats.pending_jobs,
                "running": queue_stats.running_jobs,
                "completed": queue_stats.completed_jobs,
                "failed": queue_stats.failed_jobs,
                "average_job_time": f"{queue_stats.average_job_time:.2f}s",
                "throughput_per_minute": f"{queue_stats.throughput_jobs_per_minute:.2f}",
            },
            "agents_metrics": agents_metrics,
        }
    
    async def start_auto_scaler(self, llm: Any = None, agent_config: Any = None, 
                               factory_registry: Any = None, agent_type: str = None):
        """Start the auto-scaling monitor with support for dynamic agent creation."""
        if self._scaler_task and not self._scaler_task.done():
            logger.warning("Auto-scaler already running")
            return
        
        # Store parameters for dynamic agent creation
        self._llm = llm
        self._agent_config = agent_config
        self._factory_registry = factory_registry
        self._agent_type = agent_type or self.config.agent_type
        
        self._scaler_task = asyncio.create_task(self._auto_scale_loop())
        logger.info(f"Auto-scaler started for {self.config.agent_type} "
                   f"(dynamic creation: {'enabled' if factory_registry else 'disabled'})")
    
    async def stop_auto_scaler(self):
        """Stop the auto-scaling monitor."""
        if self._scaler_task:
            self._scaler_task.cancel()
            try:
                await self._scaler_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Auto-scaler stopped for {self.config.agent_type}")
    
    async def _auto_scale_loop(self):
        """Loop that monitors and adjusts pool size."""
        while True:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds
                
                queue_stats = await self.job_queue.get_stats()
                current_agents = len(self.agents)
                
                # Calculate queue utilization
                queue_util = queue_stats.pending_jobs / max(1, current_agents * 5)
                
                logger.debug(f"{self.config.agent_type}: {current_agents} agents, "
                           f"{queue_stats.pending_jobs} pending jobs, "
                           f"utilization: {queue_util:.1%}")
                
                # Scale up if queue too full
                if queue_util >= self.config.scale_up_threshold:
                    time_since_scale_up = (
                        datetime.now() - self._last_scale_up_time
                    ).total_seconds()
                    
                    if (time_since_scale_up >= self.config.scale_up_cooldown_seconds and
                        current_agents < self.config.max_agents):
                        await self._scale_up()
                        self._last_scale_up_time = datetime.now()
                
                # Scale down if queue too empty
                elif queue_util <= self.config.scale_down_threshold:
                    time_since_scale_down = (
                        datetime.now() - self._last_scale_down_time
                    ).total_seconds()
                    
                    if (time_since_scale_down >= self.config.scale_down_cooldown_seconds and
                        current_agents > self.config.min_agents):
                        await self._scale_down()
                        self._last_scale_down_time = datetime.now()
                
                # Remove idle agents
                await self._remove_idle_agents()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scaler error: {e}")
    
    async def _scale_up(self):
        """Add a new agent to the pool."""
        current = len(self.agents)
        if current < self.config.max_agents:
            # Try to create new agent using factory
            if self._factory_registry and self._llm and self._agent_config and self._agent_type:
                try:
                    # Create new agent instance
                    agent = await self._factory_registry.create_agent(
                        self._agent_type,
                        self._llm,
                        self._agent_config
                    )
                    
                    if agent:
                        agent_id = await self.add_agent(agent)
                        logger.info(f"Scaled up {self.config.agent_type}: spawned new agent {agent_id}")
                        return
                
                except Exception as e:
                    logger.error(f"Failed to scale up agent: {e}")
            
            # Fallback: log warning if no factory available
            logger.warning(f"Scale up triggered for {self.config.agent_type}, "
                          f"but no agent factory provided. Manual scaling required.")
    
    async def _scale_down(self):
        """Remove an idle agent from the pool."""
        idle_agents = [aid for aid in self.agents 
                      if aid not in self._running_agents]
        
        if idle_agents and len(self.agents) > self.config.min_agents:
            agent_to_remove = idle_agents[0]
            await self.remove_agent(agent_to_remove)
            logger.info(f"Scaled down {self.config.agent_type}: removed {agent_to_remove}")
    
    async def _remove_idle_agents(self):
        """Remove agents that have been idle too long."""
        idle_candidates = []
        for agent_id, metrics in self.metrics.items():
            if (agent_id not in self._running_agents and
                metrics.is_idle(self.config.idle_timeout_seconds) and
                len(self.agents) > self.config.min_agents):
                idle_candidates.append(agent_id)
        
        for agent_id in idle_candidates:
            await self.remove_agent(agent_id)
            logger.info(f"Removed idle agent {agent_id}")
