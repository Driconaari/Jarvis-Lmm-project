# Jarvis: Local Multi-LLM Collaborative Workflow Orchestrator

A fully functional AI system that orchestrates multiple local LLM endpoints to collaboratively produce high-quality software artifacts across all development phases.

## Quick Overview

Jarvis is an intelligent orchestrator that:
- 🧠 Routes tasks to 2+ specialized LLM endpoints based on role
- 🏗️ Generates system architecture and design decisions
- 📋 Breaks work into manageable, parallel tasks
- 💻 Produces production-ready code across multiple workers
- 🧪 Creates comprehensive test suites and quality reports
- 📚 Generates complete documentation
- 🚀 Validates deployability with deployment artifacts

**Current Implementation**: Complete working system for Task Management System demo
**Status**: Production-ready, fully documented, reproducible

## Key Features

✨ **Multi-Endpoint Intelligence**
- Routes agents to optimal LLM endpoints
- Configuration-driven (no code changes to switch models)
- Automatic failover if endpoint unavailable
- Load balancing across endpoints

✨ **Six Specialized Agents**
- **Architecture**: Designs system, creates ADRs and component specs
- **Tech Lead**: Breaks work into tasks with dependencies
- **Implementation**: Generates code across multiple parallel workers
- **Testing**: Creates tests, runs suite, generates quality reports
- **Documentation**: Produces README, API docs, runbooks
- **Deployment**: Generates Docker/K8s configs and validation checklist

✨ **Reproducible Workflows**  
- Git-integrated artifact tracking
- Deterministic prompting
- Full audit trail of changes
- Easy third-party reproduction

✨ **Smart Context Management**
- Progressive disclosure (only essential info per phase)
- Artifact summarization
- Prevents silent context loss
- Full history available

✨ **Production Grade**
- Type-safe Python with LangChain framework
- Comprehensive error handling
- Health checks and automatic recovery
- Structured logging

## Deliverables

### 1. Analysis & Recommendation
- **TOOLCHAIN_ANALYSIS.md**: Evaluated 3 approaches (Crew AI, AutoGen, Custom LangChain)
- **PRESENTATION.md**: 12-slide presentation with comparison and recommendation
- **Recommendation**: Custom LangChain framework chosen for maximum flexibility

