# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NovelGen is a sophisticated Chinese-language AI novel generation system that creates complete novels through a structured pipeline. It combines **LangChain** for business logic with **LangGraph** for workflow orchestration, featuring intelligent memory management via Mem0, checkpointing for resumption, and both CLI and web interfaces.

### Core Architecture
- **6-Step Pipeline**: World creation → Theme/Conflict → Characters → Outline → Chapter planning → Text generation
- **LangGraph Workflow**: Stateful, graph-based orchestration with SQLite checkpointing
- **Structured Outputs**: All data uses Pydantic models (defined in `models.py`)
- **Dual Interface**: CLI (`ng` command) + Web API (FastAPI + React frontend)

## Quick Start Commands

### Development Setup
```bash
# Install dependencies (preferred)
uv sync

# Alternative installation
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your OpenAI API key
```

### Running the System

**CLI Interface (Recommended):**
```bash
# Full novel generation
ng generate --project demo_001

# Resume from specific chapter
ng resume --project demo_001 --chapter 3

# Export to text file
ng export --project demo_001

# List projects
ng list
```

**Direct Python:**
```bash
# Run full demo
python main.py

# Direct orchestrator
python -m novelgen.runtime.orchestrator \
  --project projects/demo_001 \
  --steps world,characters,outline,chapters_plan,chapters
```

**Web Application:**
```bash
# Backend (FastAPI + Celery + Redis)
# Ensure Redis is running: docker-compose up -d redis
uv run uvicorn novelgen.api.main:app --reload  # http://127.0.0.1:8000

# Frontend (React + Vite)
cd frontend
npm install
npm run dev  # http://127.0.0.1:5173
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_end_to_end.py -v

# Test LangGraph integration
pytest tests/test_langgraph_integration.py -v

# Test checkpointing
pytest tests/test_checkpointing.py -v

# Test memory (Mem0)
pytest tests/test_mem0_basic.py -v
```

## High-Level Architecture

### 6-Step Generation Pipeline
Each step is an independent LangChain chain that can be run standalone:

1. **World Creation** (`chains/world_chain.py`) → Generates world settings
2. **Theme & Conflict** (`chains/theme_conflict_chain.py`) → Defines story themes
3. **Character Development** (`chains/characters_chain.py`) → Creates characters
4. **Outline Generation** (`chains/outline_chain.py`) → Creates chapter structure
5. **Chapter Planning** (`chains/chapters_plan_chain.py`) → Detailed scene breakdown
6. **Text Generation** (`chains/scene_text_chain.py`) → Writes novel content

### Advanced Features
- **Dynamicchains Chapter Expansion** (`/story_progress_chain.py`) → Auto-evaluates story progress
- **Scene Generation Subgraph** → Nested workflow for fine-grained scene generation
- **Revision System** (`chains/chapter_revision_chain.py`) → Iterative content improvement
- **Consistency Checking** (`runtime/consistency.py`) → Validates narrative coherence
- **Memory Management** (`runtime/mem0_manager.py`) → Mem0 integration for entity tracking

### Project Structure
```
novelgen/
├── chains/              # LangChain processing chains (6 steps + advanced)
├── runtime/             # LangGraph orchestration & utilities
│   ├── workflow.py      # StateGraph definition (core orchestration)
│   ├── nodes.py         # Node implementations wrapping chains
│   ├── orchestrator.py  # Main orchestrator (backward compatible)
│   ├── mem0_manager.py  # Mem0 memory layer
│   ├── consistency.py   # Consistency checking
│   ├── exporter.py      # Text export functionality
│   └── summary.py       # Chapter/book summaries
├── api/                 # FastAPI web interface
│   ├── main.py          # API entry point
│   ├── routes/          # API endpoints
│   └── websockets/      # WebSocket for real-time updates
├── models.py            # All Pydantic models (state + data structures)
├── config.py            # Configuration management
├── llm.py              # LLM initialization
└── cli.py              # CLI interface (ng command)
```

### Data Flow (LangGraph)
1. `settings.json` → Initial state input
2. LangGraph manages state through 6-step pipeline
3. Each node processes current state → returns updated state
4. Outputs stored in `projects/{project_name}/` as JSON
5. SQLite checkpointing enables pause/resume at any step
6. Final export combines chapters to single text file

## Critical Implementation Rules

**From `.cursor/rules/base.mdc` - Must Follow:**

1. **Modular Design**: Each step must be an independent chain/LangGraph node
2. **Structured Output Priority**: All chain outputs must use Pydantic models
3. **Iterative & Modifiable**: Each chain must run standalone without UI dependency
4. **State Management**: Use LangGraph for workflow state; external persistence via JSON
5. **Separation of Concerns**: LangChain (business logic) + LangGraph (orchestration)
6. **Data Structures**: All models in `models.py` (including LangGraph state)
7. **No Business Logic in LangChain/LangGraph**: Keep layers decoupled
8. **Structured Prompts**: Use JSON schema constraints, avoid free-form output
9. **Node Logic**: `LangGraph State → Extract Input → PromptTemplate → LLM → OutputParser → Python Object → Update State`
10. **Workflow Definition**: LangGraph StateGraph with nodes + edges
11. **Chinese Language**: All prompts and outputs in Chinese
12. **Modern Syntax**: LangChain 1.0+ and LangGraph 1.0+ patterns

## Common Development Tasks

