"""
Scalable Jarvis - Main Entry Point
Multi-LLM Orchestrator with Auto-Scaling Capabilities
"""

import asyncio
import sys
import logging
from pathlib import Path
from loguru import logger

from jarvis.scalable_orchestrator import ScalableOrchestrator, ScalabilityConfig
from jarvis.agent_pool import PoolConfig
from agents import (
    ArchitectureAgent,
    TechLeadAgent,
    ImplementationAgent,
    TestingAgent,
    DocumentationAgent,
    DeploymentAgent
)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
logger.add("output/jarvis_scalable.log", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}")


async def setup_scalable_orchestrator(config_path: str = "config/jarvis_config.yaml") -> ScalableOrchestrator:
    """Initialize scalable orchestrator with auto-scaling pools."""
    logger.info("Initializing Scalable Jarvis Multi-LLM Orchestrator...")
    
    # Configure scalability
    scalability_config = ScalabilityConfig(
        enable_job_queue=True,
        enable_auto_scaling=True,
        max_queue_size=500,  # Can queue up to 500 jobs
        refresh_interval_seconds=3,
        
        # Implementation agents can scale from 2-10 workers
        implementation_pool_config=PoolConfig(
            agent_type="implementation",
            min_agents=2,
            max_agents=10,
            scale_up_threshold=0.7,      # Scale up when 70% full
            scale_down_threshold=0.2,    # Scale down when 20% full
            scale_up_cooldown_seconds=2,
            scale_down_cooldown_seconds=10,
        ),
        
        # Other agents scale from 1-3 workers
        default_pool_config=PoolConfig(
            agent_type="default",
            min_agents=1,
            max_agents=3,
            scale_up_threshold=0.75,
            scale_down_threshold=0.15,
        )
    )
    
    # Create scalable orchestrator
    orchestrator = ScalableOrchestrator(config_path, scalability_config)
    logger.info("✓ ScalableOrchestrator created")
    
    return orchestrator


async def setup_agent_pools(orchestrator: ScalableOrchestrator):
    """Setup agent pools for each agent type."""
    logger.info("Setting up agent pools...")
    
    # Setup pools for each agent type
    pool_config = orchestrator.scalability_config.default_pool_config
    
    for agent_name in ["architecture", "tech_lead", "testing", "documentation", "deployment"]:
        orchestrator.setup_agent_pool(agent_name, pool_config)
    
    # Implementation gets special config with more workers
    impl_config = orchestrator.scalability_config.implementation_pool_config
    orchestrator.setup_agent_pool("implementation", impl_config)
    
    logger.info("✓ All agent pools configured")


async def register_agents(orchestrator: ScalableOrchestrator):
    """Register all specialized agents with the orchestrator."""
    logger.info("Registering specialized agents...")
    
    config = orchestrator.config
    
    for agent_name in ["architecture", "tech_lead", "implementation", "testing", "documentation", "deployment"]:
        agent_config = config.agents.get(agent_name)
        if not agent_config:
            logger.warning(f"  No config for agent: {agent_name}")
            continue
        
        try:
            llm, endpoint = orchestrator.router.get_routed_llm(agent_name)
            logger.debug(f"  Routed agent '{agent_name}' to {endpoint.name}")
            
            agent_classes = {
                "architecture": ArchitectureAgent,
                "tech_lead": TechLeadAgent,
                "implementation": ImplementationAgent,
                "testing": TestingAgent,
                "documentation": DocumentationAgent,
                "deployment": DeploymentAgent,
            }
            
            agent_class = agent_classes.get(agent_name)
            if agent_class:
                agent = agent_class(llm, agent_config)
                orchestrator.register_agent(agent_name, agent)
                logger.info(f"  ✓ Registered: {agent_name} ({agent_config.role})")
        
        except Exception as e:
            logger.error(f"  Failed to register agent {agent_name}: {e}")