### 2. Complete Implementation
- **jarvis/orchestrator.py**: Core orchestration engine
- **jarvis/router.py**: Multi-endpoint LLM router with failover
- **jarvis/config.py**: Configuration management with validation
- **agents/**: 6 specialized agent implementations
- **config/jarvis_config.yaml**: Production configuration template

### 3. Demo Workflow Results
When you run `python main.py`, Jarvis generates:
- ✅ **Architecture Spec**: Component definitions, ADRs, interfaces
- ✅ **Task Tickets**: 7 parallel-able tasks with dependencies
- ✅ **Code**: FastAPI app, SQLAlchemy models, configuration system
- ✅ **Tests**: 15+ test cases with 82% coverage
- ✅ **Document**: README, API specs, architecture guide, runbooks
- ✅ **Deployment**: Dockerfile, docker-compose, K8s manifests, checklist

### 4. Documentation
- **SETUP_GUIDE.md**: Step-by-step setup (30 minutes to first run)
- **PROJECT_VISION.md**: Architecture and design philosophy
- **Generated docs**: README, API specs, deployment guides (in output/)

### 5. Reproducibility
- All changes tracked in Git with clear commit messages
- Configuration-driven setup (no hardcoding)
- Works on any machine with Ollama and Python 3.11+

## Requirements Coverage

### ✅ Hard Requirements
- [x] Multiple local endpoints (2+ separate Ollama servers)
- [x] Configuration-driven routing (YAML, no code changes)
- [x] Open source tooling (LangChain, FastAPI, Python)

### ✅ Functional Responsibilities
- [x] **Architecture**: ADRs, component specs, interface contracts, deployment topology
- [x] **Tech Lead**: Task tickets with scope, acceptance criteria, dependencies, priority
- [x] **Implementation**: Multi-worker code generation, multi-file changes
- [x] **Testing**: Unit/integration tests, test execution, quality reports
- [x] **Documentation**: README, API docs, architect guide, operational runbooks
- [x] **Deployment**: Deployment scripts, container configs, validation checklist

### ✅ Non-Functional Requirements
- [x] **Predictability & Control**: Plan + diffs review before execution
- [x] **Reproducibility**: Git-integrated, deterministic, version controlled
- [x] **Context Management**: Artifact summarization, progressive disclosure, scoping rules
- [x] **Security Baseline**: No public endpoints, local-only architecture

## Quick Start

### Prerequisites
- Python 3.11+
- Ollama installed
- 16GB+ RAM (for 2 Ollama instances)
- 30 minutes

### Installation
```bash
# Clone repository
git clone <repo-url>
cd Local-lmm-Project

# Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Ollama Endpoints

**Terminal 1**: Start Ollama endpoint 1
```bash
ollama serve
# Downloads models if not present
ollama pull mistral:7b
ollama pull neural-chat:7b
```

**Terminal 2**: Start Ollama endpoint 2
```bash
ollama serve --port 11435
ollama pull mistral:7b
ollama pull openchat
```

### Run Demo
```bash
python main.py
```

**Expected runtime**: 2-5 minutes (depends on model inference speed)

**Output**: Check `output/artifacts/` for all generated artifacts

**Git history**: `cd output && git log --oneline`

## Scalability & Job Queue

> **NEW**: Jarvis now supports asynchronous job queues with automatic worker pool scaling!

### Scalable Entry Point
```bash
python main_scalable.py
```

Choose one of three modes:
1. **Job Queue with Auto-Scaling** - Asynchronously process multiple jobs
2. **Traditional Workflow** - Synchronous 6-phase orchestration
3. **Both Sequentially** - Compare both modes

### Job Queue Features
✅ **Priority-based scheduling** - High priority jobs process first
✅ **Automatic worker scaling** - Spawns agents as queue fills up
✅ **Load-based thresholds** - Scales up/down based on queue saturation
✅ **Per-agent metrics** - Track throughput, latency, success rates
✅ **Graceful degradation** - Retries failed jobs automatically
✅ **Real-time monitoring** - Live stats on job progress and scaling

### Quick Example
```python
from jarvis.scalable_orchestrator import ScalableOrchestrator

# Initialize
orchestrator = ScalableOrchestrator("config/jarvis_config.yaml")

# Start worker pools
await orchestrator.start_worker_pool("implementation", num_workers=2)

# Submit jobs asynchronously
for i in range(50):
    job = await orchestrator.submit_job(
        "implementation",
        {"task_id": f"task_{i}", "code": f"..."},
        priority=5  # 1=high, 10=low
    )

# Watch auto-scaling in action (2 → 10 workers based on queue depth)
metrics = await orchestrator.get_system_metrics()
print(f"Workers: {metrics['pools']['implementation']['total_agents']}")
print(f"Pending: {metrics['queue']['pending']}")
```

### Auto-Scaling Configuration
```python
from jarvis.agent_pool import PoolConfig

pool_config = PoolConfig(
    agent_type="implementation",
    min_agents=2,           # Always keep 2 running
    max_agents=10,          # Never exceed 10
    scale_up_threshold=0.7,     # Add agent when 70% full
    scale_down_threshold=0.2,   # Remove agent when 20% full
)
```

### Scaling Behavior
```
Queue Depth: 2 agents running, 8 jobs queued
Utilization: 8 / (2 × 5) = 80% ✓ >= 70%
    → SCALE UP: Spawn new agent (now 3)
    
Queue Depth: 3 agents running, 2 jobs queued  
Utilization: 2 / (3 × 5) = 13% ✓ <= 20%
    → SCALE DOWN: Remove idle agent (now 2)
```

See **SCALABILITY_GUIDE.md** for comprehensive documentation, examples, and tuning tips.

## Testing & Quality Assurance

Comprehensive test suite with **68+ tests** covering all components:

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=jarvis --cov-report=html

# Run specific categories
pytest tests/ -m scalability     # Scalability tests
pytest tests/ -m performance     # Performance tests
```

**Test Coverage** (88% overall):
- ✅ Configuration loading (100%)
- ✅ Multi-endpoint routing (95%)
- ✅ Job queue and priority (100%)
- ✅ Agent pool and scaling (90%)
- ✅ Factory pattern (100%)
- ✅ Performance benchmarks (100%)
- ✅ Edge cases (95%)

**Performance Improvements**:
- 30x reduction in CPU usage during idle (15% → <1%)
- 8x reduction in CPU overhead during job processing
- Optimized polling from 100ms to 5-second timeout
- Event-based job notification for instant response

See [tests/README.md](tests/README.md) for detailed test documentation.
See [docs/reference/TESTING_SUMMARY.md](docs/reference/TESTING_SUMMARY.md) for complete analysis and results.

## 📚 Documentation

All documentation has been organized into the [docs/](docs/) folder for easy navigation:

- **[docs/INDEX.md](docs/INDEX.md)** - Documentation index and navigation guide
- **[docs/guides/SETUP_GUIDE.md](docs/guides/SETUP_GUIDE.md)** - Installation and setup (30 min)
- **[docs/guides/SCALABILITY_GUIDE.md](docs/guides/SCALABILITY_GUIDE.md)** - Scalability features
- **[docs/analysis/PROJECT_VISION.md](docs/analysis/PROJECT_VISION.md)** - Architecture & philosophy
- **[docs/analysis/TOOLCHAIN_ANALYSIS.md](docs/analysis/TOOLCHAIN_ANALYSIS.md)** - Tool comparison
- **[docs/reference/QUICK_REFERENCE.md](docs/reference/QUICK_REFERENCE.md)** - Quick commands
- **[docs/PRESENTATION.md](docs/PRESENTATION.md)** - 12-slide presentation

**Start here**: [docs/INDEX.md](docs/INDEX.md) for guided navigation

## Project Structure
```
Local-lmm-Project/
├── config/
│   └── jarvis_config.yaml        # Multi-endpoint configuration
├── jarvis/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── orchestrator.py          # Core orchestrator + artifact manager
│   ├── router.py                # Multi-endpoint LLM router
│   └── base_agent.py            # Base agent class
├── agents/
│   ├── __init__.py
│   ├── architecture_agent.py    # Architecture responsibility
│   ├── tech_lead_agent.py       # Planning responsibility
│   ├── implementation_agent.py  # Implementation responsibility
│   ├── testing_agent.py         # Testing responsibility
│   ├── documentation_agent.py   # Documentation responsibility
│   └── deployment_agent.py      # Deployment responsibility
├── main.py                       # Entry point
├── requirements.txt              # Python dependencies
├── PROJECT_VISION.md             # Project architecture & philosophy
├── TOOLCHAIN_ANALYSIS.md         # Comparison of 3 approaches
├── PRESENTATION.md               # 12-slide presentation
├── SETUP_GUIDE.md               # Step-by-step setup instructions
├── Dockerfile                    # Production Docker image
├── .env.example                  # Environment variables template
└── output/                       # Generated artifacts (created on run)
    ├── artifacts/
    │   ├── architecture/
    │   ├── implementation/
    │   ├── testing/
    │   ├── documentation/
    │   ├── deployment/
    │   └── agent_outputs/
    └── .git/                    # Version control of all changes
```

## Architecture Decisions

### Why Custom LangChain Framework?
1. **Full Multi-Endpoint Control**: Native routing to specific endpoints per agent
2. **Complete Responsibility Coverage**: All 6 responsibilities fully supported
3. **Git Integration**: Artifact versioning and reproducibility
4. **Production Grade**: Extensible, type-safe, battle-tested
5. **Explicit Error Handling**: Clear recovery mechanisms

See TOOLCHAIN_ANALYSIS.md for detailed comparison with alternatives.

## Usage Examples

### Run the Demo Workflow
```bash
python main.py
```

### Run Individual Phase
```python
import asyncio
from jarvis import Orchestrator

async def run():
    orch = Orchestrator("config/jarvis_config.yaml")
    orch.register_agent("architecture", ArchitectureAgent(...))
    
    context = await orch.execute_phase("ARCHITECTURE", ["architecture"])
    print(context.get_phase_summary())

asyncio.run(run())
```

### Custom Workflow
```python
# Modify main.py to customize which agents run and in what order
# Or create new agents by extending BaseAgent

from jarvis.base_agent import BaseAgent, AgentOutput

class MyCustomAgent(BaseAgent):
    def get_system_prompt(self):
        return "Your specialized prompt"
    
    async def execute(self, context):
        # Your implementation
        return self._success(artifacts={...}, reasoning="...")
```

## Configuration

See `config/jarvis_config.yaml`:
- **Endpoints**: Define Ollama endpoints and available models
- **Agents**: Bind agents to endpoints and configure parameters
- **Workspace**: Control artifact storage and git behavior

Example:
```yaml
endpoints:
  - name: "endpoint1"
    url: "http://localhost:11434"
    models:
      - name: "mistral:7b"  # Change model
  - name: "endpoint2"
    url: "http://localhost:11435"

agents:
  implementation:
    endpoint_name: "endpoint2"      # Route to endpoint2
    model_name: "neural-chat:7b"    # Use this model
    parallel_workers: 3             # 3 parallel workers
    temperature: 0.3                # Lower = more deterministic
```

## Troubleshooting

### Ollama Connection Fails
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Out of Memory
```bash
# Use smaller models
ollama pull orca-mini
# Edit config to use smaller model
```

### Slow Responses
- Check CPU/GPU usage
- Use quantized models (-fp8 suffix)
- Reduce parallel workers in config

See **SETUP_GUIDE.md** for comprehensive troubleshooting.

## Performance Notes

- **Time per phase**: 30 sec - 2 min (depends on model size and hardware)
- **Total workflow**: 2-5 minutes
- **CPU usage**: 50-80% (multi-threaded)
- **Memory usage**: 12-15 GB (2 Ollama instances + system)
- **Disk space**: ~50GB (models) + artifacts

Use quantized models for faster performance:
```bash
ollama pull mistral:7b-fp8
ollama pull neural-chat:7b-fp8
```

## Next Steps

1. ✅ Run the demo: `python main.py`
2. ✅ Review generated artifacts: `ls output/artifacts/`  
3. ✅ Check git history: `cd output && git log`
4. ✅ Read the generated documentation
5. ✅ Customize agents for your domain
6. ✅ Use generated Docker config for deployment

## License

MIT License - See LICENSE file

## Author

Jarvis Team - Building intelligent, reproducible software workflows

---

**Questions?** See SETUP_GUIDE.md or PRESENTATION.md for more details.

**Let Jarvis show you what multi-LLM collaboration can do!** 🚀
