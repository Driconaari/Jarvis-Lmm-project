# Examples

This folder contains example code and demonstrations.

## Usage Examples

### Scalability Examples

Run practical examples of Jarvis scalability features:

```bash
# From project root:
python examples_scalability.py
```

**Available examples:**
1. **Basic Job Submission** - Submit jobs and watch processing
2. **Priority Scheduling** - Different priority jobs process in order
3. **Auto-Scaling Under Load** - Watch agents scale based on queue
4. **Monitoring Metrics** - Extract and analyze system statistics
5. **Automatic Retry** - Jobs retry automatically on failure

### Quick Start Examples

```bash
# Traditional workflow
python main.py

# Scalable with job queues
python main_scalable.py

# Run tests
pytest tests/ -v
```

### Code Examples

See documentation for inline code examples:
- [../guides/SCALABILITY_QUICKREF.md](../guides/SCALABILITY_QUICKREF.md) - Copy-paste ready examples
- [../guides/SCALABILITY_GUIDE.md](../guides/SCALABILITY_GUIDE.md) - Detailed usage patterns

## 📂 Files

- `../examples_scalability.py` - Runnable scalability examples
- `../main.py` - Traditional entry point
- `../main_scalable.py` - Scalable entry point

---

**See [../guides/SCALABILITY_GUIDE.md](../guides/SCALABILITY_GUIDE.md) for complete examples**
