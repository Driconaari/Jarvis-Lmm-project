"""
Scalability Examples
Practical examples of using Jarvis with job queues and auto-scaling
"""

import asyncio
from datetime import datetime
from jarvis.scalable_orchestrator import ScalableOrchestrator, ScalabilityConfig
from jarvis.agent_pool import PoolConfig
from loguru import logger


async def example_1_basic_job_submission():
    """Example 1: Submit jobs to queue and let auto-scaling handle it."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 1: Basic Job Submission")
    logger.info("="*70)
    
    orchestrator = ScalableOrchestrator("config/jarvis_config.yaml")
    
    # Setup
    await orchestrator.start_worker_pool("implementation", num_workers=1)
    await orchestrator.start_stats_monitor()
    
    # Submit 10 jobs
    logger.info("Submitting 10 implementation jobs...")
    for i in range(10):
        job = await orchestrator.submit_job(
            "implementation",
            {"task_id": f"task_{i}", "code": f"def func_{i}(): pass"},
            priority=5
        )
        logger.info(f"  Job {i+1}/10 submitted: {job.job_id}")
        await asyncio.sleep(0.1)
    
    # Watch progress
    logger.info("\nMonitoring job processing (60 seconds)...")
    for i in range(12):
        await asyncio.sleep(5)
        metrics = await orchestrator.get_system_metrics()
        print(f"\n[{i*5}s] Queue: {metrics['queue']['pending']} pending, "
              f"{metrics['queue']['running']} running, "
              f"Workers: {metrics['pools']['implementation']['total_agents']}")
    
    # Cleanup
    await orchestrator.stop_all_workers()
    logger.info("\n✓ Example 1 complete")


async def example_2_priority_scheduling():
    """Example 2: Different job priorities process in correct order."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 2: Priority-Based Scheduling")
    logger.info("="*70)
    
    orchestrator = ScalableOrchestrator("config/jarvis_config.yaml")
    
    # Setup with slow processing to show priority effect
    await orchestrator.start_worker_pool("testing", num_workers=1)
    
    logger.info("Submitting jobs with different priorities...")
    
    # Low priority background task
    bg_job = await orchestrator.submit_job(
        "testing",
        {"task_id": "background", "test_count": 10},
        priority=9  # Lowest priority
    )
    logger.info(f"  Background job (priority 9): {bg_job.job_id}")
    
    # Medium priority regular task
    regular_job = await orchestrator.submit_job(
        "testing",
        {"task_id": "regular", "test_count": 10},
        priority=5  # Normal priority
    )
    logger.info(f"  Regular job (priority 5): {regular_job.job_id}")
    
    # High priority urgent task (submitted last, but should complete first!)
    urgent_job = await orchestrator.submit_job(
        "testing",
        {"task_id": "urgent", "test_count": 10},
        priority=1  # Highest priority
    )
    logger.info(f"  Urgent job (priority 1): {urgent_job.job_id}")
    
    # Monitor completion order
    logger.info("\nWatching completion order (should be: urgent → regular → background)")
    jobs_to_track = {
        bg_job.job_id: "background (priority 9)",
        regular_job.job_id: "regular (priority 5)",
        urgent_job.job_id: "urgent (priority 1)",
    }
    
    for i in range(30):
        await asyncio.sleep(2)
        for job_id, desc in list(jobs_to_track.items()):
            status = await orchestrator.get_job_status(job_id)
            if status and status['status'] == 'COMPLETED':
                logger.info(f"  ✓ {desc} completed")
                del jobs_to_track[job_id]
        
        if not jobs_to_track:
            break
    
    await orchestrator.stop_all_workers()
    logger.info("\n✓ Example 2 complete")


