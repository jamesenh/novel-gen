## 1. Proposal Acceptance
- [x] 1.1 Review/confirm v2 scope, non-goals, acceptance criteria

## 2. Specs (Baseline for v2)
- [x] 2.1 Add orchestration requirements (chapter loop + blocker gate)
- [x] 2.2 Add persistence requirements (artifact write + sync invariants)
- [x] 2.3 Add agent-plugins requirements (plugin I/O contract + no direct writes)
- [x] 2.4 Add validation requirements (schema checks before persistence)
- [x] 2.5 Run `openspec validate refactor-v2-workflow-agent-plugins --strict` and fix issues

## 3. Implementation (MVP Slice)
- [x] 3.1 Decide v2 package layout aligned with `docs/开发文档.md` (use `app/` + `python -m app.main`)
- [x] 3.2 Scaffold Python package + CLI entry (`init`, `run --project --chapters`)
- [x] 3.3 Implement config loading (env + `.env.example`) for `PROJECT_NAME`, thresholds, and paths
- [x] 3.4 Define `State` model and run identifiers (`run_id`, `chapter_id`)
- [x] 3.5 Define minimal schemas + required metadata fields (`schema_version`, `generated_at`, `generator`)
- [x] 3.6 Implement minimal nodes: plan → write → audit(plugin) → apply_patch → store
- [x] 3.7 Implement plugin registry and a no-op plugin + one "continuity" plugin stub (issues w/ evidence + fix hints)
- [x] 3.8 Implement persistence writer: standard paths + atomic bundle write for chapter/artifacts
- [x] 3.9 Handle optional DB: if `data/novel.db` exists, mark it stale (or update) consistently with the written artifacts
- [x] 3.10 Add tests: blocker routing loop + schema validation contract + plugin no-write boundary

## 4. Documentation
- [x] 4.1 Update `docs/开发文档.md` only where it conflicts with v2 baseline (minimal edits)

## 5. Implementation Completion (Make MVP Truly Spec-Compliant)

### 5.1 Fix config → runtime wiring
- [x] 5.1.1 Pass `Config.max_revision_rounds` into `create_initial_state(..., max_revision_rounds=...)` so `MAX_REVISION_ROUNDS` actually affects routing
- [x] 5.1.2 Define/implement how `qa_blocker_max` / `qa_major_max` participate in gating (either remove them from config, or use them in routing and tests)

### 5.2 Make persistence "atomic bundle write" real
- [x] 5.2.1 Implement atomic chapter bundle write: write all chapter artifacts to a temp dir/files and `rename()` into place only after all writes succeed
- [x] 5.2.2 Define failure behavior: if any write fails, ensure no partial chapter artifacts remain (and add a targeted unit test)

### 5.3 Expand "schema validation before persistence" to all structured artifacts we write
- [x] 5.3.1 Add schema(s) and validation for `consistency_reports.json` (or its per-chapter entries) and validate before writing
- [x] 5.3.2 Add schema(s) and validation for `chapter_memory.json` and validate before writing
- [x] 5.3.3 Validate plugin output (`issues`) and aggregated `audit_result` against schema before persisting (reject invalid plugin issues with actionable error)
- [x] 5.3.4 Ensure validation errors include field path + reason in surfaced exception/message (and add/adjust tests accordingly)

### 5.4 Fill missing identifiers promised by the proposal/tasks
- [x] 5.4.1 Add `revision_id` to `State` (and decide how it increments across revision loop rounds)
- [x] 5.4.2 Persist `run_id` + `revision_id` (and/or embed into `generator`) into chapter plan/content so artifacts are traceable across runs and revisions

### 5.5 Add an end-to-end "artifact contract" test
- [x] 5.5.1 Add an integration test that runs `build_graph(...).invoke(create_initial_state(...))` against a temp project root and asserts these files exist after 1 chapter: `chapters/chapter_001_plan.json`, `chapters/chapter_001.json`, `consistency_reports.json`, `chapter_memory.json`
- [x] 5.5.2 In the integration test, assert the persisted JSON includes required metadata fields (`schema_version`, `generated_at`, `generator`)

### 5.6 Align documentation with actual CLI surface
- [x] 5.6.1 Update `docs/开发文档.md` to match implemented commands (remove/mark `change` and `export` as "planned", or implement them)
- [x] 5.6.2 Ensure examples for `python -m app.main ...` match actual argparse options (`--prompt`, `--chapters`, etc.)
