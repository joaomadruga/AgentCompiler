# Decisões de arquitetura

| Decisão | Motivo |
|---|---|
| Python e organização semelhante ao Nino | Manter familiaridade com agentes, schemas, prompts, core e services |
| DAG como representação intermediária | Representar dependências e resultados compartilhados |
| Planejamento separado da execução | LLM decide tarefas; Python controla o agendamento |
| Passes explícitos em compiler/optimizations | Permitir testar cada transformação e registrar o que mudou |
| Contexto por execução | Evitar misturar resultados e estado entre solicitações |
| Benchmark isolado | Manter cenários e comparações fora do runtime |

## Pendências antes da implementação

- Fechar schemas de agente, tarefa, referências, efeitos e resultados.
- Definir a semântica de falhas, dependências bloqueadas e saídas parciais.
- Definir o contrato de concorrência dos agentes registrados.
- Escolher integração com LLM e formato de saída estruturada.
- Definir como novos planos referenciam resultados de rodadas anteriores.

Os arquivos atuais são placeholders documentados, sem contratos ou algoritmos implementados.
