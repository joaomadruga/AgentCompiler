# AgentCompiler

**Turn LLM-generated action plans into checked programs before executing them.**

A continuation of **AgentCompiler: An LLM Compiler for Parallel Multi-Agent Orchestration**, the undergraduate thesis by João Pedro de Moraes Madruga at UFPE, supervised by Filipe Carlos de Albuquerque Calegario. The reconstruction now centers on verifiable orchestration rather than parallelism alone.

> **Status:** an orchestration runtime exists, with DAG/schema validation, optimization, bounded execution, structured-response repair, and replanning. The broader contract-driven compilation approach described below is a research direction. Neither hypothesis has been validated; `benchmark/` remains a scaffold.

## The problem: too much responsibility in the orchestrator

Assume the baseline already has an orchestrator and parallel execution. It still asks the model to choose appropriate actions, supply compatible data, respect action constraints, and satisfy the request. In a long workflow, an unchecked planning mistake can propagate into later actions.

```mermaid
flowchart LR
    U[User intent] --> O[LLM orchestrator]
    O --> P[Action plan]
    P --> E[Execution including parallel tasks]
    E --> R[Result]
    O -. Must get constraints and dependencies right .-> P
```

The proposal is to express plans in a restricted action language with trusted contracts. The model proposes; a deterministic harness checks explicit properties, rejects invalid plans, and provides diagnostics for bounded correction.

## Central hypothesis: verifiable action generation

> **Agent plans expressed in a restricted language, with verifiable contracts and diagnostic-guided correction, can produce more reliable actions than unconstrained delegation to an orchestrator.**

```mermaid
flowchart TD
    U[User intent] --> L[LLM proposes a program]
    R[Trusted action registry and explicit requirements] --> C[Compile and check]
    L --> C
    C --> V{Declared checks pass?}
    V -->|No| D[Specific diagnostics]
    D --> B{Repair budget available?}
    B -->|Yes| L
    B -->|No| STOP[Stop without execution]
    V -->|Yes| E[Dependency-driven execution]
    E --> K[Check resolved inputs and actual outputs]
    K --> F[Result or explicit failure]
```

| Language/compiler concept | Property to make explicit | Scope |
|---|---|---|
| Restricted intermediate representation | Only registered actions, explicit arguments and references | Existing structured-plan foundation |
| Types and contracts | Compatible inputs, references and structured outputs | Existing schema/graph checks; partial static knowledge |
| Preconditions and postconditions | Required state before an action and verified state afterward | Proposed explicit contract layer |
| Effect system | Permitted state changes and conflicts between actions | Existing effect metadata; broader enforcement proposed |
| Requirement coverage analysis | Every formalized requirement has an accountable output/check | Proposed; intent must first be translated correctly |
| Compiler diagnostics and repair | Explain the violated rule and bound correction attempts | Existing validation feedback; richer diagnostics proposed |

**A validated plan satisfies the checks encoded in the harness. It does not automatically understand the user's intent, establish factual truth, or guarantee overall answer quality.** State-dependent conditions must be rechecked at execution time; validation cannot guarantee an external service will succeed.

### A sequential example where compilation matters

Illustrative action contracts, not a shipped domain integration:

```mermaid
flowchart LR
    A[Locate purchase] --> B[Cancel purchase]
    B --> C[Refund payment]
    C -. Missing payment and refundable amount evidence .-> D[Reject plan before execution]
```

```mermaid
flowchart LR
    A[Locate purchase] --> B[Verify payment]
    B --> C[Determine refundable amount]
    C --> D[Cancel purchase]
    D --> E[Refund payment using verified inputs]
```

The compiler catches the missing prerequisite because the action contract declares it. This example remains sequential: the potential benefit is preventing an invalid action sequence, not adding concurrency. A complete contract must also address authorization, current state, and effects; this simplified illustration is not a refund policy.

## Secondary hypothesis: smaller orchestrators

> **If verifiable constraints reduce the planning burden, a smaller model with bounded diagnostic-guided repair may achieve comparable reliability to a stronger orchestrator at lower total cost and latency.**

```mermaid
flowchart LR
    M[Smaller model proposes] --> C[Compile and check]
    C -->|Valid| E[Execute]
    C -->|Invalid| D[Diagnostics]
    D --> R[Bounded correction]
    R --> C
    R -. Persistent failure: proposed policy .-> S[Stronger model or stop]
```

