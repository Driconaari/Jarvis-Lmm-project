"""
Jarvis Orchestrator
Central coordinator for multi-agent workflows.
Manages artifact flow, context preservation, and reproducibility.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import re
from loguru import logger
from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError

from jarvis.config import ConfigManager, JarvisConfig
from jarvis.router import MultiEndpointRouter
from jarvis.base_agent import AgentOutput


class ArtifactManager:
    """Manages artifact creation, versioning, and git tracking."""
    
    def __init__(self, config: JarvisConfig):
        self.config = config
        self.repo_path = Path(config.workspace.git_repo)
        self.artifacts_path = self.repo_path / config.workspace.artifacts_dir
        self.repo = None
        self._init_repo()
    
    def _init_repo(self):
        """Initialize or open git repository."""
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        try:
            self.repo = Repo(self.repo_path)
            logger.info(f"Opened existing git repo: {self.repo_path}")
        except InvalidGitRepositoryError:
            self.repo = Repo.init(self.repo_path)
            # Set up initial config
            with self.repo.config_writer() as git_config:
                git_config.set_value("user", "name", "Jarvis").release()
                git_config.set_value("user", "email", "jarvis@local.ai").release()
            logger.info(f"Initialized new git repo: {self.repo_path}")
        
        self.artifacts_path.mkdir(exist_ok=True)
    
    def save_artifact(self, artifact_type: str, name: str, content: str, description: str = "") -> Path:
        """Save an artifact to disk."""
        subdir = self.artifacts_path / artifact_type
        subdir.mkdir(exist_ok=True)
        
        # Slugify name
        safe_name = re.sub(r'[^a-z0-9_-]', '_', name.lower())
        file_path = subdir / f"{safe_name}.txt"
        
        file_path.write_text(content, encoding='utf-8')
        logger.debug(f"Saved {artifact_type}/{name} to {file_path}")
        
        return file_path
    
    def save_agent_output(self, output: AgentOutput) -> Path:
        """Save agent output as JSON artifact."""
        subdir = self.artifacts_path / "agent_outputs"
        subdir.mkdir(exist_ok=True)
        
        timestamp = output.timestamp.strftime("%Y%m%d_%H%M%S")
        file_path = subdir / f"{output.agent_name}_{timestamp}.json"
        
        file_path.write_text(output.to_json(), encoding='utf-8')
        logger.debug(f"Saved agent output: {file_path}")
        
        return file_path
    
    def commit_artifacts(self, phase: str, message: str = "") -> Optional[str]:
        """Commit all artifacts to git with descriptive message."""
        if not self.repo:
            logger.warning("No git repo, skipping commit")
            return None
        
        try:
            # Stage all changes in artifacts directory
            artifacts_relative = str(self.artifacts_path.relative_to(self.repo_path))
            self.repo.index.add([artifacts_relative])
            
            commit_msg = f"[{phase}] {message or f'Completed {phase} phase'}"
            commit = self.repo.index.commit(commit_msg)
            logger.info(f"✓ Committed: {commit.hexsha[:8]} - {commit_msg}")
            return commit.hexsha
        
        except GitCommandError as e:
            if "nothing to commit" in str(e):
                logger.debug(f"No changes to commit for phase {phase}")
                return None
            logger.error(f"Git commit failed: {e}")
            return None
    
    def get_artifact_summary(self) -> Dict[str, int]:
        """Get summary of all saved artifacts."""
        summary = {}
        if self.artifacts_path.exists():
            for subdir in self.artifacts_path.iterdir():
                if subdir.is_dir():
                    count = len(list(subdir.glob("*.*")))
                    summary[subdir.name] = count
        return summary
    
    def get_git_log(self, limit: int = 10) -> List[str]:
        """Get recent git commits."""
        if not self.repo:
            return []
        
        commits = []
        for commit in self.repo.iter_commits(max_count=limit):
            commits.append(f"{commit.hexsha[:8]} - {commit.message.strip()}")
        return commits


class WorkflowContext:
    """Maintains context across agent executions."""
    
    def __init__(self, project_name: str, config: JarvisConfig):
        self.project_name = project_name
        self.config = config
        self.phase_outputs: Dict[str, AgentOutput] = {}
        self.shared_artifacts: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
    
    def add_phase_output(self, phase_name: str, output: AgentOutput):
        """Add output from a phase."""
        self.phase_outputs[phase_name] = output
        self.shared_artifacts.update(output.artifacts)
        
        self.execution_log.append({
            "timestamp": output.timestamp.isoformat(),
            "phase": phase_name,
            "agent": output.agent_name,
            "status": output.status,
            "artifact_count": len(output.artifacts)
        })
    
    def get_phase_summary(self) -> str:
        """Generate summary of all phases executed."""
        summary = [f"Workflow for project: {self.project_name}"]
        summary.append(f"Start time: {self.start_time.isoformat()}")
        summary.append(f"\nPhases executed: {len(self.phase_outputs)}")
        
        for phase_name, output in self.phase_outputs.items():
            summary.append(f"\n  → {phase_name}: {output.status}")
            summary.append(f"     Agent: {output.agent_name}")
            summary.append(f"     Artifacts: {list(output.artifacts.keys())}")
            if output.errors:
                summary.append(f"     Errors: {', '.join(output.errors)}")
        
        return "\n".join(summary)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export context to dictionary for review."""
        return {
            "project_name": self.project_name,
            "start_time": self.start_time.isoformat(),
            "phases": {name: output.to_dict() for name, output in self.phase_outputs.items()},
            "execution_log": self.execution_log,
            "shared_artifacts_count": len(self.shared_artifacts)
        }


