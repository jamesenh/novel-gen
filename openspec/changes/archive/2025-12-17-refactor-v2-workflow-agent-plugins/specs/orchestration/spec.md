## ADDED Requirements

### Requirement: Chapter Loop Execution
The system SHALL execute a chapter loop from `chapter_id = 1` through `num_chapters`, producing required artifacts for each chapter under `projects/<project>/chapters/`.

#### Scenario: Run generates first chapter
- **WHEN** the user runs the workflow with `--chapters 1`
- **THEN** the system produces `chapters/chapter_001_plan.json` and `chapters/chapter_001.json`
- **AND THEN** the system produces updated `consistency_reports.json` and `chapter_memory.json`

### Requirement: Audit-and-Revision Gate
The system SHALL NOT advance to the next chapter unless the latest audit result for the current chapter has `blocker == 0`.

#### Scenario: Blockers force revision loop
- **WHEN** an audit result for the current chapter reports `blocker > 0`
- **THEN** the system enters a revision loop for the same `chapter_id`
- **AND THEN** the system re-runs audit after applying the revision

#### Scenario: Passing gate advances chapter
- **WHEN** an audit result for the current chapter reports `blocker == 0`
- **THEN** the system MAY advance to the next chapter

### Requirement: Revision Loop Bound
The system SHALL enforce a maximum number of revision rounds per chapter to prevent infinite loops.

#### Scenario: Exhausted revisions stops automation
- **WHEN** the maximum revision rounds is reached and `blocker > 0` remains
- **THEN** the system marks the chapter as `needs_human_review`
- **AND THEN** the system stops automatic advancement

