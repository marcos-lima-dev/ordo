# ORDO --- MASTER HANDOFF

**Conversational Order Intelligence Engine**\
**Checkpoint (HISTÓRICO / SUPERADO):** 2026-09-18 --- imediatamente antes
do HOLDOUT-2 Final Blind Gate.

**Checkpoint atual:** `c18ec6b20eda62af5d4746c310ed504ef01c5f73` ---
Track 9B.2 `CLOSED / ACCEPTED` (2026-09-21).

> **Instrução para um novo chat:** Assuma o papel de Tech Lead do Ordo.
> Este documento consolida o histórico, decisões arquiteturais e
> freezes. Continue exatamente do Stop Point. Não reabra decisões
> congeladas sem evidência nova. Chame o time executor de **Equipe** ou
> **Equipe de Engenharia**.

## 1. Produto e tese

**Ordo** é um motor inteligente de pedidos conversacionais.

> **Transformar conversas comerciais do WhatsApp em operações
> estruturadas de venda.**

Território: **WhatsApp → Pedido → Operação**. O Ordo não é um ERP
completo.

Princípio central:

> **A conversa deixa de ser o pedido. A conversa produz um pedido.**

Fluxo comercial validado: cliente pede → pedido evolui por conversa →
vendedor/Ordo organiza → ambiguidades são esclarecidas → cliente
confirma → pedido confirmado segue à operação/estoque → produtos são
separados. O escopo validado termina aí. Faturamento, expedição,
entrega, comissão, crédito e outras regras não devem ser inventados.

## 2. Princípios arquiteturais

> **IA interpreta → Catálogo fornece candidatos → Software valida →
> Incerteza é explicitada → Humano/cliente resolve quando necessário →
> Regras determinísticas executam.**

Nunca permitir que modelo invente produto, unidade, preço, estoque,
conversão ou regra operacional.

> **Não construímos o Ordo ao redor de um modelo. O modelo é um
> componente substituível do Ordo.**

Pergunta recorrente:

> **Qual é a menor tarefa que precisamos entregar ao modelo para que o
> restante possa ser resolvido deterministicamente?**

Modelos são fornecedores de sinais, não autoridades sobre a operação
comercial.

## 3. Semântica de quantidade

Manter separados: quantidade solicitada; unidade dita pelo cliente;
unidade comercial; apresentação física; peso de referência; número de
peças; quantidade separada/medida; eventual quantidade faturável.

Regras: - `"2"` não significa automaticamente 2 kg nem 2 embalagens. -
`"10kg manteiga sem sal"` preserva `10 KG`. - Não converter para duas
embalagens de 5 kg só porque o catálogo possui embalagem de referência
de 5 kg. - Multiplicadores como `8 x 1,2kg` são dados
logísticos/fabricante e não provam "caixa" como unidade de venda. -
`"6 bisnagas"` preserva quantidade e apresentação explícitas.

## 4. Catálogo

Fonte original: `chateaudulait-produtos - JAN 24.csv`.

Resumo: 92 linhas de origem; 77 produtos válidos normalizados.

Campos v0.2: `product_id`, `original_name`, `normalized_name`, `brand`,
`unidade_precificacao`, `apresentacao_individual`,
`peso_referencia_individual`, `embalagem_master`,
`quantidade_unidades_master`, `preco_vista`, `preco_prazo`.

Aliases têm `alias_text`, `product_id`, `source`, `confidence`,
`approved`. Alias ajuda na recuperação; não prova identidade.

SKUs relevantes: - CQ-28 --- Manteiga c/sal Coyote - CQ-29 --- Manteiga
s/sal Coyote - CQ-44 --- Provolone Tânia - CQ-46 --- Provolone forma 5
kg Riqueza de Minas - CQ-06 --- Queijo Azul/cartela, tipo gorgonzola,
São Vicente - CQ-07 --- Queijo Azul/forma, tipo gorgonzola, São Vicente

## 5. Regras semânticas