This is a consequence to investigate, **not the central hypothesis or an established gain**. Retries and escalation may erase savings. Evaluation must count planning, validation, repair, escalation, execution, and failed attempts. The current runtime does not implement automatic model escalation.

| Priority | Question | Evidence needed |
|---|---|---|
| Central | Does compilation plus diagnostic-guided repair improve action reliability? | Compare with an orchestrated, parallel-capable baseline; separate contract violations from intent and task success |
| Secondary | Can a smaller planner preserve reliability while reducing resources? | Compare models with/without the harness; count total latency, cost, retries and escalation |
| Supporting | Do optimizations and scheduling reduce execution work? | Isolate those contributions rather than attributing all gains to compilation |

## Watch the hypothesis

[![From unchecked delegation to checked action programs](docs/visuals/execution-flow.svg)](docs/visuals/execution-flow.html)

**[Open the interactive animation](docs/visuals/execution-flow.html)** — follow an invalid proposal through diagnosis, correction, validation, and execution. A separate optional lane illustrates the smaller-model hypothesis.

GitHub shows the static preview. Download and open the self-contained HTML, or serve the repository locally:

```bash
python -m http.server 8000
# Open http://localhost:8000/docs/visuals/execution-flow.html
```

The animation is conceptual: playback timing is not execution latency, and no benchmark gains are depicted.

## Existing runtime foundation

```mermaid
flowchart LR
    O[LLM structured plan] --> V[Graph and schema validation]
    V --> P[Contract-permitted optimization passes]
    P --> S[Scheduler and executor]
    S --> F[Synthesis or bounded replanning]
```

The DAG represents dependencies and shared results; it is not itself a correctness guarantee. Trusted agent schemas and effect declarations come from the registry. Static checks use available schema information; resolved inputs and actual outputs are checked at runtime. The extended action language and state contracts remain to be designed.

## Implemented optimizations

The compiler applies independent passes after graph validation and validates the resulting graph again. Each transformation is recorded in the execution report.

```mermaid
flowchart LR
    subgraph Before[Before: duplicate work]
        A1[Retrieve document] --> B1[Summarize]
        A2[Retrieve same document] --> C1[Classify]
        B1 --> D1[Response]
        C1 --> D1
    end
    subgraph After[After: shared result]
        A3[Retrieve document once] --> B2[Summarize]
        A3 --> C2[Classify]
        B2 --> D2[Response]
        C2 --> D2
    end
```

| Pass | Application condition |
|---|---|
| Deduplication | Same registered agent/version, instruction, bindings, and dependencies within one run; explicitly reusable result |
| Dead task elimination | Task is explicitly pure and does not contribute to a requested output or a read/write task |

Two LLM calls with similar instructions are not automatically equivalent. Independent evaluations must remain independent. Writes and other external actions need declared effects to prevent incorrect transformations.

### Scheduling

```mermaid
flowchart LR
    A[Dependencies resolved] --> B[Ready task queue]
    B --> C{Capacity available?}
    C -->|Yes| D[Execute task]
    C -->|No| E[Wait for completion]
    D --> F[Update state and release successors]
    E --> F
    F --> B
```

| Implemented | Future extension |
|---|---|
| Topological validation and dependency-driven readiness | Automatic duration estimation from traces |
| FIFO or estimated critical-path priority | Streaming planning |
| Bounded concurrency and no layer barriers | Further optimization passes |

Topological ordering guarantees a valid order, not minimum latency. Benefits depend on dependencies, task duration, and resource limits.

## Specialized agents

```mermaid
flowchart LR
    I[Instruction and inputs] --> A[Specialized agent]
    C[Execution context] --> A
    A <--> L[LLM]
    A <--> T[Tools]
    A --> R[Structured result]
```

The registry describes capabilities and contracts. The compiler schedules tasks, and the same agent may execute distinct tasks. `concurrent=False` serializes invocations of a registered agent across runs sharing the registry, on the same event loop.

| Agent | Execution |
|---|---|
| `FunctionAgent` | An async Python function receiving instruction, resolved inputs, and run context |
| `LLMAgent` | A caller-provided role prompt and model, optionally using real registered tools |

Tool inputs and outputs are schema-validated. Tool observations feed the next model call. Tool calls within a specialist execute sequentially; separate DAG tasks execute concurrently. An agent's effect, reuse, retry, and concurrency declarations must be compatible with its tools.

Customer support, research, and other experimental specialists will be defined later inside `benchmark/`, keeping the runtime independent of a specific domain.

## Execution lifecycle

