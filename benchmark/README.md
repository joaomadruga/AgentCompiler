# Benchmark

Reserved for a future benchmark design. No datasets, scenarios, baselines, evaluation logic, or results have been implemented.

All benchmark-specific code and artifacts will remain inside this directory. The AgentCompiler runtime must not import from `benchmark/`.

## Research priorities, pending protocol design

1. **Central:** test whether restricted action programs, verifiable contracts, and diagnostic-guided repair improve action reliability against an orchestrated, parallel-capable baseline.
2. **Secondary:** test whether a smaller planner can preserve reliability at lower total cost and latency with bounded repair, including any escalation overhead.

Keep encoded-contract compliance distinct from intent alignment and task success. Parallelism alone does not establish the central hypothesis. No experiment, scenario, dataset or protocol is implemented or finalized here.