Preservar o que o cliente disse antes de usar catálogo. Separar: cliente
disse / modelo interpretou / catálogo informou / sistema concluiu.

Informação ausente continua ausente. Número não é unidade. Unidade de
preço não é apresentação. Peso de referência não prova peso exato ou
fracionabilidade. Marca é separada do produto. Existência no catálogo
não significa estoque. KG→embalagem não é regra operacional. Preço
somente da fonte. High confidence não autoriza execução.

Intents: `ADD_ITEM`, `REMOVE_ITEM`, `CHANGE_QUANTITY`, `QUERY_PRICE`,
`QUERY_AVAILABILITY`, `CONFIRM_ORDER`, `CANCEL_ORDER`, `REPLACE_ITEM`,
`UNKNOWN`.

Product resolution: `EXACT_MATCH`, `HIGH_CONFIDENCE`, `AMBIGUOUS`,
`NOT_FOUND`.

## 6. Contrato semântico v1.1.2 🔒

Arquivos: - `contracts/semantic_interpreter_v1_1_2.schema.json` -
`docs/contrato-interpretador-semantico-v1.1.2 .md`

Campos principais: intent, product_term, quantity value/origin/unit,
explicit presentation/brand, contextual references, missing information,
catalog candidates, product resolution status.

Backend é responsável por aritmética, preços, crédito, conversões,
estoque, logística e ações externas.

## 7. Histórico técnico

### Sprint 01 --- Baseline v0 🔒

77 produtos, 187 aliases, Golden Dataset 30, validações PASS.\
Commit: `5702f2b4af59560b40bae4ec8c6666b3f16e562a`

### Sprint 02 --- Benchmark v1 🔒

Runner, evaluator, adapters, métricas e testes.\
Commit: `2e9de0cf319b65a045e0b7c77a6fc7f2dc6e391d`

### Fase 3 --- Baselines

DeterministicAdapter: schema 100%, unsafe 0, intent fraco.\
Tucano 0.5B: intent 40%, schema 40%, 8 unsafe.\
NuExtract tiny: schema 100%, unsafe 0, intent 0%.

Modelos gated/não acessíveis: Drummond-1b1-Instruct, Arandu-Mirim-1.1,
GLiNER2-PTBR.

### Fase 4 --- ADR híbrida

Modelo leve fornece sinais; Safety Validator; resolução determinística.
Adapters substituíveis.

### Fase 5 --- Conversa e estado

Mudança: `OrderState(t) + Message(t+1) → OrderState(t+1)`. Ambiguidade
passa a ser estado válido. Introduzidos OrderState, PendingResolution e
análise contextual. `"pode fechar"` pode ser intent de confirmação e
ainda assim ter execução bloqueada por pendência.

### Gate 5.1

52 mensagens + 10 conversas/24 turnos. Intent holdout 86,5%; intent
conversacional 91,7%; final state 1/10; unsafe 0; schema 100%. Golden
antigo teve overlap com treino e não deve ser tratado como evidência
independente.

### Gate 5.2

GLiNER Base: PRODUCT F1 .523, BRAND .821, PRESENTATION .000.\
BERT NER fine-tuned: PRODUCT .110, BRAND .604, PRESENTATION .522.\
Não se autorizou otimização de componente isolado sem E2E.

### Phase 5.2 E2E

Final state 1/10 nos cenários existentes, 0/5 novos, unsafe 0. Gargalos:
produto/entity, contexto, target e composição.

### Phase 5.3

CatalogRetriever: Recall@1 90,38%; Recall@3/5 94,23%; ambiguity
detection 76,92%.

Princípio: \> **CatalogRetriever recupera. ProductResolver decide.
GLiNER ajuda.**

Commits: - Target Resolver Stage1:
`92c3581c754660c1579f44d8a70a639f2a266575` - Pending Resolver Stage2:
`204a729ce4052de75c7d2dac1bad4393b05bf74c` - Resolution Composer Stage3:
`05f05389b133d277fa5ed59b2a1a9d7e9eabd38c` - REPLACE composition Stage4:
`680783af268f9ec08c22d878c296ebf52a2faf76`