async def demo_job_submission(orchestrator: ScalableOrchestrator):
    """Demo: Submit multiple jobs to worker pools."""
    logger.info("\n" + "="*70)
    logger.info("DEMO: Job Submission with Auto-Scaling")
    logger.info("="*70 + "\n")
    
    # Start worker pools
    logger.info("Starting worker pools with auto-scaling...")
    await orchestrator.start_worker_pool("implementation", num_workers=2)
    await orchestrator.start_worker_pool("testing", num_workers=1)
    
    # Start stats monitor
    await orchestrator.start_stats_monitor()
    
    logger.info("✓ Worker pools and stats monitor started\n")
    
    # Submit multiple implementation jobs
    logger.info("Submitting implementation jobs...")
    for i in range(8):
        job = await orchestrator.submit_job(
            "implementation",
            {
                "task_id": f"impl_task_{i}",
                "code_snippet": f"def task_{i}(): pass",
                "test_count": 5,
            },
            priority=5 - (i % 3),  # Vary priorities
        )
        logger.info(f"  Job {job.job_id} submitted (priority: {job.priority})")
        await asyncio.sleep(0.2)
    
    # Let jobs process
    logger.info("\nProcessing jobs (watch for auto-scaling)...")
    await asyncio.sleep(15)
    
    # Get final metrics
    metrics = await orchestrator.get_system_metrics()
    
    logger.info("\n" + "="*70)
    logger.info("FINAL METRICS")
    logger.info("="*70)
    logger.info(f"Jobs Completed: {metrics['queue']['completed']}")
    logger.info(f"Jobs Failed: {metrics['queue']['failed']}")
    logger.info(f"Average Job Time: {metrics['queue']['average_job_time']:.2f}s")
    logger.info(f"Throughput: {metrics['queue']['throughput_jobs_per_minute']:.2f} jobs/min")
    
    for agent_type, pool_stats in metrics['pools'].items():
        logger.info(f"\n{agent_type}:")
        logger.info(f"  Agents: {pool_stats['total_agents']} "
                   f"(idle: {pool_stats['idle_agents']}, busy: {pool_stats['busy_agents']})")
    
    # Cleanup
    await orchestrator.stop_all_workers()


async def demo_traditional_workflow(orchestrator: ScalableOrchestrator):
    """Demo: Traditional workflow (for comparison)."""
    logger.info("\n" + "="*70)
    logger.info("DEMO: Traditional Workflow (Without Job Queue)")
    logger.info("="*70 + "\n")
    
    # This runs like the original system
    context = await orchestrator.execute_full_workflow(
        "Scalable Task Management System",
        {"description": "Demo project using scalable orchestrator"}
    )
    
    logger.info(context.get_phase_summary())


async def main():
    """Main entry point."""
    try:
        # Setup
        orchestrator = await setup_scalable_orchestrator()
        await setup_agent_pools(orchestrator)
        register_agents(orchestrator)
        
        # Choose demo mode
        logger.info("\n" + "="*70)
        logger.info("JARVIS SCALABLE ORCHESTRATOR")
        logger.info("="*70)
        logger.info("\nSelect demo mode:")
        logger.info("  1. Job Queue with Auto-Scaling (recommended)")
        logger.info("  2. Traditional Workflow")
        logger.info("  3. Both sequentially")
        
        choice = input("\nEnter choice (1-3) [default: 1]: ").strip() or "1"
        
        if choice == "1":
            await demo_job_submission(orchestrator)
        elif choice == "2":
            await demo_traditional_workflow(orchestrator)
        elif choice == "3":
            await demo_job_submission(orchestrator)
            logger.info("\n" + "="*70)
            logger.info("Running traditional workflow next...")
            logger.info("="*70 + "\n")
            await demo_traditional_workflow(orchestrator)
        else:
            logger.error("Invalid choice")
            return 1
        
        logger.info("\n✓ Scalable Jarvis execution completed successfully!")
        return 0
    
    except KeyboardInterrupt:
        logger.warning("\n⚠ Jarvis interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"\n✗ Jarvis failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