```mermaid
stateDiagram-v2
    [*] --> Planning
    Planning --> Validation
    Validation --> Planning: repair invalid plan
    Validation --> Execution: validated and optimized plan
    Execution --> Evaluation: tasks completed or execution blocked
    Evaluation --> Planning: replan using previous results
    Evaluation --> Response: sufficient information
    Response --> [*]
    Planning --> Termination: limit reached
    Execution --> Termination: unrecoverable failure
    Evaluation --> Termination: limit reached
    Termination --> [*]
```

Replanning preserves successful results. Every new task needs a fresh ID; new plans can reference successful results from previous rounds. Removed task IDs remain reserved. Retrying a task requires both a retry-safe agent contract and an explicitly retryable `AgentExecutionError`.

| Outcome | Behavior |
|---|---|
| Task failure | Dependent tasks become blocked; independent work continues |
| Task timeout | Task fails; dependencies become blocked |
| Run timeout | Running tasks are cancelled and partial results are retained |
| Caller cancellation | Child tasks are cancelled and awaited; cancellation propagates |
| Uncertain write-tool failure | Specialist fails without automatic replay of the tool loop |
| Replanning budget exhausted | Run stops without claiming completion |

Cancellation cannot undo external effects. Handlers must be cooperative async functions and handle their own external cleanup.

## Repository layout

```text
AgentCompiler/
├── AGENTS.md
├── src/
│   ├── __init__.py          # Public runtime API
│   ├── __main__.py          # Service-factory CLI
│   ├── agents/
│   │   ├── orchestrator/
│   │   │   ├── agent.py
│   │   │   ├── schemas.py
│   │   │   └── prompts/
│   │   │       ├── planning.py
│   │   │       └── synthesis.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── context.py
│   │   └── schemas.py
│   ├── compiler/
│   │   ├── compiler.py
│   │   ├── schemas.py
│   │   ├── validation.py
│   │   ├── scheduler.py
│   │   ├── executor.py
│   │   └── optimizations/
│   │       ├── deduplication.py
│   │       └── dead_tasks.py
│   ├── core/
│   │   ├── config.py
│   │   ├── llm.py
│   │   └── tracing.py
│   └── services/
│       └── execution_service.py
├── benchmark/
│   ├── README.md
│   ├── run.py
│   ├── harness.py
│   ├── configs/
│   ├── datasets/
│   ├── scenarios/
│   ├── baselines/
│   ├── evaluation/
│   ├── tests/
│   ├── results/
│   └── reports/
├── tests/
├── examples/
├── docs/
├── pyproject.toml
├── uv.lock
├── Makefile
└── .env.example
```

