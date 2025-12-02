<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NovelGen is a sophisticated Chinese-language AI novel generation system built with Python, LangChain, and LangGraph. It creates complete novels through a structured 6-step pipeline from world-building to final chapter generation, with intelligent memory management and dynamic chapter expansion capabilities.

## Essential Commands

### Development Setup
```bash
# Install dependencies (preferred method)
uv sync

# Alternative installation
pip install -r requirements.txt

# Set up environment
cp .env.template .env
# Edit .env with your OpenAI API key
```

### Running the System
```bash
# Full novel generation demo
python main.py

# CLI usage (preferred method)
ng generate --project demo_001           # Generate complete novel
ng resume --project demo_001 --chapter 3  # Resume from specific chapter
ng export --project demo_001             # Export to text file
ng list                                 # List available projects

# Direct orchestrator usage
python -m novelgen.runtime.orchestrator \
  --project projects/demo_001 \
  --steps world,characters,outline,chapters_plan,chapters

# Run tests
pytest tests/                           # Run all tests
pytest tests/test_end_to_end.py        # Run specific test
```

### Debugging and Development
```bash
# Enable debug mode
export NOVELGEN_DEBUG=1
ng generate --project demo_001          # Shows detailed execution logs

# Test individual chains
python -c "
from novelgen.chains.world_chain import WorldCreationChain
chain = WorldCreationChain()
result = chain.run({'project_name': 'test', 'world_description': 'test world'})
print(result)
"
```

## Architecture Overview

### 6-Step Novel Generation Pipeline
1. **World Creation** (`chains/world_chain.py`) → Generates world settings
2. **Theme & Conflict** (`chains/theme_conflict_chain.py`) → Defines story themes
3. **Character Development** (`chains/characters_chain.py`) → Creates characters
4. **Outline Generation** (`chains/outline_chain.py`) → Creates chapter structure
5. **Chapter Planning** (`chains/chapters_plan_chain.py`) → Detailed scene breakdown
6. **Text Generation** (`chains/scene_text_chain.py`) → Writes novel content

### Advanced Workflow Features
- **Dynamic Chapter Expansion** (`chains/story_progress_chain.py`) → Automatically evaluates story progress and expands outline
- **Scene Generation Subgraph** → Nested workflow for fine-grained scene-level generation
- **Revision System** (`chains/chapter_revision_chain.py`) → Iterative improvement of generated content
- **Consistency Checking** (`runtime/consistency.py`) → Validates narrative coherence and character consistency

### Key Design Principles (from .cursor/rules/base.mdc)
- **Graph-Based Workflow**: The novel generation pipeline is implemented as a LangGraph workflow, where each step is a node in the graph
- **Modular Design**: Each step is an independent LangChain component (node)
- **Structured Output**: All outputs use Pydantic models (defined in `models.py`)
- **State Management**: LangGraph handles state persistence and flow between nodes
- **JSON Communication**: Chains still communicate via JSON files for external persistence
- **LangChain Separation**: Business logic separated from LangChain code
- **Prompt Structure**: Must include task, input, output format (JSON schema), and notes

### Project Structure
```
novelgen/
├── chains/           # LangChain processing chains (6 steps + advanced features)
├── runtime/          # Orchestration with LangGraph and utilities
│   ├── orchestrator.py         # Main orchestrator with backward compatibility
│   ├── workflow.py             # LangGraph workflow definition
│   ├── nodes.py                # LangGraph node implementations
│   ├── mem0_manager.py         # Intelligent memory management
│   ├── consistency.py          # Consistency checking utilities
│   ├── exporter.py             # Text export functionality
│   └── memory.py               # Memory utilities
├── models.py         # All Pydantic data models (including LangGraph state)
├── config.py         # Configuration management
├── llm.py           # LLM initialization
└── cli.py           # Command-line interface (ng command)
```

### Data Flow (LangGraph)
1. `settings.json` is loaded as the initial input to the workflow
2. LangGraph manages the state throughout the 6-step pipeline
3. Each node (chain) processes the current state and returns an updated state
4. All outputs are still stored in `projects/{project_name}/` at appropriate stages
5. Final export combines all chapters into single text file
6. SQLite-based checkpointing enables interruption and resumption at any step

### Memory Management (Mem0 Integration)
- **Entity Management**: Automatic character state tracking and conflict resolution
- **User Preferences**: Framework for learning writing style and preferences
- **Zero Deployment**: Reuses existing ChromaDB infrastructure
- **Backward Compatibility**: Can be disabled without affecting core functionality

## Critical Implementation Rules

