## ADDED Requirements

### Requirement: LLM structured output mode for supported backends
The system SHALL use provider-supported structured output capabilities (such as `with_structured_output` and JSON mode / tool calling) for chains whose outputs are defined by Pydantic models, whenever the configured LLM backend explicitly supports such capabilities.

#### Scenario: OpenAI backend with JSON mode
- **WHEN** a chain (e.g. characters_chain, chapters_plan_chain, scene_text_chain, revision_chain) is executed using an OpenAI-compatible backend that supports JSON mode or tool calling
- **THEN** the chain SHALL obtain its LLM instance via a structured-output-enabled configuration (e.g. `with_structured_output(PydanticModel)`)
- **AND** the chain SHALL receive a fully validated Pydantic object without manual JSON parsing in the chain implementation.

#### Scenario: Non-JSON-mode backend
- **WHEN** the configured LLM backend does not support JSON mode or tool calling required by structured output
- **THEN** the chain SHALL fall back to the existing `PydanticOutputParser + LLMJsonRepairOutputParser` based implementation
- **AND** the system SHALL NOT attempt to enable structured output mode for that backend.

### Requirement: Unified JSON output cleanup for legacy parsing path
The system SHALL apply a unified, conservative cleanup step to raw LLM outputs before feeding them into JSON parsers in the legacy parsing path.

#### Scenario: Markdown-wrapped JSON output
- **WHEN** a model returns JSON wrapped in Markdown code fences (e.g. ```json ... ```)
- **THEN** the cleanup step SHALL remove Markdown fences and extract the innermost JSON object text
- **AND** the cleaned text SHALL be passed to the JSON parser or repair parser.

#### Scenario: Additional explanatory text around JSON
- **WHEN** a model returns explanatory text before or after the JSON object
- **THEN** the cleanup step SHALL heuristically trim the output to the substring from the first `{` to the last `}`
- **AND** the trimmed substring SHALL be used as the candidate JSON for further parsing or repair.

### Requirement: Fallback JSON repair for non-structured-output backends
The system SHALL retain and use an LLM-powered JSON repair mechanism for backends where structured output mode is not available or disabled.

#### Scenario: Initial JSON parse failure on non-JSON-mode backend
- **WHEN** JSON parsing via the base Pydantic/JSON parser fails for a backend that does not support structured output
- **THEN** the system SHALL invoke the LLMJsonRepairOutputParser (or equivalent) with the original output, error message, and format instructions
- **AND** the system SHALL retry parsing repaired outputs up to a configured maximum number of attempts.

### Requirement: Future support for two-step generation of long-form content
The system SHALL allow future evolution of chains that produce large text payloads (e.g. scene text, chapter revisions) into a two-step generation pattern separating structure from long-form content, while still exposing a single Pydantic output model to callers.

#### Scenario: Two-step generation for scene text (future-compatible)
- **WHEN** a scene_text_chain implementation is updated to first generate structural metadata and then generate long-form content in a separate call
- **THEN** the chain implementation SHALL compose the final Pydantic `GeneratedScene` object in Python code
- **AND** the external interface and JSON schema for `GeneratedScene` SHALL remain stable for downstream chains and persistence.

## MODIFIED Requirements

### Requirement: LLM JSON strictness and error handling
The system MUST maintain strict JSON correctness for all chain outputs that are passed between stages or persisted, while allowing different enforcement mechanisms depending on backend capabilities.

#### Scenario: Structured-output backend
- **WHEN** a chain uses structured output mode supported by the backend
- **THEN** JSON correctness SHALL be primarily enforced by the provider/SDK via structured output / JSON mode
- **AND** additional repair steps SHOULD NOT be invoked in the normal success path.

#### Scenario: Legacy parsing backend
- **WHEN** a chain uses the legacy parsing path with `PydanticOutputParser + LLMJsonRepairOutputParser`
- **THEN** the system SHALL continue to enforce strict JSON correctness via Pydantic validation
- **AND** the new unified cleanup step SHALL be applied before any parsing or repair attempts to reduce avoidable failures (e.g. Markdown wrapping, trivial surrounding text).
