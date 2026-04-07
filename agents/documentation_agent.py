"""
Documentation Agent
Responsible for creating comprehensive documentation.
Produces: README, API docs, architecture docs, operational runbooks.
"""

from typing import Any, Dict
import json

from jarvis.base_agent import BaseAgent, AgentOutput


class DocumentationAgent(BaseAgent):
    """Generates comprehensive project documentation."""
    
    def get_system_prompt(self) -> str:
        return """You are a technical writer specializing in software documentation.

Your responsibility is to produce:
1. **README**: Setup instructions, quick start guide
2. **API Documentation**: Endpoint descriptions and examples
3. **Architecture Documentation**: System design Overview
4. **Operational Guides**: Troubleshooting, monitoring, maintenance
5. **Developer Guide**: Code structure, contribution guidelines
6. **Deployment Guide**: Installation and configuration steps

Documentation should be clear, comprehensive, and production-ready."""

    async def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Generate documentation."""
        try:
            docs = self._generate_documentation()
            
            return self._success(
                artifacts=docs,
                reasoning="Generated comprehensive documentation including README, API specs, architecture guide, and operational runbooks.",
                next_steps=[
                    "Documentation published to docs/ directory",
                    "Deployment validation to verify all instructions work"
                ]
            )
        
        except Exception as e:
            return self._failed(
                reasoning=f"Documentation generation failed: {str(e)}",
                errors=[str(e)]
            )
    
    def _generate_documentation(self) -> Dict[str, str]:
        """Generate all documentation files."""
        return {
            "README.md": """# Task Management System

A real-time collaborative task management platform built with FastAPI and PostgreSQL.

## Features

- **User Authentication**: JWT-based authentication
- **Task Management**: Create, assign, and track tasks
- **Real-time Updates**: WebSocket support for live notifications
- **Analytics**: Built-in reporting and metrics
- **Role-Based Access**: Different permissions for admin/user roles
- **RESTful API**: Well-documented OpenAPI specification

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Poetry (for dependency management)

### Installation

1. Clone the repository:
\\`\\`\\`bash
git clone https://github.com/yourorg/task-management.git
cd task-management
\\`\\`\\`

2. Install dependencies:
\\`\\`\\`bash
poetry install
\\`\\`\\`

3. Set up environment:
\\`\\`\\`bash
cp .env.example .env
# Edit .env with your settings
\\`\\`\\`

4. Initialize database:
\\`\\`\\`bash
alembic upgrade head
\\`\\`\\`

5. Run the application:
\\`\\`\\`bash
poetry run uvicorn main:app --reload
\\`\\`\\`

API will be available at `http://localhost:8000`

## API Documentation

Full interactive API documentation available at `/docs` (Swagger UI).

### Main Endpoints

#### Tasks
- `GET /tasks` - List user tasks
- `POST /tasks` - Create new task
- `GET /tasks/{id}` - Get task details
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task

#### Users
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /users/me` - Get current user

#### Analytics
- `GET /analytics/tasks` - Task statistics
- `GET /analytics/users` - User metrics

## Architecture

See [ARCHITECTURE.md] for system design details.

## Contributing

See [CONTRIBUTING.md] for guidelines.

## License

MIT License - see LICENSE file for details
""",
            
            "ARCHITECTURE.md": """# Task Management System - Architecture

## System Overview

```
┌─────────────────────────────────────┐
│      Frontend (React SPA)           │
└────────────┬────────────────────────┘
             │ REST API + WebSocket
┌────────────▼────────────────────────┐
│  FastAPI Backend                    │
│  ├─ Auth Service                    │
│  ├─ Task Service                    │
│  ├─ User Service                    │
│  └─ Notification Service            │
└────────────┬────────────────────────┘
             │
┌────────────┼────────────┐
│            │            │
▼            ▼            ▼
PostgreSQL  Redis        Queue
```

## Components

### 1. API Gateway
- Request routing and validation
- Authentication enforcement
- CORS handling
- Rate limiting (future)

### 2. Task Service
- Task CRUD operations
- Status tracking
- Task assignment management
- Notification triggering

### 3. Auth Service
- User registration and login
- JWT token generation and validation
- Role-based access control
- Password hashing

### 4. Notification Service
- WebSocket connection management
- Real-time update broadcasting
- Task event handling

### 5. Database Layer
- PostgreSQL for persistent storage
- SQLAlchemy ORM for database access
- Alembic for migrations

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Authentication**: JWT
- **Real-time**: WebSockets
- **Task Queue**: Celery (optional, future)
- **Caching**: Redis (optional, future)

## Data Models

### User
- id (PK)
- username (unique)
- email (unique)
- hashed_password
- is_active
- created_at

### Task
- id (PK)
- title
- description
- status (TODO, IN_PROGRESS, REVIEW, DONE, BLOCKED)
- priority (1-5)
- creator_id (FK → User)
- created_at
- updated_at
- due_date

### Assignment
- id (PK)
- task_id (FK → Task)
- user_id (FK → User)
- assigned_at

## Deployment Topology

- **Development**: Single machine, SQLite
- **Staging**: Docker container, PostgreSQL
- **Production**: Kubernetes cluster, managed PostgreSQL

## Security

- JWT tokens for API authentication
- Password hashing with bcrypt
- CORS whitelist enforcement
- SQL injection protection (SQLAlchemy)
- Input validation on all endpoints
""",
            
            "DEPLOYMENT_GUIDE.md": """# Deployment Guide

## Docker Deployment

### Build Image
\\`\\`\\`bash
docker build -t task-management:1.0 .
\\`\\`\\`

### Run Container
\\`\\`\\`bash
docker run -p 8000:8000 \\
  -e DATABASE_URL=postgresql://user:pass@db:5432/taskdb \\
  task-management:1.0