class Orchestrator:
    """Main orchestrator coordinating all agents and artifacts."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get()
        self.router = MultiEndpointRouter(self.config_manager)
        self.artifact_manager = ArtifactManager(self.config)
        self.agents: Dict[str, Any] = {}
        logger.info("Orchestrator initialized")
    
    def register_agent(self, agent_name: str, agent_instance: Any):
        """Register an agent instance."""
        self.agents[agent_name] = agent_instance
        logger.info(f"Registered agent: {agent_name} ({agent_instance.role})")
    
    async def execute_phase(
        self,
        phase_name: str,
        agents_to_run: List[str],
        context: Optional[WorkflowContext] = None,
        sequential: bool = False
    ) -> WorkflowContext:
        """Execute a workflow phase with specified agents."""
        if context is None:
            context = WorkflowContext("jarvis_workflow", self.config)
        
        logger.info(f"═══ Starting phase: {phase_name} ═══")
        
        if sequential:
            # Run agents one by one
            for agent_name in agents_to_run:
                if agent_name not in self.agents:
                    logger.error(f"Agent not found: {agent_name}")
                    continue
                
                agent = self.agents[agent_name]
                logger.info(f"→ Executing {agent.name} ({agent.role})")
                
                try:
                    # Pass context to agent
                    output = await agent.execute(context.to_dict())
                    context.add_phase_output(f"{phase_name}_{agent_name}", output)
                    self.artifact_manager.save_agent_output(output)
                    logger.info(f"  ✓ {output.status.upper()}")
                
                except Exception as e:
                    logger.error(f"  ✗ Agent failed: {e}")
        else:
            # Run agents in parallel
            tasks = [
                self.agents[agent_name].execute(context.to_dict())
                for agent_name in agents_to_run
                if agent_name in self.agents
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for agent_name, result in zip(agents_to_run, results):
                if isinstance(result, Exception):
                    logger.error(f"Agent {agent_name} failed: {result}")
                else:
                    context.add_phase_output(f"{phase_name}_{agent_name}", result)
                    self.artifact_manager.save_agent_output(result)
        
        # Auto-commit if configured
        if self.config.workspace.auto_commit:
            self.artifact_manager.commit_artifacts(phase_name)
        
        logger.info(f"═══ Phase {phase_name} complete ═══\n")
        return context
    
    def generate_diff_preview(self, context: WorkflowContext) -> str:
        """Generate a preview of all changes for review."""
        preview = ["# Workflow Diff Preview", ""]
        
        for phase_name, output in context.phase_outputs.items():
            if output.status == "success":
                preview.append(f"## Phase: {phase_name}")
                preview.append(f"Agent: {output.agent_name}")
                preview.append(f"Status: {output.status}")
                preview.append("")
                
                if output.artifacts:
                    preview.append("### Artifacts Generated:")
                    for artifact_name, artifact_content in output.artifacts.items():
                        preview.append(f"- **{artifact_name}**")
                        if isinstance(artifact_content, str) and len(artifact_content) < 200:
                            preview.append(f"  ```\n  {artifact_content}\n  ```")
                        preview.append("")
                
                if output.reasoning:
                    preview.append(f"### Reasoning:\n{output.reasoning}\n")
        
        git_log = self.artifact_manager.get_git_log(5)
        if git_log:
            preview.append("## Recent Git Commits")
            for commit in git_log:
                preview.append(f"- {commit}")
        
        return "\n".join(preview)
    
    async def execute_full_workflow(self, project_name: str, demo_spec: Dict[str, Any]) -> WorkflowContext:
        """Execute a complete workflow from architecture through deployment."""
        context = WorkflowContext(project_name, self.config)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"  JARVIS - Multi-LLM Workflow Execution")
        logger.info(f"  Project: {project_name}")
        logger.info(f"  Started: {context.start_time.isoformat()}")
        logger.info(f"{'='*60}\n")
        
        # Phase 1: Architecture
        context = await self.execute_phase("ARCHITECTURE", ["architecture"], context, sequential=True)
        
        # Phase 2: Tech Lead (Planning)
        context = await self.execute_phase("PLANNING", ["tech_lead"], context, sequential=True)
        
        # Phase 3: Implementation
        context = await self.execute_phase("IMPLEMENTATION", ["implementation"], context, sequential=False)
        
        # Phase 4: Testing
        context = await self.execute_phase("TESTING", ["testing"], context, sequential=True)
        
        # Phase 5: Documentation
        context = await self.execute_phase("DOCUMENTATION", ["documentation"], context, sequential=True)
        
        # Phase 6: Deployment Validation
        context = await self.execute_phase("DEPLOYMENT", ["deployment"], context, sequential=True)
        
        logger.info(context.get_phase_summary())
        
        # Final commit
        duration = (datetime.now() - context.start_time).total_seconds()
        self.artifact_manager.commit_artifacts("COMPLETE", f"Workflow complete ({duration:.1f}s)")
        
        return context
