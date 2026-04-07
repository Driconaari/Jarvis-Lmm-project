# Jarvis Setup Guide
## Complete Step-by-Step Installation & Configuration

---

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Ollama Endpoint Setup](#ollama-endpoint-setup)
4. [Configuration](#configuration)
5. [Running the Demo](#running-the-demo)
6. [Troubleshooting](#troubleshooting)
7. [Customization](#customization)

---

## System Requirements

### Hardware
- **CPU**: 8+ cores recommended (for running 2+ Ollama instances)
- **RAM**: 16GB minimum (Ollama needs 8GB, system 4GB, buffer)
- **Storage**: 50GB+ (Ollama models take 4-10GB each)
- **GPU**: Optional but recommended (CUDA-capable NVIDIA GPU for faster inference)

### Software
- **OS**: Windows 10+, macOS 11+, or Linux (Ubuntu 20.04+)
- **Python**: 3.11 or higher
- **Git**: Latest version
- **Docker** (optional): For containerized deployment
- **Ollama**: Installed and running

### Network
- Localhost access (127.0.0.1)
- Ports: 11434-11435 (Ollama), 8000-8001 (API)
- No internet required for local execution

---

## Installation

### Step 1: Install Ollama

**Windows/macOS**:
1. Download from https://ollama.ai
2. Run the installer
3. Verify installation:
   ```cmd
   ollama --version
   ```

**Linux (Ubuntu/Debian)**:
```bash
curl https://ollama.ai/install.sh | sh
ollama --version
```

### Step 2: Clone/Download Jarvis

```bash
cd c:\\Users\\Aku-1
git clone https://github.com/yourorg/jarvis.git Local-lmm-Project
cd Local-lmm-Project
```

Or if already have the files:
```bash
cd c:\\Users\\Aku-1\\Local-lmm-Project
```

### Step 3: Set Up Python Environment

**Create virtual environment**:
```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Or using conda
conda create -n jarvis python=3.11
conda activate jarvis
```

**Install dependencies**:
```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python -c "import langchain; import fastapi; print('✓ All dependencies installed')"
```

---

## Ollama Endpoint Setup

### Start Ollama Server 1 (Endpoint 1)

**Terminal 1**:
```bash
# Default port: 11434
ollama serve

# Or specify custom port
ollama serve --port 11434
```

Expected output:
```
2024/01/15 15:30:00 Listening on 127.0.0.1:11434
```

### Download Models for Endpoint 1

**Terminal 2** (new terminal, keep Terminal 1 running):
```bash
# Download Mistral 7B model
ollama pull mistral:7b

# Download Neural-Chat model
ollama pull neural-chat:7b

# Verify models
ollama list
```

Expected output:
```
NAME                  ID              SIZE   MODIFIED
mistral:7b           abc123def456    4.1 GB  2 hours ago
neural-chat:7b       xyz789uvw012    4.6 GB  1 hour ago
```

### Start Ollama Server 2 (Endpoint 2)

**Terminal 3** (new terminal):
```bash
# Start second Ollama instance on different port
ollama serve --port 11435
```

### Download Models for Endpoint 2

**Terminal 4** (new terminal):
```bash
# Tell Ollama to use port 11435
export OLLAMA_PORT=11435

# Download models
ollama pull mistral:7b
ollama pull openchat
```

### Verify Both Endpoints

```bash
# Test endpoint 1
curl http://localhost:11434/api/tags

# Test endpoint 2
curl http://localhost:11435/api/tags
```

Both should return JSON with list of available models.

---

## Configuration

### Step 1: Verify Default Config

The file `config/jarvis_config.yaml` contains default configuration:

```yaml
endpoints:
  - name: "endpoint1"
    url: "http://localhost:11434"
    models:
      - name: "mistral:7b"
      - name: "neural-chat:7b"
  
  - name: "endpoint2"
    url: "http://localhost:11435"
    models:
      - name: "mistral:7b"
      - name: "openchat"

agents:
  architecture:
    endpoint_name: "endpoint1"
    model_name: "mistral:7b"
  
  # ... other agents ...
```

### Step 2: Customize Configuration (Optional)

Edit `config/jarvis_config.yaml` to:

**Change endpoint ports** (if using different ports):
```yaml
endpoints:
  - name: "endpoint1"
    url: "http://localhost:YOUR_PORT_1"
  - name: "endpoint2"
    url: "http://localhost:YOUR_PORT_2"
```

**Swap models or endpoints**:
```yaml
agents:
  implementation:
    model_name: "neural-chat:7b"  # Change model
    endpoint_name: "endpoint2"    # Change endpoint
```

**Adjust agent parameters**:
```yaml
agents:
  implementation:
    temperature: 0.3              # Lower = more deterministic
    parallel_workers: 3           # Increase parallelism
    timeout: 180                  # Increase timeout for slow endpoint
```

### Step 3: Create Output Directory (Optional)

```bash
# Jarvis will create this automatically, but you can pre-create it
mkdir -p output/artifacts
cd output
git init
git config user.name "Jarvis"
git config user.email "jarvis@local.ai"
```

---

## Running the Demo

### One-Command Demo

**Ensure all prerequisites are running**:
1. ✓ Terminal 1: Ollama endpoint 1 running (`ollama serve`)
2. ✓ Terminal 3: Ollama endpoint 2 running (`ollama serve --port 11435`)
3. ✓ Models downloaded on both endpoints

**Run the demo**:
```bash
# From project root
python main.py
```

Expected output:
```
Initializing Jarvis Multi-LLM Orchestrator...
  Endpoints: 2
  Agents: 6
  Workspace: ./output

Registering specialized agents...
  ✓ Registered: architecture (Architecture & Design)
  ✓ Registered: tech_lead (Tech Lead & Planning)
  ✓ Registered: implementation (Software Implementation)
  ✓ Registered: testing (Testing & Quality Assurance)
  ✓ Registered: documentation (Technical Documentation)
  ✓ Registered: deployment (Deployment Validation)

======================================================================
STARTING DEMO WORKFLOW: Task Management System
======================================================================

═══ Starting phase: ARCHITECTURE ═══
→ Executing architecture (Architecture & Design)
  ✓ SUCCESS

═══ Starting phase: PLANNING ═══
→ Executing tech_lead (Tech Lead & Planning)
  ✓ SUCCESS

[... continues through all 6 phases ...]

======================================================================
DEMO WORKFLOW COMPLETE
======================================================================
Output directory: ./output
All artifacts saved and committed to git

✓ Jarvis execution completed successfully!
```

### Expected Outputs

After running, check `output/` directory:

```
output/
├── artifacts/
│   ├── architecture/
│   │   ├── architecture_spec.json
│   │   └── raw_response.txt
│   ├── implementation/
│   │   ├── main.py
│   │   ├── models.py
│   │   └── config.py
│   ├── testing/
│   │   ├── test_models.py
│   │   ├── test_api.py
│   │   └── quality_report.txt
│   ├── documentation/
│   │   ├── README.md
│   │   ├── ARCHITECTURE.md
│   │   └── OPENAPI.md
│   ├── deployment/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── DEPLOYMENT_CHECKLIST.md
│   └── agent_outputs/
│       ├── architecture_20240115_153000.json
│       ├── tech_lead_20240115_153015.json
│       └── [... other agent outputs ...]
└── .git/
    └── [git history with all commits]
```

### Verify Git History

```bash
cd output
git log --oneline
```

Expected output:
```
f8g1c36 [DEPLOYMENT] Generate deployment artifacts
e7f0b25 [DOCUMENTATION] Write docs
d6e9a14 [TESTING] Create test suite
c5d8f03 [IMPLEMENTATION] Generate code
b2e4c91 [PLANNING] Break into tasks
ae3f8d2 [ARCHITECTURE] Create system architecture
```

---

## Running Custom Workflows

### Extend for Your Project

**1. Modify the workflow in `main.py`**:

```python
async def main_custom():
    orchestrator = setup_orchestrator()
    register_agents(orchestrator)
    
    # Run custom workflow
    context = await orchestrator.execute_full_workflow(
        "My Project Name",
        {"description": "Custom project specification"}
    )
    
    # Or run individual phases
    context = await orchestrator.execute_phase(
        "ARCHITECTURE",
        ["architecture"],
        sequential=True
    )
```

**2. Create custom agents** (optional):

```python
# agents/custom_agent.py
from jarvis.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    def get_system_prompt(self):
        return "You are specialized in..."
    
    async def execute(self, context):
        # Your implementation
        return self._success(...)
```

**3. Register and run**:

```python
orchestrator.register_agent("my_custom", MyCustomAgent(llm, config))
context = await orchestrator.execute_phase(
    "CUSTOM_PHASE",
    ["my_custom"]
)
```

---

## Troubleshooting

### Issue: "Connection refused" to Ollama

**Symptom**: `ConnectionError: Failed to connect to http://localhost:11434`

**Diagnosis**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check port is correct
netstat -an | find \"11434\"
```

**Solution**:
1. Start Ollama: `ollama serve`
2. Verify port matches config
3. Check firewall settings

### Issue: "Model not found"

**Symptom**: `Error: Model 'mistral:7b' not found`

**Diagnosis**:
```bash
ollama list
```

**Solution**:
```bash
# Download the model
ollama pull mistral:7b

# Or update config to use available model
# Check output of 'ollama list'
```

### Issue: Out of memory

**Symptom**: Ollama crashes or freezes

**Diagnosis**:
```bash
# Check available RAM
free -h  # Linux
Get-ComputerInfo | Select-Object TotalPhysicalMemory  # Windows
```

**Solution**:
1. Close other applications
2. Download smaller models:
   ```bash
   ollama pull mistral:3b  # Smaller version
   ollama pull orca-mini   # Lightweight
   ```
3. Reduce parallel_workers in config

### Issue: Slow API responses

**Symptom**: Queries taking > 5 seconds per agent

**Diagnosis**:
- Check CPU/GPU usage
- Verify endpoint is healthy
- Check model size (larger = slower)

**Solution**:
1. Use smaller models:
   ```bash
   ollama pull neural-chat:7b-fp8  # Quantized version
   ```
2. Reduce parallel workers
3. Increase timeout in config

### Issue: Git merge conflicts

**Symptom**: "error: Your local changes would be overwritten"

**Solution**:
```bash
cd output
git reset --hard HEAD
# Re-run Jarvis
```

---

## Advanced Configuration

### Running on Different Machine

**Endpoint on server, API on client**:

1. On server (192.168.1.100):
   ```bash
   ollama serve --port 0.0.0.0:11434
   ```

2. On client, update config:
   ```yaml
   endpoints:
     - name: "remote_endpoint"
       url: "http://192.168.1.100:11434"
   ```

### Scale to Production

**Docker Deployment**:
```bash
# Build and run
docker build -t jarvis:1.0 .
docker run -p 8000:8000 \\
  -e DATABASE_URL=postgresql://... \\
  jarvis:1.0
```

**Kubernetes**:
```bash
kubectl apply -f kubernetes-deployment.yaml
```

### Performance Tuning

Adjust in `config/jarvis_config.yaml`:

```yaml
agents:
  implementation:
    temperature: 0.2        # Lower = more consistent
    parallel_workers: 4     # Higher = more parallelism
    timeout: 300            # Longer = less failures

workspace:
  max_context_tokens: 16000 # Larger window = better context
```

---

## Next Steps

After successful demo:

1. ✅ Review generated artifacts in `output/artifacts/`
2. ✅ Check git history: `git log --oneline`
3. ✅ Customize configuration for your project
4. ✅ Extend agents for domain-specific tasks
5. ✅ Integrate with your CI/CD pipeline
6. ✅ Deploy to production using generated Docker/K8s configs

---

## Support & Documentation

- **Project Structure**: See `PROJECT_VISION.md`
- **Architecture Details**: See `TOOLCHAIN_ANALYSIS.md`
- **API Reference**: See agents' docstrings
- **Generated Docs**: See `output/artifacts/documentation/`

---

## Quick Reference

### Commands
```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run Ollama servers (separate terminals)
ollama serve
ollama serve --port 11435

# Download models
ollama pull mistral:7b
ollama pull neural-chat:7b

# Run Jarvis
python main.py

# Check outputs
cd output && git log --oneline
ls -la artifacts/
```

### Files
- `config/jarvis_config.yaml` - Configuration
- `main.py` - Entry point  
- `jarvis/orchestrator.py` - Core orchestrator
- `agents/*.py` - Specialized agents
- `output/artifacts/` - Generated outputs
- `output/.git/` - Version history

### Endpoints
- Endpoint 1: `http://localhost:11434` (default Ollama port)
- Endpoint 2: `http://localhost:11435` (custom second instance)

### Models
Default configuration uses:
- `mistral:7b` - General purpose
- `neural-chat:7b` - Good at planning/documentation
- `openchat` - Alternative on endpoint 2

---

## Success Criteria Checklist

After running Jarvis, verify:

- [ ] Ollama endpoints both responding
- [ ] All 6 agents registered successfully
- [ ] All 6 phases completed (ARCHITECTURE, PLANNING, IMPLEMENTATION, TESTING, DOCUMENTATION, DEPLOYMENT)
- [ ] Artifacts generated for each phase
- [ ] Git commits created for each phase
- [ ] No error messages in final output
- [ ] Can read generated code/docs in `output/artifacts/`
- [ ] Third party can reproduce by following this guide

---

**Congratulations!** You have successfully deployed Jarvis! 🎉

For questions or issues, refer to [TROUBLESHOOTING](#troubleshooting) section.
