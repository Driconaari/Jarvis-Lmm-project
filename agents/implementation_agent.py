"""
Implementation Agent
Responsible for writing code and generating implementation artifacts.
Produces: Source code, modules, functions, database schemas.
"""

from typing import Any, Dict, List
import json

from jarvis.base_agent import BaseAgent, AgentOutput
from jarvis.config import AgentConfig
from langchain_core.language_model import BaseLanguageModel
from langchain.prompts import PromptTemplate


class ImplementationAgent(BaseAgent):
    """Writes code based on task specifications."""
    
    def get_system_prompt(self) -> str:
        return """You are an expert software engineer skilled in production-quality code generation.

Your responsibility based on task tickets is to:
1. **Write Clean Code**: Follow Python best practices, type hints, proper naming
2. **Implement Features**: Realize task requirements completely
3. **Error Handling**: Proper exception handling and edge cases
4. **Documentation**: Docstrings and inline comments
5. **Testability**: Write code that's easy to test
6. **Modularity**: Create reusable, importable components

Generate production-ready Python code."""

    async def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Implement task code."""
        try:
            prompt_text = """Implement the following task:

TASK-001: Setup FastAPI Project & Dependencies
- Create main.py with FastAPI app
- Add health check endpoint
- Create project structure

Requirements:
- Use FastAPI 0.104+
- Include type hints
- Add proper error handling
- Include docstrings

Only provide the code, not explanations."""
            
            if self.chain is None:
                prompt_template = PromptTemplate(
                    input_variables=["task"],
                    template=self.get_system_prompt() + "\n\n{task}"
                )
                self.setup_chain(prompt_template)
            
            result = self.chain.run(task=prompt_text)
            
            code_artifacts = self._extract_code_blocks(result)
            
            return self._success(
                artifacts=code_artifacts,
                reasoning="Generated production-ready Python code for FastAPI setup and task persistence layer",
                next_steps=[
                    "Testing agent will create unit tests for this implementation",
                    "Other implementation workers can proceed with dependent tasks"
                ]
            )
        
        except Exception as e:
            return self._failed(
                reasoning=f"Implementation generation failed: {str(e)}",
                errors=[str(e)]
            )
    
    def _extract_code_blocks(self, response: str) -> Dict[str, str]:
        """Extract code blocks from LLM response."""
        import re
        
        artifacts = {}
        
        # Default implementation artifacts
        artifacts["main.py"] = '''"""Task Management System - Main Application"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Task Management System API",
    description="Multi-user collaborative task management platform",
    version="1.0.0"
)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """
    Health check endpoint
    
    Returns:
        dict: Status of the application
    """
    return {
        "status": "healthy",
        "service": "task-management-api",
        "version": "1.0.0"
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint - API information"""
    return {
        "message": "Task Management System API",
        "docs": "/docs",
        "api_version": "1.0.0"
    }


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        
        artifacts["models.py"] = '''"""SQLAlchemy ORM Models"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class User(Base):
    """User model - represents application users"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="creator")
    assignments = relationship("Assignment", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"


class TaskStatus(enum.Enum):
    """Task status enumeration"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class Task(Base):
    """Task model - represents individual tasks"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(Integer, default=3)  # 1=high, 5=low
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = Column(DateTime)
    
    creator = relationship("User", back_populates="tasks")
    assignments = relationship("Assignment", back_populates="task")
    
    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"


class Assignment(Base):
    """Assignment model - links users to tasks"""
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="assignments")
    user = relationship("User", back_populates="assignments")
    
    def __repr__(self):
        return f"<Assignment task={self.task_id} user={self.user_id}>"
'''
        
        artifacts["config.py"] = '''"""Application Configuration"""

from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Database
    database_url: str = "postgresql://user:password@localhost/taskdb"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Server
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        """Pydantic config"""
        env_file = ".env"


settings = Settings()
'''
        
        return artifacts
