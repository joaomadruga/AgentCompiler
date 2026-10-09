# Architecture decisions

| Decision | Rationale |
|---|---|
| Python and a layout similar to Nino | Keep agents, schemas, prompts, core, and services familiar |
| DAG as the intermediate representation | Represent dependencies and shared results |
| Planning separate from execution | The LLM decides tasks; Python controls scheduling |
| Explicit passes in compiler/optimizations | Test each transformation and record changes |
| Context scoped to each execution | Avoid mixing results and state across requests |
| Isolated benchmark | Keep scenarios and comparisons outside the runtime |

## Open decisions before implementation

- Finalize schemas for agents, tasks, references, effects, and results.
- Define failure semantics, blocked dependencies, and partial outputs.
- Define the concurrency contract for registered agents.
- Choose LLM integration and structured output format.
- Define how new plans reference results from previous rounds.

Current files are documented placeholders, without implemented contracts or algorithms.
