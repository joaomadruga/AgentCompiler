# Research direction and hypotheses

AgentCompiler originates in João Pedro de Moraes Madruga's UFPE undergraduate thesis, supervised by Filipe Carlos de Albuquerque Calegario. The reconstruction shifts its primary question from parallel execution to verifiable action generation.

## Central hypothesis

Agent plans expressed in a restricted language, with verifiable contracts and diagnostic-guided correction, can produce more reliable actions than unconstrained delegation to an orchestrator.

Assume comparison systems already orchestrate agents and support parallel execution. The proposed contribution is moving explicitly formalizable obligations from model judgment into deterministic checks. A DAG is a useful representation, not the entire contribution.

## Secondary hypothesis

A smaller planning model, supported by compilation and bounded repair, may approach a stronger orchestrator's reliability with lower total cost and latency. This depends on repair frequency, escalation, contract coverage, and model performance. It is unvalidated and subordinate to the central reliability hypothesis.

## Evidence boundaries

| Claim | Current status |
|---|---|
| Structured planning, Pydantic nominal contracts, schema/graph checks, diagnostic-guided repair and execution exist | Implemented first slice; manually exercised |
| Explicit state contracts and requirement coverage are enforced | Proposed; not implemented |
| Compilation improves end-to-end action reliability | Unvalidated central hypothesis |
| A smaller model saves resources at comparable reliability | Unvalidated secondary hypothesis |
| Parallelism or optimization alone proves either hypothesis | Insufficient evidence |

A future protocol should distinguish encoded-contract compliance, intent alignment, factual quality, and actual task success. Candidate comparisons include the same model with and without checks, and smaller/stronger models under matched contracts, tools and budgets. Count retries and failures in full. These are evaluation questions, not a settled benchmark design.

## Historical references

| Source | Role |
|---|---|
| Original thesis and implementation | Historical specialist orchestration proposal; old results do not validate this version |
| LLMCompiler | Dependency planning and dispatch inspiration; its published gains are not this project's results |
| Traditional compiler concepts | Restricted representations, contracts, analysis and diagnostics motivate the new direction |

- [Previous implementation](https://github.com/joaomadruga/pipeline-task-automation)
- [LLMCompiler paper](https://arxiv.org/pdf/2312.04511)
- [LLVM analysis and transformation passes](https://llvm.org/docs/Passes.html)

The hypotheses above are this project's proposals, not findings attributed to these references.
