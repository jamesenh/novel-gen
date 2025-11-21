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

NovelGen is a Chinese-language AI novel generation system built with Python and LangChain. It creates complete novels through a structured 6-step pipeline from world-building to final chapter generation.

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

# Run specific generation steps
python -m novelgen.runtime.orchestrator \
  --project projects/demo_001 \
  --steps world,characters,outline,chapters_plan,chapters

# Export novel text
python -m novelgen.runtime.export \
  --project projects/demo_001 \
  --output demo_001_full.txt
```

## Architecture Overview

### 6-Step Novel Generation Pipeline
1. **World Creation** (`chains/world_chain.py`) → Generates world settings
2. **Theme & Conflict** (`chains/theme_conflict_chain.py`) → Defines story themes
3. **Character Development** (`chains/characters_chain.py`) → Creates characters
4. **Outline Generation** (`chains/outline_chain.py`) → Creates chapter structure
5. **Chapter Planning** (`chains/chapters_plan_chain.py`) → Detailed scene breakdown
6. **Text Generation** (`chains/scene_text_chain.py`) → Writes novel content

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
├── chains/           # LangChain processing chains (6 steps, nodes in the graph)
├── runtime/          # Orchestration with LangGraph and utilities
│   ├── orchestrator.py         # Current orchestrator (to be replaced/updated)
│   └── workflow.py             # New LangGraph workflow definition
├── models.py         # All Pydantic data models (including LangGraph state)
├── config.py         # Configuration management
└── llm.py           # LLM initialization
```

### Data Flow (LangGraph)
1. `settings.json` is loaded as the initial input to the workflow
2. LangGraph manages the state throughout the 6-step pipeline
3. Each node (chain) processes the current state and returns an updated state
4. All outputs are still stored in `projects/{project_name}/` at appropriate stages
5. Final export combines all chapters into single text file

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

### Debugging Generation Issues
1. Check individual chain outputs in `projects/{name}/` JSON files
2. Verify Pydantic model validation
3. Review prompt templates for clarity
4. Test with smaller step subsets

## Environment Requirements

- Python 3.10+
- OpenAI API key in `.env`
- uv package manager (preferred) or pip
- All dependencies in `pyproject.toml`