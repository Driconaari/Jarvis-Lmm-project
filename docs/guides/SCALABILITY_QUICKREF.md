# Scalability Quick Reference

## Quick Start (30 seconds)

```bash
python main_scalable.py
# Select option 1: Job Queue with Auto-Scaling
```

## Submit Jobs (1 minute)

```python
import asyncio
from jarvis.scalable_orchestrator import ScalableOrchestrator

async def main():
    orch = ScalableOrchestrator()
    await orch.start_worker_pool("implementation", num_workers=2)
    
    # High priority
    job1 = await orch.submit_job("implementation", {...}, priority=1)
    
    # Normal priority
    job2 = await orch.submit_job("implementation", {...}, priority=5)
    
    # Low priority
    job3 = await orch.submit_job("implementation", {...}, priority=9)
    
    # Check status
    status = await orch.get_job_status(job1.job_id)
    print(status)

asyncio.run(main())
```

## Key Concepts

### Priority Levels
- **1** = Highest (process immediately)
- **5** = Normal (process eventually)
- **9** = Lowest (process when idle)

### Auto-Scaling Thresholds
```
Scale UP:   Queue Utilization >= 70% → Spawn agent
Scale DOWN: Queue Utilization <= 20% → Remove agent

Utilization = Pending Jobs / (Current Agents × 5)
```

### Available Methods

| Method | Purpose | Example |
|--------|---------|---------|
| `submit_job()` | Queue a new job | `await orch.submit_job("impl", {...}, priority=5)` |
| `get_job_status()` | Check job status | `await orch.get_job_status(job_id)` |
| `get_system_metrics()` | Monitoring stats | `metrics = await orch.get_system_metrics()` |
| `start_worker_pool()` | Create worker pool | `await orch.start_worker_pool("impl", num_workers=2)` |
| `stop_all_workers()` | Shutdown cleanly | `await orch.stop_all_workers()` |

## Common Tasks

### Task 1: Submit 100 Jobs and Let Auto-Scale

```python
# Start with 1 worker
await orch.start_worker_pool("implementation", num_workers=1)

# Submit jobs
for i in range(100):
    await orch.submit_job("implementation", {...})

# System auto-scales: 1 → 10 workers as queue grows
# Then scales down: 10 → 1 worker as queue empties
```

### Task 2: Monitor Auto-Scaling

```python
# Start monitoring
await orch.start_stats_monitor()

# Watch workers scale
for i in range(30):
    await asyncio.sleep(2)
    metrics = await orch.get_system_metrics()
    
    workers = metrics['pools']['implementation']['total_agents']
    pending = metrics['queue']['pending']
    
    print(f"Workers: {workers}, Pending: {pending}")
```

### Task 3: Submit Different Priorities

```python
# Critical - must complete within minutes
critical = await orch.submit_job(..., priority=1)

# Normal work
normal = await orch.submit_job(..., priority=5)

# Batch/background - can run overnight
background = await orch.submit_job(..., priority=9)

# Queue processes: critical → normal → background
```

### Task 4: Get Real-Time Metrics

```python
metrics = await orch.get_system_metrics()

print(f"Queue depth: {metrics['queue']['pending']}")
print(f"Throughput: {metrics['queue']['throughput_jobs_per_minute']:.2f} jobs/min")
print(f"Avg time: {metrics['queue']['average_job_time']:.2f}s")

for agent_type, stats in metrics['pools'].items():
    print(f"{agent_type}: {stats['total_agents']} workers")
```

### Task 5: Handle Failures & Retry

```python
# Job will retry up to 3 times on failure
job = await orch.submit_job(
    "implementation",
    {...},
    max_retries=3
)

# Monitor for eventual success/failure
while True:
    status = await orch.get_job_status(job.job_id)
    
    if status['status'] == 'COMPLETED':
        print("Success!")
        break
    elif status['status'] == 'FAILED':
        print(f"Failed: {status.get('error')}")
        break
    
    await asyncio.sleep(5)
```

## Configuration Reference

### Scaling Parameters

```python
from jarvis.agent_pool import PoolConfig

config = PoolConfig(
    agent_type="implementation",
    
    # Pool size
    min_agents=2,               # Minimum always running
    max_agents=10,              # Never exceed this
    
    # Scale-up
    scale_up_threshold=0.7,     # Trigger at 70% full
    scale_up_cooldown_seconds=2,    # Min time between scale-ups
    
    # Scale-down
    scale_down_threshold=0.2,   # Trigger at 20% full
    scale_down_cooldown_seconds=30, # Min time between scale-downs
    
    # Idle cleanup
    idle_timeout_seconds=60,    # Remove agents idle this long
)
```

### Tuning for Different Workloads