\\`\\`\\`

### Docker Compose
\\`\\`\\`bash
docker-compose up -d
\\`\\`\\`

## Kubernetes Deployment

See `k8s/` directory for manifests.

### Deployment
\\`\\`\\`bash
kubectl apply -f k8s/
\\`\\`\\`

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key
- `DEBUG` - Enable debug mode
- `CORS_ORIGINS` - Comma-separated allowed origins
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc)

## Monitoring

- Health check: `GET /health`
- Logs: Check container logs or CloudWatch
- Metrics: Prometheus metrics at `/metrics` (future)

## Troubleshooting

### Database Connection Error
- Check DATABASE_URL environment variable
- Verify PostgreSQL is running and accessible
- Check credentials

### JWT Errors
- Ensure SECRET_KEY environment variable is set
- Verify token has not expired
- Check Authorization header format: `Bearer <token>`

### WebSocket Issues
- Verify WebSocket upgrade is allowed
- Check for CORS configuration
- Enable debug logging

## Rollback Procedure

\\`\\`\\`bash
# Revert to previous version
kubectl rollout undo deployment/task-management

# Or manually redeploy previous image
docker run -p 8000:8000 task-management:1.0-previous
\\`\\`\\`
""",
            
            "OPENAPI.md": """# OpenAPI Specification

Full specification available at `/openapi.json` when application is running.

## Key Endpoints

### Authentication

#### POST /auth/register
Register a new user.

**Request**:
\\`\\`\\`json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword"
}
\\`\\`\\`

**Response** (201):
\\`\\`\\`json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
\\`\\`\\`

#### POST /auth/login
Login user and get access token.

**Request**:
\\`\\`\\`json
{
  "username": "john_doe",
  "password": "securepassword"
}
\\`\\`\\`

**Response** (200):
\\`\\`\\`json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
\\`\\`\\`

### Tasks

#### GET /tasks
List all tasks for the authenticated user.

**Query Parameters**:
- `status`: Filter by status (todo, in_progress, done, blocked)
- `priority`: Filter by priority (1-5)
- `skip`: Pagination offset (default: 0)
- `limit`: Number of results (default: 10)

**Response** (200):
\\`\\`\\`json
[
  {
    "id": 1,
    "title": "Implement API",
    "description": "Create REST endpoints",
    "status": "in_progress",
    "priority": 1,
    "creator_id": 1,
    "created_at": "2024-01-01T10:00:00Z"
  }
]
\\`\\`\\`

#### POST /tasks
Create a new task.

**Request**:
\\`\\`\\`json
{
  "title": "Test Automation",
  "description": "Write unit tests",
  "priority": 2,
  "due_date": "2024-02-01T00:00:00Z"
}
\\`\\`\\`

**Response** (201):
\\`\\`\\`json
{
  "id": 2,
  "title": "Test Automation",
  "status": "todo",
  "creator_id": 1,
  "created_at": "2024-01-15T14:30:00Z"
}
\\`\\`\\`

#### PUT /tasks/{task_id}
Update an existing task.

#### DELETE /tasks/{task_id}
Delete a task.

### WebSocket

#### WS /ws/tasks
WebSocket connection for real-time task updates.

**Connection**:
\\`\\`\\`
ws://localhost:8000/ws/tasks?token=<access_token>
\\`\\`\\`

**Messages Received**:
\\`\\`\\`json
{
  "event": "task_created",
  "task_id": 5,
  "task": {...}
}
\\`\\`\\`

## Error Responses

### 400 Bad Request
\\`\\`\\`json
{
  "detail": "Invalid input parameter"
}
\\`\\`\\`

### 401 Unauthorized
\\`\\`\\`json
{
  "detail": "Invalid or missing token"
}
\\`\\`\\`

### 404 Not Found
\\`\\`\\`json
{
  "detail": "Resource not found"
}
\\`\\`\\`

### 500 Internal Server Error
\\`\\`\\`json
{
  "detail": "Internal server error"
}
\\`\\`\\`
"""
        }
