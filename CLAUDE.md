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
- **Modular Design**: Each step is an independent LangChain
- **Structured Output**: All outputs use Pydantic models (defined in `models.py`)
- **JSON Communication**: Chains communicate via JSON files only
- **LangChain Separation**: Business logic separated from LangChain code
- **Prompt Structure**: Must include task, input, output format (JSON schema), and notes

### Project Structure
```
novelgen/
├── chains/           # LangChain processing chains (6 steps)
├── runtime/          # Orchestration and utilities
├── models.py         # All Pydantic data models
├── config.py         # Configuration management
└── llm.py           # LLM initialization
```

### Data Flow
1. `settings.json` → World creation
2. Each chain reads previous JSON outputs
3. All outputs stored in `projects/{project_name}/`
4. Final export combines all chapters into single text file

## Critical Implementation Rules

1. **Always use Pydantic models** for structured outputs
2. **Chain independence**: Each chain must be runnable standalone
3. **JSON-only communication** between chains
4. **Chinese language focus**: All prompts and outputs in Chinese
5. **LangChain 1.0+ syntax**: Use modern LangChain patterns
6. **Prompt template structure**: Must include JSON schema constraints

## Common Development Tasks

### Adding a New Chain
1. Create new chain file in `novelgen/chains/`
2. Define input/output Pydantic models in `models.py`
3. Follow existing chain patterns (ChatPromptTemplate → LLM → OutputParser)
4. Add to orchestrator in `runtime/orchestrator.py`

### Modifying Existing Chains
1. Check current JSON schema in corresponding Pydantic model
2. Update prompt template to include new requirements
3. Test chain independently before integration
4. Ensure backward compatibility with existing projects

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