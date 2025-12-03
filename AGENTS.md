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

# NovelGen Project Guide

## Project Overview

NovelGen is a sophisticated **Chinese AI novel generation system** built on LangChain and LangGraph. It automates the complete novel creation process through 6 structured steps: world-building → characters → themes → outline → chapter planning → scene generation. The project serves both as a practical tool for automated novel creation and as a learning platform for advanced LangChain architecture patterns.

**Key Capabilities:**
- Complete end-to-end novel generation workflow
- Structured JSON-based data exchange between steps using Pydantic models
- LangGraph-based stateful workflow orchestration
- Optional Mem0 intelligent memory layer for user preferences and entity state management
- Vector storage with ChromaDB for semantic search and context retrieval
- Consistency checking and revision systems
- Checkpoint and resume functionality

## Technology Stack

**Core Technologies:**
- **Python 3.10+** with LangChain 1.0+ ecosystem
- **LangGraph** for complex workflow orchestration
- **OpenAI GPT models** (GPT-4, GPT-3.5-turbo) as primary LLM
- **Pydantic 2.0+** for structured output validation
- **ChromaDB** for vector storage and semantic search
- **Mem0** for intelligent memory management (optional)
- **uv** for modern Python package management

**Development Tools:**
- **pytest** for testing framework
- **OpenSpec** for spec-driven development and change management
- **dotenv** for environment configuration

## Project Architecture

```
novelgen/
├── novelgen/                 # Main package
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic data models
│   ├── llm.py               # LLM instance management
│   ├── chains/              # LangChain generation chains
│   │   ├── world_chain.py
│   │   ├── characters_chain.py
│   │   ├── outline_chain.py
│   │   ├── scene_text_chain.py
│   │   └── ...
│   └── runtime/             # Runtime orchestration
│       ├── workflow.py      # LangGraph workflow definition
│       ├── nodes.py         # LangGraph node implementations
│       ├── memory.py        # Memory management
│       ├── consistency.py   # Consistency checking
│       └── revision.py      # Chapter revision system
├── projects/                # Generated novel projects
├── tests/                   # Test suite
├── openspec/               # OpenSpec configuration
├── docs/                   # Documentation
└── examples/               # Usage examples
```

## Development Workflow

### Novel Generation Pipeline
1. **World Creation** - Generate detailed world setting from user description
2. **Theme & Conflict** - Define core themes and conflicts
3. **Character Generation** - Create protagonist, antagonist, and supporting characters
4. **Outline Creation** - Generate story structure with chapter summaries
5. **Chapter Planning** - Detailed scene-by-scene planning for each chapter
6. **Scene Text Generation** - Generate actual novel text scene by scene
7. **Consistency Checking** - Verify internal consistency and fix issues
8. **Revision System** - Apply revisions based on consistency reports

### Key Design Principles
- **Chain Independence**: Each generation step runs independently with JSON file communication
- **Structured Outputs**: All data validated through Pydantic models
- **Configuration-Driven**: Environment variables and config files for flexible deployment
- **Memory Persistence**: SQLite for structured data, ChromaDB for vectors
- **Error Recovery**: LLMJsonRepairOutputParser for automatic JSON format fixes

### Code Style Guidelines

**File Headers:**
- Each file must contain Chinese docstring explaining module functionality
- Include author info and date (jamesenh, YYYY-MM-DD)

**Naming Conventions:**
- Functions/variables: English snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

**Import Order:**
1. Standard library
2. Third-party libraries
3. Local modules (use absolute imports)

**Comments:**
- Complex logic requires Chinese comments
- Complete function docstrings with Args, Returns, and functionality description

## Build and Test Commands

### Installation
```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -r requirements.txt
```

### Configuration
```bash
# Copy environment template
cp .env.template .env

# Edit .env with your OpenAI API key
```

### Running Novel Generation
```bash
# Full workflow using main.py
python main.py

# Using orchestrator directly
python -m novelgen.runtime.orchestrator \
  --project projects/demo_001 \
  --steps world,characters,outline,chapters_plan,chapters

# Export novel to text
python main.py export_novel_cmd demo_001
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_end_to_end.py

# Run with verbose output
pytest -v
```

### Memory Management
```bash
# Check memory health
python scripts/memory_health_check.py

# Reindex vectors
python scripts/vector_reindex.py

# Export memory data
python scripts/export_memory.py
```

## Configuration Options

### Environment Variables
- **OPENAI_API_KEY**: Required for OpenAI API access
- **OPENAI_MODEL_NAME**: Default model (gpt-4, gpt-3.5-turbo)
- **TEMPERATURE**: Creativity level (0.0-2.0)
- **MEM0_ENABLED**: Enable intelligent memory layer
- **EMBEDDING_MODEL_NAME**: Vector embedding model
- **Chain-specific configs**: Individual model settings per generation step

### Project Settings (settings.json)
```json
{
  "project_name": "demo_001",
  "author": "Jamesenh",
  "llm_model": "gpt-4",
  "temperature": 0.7,
  "persistence_enabled": true,
  "vector_store_enabled": true,
  "world_description": "小说世界观描述...",
  "theme_description": "主题和冲突描述...",
  "num_chapters": 5
}
```

## Testing Strategy

**Current Approach:**
- Manual testing through demo projects (demo_001, demo_002)
- End-to-end workflow validation
- JSON format and Pydantic model validation
- Content quality and consistency checks

**Test Categories:**
- **Unit tests**: Individual component testing
- **Integration tests**: Full workflow validation
- **State persistence tests**: Checkpoint and recovery
- **Memory system tests**: Vector store integration

**Focus Areas:**
- JSON output format correctness
- Pydantic model validation
- Content coherence and consistency
- Prompt execution effectiveness

## Security Considerations

**API Security:**
- OpenAI API keys stored in environment variables
- Support for different API endpoints and providers
- Rate limiting and timeout configurations

**Content Safety:**
- Relies on OpenAI's content filtering
- Chinese market focus with cultural adaptation
- No direct content moderation controls

**Data Handling:**
- Local JSON file storage for generated content
- No database or user authentication system
- Vector storage uses local ChromaDB instance

## Important Constraints

**Technical Limitations:**
- Complete dependency on OpenAI API availability
- JSON format strictness required for pipeline success
- No concurrent generation support
- Memory usage can be high for long texts

**Business Constraints:**
- Chinese language focus only
- AI-generated content cannot be copyrighted
- Content quality varies with LLM randomness
- Cost-sensitive due to GPT-4 pricing

**System Constraints:**
- Stateless design using JSON files
- Single-user focused architecture
- No built-in caching (except generation reuse)
- Network dependency for API calls

## OpenSpec Integration

This project uses OpenSpec for spec-driven development. When making significant changes:

1. **Check existing specs**: `openspec spec list --long`
2. **List active changes**: `openspec list`
3. **Create proposals** for new features, breaking changes, or architecture shifts
4. **Follow three-stage workflow**: Create → Implement → Archive
5. **Use Chinese language** for specs and documentation to match project conventions

For detailed OpenSpec instructions, see `@/openspec/AGENTS.md`.