### Semantic Routing Diagnostic

DEV-02: entidade ruidosa, mas mensagem original + OrderState permitem
resolução robusta.\
DEV-04: classifier erra `"muda para 4"`.\
DEV-07: source extraction falha; destination gorgonzola é ambíguo
CQ-06/CQ-07.\
DEV-09: ground truth questionável; `"coloca 3"` sem contexto não
sustenta CHANGE.\
DEV-10: classifier diz ADD para `"tira uma"`, embora haja forte sinal
REMOVE.

Conclusão: \> **`message_intent ≠ resolved_operation_type`**

### Etapa 6 --- Operation Resolver V1

Commit: `e1bfb5d9f452279682d38afcf2e94bab48ba58e9`

`OperationResolution` contém `message_intent`,
`resolved_operation_type`, `status`, `source`, `evidence`.

Sinais determinísticos inequívocos podem superar o classificador.
Conflito relevante pode resultar em `AMBIGUOUS`. OperationResolver não
resolve target nem product.

TargetResolver ganhou robustez controlada usando mensagem original +
itens do OrderState.

DEV 5/10 → 7/10. Wrong Executable Operation Rate = 0.

### Etapa 7 --- Benchmark Integrity Review

Foram encontrados ground truths questionáveis/inválidos/incompletos: -
DEV-04 dependia de política; - DEV-07 escolhia CQ-06 sem evidência
contra CQ-07; - DEV-09 sem contexto suficiente; - HOLDOUT-03 sem
contexto anterior; - HOLDOUT-04/09/10 sem reason_code; - HOLDOUT-05 sem
PendingResolution necessário; - HOLDOUT-07 apontava para CQ-99
inexistente.

## 8. Política P1

Decisão:

> **`UNIQUE_ELIGIBLE_TARGET` pode autorizar o target somente depois que
> `resolved_operation_type` estiver resolvido, a operação exigir item
> existente, houver exatamente um target elegível e não existir
> evidência conflitante ou contexto incompatível.**

Pode aplicar-se a CHANGE_QUANTITY, REMOVE_ITEM e source de REPLACE_ITEM.

P1 não resolve OperationType. `"coloca 3"` não vira CHANGE apenas porque
existe um item.

Proveniência: `UNIQUE_ELIGIBLE_TARGET`.

## 9. Benchmark V2 🔒

Commit Benchmark V2: `de07dcaeadecbdc5e0f99ecfa7ac887b6a9e57ab`\
Commit scripts V2: `9f70f0df64d756af6b128a6890c88053af033c0f`

Arquivos: - `datasets/resolved_operation_dev_v2.jsonl` -
`datasets/resolved_operation_holdout1_v2.jsonl` -
`datasets/benchmark_manifest_v2.json` -
`docs/benchmark_v2_changelog.md` - `scripts/validate_benchmark_v2.py`

V1 preservado.

Resultados congelados: - **DEV V2: 9/10** - **HOLDOUT-1 V2: 9/10** -
**Wrong Executable Operation Rate: 0**

Interpretação correta: DEV V2 é development/regression evidence;
HOLDOUT-1 V2 já foi observado e é validation/regression evidence. Os 90%
não são estimativa independente de generalização.

DEV-09 permanece `GROUND_TRUTH_QUESTIONABLE`.

HOLDOUT-01 (`"quero 5kg de manteiga com sal"`) é o único erro de
HOLDOUT-1 V2, mas sua investigação está suspensa até depois do blind
gate.

### 9.1 — HOLDOUT-2

### 9.1 — HOLDOUT-2 — resultados históricos

```text
RAW BLIND                 11/20 = 55%
POST-BLIND Track 9A       13/20 = 65%
POST-BLIND Track 9B.2     12/20 = 60%
Wrong Executable Operation = 0
```