**High-throughput (many small jobs)**
```python
PoolConfig(
    min_agents=4,           # Keep more running
    max_agents=20,          # Allow more scaling
    scale_up_threshold=0.6,     # React faster
    scale_down_threshold=0.1,   # Keep more agents
)
```

**Conservative (avoid thrashing)**
```python
PoolConfig(
    min_agents=2,
    max_agents=5,
    scale_up_threshold=0.8,     # Wait longer
    scale_down_cooldown_seconds=120,  # Very conservative
)
```

**Aggressive (rapid response)**
```python
PoolConfig(
    min_agents=1,
    max_agents=15,
    scale_up_threshold=0.5,     # Scale immediately
    scale_up_cooldown_seconds=1,
    scale_down_threshold=0.1,
)
```

## Job Status Transitions

```
PENDING → RUNNING → COMPLETED  ← SUCCESS
             ↓
           FAILED            ← NO RETRIES LEFT
             ↓
         RETRYING           ← BACK TO QUEUE IF RETRIES REMAIN
             ↓
         RUNNING → COMPLETED
```

## Entry Points

### For Job Queue & Auto-Scaling
```bash
python main_scalable.py
# Select option 1
```

### For Traditional Workflow (unchanged)
```bash
python main.py
```

### For Examples
```bash
python examples_scalability.py
# Try example 1-5
```

## Monitoring Checklist

During job processing, monitor:

- ☑ **Queue depth** - `metrics['queue']['pending']`
- ☑ **Worker count** - `metrics['pools'][agent]['total_agents']`
- ☑ **Job throughput** - `metrics['queue']['throughput_jobs_per_minute']`
- ☑ **Success rate** - Count completed vs failed
- ☑ **Scaling events** - Watch worker count increase/decrease
- ☑ **Memory usage** - System performance over time

## Limits & Constraints

| Limit | Value | Notes |
|-------|-------|-------|
| Max queue size | 1000 | Configurable in ScalabilityConfig |
| Max agents per type | 10 | Configurable per PoolConfig |
| Job timeout | 300s | Configurable per job |
| Max retries per job | 3+ | Configurable, no hard limit |
| Queue check interval | 2s | Auto-scaling checks every 2s |

## Troubleshooting

### No jobs processing
```python
# Check workers exist
metrics = await orch.get_system_metrics()
assert metrics['pools'][agent_type]['total_agents'] > 0
```

### Queue growing unbounded
```python
# Check max_agents
assert config.max_agents > len(agents)

# Increase max or start more workers
```

### High memory usage
```python
# Reduce maxagents
config.max_agents = 4

# Or use smaller LLM models
```

### Slow processing
```python
# Get actual throughput
throughput = metrics['queue']['throughput_jobs_per_minute']

# If < 1 job/min, increase workers
await orch.start_worker_pool(agent_type, num_workers=more)
```

## Performance Tips

1. **Start small, let auto-scale expand**
   - Begin with `num_workers=1`
   - System adds more as needed

2. **Use appropriate max_agents**
   - Set to 2x your CPU cores
   - Avoid excessive thread creation

3. **Batch related jobs**
   - Group jobs by type
   - Use separate pools for different workloads

4. **Monitor and adjust thresholds**
   - If scaling too aggressive: increase cooldown
   - If scaling too conservative: lower thresholds

5. **Use priority for SLAs**
   - Critical work: priority 1-2
   - Normal: priority 5
   - Background: priority 8-9

## Examples

See `examples_scalability.py`:
- Example 1: Basic job submission
- Example 2: Priority scheduling
- Example 3: Watch auto-scaling
- Example 4: Metrics monitoring
- Example 5: Automatic retry

## Documentation

- **SCALABILITY_GUIDE.md** - Comprehensive guide with architecture
- **SCALABILITY_IMPLEMENTATION.md** - Implementation details
- **examples_scalability.py** - 5 practical examples
- **README.md** - Brief overview (see "Scalability & Job Queue" section)

## FAQ

**Q: Can I use ScalableOrchestrator without job queues?**
A: Yes! `execute_full_workflow()` still works as before.

**Q: Do jobs persist if system crashes?**
A: Not in current implementation. Use Redis backend for persistence (future enhancement).

**Q: Can I scale across multiple machines?**
A: Not yet. Current implementation is single-machine. Distributed version planned.

**Q: How many jobs can I queue?**
A: Default: 1000. Configure via `ScalabilityConfig.max_queue_size`.

**Q: Are agent instances shared or separately created?**
A: Separately created via factory pattern for true parallelism per instance.

---

**For more details**, see the comprehensive guides:
- Detailed tuning → **SCALABILITY_GUIDE.md**
- Architecture details → **SCALABILITY_IMPLEMENTATION.md**
- Running examples → **examples_scalability.py**
