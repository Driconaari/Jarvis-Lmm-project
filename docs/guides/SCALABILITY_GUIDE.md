# Scalability Guide for Jarvis
## Auto-Scaling Architecture & Usage

---

## Overview

Jarvis now includes a **scalable orchestrator** with:
- ✅ Job queue system for asynchronous task processing
- ✅ Agent pools with automatic scaling based on load  
- ✅ Priority-based job scheduling
- ✅ Real-time performance metrics
- ✅ Graceful scaling up/down

---

## Architecture

### Traditional (Original)
```
Job → Orchestrator → Agent → Result
        (synchronous)
```

### Scalable (New)
```
Job 1 ┐
Job 2 ├→ Job Queue → Agent Pool (auto-scaling) → Results
Job 3 ┘   (async)    1 agent ─→ 10 agents
Job 4             (based on load)
```

---

## Key Components

### 1. **Job Queue** (`jarvis/task_queue.py`)
- Thread-safe priority queue
- Job tracking and status management
- Statistics collection
- Automatic retry on failure

**Usage**:
```python
# Submit a job
job = Job(
    agent_type="implementation",
    task_id="my_task",
    priority=3,  # 1=high, 10=low
    payload={"code": "..."},
    max_retries=3
)
await job_queue.enqueue(job)

# Check status
job_status = await job_queue.get_job(job.job_id)
print(job_status.status)  # PENDING, RUNNING, COMPLETED, FAILED
```

### 2. **Agent Pool** (`jarvis/agent_pool.py`)
- Maintains pool of agents
- Auto-scales based on queue depth
- Tracks per-agent metrics
- Manages worker lifecycle

**Configuration**:
```python
pool_config = PoolConfig(
    agent_type="implementation",
    min_agents=2,           # Minimum, always running
    max_agents=10,          # Maximum allowed
    scale_up_threshold=0.7,     # Queue >= 70% → add agent
    scale_down_threshold=0.2,   # Queue <= 20% → remove agent
)
```

### 3. **Scalable Orchestrator** (`jarvis/scalable_orchestrator.py`)
- Enhanced orchestrator with job queue
- Manages multiple agent pools
- Worker loops that process jobs
- Statistics monitoring

---

## How Auto-Scaling Works

### **Scale-Up Trigger**
```
Queue Utilization = Pending Jobs / (Current Agents × 5)

If Utilization ≥ 70%:
    → Add one new agent (up to max)
    → Wait 2 seconds before next scale-up
```

**Example**:
```
2 agents running
Queue depth: 8 jobs
Utilization = 8 / (2 × 5) = 80% ✓

→ Spawn new agent (now 3 total)
→ Throughput increases
```

### **Scale-Down Trigger**
```
Queue Utilization ≤ 20%:
    → Remove one idle agent (keep at least min)
    → Wait 30 seconds before next scale-down
```

**Example**:
```
10 agents running
Queue depth: 3 jobs
Utilization = 3 / (10 × 5) = 6% ✓

→ Remove agent (now 9 total)
→ Reduce resource usage
```

---

## Usage Examples

### Example 1: Submit Jobs Asynchronously

```python
from jarvis.scalable_orchestrator import ScalableOrchestrator

orchestrator = ScalableOrchestrator("config/jarvis_config.yaml")

# Start worker pool
await orchestrator.start_worker_pool("implementation", num_workers=2)

# Submit jobs (fire and forget)
for i in range(50):
    job = await orchestrator.submit_job(
        "implementation",
        {"task_id": f"task_{i}", "code": f"..."},
        priority=5
    )
    print(f"Job {job.job_id} submitted")

# Check progress
while True:
    stats = await orchestrator.get_system_metrics()
    print(f"Pending: {stats['queue']['pending']}")
    print(f"Workers: {stats['pools']['implementation']['total_agents']}")
    await asyncio.sleep(2)
```

### Example 2: Priority-Based Processing

