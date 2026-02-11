# Research Agent Modes

The Diogenes research agent supports **5 different modes** that balance speed and depth based on your needs.

## Available Modes

### 1. QUICK Mode ⚡
**Best for:** Fast lookups, simple questions, time-sensitive queries

- **Speed:** ~30 seconds
- **Sources:** 3 sources max
- **Chunks:** 20 chunks for synthesis
- **Reflection:** Disabled (no iteration)
- **Quality threshold:** 0.5 (moderate)

```python
from src.core.agent.graph import ResearchAgent
from src.core.agent.modes import SearchMode

agent = ResearchAgent(mode=SearchMode.QUICK)
result = await agent.research("What is Python?")
```

**Use when:**
- You need quick answers
- Query is simple and straightforward
- Speed matters more than comprehensiveness

---

### 2. BALANCED Mode ⚖️ (DEFAULT)
**Best for:** Most general research queries

- **Speed:** ~2 minutes
- **Sources:** 5-15 sources
- **Chunks:** 50 chunks for synthesis
- **Reflection:** Enabled (up to 3 iterations)
- **Quality threshold:** 0.4 (balanced)

```python
agent = ResearchAgent()  # Balanced is default
# or explicitly:
agent = ResearchAgent(mode=SearchMode.BALANCED)
```

**Use when:**
- Standard research needs
- Good balance of speed and depth
- Most everyday queries

---

### 3. FULL Mode 📚
**Best for:** Thorough research, complex topics

- **Speed:** ~5 minutes
- **Sources:** 10-25 sources
- **Chunks:** 100 chunks for synthesis
- **Reflection:** Enabled (up to 5 iterations)
- **Quality threshold:** 0.3 (permissive)

```python
agent = ResearchAgent(mode=SearchMode.FULL)
result = await agent.research("Explain quantum entanglement")
```

**Use when:**
- Topic is complex or nuanced
- Need comprehensive coverage
- Multiple perspectives required

---

### 4. RESEARCH Mode 🎓
**Best for:** Academic research, in-depth analysis

- **Speed:** ~10 minutes
- **Sources:** 15-40 sources
- **Chunks:** 150 chunks for synthesis
- **Reflection:** Enabled (up to 7 iterations)
- **Quality threshold:** 0.2 (very permissive)

```python
agent = ResearchAgent(mode=SearchMode.RESEARCH)
result = await agent.research("Latest developments in CRISPR gene editing")
```

**Use when:**
- Academic-level research needed
- Writing papers or reports
- Need authoritative sources and citations

---

### 5. DEEP Mode 🔬
**Best for:** Exhaustive research, maximum coverage

- **Speed:** ~20 minutes
- **Sources:** 20-60 sources
- **Chunks:** 200 chunks for synthesis
- **Reflection:** Enabled (up to 10 iterations)
- **Quality threshold:** 0.1 (minimal filtering)

```python
agent = ResearchAgent(mode=SearchMode.DEEP)
result = await agent.research("State of AI safety research in 2026")
```

**Use when:**
- Exhaustive coverage required
- Meta-analysis or literature review
- Time is not a constraint

---

## Mode Configuration Details

| Parameter | Quick | Balanced | Full | Research | Deep |
|-----------|-------|----------|------|----------|------|
| **Search results/query** | 5 | 10 | 15 | 20 | 30 |
| **Max sources to crawl** | 3 | 15 | 25 | 40 | 60 |
| **Chunks for synthesis** | 20 | 50 | 100 | 150 | 200 |
| **Sources for synthesis** | 3 | 5 | 10 | 15 | 20 |
| **Max iterations** | 1 | 3 | 5 | 7 | 10 |
| **Reflection enabled** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Min quality score** | 0.5 | 0.4 | 0.3 | 0.2 | 0.1 |
| **Crawl timeout** | 30s | 60s | 90s | 120s | 180s |

---

## Usage Examples

### Command Line

```bash
# Quick mode
python test_agent_quick.py quick

# Balanced mode (default)
python test_agent_quick.py balanced

# Full mode
python test_agent_quick.py full
```

### Python API

```python
from src.core.agent.graph import ResearchAgent
from src.core.agent.modes import SearchMode

# Create agent with default mode
agent = ResearchAgent()

# Override mode per query
result = await agent.research(
    "What is Python?",
    mode=SearchMode.QUICK  # Use quick mode for this query
)

# Or set mode at agent level
quick_agent = ResearchAgent(mode=SearchMode.QUICK)
result = await quick_agent.research("What is Python?")
```

### Comparing Modes

Use the `test_modes.py` script to compare different modes:

```bash
python test_modes.py
```

This runs the same query in multiple modes and shows speed/quality tradeoffs.

---

## Mode Selection Guidelines

**Choose QUICK when:**
- ⏰ Speed is critical (< 1 minute)
- ❓ Question is simple and factual
- 🎯 Topic is well-defined

**Choose BALANCED when:**
- 🤔 Unsure which mode to use
- 📊 Need good coverage without excessive wait
- ⚖️ Want balance of speed and depth

**Choose FULL when:**
- 📖 Topic is complex or multifaceted
- 🔍 Need thorough understanding
- ⏱️ Can wait 5 minutes

**Choose RESEARCH when:**
- 🎓 Academic or professional research
- 📝 Writing papers or reports
- 🔗 Need many citations and sources

**Choose DEEP when:**
- 🔬 Exhaustive analysis required
- 📚 Literature review or meta-analysis
- ⏳ Time is not a constraint (20+ min)

---

## Performance Notes

**With qwen3:0.6b (small model):**
- Quick mode: ~30s - 1min
- Balanced mode: ~2-5min
- Full mode: ~5-10min
- Research mode: ~10-20min
- Deep mode: ~20-40min

**With larger models (e.g., llama3:8b):**
- Synthesis time significantly longer
- More accurate but slower
- Consider using Quick/Balanced for faster results

**Tips for faster research:**
1. Use Quick mode for simple queries
2. Upgrade to faster LLM models
3. Reduce `max_iterations` override
4. Use SSD for faster crawling/processing

---

## Advanced: Custom Mode Override

You can override specific mode parameters:

```python
agent = ResearchAgent(mode=SearchMode.BALANCED)

# Override max_iterations for this query
result = await agent.research(
    query="Complex topic",
    max_iterations=10  # Override the mode's default
)
```

Or create custom configurations by modifying `src/core/agent/modes.py`.

---

## See Also

- `src/core/agent/modes.py` - Mode definitions and configurations
- `test_modes.py` - Mode comparison script
- `test_agent_quick.py` - Single-mode testing

For questions or issues, check the documentation or open an issue on GitHub.