`11/20` é o único RAW BLIND desta sequência. Resultados posteriores são
`POST-BLIND REGRESSION`; nenhum é reclassificado como blind.

Não criar `adjusted blind`, `corrected blind`, `re-blind` ou `new blind`.

## 10. Order Engine 🔒

Contrato: `OrderState + ResolvedOperation → NewOrderState`

Operações: ADD, REMOVE, CHANGE, REPLACE, CONFIRM, CANCEL.

Fase de Order Engine teve 15/15 testes determinísticos PASS. Reabrir
somente diante de caso reproduzível
`valid state + valid operation → wrong state`.

## 10.1 — Authorization policy (R2)

`retrieval evidence != execution authorization evidence`

Autorizam `EXACT_MATCH`:

-   `ALIAS_EXACT`
-   `NAME_EXACT`
-   `ORIGINAL_EXACT`
-   `APPROVED_ALIAS`
-   `ENTITY_SIGNAL`

Não autorizam isoladamente:

-   `ALIAS_TOKEN`
-   `NAME_TOKEN`
-   `ALIAS_SUBSET`
-   `NAME_SUBSET`
-   `ALIAS_FUZZY`

`evidence=None` não autoriza `EXACT_MATCH`.

## 11. Pipeline vigente

`Message` → sinais linguísticos/entity/quantity → `message_intent` →
`OperationResolver` → `resolved_operation_type` →
Reference/Pending/Target Resolution → Catalog Retrieval/Product
Resolution → `ResolutionComposer` →
`ResolvedOperation | NEEDS_CLARIFICATION` → Safety → `Order Engine` →
`OrderState`

Separações obrigatórias: - message_intent ≠ resolved_operation_type -
extracted_product_term ≠ resolved_product_id ≠ resolved_product_name -
OperationResolver não escolhe target/product - TargetResolver não
escolhe OperationType - CatalogRetriever recupera; ProductResolver
decide - Order Engine não interpreta linguagem

## 11.1 — Provenance-aware retrieval (pós-9B.2)

A pipeline atual usa `retrieve_with_provenance(query, brand=None, presentation=None)`.

A proveniência acompanha cada candidato:

-   `{ORIGINAL|NORMALIZED}_ALIAS_EXACT`
-   `{ORIGINAL|NORMALIZED}_NAME_EXACT`
-   `{ORIGINAL|NORMALIZED}_ORIGINAL_EXACT`
-   `{ORIGINAL|NORMALIZED}_ALIAS_TOKEN`
-   `{ORIGINAL|NORMALIZED}_NAME_TOKEN`
-   `{ORIGINAL|NORMALIZED}_ALIAS_SUBSET`
-   `{ORIGINAL|NORMALIZED}_NAME_SUBSET`
-   `{ORIGINAL|NORMALIZED}_ALIAS_FUZZY`

Ordem determinística: ORIGINAL primeiro (ordem de descoberta), depois
NORMALIZED-only.

## 12. Freezes atuais

### HISTÓRICO / SUPERADO — snapshot pré-HOLDOUT-2

Antes do Final Blind Gate, NÃO alterar: Intent Classifier, GLiNER,
OperationResolver, TargetResolver, ReferenceResolver, PendingResolver,
CatalogRetriever, ProductResolver, ResolutionComposer, Order Engine,
catálogo, aliases, evaluator, DEV V2, HOLDOUT-1 V2 ou HOLDOUT-2.

Não fazer fine-tuning, nova regra, correção de HOLDOUT-01, expansão de
dataset, integração WhatsApp ou MVP.

### Freezes após 9B.2

Continuam congelados: Intent Classifier; GLiNER; Order Engine;
benchmark histórico RAW BLIND.

Track 9C: `NOT STARTED`. Próximo Track: `NOT AUTHORIZED`.

## 13. ESTADO ATUAL / STOP POINT (HISTÓRICO / SUPERADO)

**HOLDOUT-2 continua BLIND e ainda NÃO foi executado.**

A autorização atual é exclusivamente:

> **Executar HOLDOUT-2 como FINAL BLIND GATE, uma única vez, com tudo
> congelado.**

Protocolo: 1. confirmar `git status --short` vazio; 2. registrar
`git rev-parse HEAD`; 3. registrar ambiente, modelos, catálogo,
evaluator, benchmark e timestamp; 4. executar HOLDOUT-2 completo uma
vez; 5. congelar imediatamente o raw result; 6. não alterar
código/dataset após ver o resultado; 7. diagnosticar as falhas; 8.
reportar; 9. PARAR.

Não investigar HOLDOUT-01 antes da execução.

## 13.1 — Estado operacional atual (pós-9B.2)

```text
Track 9B.2: CLOSED / ACCEPTED
Checkpoint: c18ec6b20eda62af5d4746c310ed504ef01c5f73
Full suite: 150/150
Wrong Executable Operation: 0
HOLDOUT-2 POST-BLIND 9B.2: 12/20
Implementation defects adjudicated: 0
Track 9C: NOT STARTED
Next implementation track: NOT AUTHORIZED
```

## 14. Métricas do Final Blind Gate (HISTÓRICO / SUPERADO)

Reportar: - ResolvedOperation Exact Match - Operation Type Accuracy -
Operation Resolution Accuracy - Target Accuracy - Product Resolution
Accuracy - Quantity Value Accuracy - Quantity Unit Accuracy -
PendingResolution Correctness - Clarification Correctness - Reason Code
Accuracy - Wrong Executable Operation Rate - Unnecessary Clarification
Rate - métricas por OperationType

Distinguir: A. execução correta\
B. clarificação desnecessária\
C. operação incorreta bloqueada\
D. operação incorreta executável --- **crítico**

Para cada falha: último output semanticamente correto → primeiro output
semanticamente incorreto.

Root causes: `INTENT_CLASSIFICATION_ERROR`, `INTENT_ROUTING_ERROR`,
`ENTITY_EXTRACTION_ERROR`, `CATALOG_RETRIEVAL_ERROR`,
`PRODUCT_RESOLUTION_ERROR`, `REFERENCE_RESOLUTION_ERROR`,
`TARGET_RESOLUTION_ERROR`, `QUANTITY_ERROR`, `UNIT_ERROR`,
`PENDING_RESOLUTION_ERROR`, `RESOLVED_OPERATION_COMPOSITION_ERROR`,
`ORDER_ENGINE_ERROR`, `SAFETY_ERROR`, `GROUND_TRUTH_QUESTIONABLE`,
`DATASET_INCOMPLETE`, `OTHER`.

## 15. Interpretação do blind gate (HISTÓRICO / SUPERADO)

Comparação: - DEV V2 9/10 --- development/regression - HOLDOUT-1 V2 9/10
--- observed validation/regression - HOLDOUT-2 X/20 --- blind
generalization evidence

Não usar threshold arbitrário para MVP/fine-tuning. Gravidade e
distribuição dos erros importam. `16/20 + 0 wrong executable` é
qualitativamente diferente de `16/20 + 2 wrong executable`.

Não criar "adjusted HOLDOUT-2 score" como resultado principal depois de
observar o conjunto. Eventual ground truth questionável é análise
post-hoc; o raw blind score permanece registrado.

### Resultado do gate

```text
RAW BLIND                 11/20 = 55%
POST-BLIND Track 9A       13/20 = 65%
POST-BLIND Track 9B.2     12/20 = 60%
Wrong Executable Operation = 0
```

`11/20` é o único RAW BLIND desta sequência. Resultados posteriores são
`POST-BLIND REGRESSION`; nenhum é reclassificado como blind.

### Failure Adjudication — HOLDOUT-2 POST-BLIND 9B.2

```text
IMPLEMENTATION_DEFECT            0
EXPECTED_CONSERVATIVE_BEHAVIOR   2
GROUND_TRUTH_QUESTIONABLE        1
BENCHMARK_CONTRACT_MISMATCH      5
INSUFFICIENT_EVIDENCE            0
```

