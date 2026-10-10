# Prompt research and implementation

## Role in the new direction

Prompts generate candidate plans; they do not establish correctness. The central hypothesis assigns encoded obligations to deterministic compilation and uses diagnostics to guide bounded correction. The planning prompt now includes nominal model compatibility, conservative union handling, and correction using structured diagnostics. The update consulted Research Agent `concepts/prompt-engineering` and `concepts/tool-use` before authoring.

Explicit state contracts, requirement coverage, richer repair policies, and smaller-model escalation remain proposed work. Prompt quality alone does not validate either research hypothesis.

## Existing prompt provenance

Each runtime prompt was authored after consulting the connected Research Agent MCP. Source references are also recorded in the corresponding Python modules.

| Prompt | Research Agent sources | Applied technique |
|---|---|---|
| Planning | `plan-and-solve`, `sources/plan-and-solve`, `concepts/planning`, `concepts/compositional-reasoning` | Separate planning from execution; explicitly decompose required facts and operations, with named inputs and dependency references |
| Synthesis | `self-ask`, `concepts/evidence-boundaries`, `concepts/reasoning-and-acting` | Compose successful observations, constrain claims to evidence, and return actionable feedback when work remains |
| Specialist execution | `react`, `concepts/tool-use`, `concepts/reasoning-and-acting` | Interleave actual tool calls and observations before returning the structured result |
| Typed planning and diagnostic repair | `concepts/prompt-engineering`, `concepts/tool-use` | Explicit model identities, ancestry, all-branch compatibility, diagnostic-specific bounded correction and preservation of valid work |
| Schema and repair instructions | `concepts/prompt-engineering`, `concepts/tool-use` | Explicit output contracts and bounded correction using validation diagnostics |

These are adaptations for this runtime, not reproductions of the papers' prompts or evidence of their reported gains. The runtime requests structured artifacts and task results, not private reasoning traces.

## Public research references

- [Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Measuring and Narrowing the Compositionality Gap in Language Models](https://arxiv.org/abs/2210.03350)

Before changing prompts, consult the Research Agent again for the techniques relevant to the change.