Architecture inspired by [nino-backend](https://github.com/joaomadruga/nino-backend): agents with local prompts and schemas, shared infrastructure in `core/`, and composition in `services/`.

```mermaid
flowchart TD
    S[services] --> A[agents]
    S --> C[compiler]
    A --> CORE[core]
    C --> CONTRACTS[Agent contracts]
    C --> CORE
    B[benchmark] --> S
    EX[examples] --> S
    TEST[tests] --> A
    TEST --> C
```

**The runtime in `src/` must not import `benchmark/`.** Runtime correctness tests belong in `tests/`; experimental code, tests, and artifacts belong entirely in `benchmark/`.

## Development

Python **3.12+**, with dependencies managed by **uv**. The source package uses `src` imports, following the project layout.

```bash
git clone git@github.com:joaomadruga/AgentCompiler.git
cd AgentCompiler
uv sync --locked
make check
make demo
```

| Command | Current action |
|---|---|
| `make install` | Install development dependencies |
| `make check` | Check syntax, lint, and whitespace |
| `make lint` | Run Ruff |
| `make demo` | Execute a Python-only example with deduplication and dead task elimination |
| `make test` | Reserved pytest command; no unit tests were added or run |

### Python-only execution

```python
import asyncio
from src import AgentCompiler
from examples.parallel_plan import build_plan, build_registry

async def main():
    compiler = AgentCompiler(build_registry())
    report = await compiler.execute(build_plan())
    print(report.outputs)  # {"summary": {"total_words": 10}}
    print(report.changes)

asyncio.run(main())
```

The example performs real Python operations. Its five-task plan becomes three executions through deduplication and removal of unused pure work. This demonstrates functionality, not a benchmark or a latency claim.

### LLM planning and synthesis

Configure `.env` from `.env.example`, then run:

```bash
uv run python -m examples.llm_orchestration "Count words in these texts: hello world; graphs enable parallel execution"
```

```python
from src import ExecutionService, Settings, build_llm
from examples.parallel_plan import build_registry

async def run_request(request):
    settings = Settings()
    async with build_llm(settings) as model:
        service = ExecutionService.from_model(build_registry(), model, settings)
        result = await service.run(request)
        return result
```

The built-in adapter uses OpenAI-compatible **Chat Completions**. JSON mode is the default; responses are locally validated against Pydantic and JSON Schema contracts, with bounded repair attempts. Optional `json_schema` mode is non-strict and still uses local validation. Models requiring a different API need an injected `LanguageModel` adapter. No live API request is required for `make demo`.

`LLMAgent` accepts a model, a role prompt, an `AgentSpec`, and optional tools. Research the prompt techniques in the connected Research Agent before authoring or changing any prompt.

### CLI and tracing

```bash
uv run python -m src "Your request" --factory your_app:create_service --trace run.jsonl
```

The factory returns an `ExecutionService` (directly or asynchronously), or an async context manager yielding one. A factory that owns an LLM client should use the context-manager form to close it. `--output report.json` writes the run report instead of printing it.

```mermaid
flowchart LR
    RUN[Execution context] --> E[Structured events]
    E --> M[In-memory trace]
    E --> C[Optional callback]
    M --> J[JSONL export]
    RUN --> R[Run report]
    R --> U[LLM calls, tool calls, tokens and estimated cost]
    R --> T[Task results, optimization changes and timings]
```

Tracing does not emit prompts or task outputs by default. Reports do contain task outputs; store them accordingly. Token usage comes from provider responses. Calls with no returned usage still count as attempts. Cost estimates use explicitly configured per-million-token prices; zero defaults mean prices are unconfigured, not that the provider is free.

| Setting prefix: `AGENTCOMPILER_` | Default |
|---|---|
| `MAX_CONCURRENCY` / `MAX_TASKS` | 4 / 128 across the run |
| `MAX_ROUNDS` / `MAX_PLAN_ATTEMPTS` | 3 / 3 per structured invocation |
| `MAX_TASK_ATTEMPTS` | 2, only for retry-safe agents |
| `MAX_TOOL_CALLS` / `MAX_LLM_CALLS` | 12 per specialist invocation / 100 per run |
| `RUN_TIMEOUT_SECONDS` / `TASK_TIMEOUT_SECONDS` | 300 / 60 |
| `LLM_TIMEOUT_SECONDS` / `LLM_MAX_TOKENS` | 60 / 4096 |
| `SCHEDULING` / `OPTIMIZE` | `fifo` / `true` |
| `LLM_MODEL` / `STRUCTURED_MODE` | `gpt-4o-mini` / `json_object` |

See [runtime settings](src/core/config.py) and [.env.example](.env.example) for every option.

**All repository content must be written in English**, including documentation, diagrams, code comments, docstrings, prompts, and developer-facing messages. This project rule is recorded in [AGENTS.md](AGENTS.md).

## Research roadmap

```mermaid
flowchart LR
    A[Existing runtime foundation] --> B[Define action language and guarantees]
    B --> C[Specify diagnostics and bounded repair]
    C --> D[Evaluate central reliability hypothesis]
    D --> E[Evaluate smaller-model hypothesis]
    E --> F[Demonstration and publication]
```

The current runtime is a foundation, not an implementation of every proposed guarantee. Explicit state preconditions/postconditions, requirement coverage checks, formal effect policies, and automatic model escalation are proposed work. Benchmark design remains deferred; no runtime changes are part of this documentation revision.

See [architecture](docs/architecture.md), [research hypotheses](docs/research.md), and [roadmap](docs/roadmap.md) for scope and evidence boundaries. Previous manual integrations are functionality checks, not evidence that either hypothesis holds.

## References

- [An LLM Compiler for Parallel Function Calling — Kim et al., ICML 2024](https://arxiv.org/pdf/2312.04511): dependency planning, Task Fetching Unit, asynchronous execution, and streaming planning.
- [Previous AgentCompiler implementation](https://github.com/joaomadruga/pipeline-task-automation): original undergraduate thesis project.
- [LLVM: Analysis and Transform Passes](https://llvm.org/docs/Passes.html): reference for redundancy and dead code elimination.

This reconstruction adapts compilation ideas to agent orchestration. It does not reproduce the LLMCompiler experiments, and the gains published in that paper are not results of this project.
