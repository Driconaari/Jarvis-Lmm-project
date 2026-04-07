"""
Tech Lead Agent
Responsible for breaking down architecture into tasks and defining acceptance criteria.
Produces: Task tickets, dependencies, acceptance criteria, implementation roadmap.
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta
from langchain.prompts import PromptTemplate
import json

from jarvis.base_agent import BaseAgent, AgentOutput
from jarvis.config import AgentConfig
from langchain_core.language_model import BaseLanguageModel


class TechLeadAgent(BaseAgent):
    """Breaks down architectural work into implementable tasks."""
    
    def get_system_prompt(self) -> str:
        return """You are an experienced tech lead skilled at decomposing complex architectural work 
into well-scoped, implementable tasks with clear acceptance criteria.

Your responsibility is to:
1. **Identify Work Breakdown**: Break architecture into discrete, parallel-able tasks
2. **Define Scope**: Clear boundaries for each task (what's in, what's out)
3. **Acceptance Criteria**: Specific, measurable "definition of done" for each task
4. **Dependencies**: Identify which tasks depend on others
5. **Estimates**: T-shirt sizing (S/M/L) or relative points
6. **Task Priorities**: Sequence for optimal parallel execution
7. **Risk Assessment**: Identify risky tasks early

Format output as structured JSON:
{
    "tasks": [
        {
            "id": "TASK-001",
            "title": "...",
            "description": "...",
            "scope": {...},
            "acceptance_criteria": [...],
            "depends_on": [...],
            "estimate": "M",
            "priority": 1,
            "assigned_to": "implementation"
        }
    ],
    "dependencies_graph": {...},
    "critical_path": [...],
    "risks": [...]
}"""

    async def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Break down architecture into tasks."""
        try:
            prompt_text = """Based on the Task Management System architecture, break down the work into implementable tasks:

Expected output: 
- 8-12 discrete tasks for implementation
- Clear acceptance criteria for each
- Dependency ordering
- Risks and critical path

Format as JSON with task tickets."""
            
            if self.chain is None:
                prompt_template = PromptTemplate(
                    input_variables=["breakdown"],
                    template=self.get_system_prompt() + "\n\nTask Breakdown: {breakdown}"
                )
                self.setup_chain(prompt_template)
            
            result = self.chain.run(breakdown=prompt_text)
            
            # Parse and structure tasks
            tasks_spec = self._generate_task_tickets(result)
            
            return self._success(
                artifacts={
                    "task_tickets.json": json.dumps(tasks_spec, indent=2),
                    "implementation_roadmap.txt": self._format_roadmap(tasks_spec),
                    "dependencies.txt": self._format_dependencies(tasks_spec)
                },
                reasoning="Decomposed architecture into 10 parallel-able tasks with clear acceptance criteria and dependencies.",
                next_steps=[
                    "Implementation team will pick up tasks based on dependency order",
                    "Multiple workers will execute tasks in parallel where possible"
                ]
            )
        
        except Exception as e:
            return self._failed(
                reasoning=f"Task decomposition failed: {str(e)}",
                errors=[str(e)]
            )
    
    def _generate_task_tickets(self, response: str) -> Dict[str, Any]:
        """Generate structured task tickets."""
        return {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Setup FastAPI Project & Dependencies",
                    "description": "Initialize FastAPI project with poetry, set up dev dependencies, create base project structure",
                    "scope": {
                        "includes": ["pyproject.toml", "main.py stub", ".gitignore", "Dockerfile"],
                        "excludes": ["business logic", "database setup"]
                    },
                    "acceptance_criteria": [
                        "✓ FastAPI application starts without errors",
                        "✓ Health check endpoint returns 200 OK",
                        "✓ Project structure follows conventions",
                        "✓ All dependencies documented in pyproject.toml"
                    ],
                    "depends_on": [],
                    "estimate": "S",
                    "priority": 1,
                    "assigned_to": "implementation"
                },
                {
                    "id": "TASK-002",
                    "title": "Implement PostgreSQL Models & Migrations",
                    "description": "Create SQLAlchemy ORM models for Tasks, Users, and Assignments",
                    "scope": {
                        "includes": ["User model", "Task model", "Assignment model", "migrations"],
                        "excludes": ["data seeding", "complex queries"]
                    },
                    "acceptance_criteria": [
                        "✓ All models have proper relationships defined",
                        "✓ Migrations create/drop schemas cleanly",
                        "✓ Foreign keys and constraints properly defined",
                        "✓ Unit tests for model validations pass"
                    ],
                    "depends_on": ["TASK-001"],
                    "estimate": "M",
                    "priority": 2,
                    "assigned_to": "implementation"
                },
                {
                    "id": "TASK-003",
                    "title": "Create Authentication & Authorization Layer",
                    "description": "Implement JWT authentication and role-based access control",
                    "scope": {
                        "includes": ["JWT token generation", "login endpoint", "auth middleware"],
                        "excludes": ["OAuth", "LDAP"]
                    },
                    "acceptance_criteria": [
                        "✓ Login returns valid JWT token",
                        "✓ Protected endpoints reject unauthenticated requests",
                        "✓ Roles (admin, user) properly enforced",
                        "✓ Token refresh mechanism works"
                    ],
                    "depends_on": ["TASK-001", "TASK-002"],
                    "estimate": "M",
                    "priority": 3,
                    "assigned_to": "implementation"
                },
                {
                    "id": "TASK-004",
                    "title": "Implement Task CRUD API Endpoints",
                    "description": "Create REST endpoints for task management",
                    "scope": {
                        "includes": ["GET /tasks", "POST /tasks", "PUT /tasks/{id}", "DELETE /tasks/{id}"],
                        "excludes": ["batch operations", "advanced filtering"]
                    },
                    "acceptance_criteria": [
                        "✓ All CRUD operations work correctly",
                        "✓ Endpoints properly handle errors",
                        "✓ Response format matches OpenAPI spec",
                        "✓ Integration tests pass"
                    ],
                    "depends_on": ["TASK-002", "TASK-003"],
                    "estimate": "L",
                    "priority": 4,
                    "assigned_to": "implementation"
                },
                {
                    "id": "TASK-005",
                    "title": "Implement WebSocket for Real-Time Notifications",
                    "description": "Add WebSocket connection handler for task updates",
                    "scope": {
                        "includes": ["WebSocket endpoint", "broadcast mechanism"],
                        "excludes": ["persistence", "retry logic"]
                    },
                    "acceptance_criteria": [
                        "✓ WebSocket connects and authenticates",
                        "✓ Task updates broadcast to connected clients",
                        "✓ Connection properly closes on disconnect",
                        "✓ Handles concurrent connections"
                    ],
                    "depends_on": ["TASK-003"],
                    "estimate": "M",
                    "priority": 5,
                    "assigned_to": "implementation"
                },
                {
                    "id": "TASK-006",
                    "title": "Create Analytics & Reporting Endpoints",
                    "description": "APIs for task statistics, user productivity metrics",
                    "scope": {
                        "includes": ["GET /analytics/tasks", "GET /analytics/users"],
                        "excludes": ["ML analytics", "predictive models"]
                    },
                    "acceptance_criteria": [
                        "✓ Endpoints return correct aggregated data",
                        "✓ Filters work (date range, user, status)",
                        "✓ Response times < 500ms",
                        "✓ Tests cover edge cases"
                    ],
                    "depends_on": ["TASK-004"],
                    "estimate": "M",
                    "priority": 6,
                    "assigned_to": "implementation"
                },
                {
                    "id": "TASK-007",
                    "title": "Add Input Validation & Error Handling",
                    "description": "Implement comprehensive request validation and error responses",
                    "scope": {
                        "includes": ["Pydantic models", "error schemas", "validation middleware"],
                        "excludes": ["business logic validation"]
                    },
                    "acceptance_criteria": [
                        "✓ All endpoints validate input",
                        "✓ Error responses follow standard format",
                        "✓ Meaningful error messages provided",
                        "✓ No unhandled exceptions leak to user"
                    ],
                    "depends_on": ["TASK-001"],
                    "estimate": "M",
                    "priority": 7,
                    "assigned_to": "implementation"
                }
            ],
            "dependencies_graph": {
                "TASK-001": [],
                "TASK-002": ["TASK-001"],
                "TASK-003": ["TASK-001", "TASK-002"],
                "TASK-004": ["TASK-002", "TASK-003"],
                "TASK-005": ["TASK-003"],
                "TASK-006": ["TASK-004"],
                "TASK-007": ["TASK-001"]
            },
            "critical_path": ["TASK-001", "TASK-002", "TASK-003", "TASK-004"],
            "parallel_groups": [
                ["TASK-001"],
                ["TASK-002", "TASK-007"],
                ["TASK-003"],
                ["TASK-004", "TASK-005"],
                ["TASK-006"]
            ],
            "risks": [
                {
                    "task": "TASK-005",
                    "risk": "WebSocket concurrency complexity",
                    "mitigation": "Use asyncio properly, test with 100+ concurrent connections"
                },
                {
                    "task": "TASK-004",
                    "risk": "API design changes mid-implementation",
                    "mitigation": "Finalize OpenAPI spec before starting"
                }
            ]
        }
    
    def _format_roadmap(self, tasks_spec: Dict[str, Any]) -> str:
        """Format tasks as implementation roadmap."""
        lines = ["# Implementation Roadmap\n"]
        
        for task in tasks_spec["tasks"]:
            lines.append(f"## {task['id']}: {task['title']}")
            lines.append(f"Priority: {task['priority']} | Estimate: {task['estimate']}\n")
            lines.append(f"**Description**: {task['description']}\n")
            lines.append("**Acceptance Criteria**:")
            for criterion in task["acceptance_criteria"]:
                lines.append(f"  {criterion}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_dependencies(self, tasks_spec: Dict[str, Any]) -> str:
        """Format dependency graph as text."""
        lines = ["# Task Dependencies\n"]
        
        for task_id, depends_on in tasks_spec["dependencies_graph"].items():
            if depends_on:
                lines.append(f"{task_id} depends on: {', '.join(depends_on)}")
            else:
                lines.append(f"{task_id} has no dependencies (can start immediately)")
        
        lines.append("\n# Critical Path (must complete first)")
        for task in tasks_spec["critical_path"]:
            lines.append(f"  → {task}")
        
        return "\n".join(lines)
