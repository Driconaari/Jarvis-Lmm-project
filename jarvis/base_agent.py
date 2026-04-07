"""
Base Agent Class
Foundation for all specialized agents in the Jarvis workflow.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json
from loguru import logger
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate

from jarvis.config import AgentConfig


@dataclass
class AgentOutput:
    """Standardized output from an agent."""
    agent_name: str
    role: str
    status: str  # "success", "partial", "failed"
    timestamp: datetime
    artifacts: Dict[str, Any]  # Generated outputs
    reasoning: str  # Explanation of what was done
    errors: List[str] = None
    next_steps: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.next_steps is None:
            self.next_steps = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling datetime serialization."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class BaseAgent(ABC):
    """Base class for all Jarvis agents."""
    
    def __init__(self, llm: BaseLanguageModel, config: AgentConfig):
        self.llm = llm
        self.config = config
        self.chain = None
        logger.info(f"Initializing {config.name} agent ({config.role})")
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def role(self) -> str:
        return self.config.role
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's responsibilities."""
        pass
    
    def setup_chain(self, prompt_template: PromptTemplate) -> Optional[Any]:
        """Setup the LLM chain with given prompt template."""
        # Note: LLMChain is deprecated in newer LangChain versions
        # Storing prompt template directly for now
        self.chain = prompt_template
        logger.debug(f"{self.name} chain setup complete")
        return self.chain
    
    def _create_output(
        self,
        status: str,
        artifacts: Dict[str, Any],
        reasoning: str,
        errors: List[str] = None,
        next_steps: List[str] = None
    ) -> AgentOutput:
        """Create standardized agent output."""
        return AgentOutput(
            agent_name=self.name,
            role=self.role,
            status=status,
            timestamp=datetime.now(),
            artifacts=artifacts,
            reasoning=reasoning,
            errors=errors or [],
            next_steps=next_steps or []
        )
    
    def _success(self, artifacts: Dict[str, Any], reasoning: str, next_steps: List[str] = None) -> AgentOutput:
        """Create success output."""
        return self._create_output("success", artifacts, reasoning, next_steps=next_steps)
    
    def _partial(self, artifacts: Dict[str, Any], reasoning: str, errors: List[str], next_steps: List[str] = None) -> AgentOutput:
        """Create partial success output."""
        return self._create_output("partial", artifacts, reasoning, errors, next_steps)
    
    def _failed(self, reasoning: str, errors: List[str]) -> AgentOutput:
        """Create failed output."""
        return self._create_output("failed", {}, reasoning, errors)
    
    async def retry_with_fallback(self, max_retries: int = 3) -> AgentOutput:
        """Base retry logic with exponential backoff."""
        for attempt in range(max_retries):
            try:
                # Subclasses override execute()
                return await self.execute({})
            except Exception as e:
                logger.warning(f"{self.name} attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return self._failed(
                        f"Failed after {max_retries} attempts",
                        [str(e)]
                    )
                # Exponential backoff
                import asyncio
                await asyncio.sleep(2 ** attempt)
        
        return self._failed("Unknown failure", ["Exhausted retry attempts"])
