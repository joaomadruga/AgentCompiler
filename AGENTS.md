# AgentCompiler: project intent and contributor instructions

## Purpose and final goal

Rebuild AgentCompiler as an organized Python project that applies compiler techniques to the orchestration of specialized agents. This is a continuation of João Pedro de Moraes Madruga's undergraduate thesis at UFPE, supervised by Filipe Carlos de Albuquerque Calegario.

The central goal is verifiable action generation: express LLM-proposed plans in a restricted language, check trusted contracts deterministically, and provide precise diagnostics for bounded correction. Assume existing systems already have orchestration and parallel execution; those capabilities alone are not the contribution.

**Central hypothesis:** restricted action programs with verifiable contracts and diagnostic-guided correction can improve action reliability over unconstrained delegation to an orchestrator.

**Secondary hypothesis:** reduced planning burden may allow a smaller model with bounded repair to approach a stronger orchestrator's reliability at lower total cost and latency. This is subordinate, unvalidated, and must account for all retries and escalation.

Guarantee only explicitly encoded properties under trusted contract assumptions. Do not claim that compilation guarantees intent interpretation, factual truth, answer quality, or external success. Explicit state preconditions/postconditions, requirement coverage, richer effect enforcement, and automatic model escalation are proposed extensions, not existing functionality.

The final deliverable is a working, documented AgentCompiler with reproducible evidence for these hypotheses. A demonstration and LinkedIn post should explain the contribution, measured findings, and limitations without invented gains. Scheduling and optimization are supporting capabilities.

## Research and architectural references

- Original implementation: https://github.com/joaomadruga/pipeline-task-automation
- LLMCompiler paper: https://arxiv.org/pdf/2312.04511
- Preferred repository organization: https://github.com/joaomadruga/nino-backend
- Compiler optimization reference: https://llvm.org/docs/Passes.html

Use the original implementation as historical context, not as a specification to copy unchanged. The old runtime executes its strategies sequentially and uses simulated tool outputs. Its evaluation also has measurement and reference-answer issues. New benchmark conclusions must come from the new implementation and an explicitly defined protocol.

LLMCompiler informs the separation between planning, dependency-driven dispatch, and asynchronous execution. AgentCompiler applies these ideas to specialized agents. Document adaptations and avoid claiming that this repository reproduces the paper's experiments.

## Repository language

All content authored in this repository must be in English, including documentation, diagram labels, identifiers, comments, docstrings, prompts, configuration descriptions, tests, examples, developer-facing messages, and commit messages.

Preserve proper names and exact source identifiers. Conversations with the user may remain in their preferred language.

## Current scope and sequencing

The repository now contains an implemented runtime with Pydantic nominal contracts, conservative union compatibility, structured planning diagnostics, visual architecture documentation, and runnable examples. Live-provider evaluation and benchmarks are still pending. Keep status descriptions accurate as implementation progresses.

The benchmark design is intentionally deferred. Do not carry over the old datasets, comparisons, or customer-support and research scenarios as settled requirements. Do not implement benchmark scenarios until their purpose and protocol have been agreed with the user.

The planned sequence is:

1. Define the restricted action language and its verifiable guarantees using the existing runtime as a foundation.
2. Specify trusted types, state preconditions/postconditions, effect policies and formalized requirement coverage.
3. Define diagnostics, bounded repair, dynamic checks and explicit termination semantics.
4. Agree on a benchmark with an orchestrated, parallel-capable baseline.
5. Evaluate the central action-reliability hypothesis.
6. Evaluate the secondary smaller-model hypothesis with full resource accounting.
7. Produce a demonstration and publication grounded in measured evidence.

This sequence is a direction, not authorization to implement every stage during an unrelated or narrowly scoped request. Follow the user's current task and accepted decisions.

## Architecture and file organization

Follow the organization inspired by Nino: group related behavior together, keep prompts and schemas close to their agent, and centralize shared runtime infrastructure.

| Location | Responsibility |
|---|---|
| `src/agents/orchestrator/` | Planning, synthesis, and replanning behavior with local schemas and prompts |
| `src/agents/` | Specialist contracts, registry, and execution context |
| `src/compiler/` | Deterministic validation, compilation, scheduling, and execution |
| `src/compiler/optimizations/` | Explicit passes over the validated task graph |
| `src/core/` | Configuration, centralized LLM access, and tracing |
| `src/services/` | Composition of the complete request lifecycle |
| `tests/` | Runtime correctness tests |
| `examples/` | Small examples of the public execution flow |
| `docs/` | Architecture decisions, research context, and roadmap |
| `benchmark/` | All experimental code, dependencies' adapters, tests, datasets, results, and reports |

Runtime code in `src/` must not import `benchmark/`. Domain-specific experimental specialists belong inside `benchmark/`, not in the generic runtime. Keep comparison-framework dependencies optional and separate from runtime dependencies.

Implement application logic, runtime components, analysis, and benchmark tooling in Python. Use `pyproject.toml` and uv for dependency management; update `uv.lock` when dependencies change. Configuration and data files may use suitable formats such as JSON or YAML.

