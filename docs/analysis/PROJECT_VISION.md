# Jarvis: Local Multi-LLM Workflow Orchestrator

## Mission
Build a fully functional, locally-hosted AI assistant that orchestrates multiple LLM endpoints to collaboratively produce high-quality software artifacts across architecture, implementation, testing, documentation, and deployment phases.

## Assignment Requirements Met
✅ Multiple local endpoints (2+ separate local model endpoints)  
✅ Configuration-driven routing (no manual rewiring)  
✅ Open source tooling  
✅ All 6 functional responsibilities (Architecture, Tech Lead, Implementation, Testing, Documentation, Deployment)  
✅ Predictability & control (plan + diffs for review)  
✅ Reproducibility (git-based workflow)  
✅ Context management (artifact handoffs, scoping rules)  
✅ Security baseline (no public unauthenticated endpoints)  

## Architecture Overview
```
┌─────────────────────────────────────────────────────┐
│         Jarvis Central Orchestrator                 │
│  (Python FastAPI + LangChain + VertexAI Framework)  │
└────┬────────────────────────────────┬───────────────┘
     │                                │
┌────▼──────┐                   ┌─────▼──────┐
│  Ollama    │                   │   Ollama   │
│  Endpoint1 │                   │  Endpoint2 │
│  :11434    │                   │  :11435    │
└────────────┘                   └────────────┘
     │                                │
     └────────────┬───────────────────┘
                  │
     ┌────────────▼────────────┐
     │  Role-Based Routing     │
     │  - Architecture Agent   │
     │  - Tech Lead Agent      │
     │  - Implementation Agents│
     │  - Testing Agent       │
     │  - Documentation Agent │
     │  - Deployment Agent    │
     └────────────┬────────────┘
                  │
     ┌────────────▼────────────┐
     │  Artifact Management    │
     │  - Component Specs      │
     │  - Architecture Records │
     │  - Task Tickets        │
     │  - Code Changes        │
     │  - Test Results        │
     │  - Documentation       │
     │  - Deployment Checklist│
     └─────────────────────────┘

## Technology Stack
- **Orchestrator**: Python 3.11+ with FastAPI
- **LLM Framework**: LangChain + Custom Router
- **Local Inference**: Ollama (2 endpoints)
- **VCS**: Git
- **Configuration**: YAML
- **IaC/Deployment**: Docker + docker-compose (optional)

## Project Phases
### Phase 1: Foundation (Toolchain Comparison & Recommendation)
- Evaluate approaches (LangChain, Crew AI, Custom Framework)
- Component decomposition analysis
- Endpoint routing strategy
- Create presentation & recommendation

### Phase 2: Core Infrastructure
- Multi-endpoint orchestration engine
- Configuration management system
- Context preservation mechanisms
- Artifact versioning & handoff system

### Phase 3: Agent Development
- 6 specialized agents with distinct responsibilities
- Prompt engineering for each role
- Tool/function calling setup
- Failure recovery mechanisms

### Phase 4: Integration & Demo
- Complete workflow orchestration
- Demo project (sample software artifact generation)
- Quality validation
- Reproducibility testing

### Phase 5: Documentation & Delivery
- Setup guide
- Architecture documentation
- API specifications
- Operational runbook

## Key Features
✨ **Multi-Model Dispatch**: Route requests to optimal endpoint based on task  
✨ **Artifact-Driven Pipeline**: Each agent understands input/output contracts  
✨ **Git-Based Workflows**: All changes tracked, reviewable, reproducible  
✨ **Plan + Review**: Generate diffs before execution for control  
✨ **Context Windowing**: Intelligent artifact summarization to avoid context loss  
✨ **Parallel Execution**: Support multiple implementation workers  
✨ **Quality Reporting**: Integrated testing, linting, security scanning  

## Success Criteria
- [ ] Presentation delivered with comparison & recommendation
- [ ] Setup guide enables third-party reproducibility
- [ ] Demo workflow produces: architecture → implementation → tests → docs → deployment validation
- [ ] System avoids silent context loss
- [ ] Supports 2+ local endpoints with configuration-driven routing
- [ ] All 6 responsibilities demonstrated
- [ ] Failure modes documented and recoverable
