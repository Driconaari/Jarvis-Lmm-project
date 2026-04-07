"""
Jarvis Main Entry Point
Multi-LLM Orchestrator for Software Development Workflows
"""

import asyncio
import sys
import logging
from pathlib import Path
from loguru import logger

# Configure logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO", format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
logger.add("output/jarvis.log", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}")

from jarvis import Orchestrator, get_config_manager
from agents import (
    ArchitectureAgent,
    TechLeadAgent,
    ImplementationAgent,
    TestingAgent,
    DocumentationAgent,
    DeploymentAgent
)


def setup_orchestrator(config_path: str = "config/jarvis_config.yaml") -> Orchestrator:
    """Initialize and configure the Jarvis orchestrator."""
    logger.info("Initializing Jarvis Multi-LLM Orchestrator...")
    
    # Load configuration
    config_manager = get_config_manager(config_path)
    config = config_manager.get()
    
    logger.info(f"  Endpoints: {len(config.endpoints)}")
    logger.info(f"  Agents: {len(config.agents)}")
    logger.info(f"  Workspace: {config.workspace.git_repo}")
    
    # Create orchestrator
    orchestrator = Orchestrator(config_path)
    
    # Create router for LLM endpoint management
    router = orchestrator.router
    logger.info(f"  Router: {router.__class__.__name__} ready")
    
    return orchestrator


def register_agents(orchestrator: Orchestrator):
    """Register all specialized agents with the orchestrator."""
    logger.info("Registering specialized agents...")
    
    config = orchestrator.config
    
    # Get LLM instances for each agent using the router
    agents_info = []
    
    for agent_name in ["architecture", "tech_lead", "implementation", "testing", "documentation", "deployment"]:
        agent_config = config.agents.get(agent_name)
        if not agent_config:
            logger.warning(f"  No config for agent: {agent_name}")
            continue
        
        # Get routed LLM for this agent
        try:
            llm, endpoint = orchestrator.router.get_routed_llm(agent_name)
            logger.debug(f"  Routed agent '{agent_name}' to {endpoint.name} ({endpoint.url})")
            agents_info.append((agent_name, agent_config, llm))
        except Exception as e:
            logger.error(f"  Failed to route agent {agent_name}: {e}")
    
    # Instantiate and register agents
    agent_classes = {
        "architecture": ArchitectureAgent,
        "tech_lead": TechLeadAgent,
        "implementation": ImplementationAgent,
        "testing": TestingAgent,
        "documentation": DocumentationAgent,
        "deployment": DeploymentAgent,
    }
    
    for agent_name, agent_config, llm in agents_info:
        agent_class = agent_classes.get(agent_name)
        if agent_class:
            agent = agent_class(llm, agent_config)
            orchestrator.register_agent(agent_name, agent)
            logger.info(f"  ✓ Registered: {agent_name} ({agent_config.role})")


async def run_demo_workflow(orchestrator: Orchestrator):
    """Run a complete demo workflow."""
    logger.info("\n" + "="*70)
    logger.info("STARTING DEMO WORKFLOW: Task Management System")
    logger.info("="*70 + "\n")
    
    # Execute the full workflow
    demo_spec = {
        "project_name": "Task Management System",
        "description": "Real-time collaborative task management platform"
    }
    
    context = await orchestrator.execute_full_workflow(
        demo_spec["project_name"],
        demo_spec
    )
    
    # Generate and display summary
    logger.info("\n" + "="*70)
    logger.info("WORKFLOW EXECUTION SUMMARY")
    logger.info("="*70)
    logger.info(context.get_phase_summary())
    
    # Show artifact summary
    artifact_summary = orchestrator.artifact_manager.get_artifact_summary()
    logger.info(f"\nArtifacts Generated: {artifact_summary}")
    
    # Show git history
    git_log = orchestrator.artifact_manager.get_git_log(10)
    if git_log:
        logger.info("\nGit Commit History:")
        for commit in git_log:
            logger.info(f"  {commit}")
    
    logger.info("\n" + "="*70)
    logger.info("DEMO WORKFLOW COMPLETE")
    logger.info("="*70)
    logger.info(f"Output directory: {orchestrator.config.workspace.git_repo}")
    logger.info(f"All artifacts saved and committed to git")
    
    return context


def main():
    """Main entry point."""
    try:
        # Setup
        orchestrator = setup_orchestrator()
        register_agents(orchestrator)
        
        # Run demo
        context = asyncio.run(run_demo_workflow(orchestrator))
        
        logger.info("\n✓ Jarvis execution completed successfully!")
        return 0
    
    except KeyboardInterrupt:
        logger.warning("\n⚠ Jarvis interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"\n✗ Jarvis failed with error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