1. **Always use Pydantic models** for structured outputs and LangGraph state definition
2. **Graph-based orchestration**: Use LangGraph to orchestrate the workflow, not manual sequencing
3. **Node independence**: Each chain must be a self-contained node that can be run standalone
4. **State management**: LangGraph handles the state flow between nodes; avoid manual state passing
5. **JSON-only communication**: External persistence uses JSON files only
6. **Chinese language focus**: All prompts and outputs in Chinese
7. **LangChain 1.0+ syntax**: Use modern LangChain patterns
8. **LangGraph 1.0+ syntax**: Use modern LangGraph patterns (StateGraph, nodes, edges)
9. **Prompt template structure**: Must include task, input, output format (JSON schema), and notes
10. **Checkpointing**: All workflows must support SQLite-based checkpointing for resumption
11. **Backward compatibility**: New features must maintain compatibility with existing project structures

## Common Development Tasks

### Adding a New Chain (Node)
1. Create new chain file in `novelgen/chains/` following existing patterns
2. Define input/output Pydantic models in `models.py`
3. Follow existing chain patterns (ChatPromptTemplate → LLM → OutputParser)
4. Add to LangGraph workflow in `runtime/workflow.py`:
   - Define the node function that wraps the chain
   - Add the node to the StateGraph
   - Define edges from the new node
5. Ensure the LangGraph state model is updated if new state fields are needed
6. Add corresponding node implementation in `runtime/nodes.py`

### Modifying Existing Chains
1. Check current JSON schema in corresponding Pydantic model
2. Update prompt template to include new requirements
3. Test chain independently before integration
4. Update the LangGraph workflow if the node interface changes
5. Ensure backward compatibility with existing projects

### Adding a New Workflow Branch
1. Identify the branching point in the existing workflow
2. Define the new node(s) that will form the branch
3. Add branch conditions in the StateGraph
4. Update the state model if new state fields are needed for the branch
5. Test the complete workflow with both paths

### Memory Integration (Mem0)
1. Enable Mem0 in `.env` with `MEM0_ENABLED=true`
2. Configure memory-specific parameters in environment
3. Use `Mem0Manager` in chains for entity tracking and user preferences
4. Test memory functionality with `tests/test_mem0_basic.py`

### Debugging Generation Issues
1. Check individual chain outputs in `projects/{name}/` JSON files
2. Verify Pydantic model validation
3. Review prompt templates for clarity
4. Test with smaller step subsets
5. Enable debug mode: `export NOVELGEN_DEBUG=1`
6. Check LangGraph state persistence in SQLite checkpoints

### Testing Your Changes
```bash
# Run the full test suite
pytest tests/ -v

# Test specific functionality
pytest tests/test_langgraph_integration.py -v
pytest tests/test_checkpointing.py -v
pytest tests/test_mem0_basic.py -v

# Test with specific project
python -c "
from novelgen.runtime.orchestrator import NovelOrchestrator
orch = NovelOrchestrator('test_project')
orch.run_workflow(stop_at='world_generation')
"
```

## Environment Requirements

- Python 3.10+
- OpenAI API key in `.env`
- uv package manager (preferred) or pip
- All dependencies in `pyproject.toml`

### Optional Dependencies for Enhanced Features
- **Mem0**: Set `MEM0_ENABLED=true` in `.env` for intelligent memory management
- **Rich + Typer**: Already included for beautiful CLI interface
- **SQLite**: Used automatically for LangGraph checkpointing

### Configuration Highlights
The `.env.template` shows extensive configuration options including:
- Individual model settings per chain
- Embedding model configuration for Chinese text
- Mem0 memory management parameters
- Request timeout and retry logic
- Revision policies for novel improvement

## Current Development State

### Active Branch: `feature/langgraph-migration`
The project is actively migrating from simple orchestration to sophisticated LangGraph workflows. Key features in development:

- **Dynamic Chapter Expansion**: Automatically evaluates story progress and expands chapter count
- **Scene-Level Generation**: Nested sub-workflows for fine-grained content generation
- **Enhanced Memory Management**: Mem0 integration for intelligent entity tracking
- **Improved CLI**: New `ng` command replacing manual orchestrator calls
- **Checkpointing**: SQLite-based state persistence for reliable resumption

### Migration Status
- ✅ Core LangGraph workflow implemented
- ✅ Checkpointing and resumption working
- ✅ Dynamic chapter expansion functional
- ✅ Mem0 memory layer integrated
- ✅ CLI tool (`ng`) available
- 🔄 Scene generation subgraph being refined
- 🔄 Backward compatibility maintenance

### Key Files to Understand for Development
- `runtime/workflow.py` - Core LangGraph StateGraph definition
- `runtime/nodes.py` - Node implementations wrapping the chains
- `runtime/orchestrator.py` - Main orchestrator with backward compatibility
- `cli.py` - New CLI interface (use `ng` command)
- `runtime/mem0_manager.py` - Memory management integration

The system represents a mature, production-ready AI novel generation platform with sophisticated orchestration, intelligent memory management, and comprehensive tooling for both developers and end users.