### Adding a New Chain
1. Create chain file in `novelgen/chains/`
2. Define input/output Pydantic models in `models.py`
3. Implement chain using: `ChatPromptTemplate → LLM → PydanticOutputParser`
4. Wrap chain as node in `runtime/nodes.py`
5. Add node to `runtime/workflow.py` StateGraph
6. Define edges and branching logic
7. Test standalone before integration

### Modifying Existing Chains
1. Check current Pydantic model schema
2. Update prompt template with new requirements
3. Test chain independently
4. Update LangGraph workflow if interface changes
5. Ensure backward compatibility

### Testing Individual Chains
```python
from novelgen.chains.world_chain import WorldCreationChain

chain = WorldCreationChain()
result = chain.run({
    'project_name': 'test',
    'world_description': 'test world'
})
print(result)
```

### Debugging Generation Issues
1. Check chain outputs in/` JSON files `projects/name
2. Verify Pydantic model validation
3. Review prompt templates for clarity
4. Test with smaller step subsets
5. Enable debug mode: `export NOVELGEN_DEBUG=1`
6. Check SQLite checkpoints: `ls -la projects/{name}/.checkpoints/`

### Memory Integration (Mem0)
```python
# Enable in .env
MEM0_ENABLED=true

# Use in chains
from novelgen.runtime.mem0_manager import Mem0Manager

mem0 = Mem0Manager()
mem0.add_entity("character", name="张三", traits=["勇敢", "固执"])
```

## Environment Configuration

### Required
- Python 3.10+
- OpenAI API key in `.env`
- uv package manager (preferred)

### Optional Features
- **Mem0**: Set `MEM0_ENABLED=true` in `.env`
- **Redis**: For web app background tasks (`docker-compose up -d redis`)
- **Web Frontend**: Node.js + npm/yarn

### Key Configuration Files
- `.env` - Environment variables (copy from `.env.template`)
- `.env.template` - Extensive configuration options for all chains
- `pyproject.toml` - Project dependencies and CLI script
- `projects/` - Generated novel projects (auto-created)

## Web Application

### Backend (FastAPI)
Key endpoints:
- **Projects**: `GET/POST /api/projects`, `GET/DELETE /api/projects/{name}`
- **Generation**: `POST /api/projects/{name}/generate|resume|stop`
- **Content**: `GET /api/projects/{name}/world|characters|outline|chapters`
- **Editing**: `PUT /api/projects/{name}/world|characters|outline|chapters/{num}`
- **Export**: `GET /api/projects/{name}/export/txt|md|json`

See `docs/web_api.md` for full API documentation.

### Frontend (React + Vite)
Located in `/frontend`:
- Built with React + TypeScript + Vite
- Uses Tailwind CSS for styling
- Real-time updates via WebSockets
- Components for project management, content editing, and generation monitoring

## Current Development State

**Active Branch**: `feature/web-app-migration` (migrating from CLI to web-first)

**Migration Status**:
- ✅ Core LangGraph workflow implemented
- ✅ Checkpointing and resumption working
- ✅ Dynamic chapter expansion functional
- ✅ Mem0 memory layer integrated
- ✅ CLI tool (`ng`) available
- ✅ Web API (FastAPI) implemented
- ✅ React frontend with real-time updates
- 🔄 Enhanced scene generation subgraph
- 🔄 Expanded API features
- 🔄 Frontend component refinements

**Key Files for Understanding**:
- `runtime/workflow.py` - LangGraph StateGraph (start here!)
- `runtime/nodes.py` - Node wrappers around chains
- `runtime/orchestrator.py` - Main orchestrator with backward compatibility
- `cli.py` - CLI implementation
- `api/main.py` - Web API entry point
- `models.py` - All data structures

## Testing Strategy

**Test Types**:
- `test_langgraph_integration.py` - Workflow orchestration tests
- `test_checkpointing.py` - State persistence tests
- `test_mem0_basic.py` - Memory layer tests
- `test_end_to_end.py` - Full pipeline tests
- `test_api_web.py` - Web API tests

**Running Tests**:
```bash
# All tests with verbose output
pytest tests/ -v

# Specific test file
pytest tests/test_langgraph_integration.py -v

# With coverage
pytest tests/ --cov=novelgen --cov-report=html
```

## Configuration Highlights

From `.env.template`:
- **Chain-specific models**: Configure different models per chain (WORLD_CHAIN_MODEL_NAME, etc.)
- **Embedding models**: Support OpenAI, ModelScope, DashScope for Chinese text
- **Mem0 settings**: Parallel workers, timeout, retry logic
- **LangGraph settings**: Recursion limit, nodes per chapter estimation
- **Revision policies**: `auto_apply` or `manual_confirm`

## Documentation

- `README.md` - Project overview (Chinese)
- `docs/web_api.md` - Web API documentation
- `docs/mem0-setup.md` - Mem0 configuration guide
- `docs/langgraph-migration.md` - Migration notes
- `.cursor/rules/base.mdc` - Project philosophy and rules

## Project Philosophy

From `.cursor/rules/base.mdc`:

> This project is designed for learning LangChain, AI architecture, and LLM prompt engineering. Each step of novel creation is broken down into structured steps: world → characters → outline → scenes → text, all generated by AI with memory and revision support.

The system emphasizes **modularity**, **structured outputs**, **graph-based workflows**, and **Chinese language optimization**.