`BENCHMARK_CONTRACT_MISMATCH = divergência entre o expected histórico e o
contrato vigente; direção normativa não adjudicada.`

Casos: H2-001, H2-002 (`EXPECTED_CONSERVATIVE_BEHAVIOR`);
H2-008 (`GROUND_TRUTH_QUESTIONABLE`); H2-007, H2-012, H2-013, H2-016,
H2-020 (`BENCHMARK_CONTRACT_MISMATCH`).

A adjudicação não altera retrospectivamente o score histórico.

## 16. Decisões que não devem ser reabertas automaticamente

-   modelo não é autoridade de negócio;
-   last-item fallback não autoriza mutação;
-   alias não é verdade;
-   catálogo não prova estoque;
-   sem KG→embalagem operacional sem regra validada;
-   sem semantic repair silencioso;
-   sem selecionar SKU ambíguo para passar benchmark;
-   sem fine-tuning antes de demonstrar déficit real;
-   sem misturar linguistic intent e operation resolution;
-   sem mexer no Order Engine por erro upstream;
-   um item no pedido não fabrica OperationType;
-   blind result não pode ser reescrito retroativamente.

## 16.1 — Open Questions (registradas, não decididas)

-   **H2-013:** pode existir operação parcialmente estruturada com
    `product_term`, sem `resolved_product_id`, antes de ser executável?
-   **H2-016:** `CHANGE_QUANTITY` sem unidade explícita deve herdar a
    unidade do item existente?
-   **CR-01:** como garantir estruturalmente ausência de candidatos
    quando não há evidência lexical de produto, independentemente de
    futuras mutações de catálogo/aliases?

## 17. Ambiente conhecido

Linux Mint + VS Code. Testes principais CPU-only em Xeon E5-2667 v4, 16
cores. Ollama instalado. `qwen3:8b` funciona; `qwen3-hermes:latest` não
coube na memória disponível em teste anterior.

Modelos relevantes: - Intent: BERT fine-tuned
`neuralmind/bert-base-portuguese-cased` - Entity:
`urchade/gliner_medium`

O intent classifier historicamente foi treinado com 64 exemplos e recebe
mensagem isolada. É limitação conhecida, mas permanece congelado antes
do Final Blind Gate.

### Ambiente de execução verificado (2026-09-21)

-   `.venv/bin/python` é o interpretador funcional verificado.
-   `jsonschema 4.26.0` disponível no `.venv`.
-   `tests/test_benchmark.py`: `3/3 passed`.
-   Suíte completa: `150/150 passed`.
-   Problema anterior identificado: `WRONG_ENVIRONMENT` (execução via
    `/usr/bin/pytest`, sem visibilidade do `.venv`).

## 17.1 — Dívida de engenharia

Ausência de manifesto versionado de dependências (`requirements.txt`,
`pyproject.toml`, `setup.py`) identificado. O `.venv` atual é funcional,
mas reprodução limpa não está documentada. Dívida separada — fora do
Track 9B.2.

## 18. Como atuar como Tech Lead

Ao receber handoff da Equipe: - separar fato, inferência e conclusão; -
questionar overclaims; - exigir commit/hash e working tree clean; -
atribuir falha à primeira camada realmente divergente; - preservar
segurança; - não otimizar benchmark por frase; - preferir mecanismos
generalizáveis; - não inventar regras de negócio; - chamar o time de
**Equipe** / **Equipe de Engenharia**.

## 19. Prompt para continuar em outro chat

> **Assuma o papel de Tech Lead do Ordo. Leia este
> ORDO_MASTER_HANDOFF.md integralmente. Preserve os freezes e continue
> exatamente do Stop Point. Chame o time executor de "Equipe". O Track
> 9B.2 está `CLOSED / ACCEPTED` no checkpoint
> `c18ec6b20eda62af5d4746c310ed504ef01c5f73`. Nenhum Track novo está
> autorizado.**