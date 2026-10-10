# Architecture decisions

| Decision | Rationale |
|---|---|
| Python and a layout similar to Nino | Keep agents, schemas, prompts, core, and services familiar |
| DAG as the intermediate representation | Represent dependencies and shared results |
| Planning separate from execution | The LLM decides tasks; Python controls scheduling |
| Explicit passes in compiler/optimizations | Test each transformation and record changes |
| Context scoped to each execution | Avoid mixing results and state across requests |
| Isolated benchmark | Keep scenarios and comparisons outside the runtime |

## Contracts and behavior

- `AgentSpec` is trusted configuration; the planner cannot redefine effects or reuse permissions.
- Input bindings use literal JSON or an explicit RFC 6901 output reference.
- Graph validation checks cycles, identities, inputs, known output paths, and provably incompatible types. Full schema validation runs on resolved inputs and actual outputs.
- Reuse is local to a compiled plan; across rounds, the planner must reference successful earlier results explicitly.
- Dead task elimination preserves all read/write tasks and their prerequisites.
- Scheduler policy is FIFO or estimated critical path; no layer-wide barrier is imposed.
- Nonconcurrent registered agents are serialized across runs sharing the registry, on one event loop.
- Task failures block dependent work; independent work continues. Run deadlines cancel outstanding tasks and preserve partial results.
- Replanning reserves all old task IDs and has task, round, duration, and LLM-call limits.
- The built-in provider adapter uses Chat Completions with JSON mode or non-strict JSON Schema mode and local schema validation. Alternative APIs can implement `LanguageModel`.

## Deferred work

Streaming planning, automatic duration estimation, additional optimization passes, and the entire benchmark design remain future work. Live-provider behavior has not been evaluated. No unit tests were added or executed at the user's request.
