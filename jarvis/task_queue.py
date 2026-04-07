"""
Task Queue System for Job Scheduling
Manages job distribution to agents with auto-scaling support.
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from loguru import logger
import heapq


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Represents a task/job to be executed."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_type: str = ""  # "architecture", "implementation", etc.
    task_id: str = ""
    priority: int = 5  # 1=high, 10=low (for sorting)
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempt: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    
    def __lt__(self, other: 'Job') -> bool:
        """Enable priority queue ordering (min-priority first)."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at
    
    @property
    def elapsed_time(self) -> float:
        """Time job has been running in seconds."""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return (end_time - self.started_at).total_seconds()
        return 0.0
    
    @property
    def total_time(self) -> float:
        """Total time from creation to completion."""
        end_time = self.completed_at or datetime.now()
        return (end_time - self.created_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_time": self.elapsed_time,
            "attempt": self.attempt,
            "error": self.error,
        }


@dataclass
class QueueStats:
    """Statistics about queue performance."""
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    average_job_time: float = 0.0
    max_queue_depth: int = 0
    throughput_jobs_per_minute: float = 0.0


class JobQueue:
    """Thread-safe job queue with priority support."""
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self._queue: List[Job] = []
        self._lock = asyncio.Lock()
        self._jobs_by_id: Dict[str, Job] = {}
        self._stats = {
            "total_enqueued": 0,
            "total_dequeued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "max_queue_depth": 0,
        }
        logger.info(f"JobQueue initialized with max size {max_queue_size}")
    
    async def enqueue(self, job: Job) -> bool:
        """Add job to queue."""
        async with self._lock:
            if len(self._queue) >= self.max_queue_size:
                logger.warning(f"Queue full ({len(self._queue)}), rejecting job {job.job_id}")
                return False
            
            job.status = JobStatus.QUEUED
            heapq.heappush(self._queue, job)
            self._jobs_by_id[job.job_id] = job
            self._stats["total_enqueued"] += 1
            
            # Track max depth
            self._stats["max_queue_depth"] = max(
                self._stats["max_queue_depth"],
                len(self._queue)
            )
            
            logger.debug(f"Job {job.job_id} enqueued (priority {job.priority}, queue depth: {len(self._queue)})")
            return True
    
    async def dequeue(self) -> Optional[Job]:
        """Get next job from queue."""
        async with self._lock:
            if not self._queue:
                return None
            
            job = heapq.heappop(self._queue)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self._stats["total_dequeued"] += 1
            
            logger.debug(f"Job {job.job_id} dequeued (type: {job.agent_type})")
            return job
    
    async def mark_completed(self, job_id: str, result: Any) -> bool:
        """Mark job as completed."""
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            if not job:
                return False
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result
            self._stats["total_completed"] += 1
            
            logger.debug(f"Job {job_id} completed in {job.elapsed_time:.2f}s")
            return True
    
    async def mark_failed(self, job_id: str, error: str) -> bool:
        """Mark job as failed."""
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            if not job:
                return False
            
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.error = error
            self._stats["total_failed"] += 1
            self._stats["total_completed"] += 1
            
            logger.warning(f"Job {job_id} failed: {error}")
            return True
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs_by_id.get(job_id)
    
    async def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        async with self._lock:
            pending = sum(1 for j in self._queue if j.status == JobStatus.PENDING)
            running = sum(1 for j in self._jobs_by_id.values() if j.status == JobStatus.RUNNING)
            completed = sum(1 for j in self._jobs_by_id.values() if j.status == JobStatus.COMPLETED)
            failed = sum(1 for j in self._jobs_by_id.values() if j.status == JobStatus.FAILED)
            
            # Calculate average job time
            completed_jobs = [j for j in self._jobs_by_id.values() 
                            if j.status == JobStatus.COMPLETED]
            avg_time = sum(j.total_time for j in completed_jobs) / len(completed_jobs) \
                      if completed_jobs else 0.0
            
            # Calculate throughput
            if completed_jobs:
                time_span = (datetime.now() - completed_jobs[0].created_at).total_seconds()
                throughput = (len(completed_jobs) / time_span * 60) if time_span > 0 else 0
            else:
                throughput = 0.0
            
            return QueueStats(
                total_jobs=len(self._jobs_by_id),
                pending_jobs=pending,
                running_jobs=running,
                completed_jobs=completed,
                failed_jobs=failed,
                average_job_time=avg_time,
                max_queue_depth=self._stats["max_queue_depth"],
                throughput_jobs_per_minute=throughput,
            )
    
    async def get_pending_count(self) -> int:
        """Get number of pending jobs."""
        async with self._lock:
            return len(self._queue)
    
    async def get_running_count(self) -> int:
        """Get number of running jobs."""
        async with self._lock:
            return sum(1 for j in self._jobs_by_id.values() if j.status == JobStatus.RUNNING)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            if job and job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                logger.info(f"Job {job_id} cancelled")
                return True
            return False
    
    def get_queue_health(self) -> Dict[str, Any]:
        """Get queue health metrics."""
        stats_dict = dict(self._stats)
        return {
            "queue_depth": len(self._queue),
            "total_jobs_tracked": len(self._jobs_by_id),
            **stats_dict,
        }