```python
# High priority - processed first
critical_job = await orchestrator.submit_job(
    "implementation",
    {"task": "urgent", "data": "..."},
    priority=1,  # Highest
    max_retries=5
)

# Normal priority - eventually processed
normal_job = await orchestrator.submit_job(
    "implementation",
    {"task": "regular", "data": "..."},
    priority=5   # Normal
)

# Low priority - processed when idle
background_job = await orchestrator.submit_job(
    "implementation",
    {"task": "background", "data": "..."},
    priority=9   # Lowest
)
```

### Example 3: Monitor and React to Scaling

```python
# Start monitoring
await orchestrator.start_stats_monitor()

# Wait and watch auto-scaling in action
for i in range(30):
    await asyncio.sleep(2)
    metrics = await orchestrator.get_system_metrics()
    
    impl_pool = metrics['pools']['implementation']
    print(f"Implementation: {impl_pool['total_agents']} agents, "
          f"{impl_pool['idle_agents']} idle, "
          f"{impl_pool['busy_agents']} busy")
```

---

## Configuration Parameters

### Queue Configuration
| Parameter | Default | Purpose |
|---|---|---|
| `max_queue_size` | 1000 | Maximum jobs that can be queued |
| `enable_job_queue` | True | Enable job queueing |

### Agent Pool Configuration
| Parameter | Default (Impl) | Purpose |
|---|---|---|
| `min_agents` | 2 | Minimum pool size |
| `max_agents` | 10 | Maximum pool size |
| `scale_up_threshold` | 0.7 | Queue fill % to trigger scale-up |
| `scale_down_threshold` | 0.2 | Queue fill % to trigger scale-down |
| `scale_up_cooldown_seconds` | 2 | Minimum time between scale-ups |
| `scale_down_cooldown_seconds` | 10 | Minimum time between scale-downs |
| `idle_timeout_seconds` | 90 | Auto-remove agents idle this long |

### Tuning Tips
```python
# Fast response to load spikes (aggressive scaling)
aggressive = PoolConfig(
    min_agents=2,
    max_agents=20,
    scale_up_threshold=0.5,      # Scale up faster
    scale_down_threshold=0.1,    # Keep more agents around
    scale_up_cooldown_seconds=1, # React quickly
)

# Conservative (stable, less churn)
conservative = PoolConfig(
    min_agents=3,
    max_agents=8,
    scale_up_threshold=0.8,      # Scale up cautiously
    scale_down_threshold=0.1,    # Prefer to keep agents
    scale_down_cooldown_seconds=60,  # Remove slowly
)
```

---

## Performance Metrics

### Available Metrics
```python
metrics = await orchestrator.get_system_metrics()

# Queue metrics
metrics['queue']['pending']            # Jobs waiting
metrics['queue']['running']            # Currently executing
metrics['queue']['completed']          # Successfully finished
metrics['queue']['failed']             # Failed jobs
metrics['queue']['average_job_time']   # Avg execution time
metrics['queue']['throughput_jobs_per_minute']  # Jobs/min

# Pool metrics per agent type
metrics['pools']['implementation']['total_agents']
metrics['pools']['implementation']['idle_agents']
metrics['pools']['implementation']['busy_agents']
```

### Monitoring Example
```python
async def monitor_system():
    while True:
        await asyncio.sleep(5)
        metrics = await orchestrator.get_system_metrics()
        
        # Alert if queue growing too fast
        if metrics['queue']['pending'] > 100:
            logger.warning(f"Queue overloaded: {metrics['queue']['pending']} jobs")
        
        # Alert if scaling maxed out
        for agent_type, pool_stats in metrics['pools'].items():
            if pool_stats['busy_agents'] == pool_stats['total_agents']:
                logger.warning(f"{agent_type} pool at capacity!")
```

---

## Troubleshooting

### Problem: Jobs staying in QUEUED state
**Diagnosis**:
```python
metrics = await orchestrator.get_system_metrics()
print(f"Total agents: {metrics['pools']['implementation']['total_agents']}")
print(f"Pending: {metrics['queue']['pending']}")
```

**Solution**: 
- Increase `max_agents` in pool config
- Check if agents are throwing errors
- Verify job payloads are valid

### Problem: Memory usage growing
**Cause**: Too many agents spawned

**Solution**:
```python
config.implementation_pool_config.max_agents = 5  # Reduce max
```

