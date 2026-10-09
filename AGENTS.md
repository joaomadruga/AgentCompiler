# Project memory and contributor instructions

## Repository language

All content authored in this repository must be in English. This includes:

- Documentation, headings, tables, and diagram labels.
- Code identifiers, comments, and docstrings.
- Agent prompts, configuration descriptions, and developer-facing messages.
- Tests, examples, and benchmark descriptions.
- Commit messages.

Preserve proper names and exact source identifiers. This rule governs repository content; conversations with the user may remain in their preferred language.

## Current scope

The repository is an initial Python scaffold. Do not describe planned functionality as implemented or present hypothetical performance gains as measured results.

Keep all benchmark-specific code, tests, datasets, and artifacts inside `benchmark/`. Its design is deferred. Runtime code in `src/` must not import from `benchmark/`.

Follow the existing organization: agent-local schemas and prompts, deterministic compilation in `src/compiler/`, shared infrastructure in `src/core/`, and lifecycle composition in `src/services/`.