## Prompt research requirement

Before writing or modifying any prompt, consult the connected Research Agent MCP for relevant prompting techniques and read the supporting source or wiki page. Record the consulted sources in the prompt module or `docs/prompts.md`. Do not substitute an unresearched generic prompt. If the Research Agent is unavailable, complete independent work and report the missing capability before authoring prompts.

## Runtime design principles

- The orchestrator decides what work is needed and which data dependencies exist. Python controls validation, optimization, scheduling, and execution.
- Represent plans as directed acyclic graphs of tasks, not rigid lists or trees. A result may feed several tasks, and a task may consume several results.
- Give tasks stable IDs, explicit instructions, typed inputs and outputs, and explicit references to predecessor outputs. The same agent may execute multiple tasks.
- Release a task as soon as its own dependencies are satisfied. Avoid waiting for an entire layer when that barrier is unnecessary.
- Start with dependency-driven scheduling such as Kahn's algorithm. Topological ordering provides validity, not a guarantee of minimum latency.
- Use bounded async concurrency and declare whether registered agents support concurrent invocations. Do not share mutable request state accidentally.
- Keep execution context scoped to one run. Pass the instruction and required data to specialists rather than automatically sending the entire accumulated history.
- Centralize LLM construction and structured invocation in `src/core/llm.py`. Allow injected models and executables so deterministic components can be tested without live LLM calls.
- Define failure, retry, timeout, cancellation, and blocked-dependency semantics explicitly. Technical retries belong to execution; changes in resolution strategy belong to orchestration.
- Preserve valid results across replanning rounds and bound rounds, attempts, concurrency, and duration.
- Evaluate streaming planning and critical-path prioritization after the basic runtime works.

## Typed contract rules

Preserve Pydantic class identity in registry snapshots. The compiler accepts model subtypes for base inputs, rejects the reverse and unrelated models, and requires every source-union branch to fit a target branch. Typed references require typed producers; do not silently treat matching JSON shapes as nominal compatibility.

Keep JSON paths explicit; typed RootModel wrappers, aliases, and excluded fields are unsupported. Validate actual data with strict Pydantic validation, including custom validators. Base-typed JSON consumers see their declared fields. Validators must be deterministic and validation-only or idempotent; external state checks belong to actions. Literal data and model class names are not proofs of authorization or truth.

Planning diagnostics must identify affected tasks/inputs and expected/received types where applicable. Feed diagnostics and the rejected candidate into bounded repair, then revalidate the complete plan. Preserve legacy schema registrations. State preconditions/postconditions, requirement coverage, conditional union narrowing, and automatic model escalation remain deferred.

## Optimization correctness

Initial candidate passes are deduplication and dead task elimination. Keep each pass separate, testable, and observable through a record of changes.

Apply transformations only when contracts establish that they preserve required results and observable effects. Explicitly describe effects and whether a result is reusable.

Do not equate similar natural-language instructions with equivalent computations. Independent LLM evaluations may intentionally require separate calls. Writes and other external actions must not be merged or removed merely because their arguments match or their outputs appear unused.

Dead task elimination starts from the declared requested outputs and preserves required effectful tasks. Deduplication must account for operation, arguments, relevant context, and reuse permissions. Do not remove semantic dependencies merely to make a diagram look more parallel.

## Verification and documentation standards

- Prefer clear typed contracts, explicit construction, and small components with concrete responsibilities. Avoid speculative abstractions and placeholder APIs presented as working features.
- Test behavior that matters: dependency resolution, actual concurrency, graph validation, optimization preservation, failure propagation, cancellation, and run isolation.
- Separate deterministic correctness tests from paid or network-dependent experiments.
- Do not create or run unit tests unless the user explicitly changes this instruction. Validate changes with `make check`, runnable examples, and scoped manual integration checks. Keep integration exercises distinct from benchmark claims.
- Keep the README detailed but primarily visual: Mermaid diagrams, repository trees, and compact comparison tables. Use measured charts only when real data exists.
- Clearly distinguish implemented features, planned features, illustrative examples, and measured results.
- Update the README, architecture notes, and roadmap when accepted architecture or functionality changes.
- Write concise English commit messages describing the concrete change. Commit and push to `main` when requested by the user.

## Future benchmark requirements

All benchmark work stays inside `benchmark/`, and its design must be revisited with the user. Once defined, it should prioritize the central action-reliability hypothesis, then the secondary smaller-model hypothesis. The baseline must not be artificially limited to sequential execution. Explain the use case and isolate the contribution of compilation, diagnostics, repair, optimizations and scheduling.

Preserve reference answers separately from generated outputs. Record reproducible configuration, source revision, tools, model settings, limits, failures, and repetitions. Measure total request latency and its stages; distinguish LLM calls, agent executions, and tool calls. Evaluate output quality alongside latency and resource usage.

Separate controlled fixtures from live integrations and scheduler-only comparisons from end-to-end architecture comparisons. Report limitations and variability. Published LLMCompiler gains and results from the old thesis are context, not measurements of this version.