### Problem: Slow job processing
**Cause**: Queue depth high, agents not keeping up

**Solution**:
```python
# Increase scale-up threshold (spawn agents faster)
config.implementation_pool_config.scale_up_threshold = 0.5

# Or increase max pool size
config.implementation_pool_config.max_agents = 20
```

---

## Running Scalable Jarvis

### Quick Start
```bash
# Run with job queue and auto-scaling
python main_scalable.py

# Select option 1 for job queue demo
# Select option 2 for traditional workflow
# Select option 3 for both
```

### As Library
```python
from jarvis.scalable_orchestrator import ScalableOrchestrator

orchestrator = ScalableOrchestrator()
await orchestrator.start_worker_pool("implementation", num_workers=3)

# Submit jobs
job = await orchestrator.submit_job("implementation", {...})

# Monitor progress
metrics = await orchestrator.get_system_metrics()
```

---

## Scaling Scenarios

### Scenario 1: Batch Processing (100 independent tasks)
```python
# Configuration
# Many workers to parallelize
max_agents = 20
min_agents = 5
scale_up_threshold = 0.6

# Submit all jobs at once
for i in range(100):
    await orchestrator.submit_job("implementation", {...})

# System automatically spawns agents as queue grows
# Processes in parallel, scaling down as queue empties
```

### Scenario 2: Steady Stream (continuous jobs)
```python
# Configuration
# Maintain baseline workers, respond to spikes
max_agents = 8
min_agents = 2
scale_up_threshold = 0.7

# Keep submitting jobs continuously
while True:
    await orchestrator.submit_job("implementation", {...})
    await asyncio.sleep(0.5)  # Job every 500ms

# System keeps 2-8 workers running based on queue depth
```

### Scenario 3: Mixed Priority (urgent + background)
```python
# Urgent background jobs (priority 1-2)
# Normal jobs (priority 5-6)
# Background jobs (priority 8-10)

# System processes urgent first, backgroundfills unused capacity
critical = await orchestrator.submit_job(..., priority=1)
normal = await orchestrator.submit_job(..., priority=5)
background = await orchestrator.submit_job(..., priority=9)

# Stats show: urgent jobs complete first, background completes later
```

---

## Migration from Original Jarvis

### Original (Synchronous)
```python
context = await orchestrator.execute_full_workflow(...)
# Blocks until complete
```

### Scalable (Asynchronous)
```python
# Submit jobs asynchronously
await orchestrator.start_worker_pool("implementation", num_workers=3)

for task_data in tasks:
    job = await orchestrator.submit_job("implementation", task_data)
    # Returns immediately, job processes in background

# Check progress
metrics = await orchestrator.get_system_metrics()

# Or use traditional mode
context = await orchestrator.execute_full_workflow(...)
```

---

## Best Practices

1. **Start with single worker, let auto-scaling expand**
   ```python
   await orchestrator.start_worker_pool("implementation", num_workers=1)
   # System will expand as needed
   ```

2. **Use appropriate cooldown times**
   ```python
   # Aggressive for bursty traffic
   scale_up_cooldown_seconds = 1
   
   # Conservative for steady load
   scale_down_cooldown_seconds = 60
   ```

3. **Monitor and alert on key metrics**
   ```python
   metrics = await orchestrator.get_system_metrics()
   
   if metrics['queue']['pending'] > config.thresholds['alert_queue_depth']:
       notify_ops_team()
   ```

4. **Set realistic max_agents limits**
   ```python
   # Avoid runaway scaling
   max_agents = cpu_cores * 2  # Or based on memory
   ```

5. **Use priority for SLA compliance**
   ```python
   if is_urgent_task:
       job = await orchestrator.submit_job(..., priority=1)
   else:
       job = await orchestrator.submit_job(..., priority=5)
   ```

---

## What's Next

- **Persistent Queue**: Add Redis/database backend for durability
- **Distributed Workers**: Scale across machines
- **Adaptive Scaling**: ML-based queue prediction
- **Circuit Breaker**: Graceful degradation under extreme load
- **Request Batching**: Combine small jobs into larger batches

---

**Your Jarvis is now production-scalable!** 🚀

See `main_scalable.py` for working examples.