async def example_3_auto_scaling_under_load():
    """Example 3: Watch auto-scaling spawn agents as queue fills up."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 3: Auto-Scaling Under Load")
    logger.info("="*70)
    
    # Configure for aggressive scaling (for demo visibility)
    scaling_config = ScalabilityConfig(
        enable_auto_scaling=True,
        implementation_pool_config=PoolConfig(
            agent_type="implementation",
            min_agents=1,           # Start with 1
            max_agents=5,           # Max 5 for demo
            scale_up_threshold=0.5,     # Aggressive: scale at 50%
            scale_down_threshold=0.15,
        )
    )
    
    orchestrator = ScalableOrchestrator("config/jarvis_config.yaml", scaling_config)
    
    # Start with single worker
    logger.info("Starting with 1 worker...")
    await orchestrator.start_worker_pool("implementation", num_workers=1)
    
    # Submit many jobs to trigger scaling
    logger.info("\nSubmitting 20 jobs rapidly to trigger scaling...")
    for i in range(20):
        await orchestrator.submit_job(
            "implementation",
            {"task_id": f"scaling_task_{i}", "duration_seconds": 2},
            priority=5
        )
        if (i + 1) % 5 == 0:
            logger.info(f"  {i + 1} jobs submitted")
    
    # Monitor scaling events
    logger.info("\nMonitoring auto-scaling (look for agent count changes):")
    prev_agent_count = 1
    
    for i in range(40):
        await asyncio.sleep(1)
        metrics = await orchestrator.get_system_metrics()
        
        impl_pool = metrics['pools']['implementation']
        agent_count = impl_pool['total_agents']
        
        if agent_count != prev_agent_count:
            logger.info(f"  [SCALING] Workers: {prev_agent_count} → {agent_count} "
                       f"(Queue: {metrics['queue']['pending']} pending)")
            prev_agent_count = agent_count
        
        # Update every 5 seconds
        if i % 5 == 0:
            logger.info(f"  [{i}s] Workers: {agent_count}, "
                       f"Pending: {metrics['queue']['pending']}, "
                       f"Completed: {metrics['queue']['completed']}")
    
    await orchestrator.stop_all_workers()
    logger.info("\n✓ Example 3 complete")


async def example_4_monitoring_metrics():
    """Example 4: Extract and analyze system metrics."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 4: Monitoring Metrics")
    logger.info("="*70)
    
    orchestrator = ScalableOrchestrator("config/jarvis_config.yaml")
    
    # Setup multiple pools
    logger.info("Setting up multiple pools...")
    await orchestrator.start_worker_pool("implementation", num_workers=2)
    await orchestrator.start_worker_pool("testing", num_workers=1)
    await orchestrator.start_worker_pool("documentation", num_workers=1)
    
    # Submit mixed jobs
    logger.info("\nSubmitting jobs to different pools...")
    for i in range(15):
        agent_type = ["implementation", "testing", "documentation"][i % 3]
        await orchestrator.submit_job(
            agent_type,
            {"task_id": f"{agent_type}_{i}", "complexity": "medium"},
            priority=5
        )
    
    # Wait for some processing
    await asyncio.sleep(10)
    
    # Get detailed metrics
    metrics = await orchestrator.get_system_metrics()
    
    logger.info("\n=== DETAILED METRICS ===")
    logger.info(f"\nQueue Stats:")
    logger.info(f"  Pending: {metrics['queue']['pending']}")
    logger.info(f"  Running: {metrics['queue']['running']}")
    logger.info(f"  Completed: {metrics['queue']['completed']}")
    logger.info(f"  Failed: {metrics['queue']['failed']}")
    logger.info(f"  Avg job time: {metrics['queue']['average_job_time']:.2f}s")
    logger.info(f"  Throughput: {metrics['queue']['throughput_jobs_per_minute']:.2f} jobs/min")
    
    logger.info(f"\nPer-Pool Stats:")
    for agent_type, pool_stats in metrics['pools'].items():
        logger.info(f"\n  {agent_type}:")
        logger.info(f"    Total agents: {pool_stats['total_agents']}")
        logger.info(f"    Idle agents: {pool_stats['idle_agents']}")
        logger.info(f"    Busy agents: {pool_stats['busy_agents']}")
        logger.info(f"    Queue - pending: {pool_stats['queue_stats']['pending']}")
        logger.info(f"    Queue - completed: {pool_stats['queue_stats']['completed']}")
    
    await orchestrator.stop_all_workers()
    logger.info("\n✓ Example 4 complete")


async def example_5_retry_on_failure():
    """Example 5: Jobs automatically retry on failure."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 5: Automatic Retry on Failure")
    logger.info("="*70)
    
    orchestrator = ScalableOrchestrator("config/jarvis_config.yaml")
    
    await orchestrator.start_worker_pool("implementation", num_workers=2)
    
    logger.info("Submitting jobs with retry configuration...")
    
    # Job that will retry up to 3 times on failure
    job = await orchestrator.submit_job(
        "implementation",
        {"task_id": "flaky_task", "should_fail": True},
        priority=5,
        max_retries=3  # Will retry up to 3 times
    )
    
    logger.info(f"Job submitted: {job.job_id}")
    logger.info(f"Max retries: {job.max_retries}")
    
    # Monitor job status
    logger.info("\nMonitoring job (may retry if it fails):")
    for i in range(20):
        await asyncio.sleep(2)
        status = await orchestrator.get_job_status(job.job_id)
        
        if status:
            logger.info(f"  [{i*2}s] Status: {status['status']}")
            
            if status['status'] in ['COMPLETED', 'FAILED']:
                logger.info(f"  Final status: {status['status']}")
                if 'result' in status:
                    logger.info(f"  Result: {status['result']}")
                if 'error' in status:
                    logger.info(f"  Error: {status['error']}")
                break
    
    await orchestrator.stop_all_workers()
    logger.info("\n✓ Example 5 complete")


async def main():
    """Run selected examples."""
    logger.info("\n" + "="*70)
    logger.info("JARVIS SCALABILITY EXAMPLES")
    logger.info("="*70)
    logger.info("\nAvailable examples:")
    logger.info("  1. Basic Job Submission")
    logger.info("  2. Priority-Based Scheduling")
    logger.info("  3. Auto-Scaling Under Load")
    logger.info("  4. Monitoring Metrics")
    logger.info("  5. Automatic Retry on Failure")
    logger.info("  6. Run All Examples")
    
    choice = input("\nSelect example (1-6): ").strip() or "1"
    
    try:
        if choice == "1":
            await example_1_basic_job_submission()
        elif choice == "2":
            await example_2_priority_scheduling()
        elif choice == "3":
            await example_3_auto_scaling_under_load()
        elif choice == "4":
            await example_4_monitoring_metrics()
        elif choice == "5":
            await example_5_retry_on_failure()
        elif choice == "6":
            await example_1_basic_job_submission()
            await example_2_priority_scheduling()
            await example_3_auto_scaling_under_load()
            await example_4_monitoring_metrics()
            await example_5_retry_on_failure()
        else:
            logger.error("Invalid choice")
            return 1
        
        logger.info("\n" + "="*70)
        logger.info("All examples completed!")
        logger.info("="*70)
        return 0
    
    except KeyboardInterrupt:
        logger.warning("\n⚠ Examples interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
