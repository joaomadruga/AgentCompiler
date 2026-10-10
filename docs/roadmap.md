# Roadmap

## Existing foundation

- [x] Python runtime and Nino-inspired organization.
- [x] Structured plans, schema/reference/cycle validation and bounded planning repair.
- [x] Dependency scheduling, execution limits, tools, synthesis and replanning.
- [x] Contract-permitted deduplication and pure dead-task elimination.
- [x] Manual integration exercises without unit tests.
- [x] Documentation centered on verifiable action generation.

## Proposed research sequence

1. Define the restricted action language and precise acceptance guarantees.
2. Specify trusted types, state preconditions/postconditions and effect policies.
3. Identify which user requirements can be formalized and how interpretation errors are exposed.
4. Define diagnostics, bounded correction and safe termination semantics.
5. Agree on a benchmark comparing reliability against an orchestrated, parallel-capable baseline.
6. Evaluate the central hypothesis before treating model downsizing as a benefit.
7. Evaluate the secondary smaller-model hypothesis with all repair/escalation costs included.
8. Publish a demonstration and LinkedIn post grounded in measured results and limitations.

These steps are proposals, not implemented features or authorization to start coding. Benchmark design remains deferred. Streaming, scheduling policies and further optimization passes are supporting work, not the main research question.
