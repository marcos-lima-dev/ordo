# ORDO — CURRENT STATE

> Mapa de navegação do conhecimento vigente.
> Não é histórico. Não é log. Não é handoff.
> Serve para: localizar rapidamente o que está fechado, o que
> reutilizar, o que está congelado, o que está parkeado, o que
> está ativo, e onde está a evidência.

---

## CHECKPOINT OFICIAL

`c306c1378d966c5734cb74aa8dacc37c28814313`

**Checkpoint anterior (superseded):** `12ca86b7a8897e5060019cab1469b6e5926e4992` — promoção documental de Telegram Controlled Execution v1 para CURRENT_STATE. Preservado como referência histórica; não é estado operacional.

---

## PRODUCT IDENTITY

**Ordo — Conversational Order Intelligence Engine.**

> Transformar conversas comerciais do WhatsApp em operações
> estruturadas de venda.
>
> A conversa deixa de ser o pedido. A conversa produz um pedido.

Modelos fornecem sinais; software resolve e valida; ambiguidade é explicitada; Order Engine executa somente operações resolvidas.

---

## ARCHITECTURE (vigente)

Caminho COMMAND canônico:

Message
  → sinais (QueryIntent, CommandEvidence)
  → message_intent → OperationResolver → resolved_operation_type
  → Reference/Pending/Target Resolution
  → Catalog Retrieval / Product Resolution (Evidence v0)
  → ResolutionComposer
  → ResolutionResult (OPERATION | NEEDS_CLARIFICATION)
  → command_execution (to_resolved_operation → execute_resolution)
  → OrderEngine.apply
  → OrderState

Regras estruturais:
- `message_intent ≠ resolved_operation_type`.
- OperationResolver não resolve target/product.
- CatalogRetriever recupera; ProductResolver decide.
- OrderEngine não interpreta linguagem.

Camadas recentes:
- **PA-1 Authority** (`pipeline/pa1_authority.py`) — wrapper que aplica PA-1 Policy Slice v0 antes de `resolve_operation`.
- **PA-2 Stage 1** (`pipeline/pa2_association.py`) — armazém factual de associações históricas validadas. Sem authority.
- **Telegram Controlled Execution v1** (`pipeline/telegram_execution.py`) — harness que liga Telegram ao caminho canônico de execução, restrito a chats autorizados e a kill switch explícito.

---

## ACTIVE

Nenhuma etapa funcional ativa.

---

## CLOSED → REUSE

Capacidades fechadas, testadas, commitadas. **Não reinvestigar.**
Reabrir somente com evidência nova concreta (`REOPEN`).

| Capacidade | Commit | Notas |
|---|---|---|
| Track 9B.2 — Safe Catalog Retrieval | `c18ec6b` | Provenance-aware retrieval; separação evidence/authorization; candidate ordering determinístico. Origem direta da R2 e da Evidence Contract v0. |
| Evidence Contract v0 | `c94bd4e` | Estrutura `Evidence(sku, stream, match_kind, match_strength, source?, approved?)`. Substitui a representação por strings; consolida Track C. |
| PA-1 Explicit Identifier Input | `3c2b976` | Observer + Verifier. Implementados e testados em isolamento. |
| PA-1 Authority Wrapper | `90a412d` | `make_pa1_authority_wrapper`. `pre_resolved_product_id` keyword-only em `resolve_operation`. ADD_ITEM apenas. |
| PA-2 Validated Historical Association — Stage 1 | `983485d` | `HistoricalAssociationRecord` + `PA2AssociationStore`. Factual. Sem applicability, sem authority. |
| Telegram Controlled Execution v1 | `7ed31d3` | Harness Telegram→`orchestrate_command`. Kill switch booleano no harness. Safety obrigatório. Restrito a chats autorizados. Zero external commercial side effect. Autoridade máxima: mutação de `OrderState` via caminho canônico. |
| Telegram Conversation Loop Closure v1 | `c306c13` | Ciclo conversacional Telegram fechado. `Response Composition ≠ Response Delivery`. `Channel Delivery ≠ Domain Interpretation`. `NOT_ELIGIBLE → NO RESPONSE`. `Conversation Loop Closure ≠ external commercial execution`. Sem external commercial side effect. |
| Canonical Command Execution | `f264e0f` | `compose_command_execution` → `to_resolved_operation` → `execute_resolution` → `OrderEngine.apply`. |
| Session State | `5129e75` | `InMemoryConversationSessionStore`. `ConversationId` opaco. |
| Idempotency Stage 1 | `4f8e4e9` | `IdempotencyKey(ConversationId, ExternalMessageId)`. Atomicidade contratual. |
| Channel Boundary Stage 1 | `6d5b786` | `ChannelIdentity(channel, external_conversation_id)` → `ConversationId`. Mapping 1:1 in-memory. |
| Application Processing Boundary | `fd79e48` | `ApplicationProcessor.process(message) → ProcessingResult`. Stateless; sem OrderState; sem execução. |
| Telegram Shadow Pilot | `6361a61` | Transport + adapter + shadow stateless. Zero Authority. |
| Recognition Robustness Stage 1 | `e035890` | Classes novas; reconhecimento de `quanto tá`. |
| Track A — Same-SKU Evidence Preservation | `4096b86` | P101–P103. Preservação de positive evidence same-SKU no merge. |

---

## POLÍTICAS VIGENTES

### R2 — Retrieval Evidence ≠ Authorization

**Princípio vigente:**
`retrieval evidence ≠ execution authorization evidence`.

**Representação atual:**
Evidence Contract v0 (`order/evidence.py`) + política atual do `ProductResolver._is_positive` (`order/product_resolver.py`).

**Representação histórica — Track 9B.2 (`c18ec6b`):**

Autorizam `EXACT_MATCH` (positive sources):
`ALIAS_EXACT`, `NAME_EXACT`, `ORIGINAL_EXACT`, `APPROVED_ALIAS`, `ENTITY_SIGNAL`.

Não autorizam isoladamente:
`ALIAS_TOKEN`, `NAME_TOKEN`, `ALIAS_SUBSET`, `NAME_SUBSET`, `ALIAS_FUZZY`.

`evidence=None` não autoriza `EXACT_MATCH`.

> A lista acima pertence à representação anterior à Evidence Contract v0. Preservada para navegação histórica. A representação operacional vigente é Evidence Contract v0.

### P1 — Unique Eligible Target

`UNIQUE_ELIGIBLE_TARGET` pode resolver target **somente depois** de o `OperationType` estar resolvido, para operação que exige item existente, com exatamente um target elegível e sem evidência conflitante.

P1 **não** transforma `"coloca 3"` em `CHANGE_QUANTITY` só porque há um item.

### CR-01 / CR-02

- **CR-02:** `structurally protected by authorization policy`.
- **CR-01:** `NOT structurally guaranteed against every future catalog/alias mutation`.

---

## FROZEN

Decisões, princípios e invariantes que **não podem ser modificados**
sem `REOPEN` explícito autorizado.

> **FROZEN congela decisões, não arquivos inteiros.** Um módulo
> pode existir dentro de arquitetura congelada sem que cada linha
> do arquivo seja imutável. O que está congelado é a política,
> contrato ou invariante que o módulo realiza.

### Princípios

- **T10-P1 … T10-P55** — Track 10 / QUERY.
- **P56 … P104** — pós-Track-10.
- **P101** — Same-SKU positive evidence must not be discarded by aggregation.
- **P102** — Aggregation must never manufacture evidence.
- **P103** — Aggregation must never cross SKU boundaries.
- **P104** — Contextual evidence ≠ target authority.
- **P105** — Evidence representation ≠ resolution authority.

### Decisões de contrato

- **Evidence Contract v0** — shape e semântica (`order/evidence.py`).
- **Política de positividade** — `ProductResolver._is_positive` (`order/product_resolver.py`). Conforme R2 e 9B.2.
- **Conteúdo ativo de catálogo e aliases** — mudanças exigem decisão explícita.
- **Boundaries públicos protegidos por contract guards:**
  - `CallerResult` — `test_call07b`, `test_call10`.
  - `ProcessingResult` — `test_ap05`, `test_ap11`.
  - `OrchestrationResult` — `test_ao08`, `test_ao09`.

### Escopos

- **Track B — GLiNER misclassification:** FROZEN.
- **Track C — Normalization Discriminator Loss:** FECHADO (Evidence Contract v0, `c94bd4e`).
- **CDP (Contextual Discriminator Preservation):** PARKED / SEPARATE LAYER.

---

## PARKED

Válido, mas **não ativo**. Classificar como `PARK` quando encontrado.
Não investigar sem necessidade concreta para etapa ativa.

- **PA-2 Commercial Identity Authority** — **NOT IMPLEMENTED / DEFERRED**.
- **PA-2 Stage 2** — applicability, matcher, Authority Wrapper.
- **PA-2 runtime wiring** — deferred até caller de produção.
- **Relationship Scope mechanism** — domínio caracterizado; mecanismo UNSPECIFIED.
- **`CustomerId` / `RelationshipId`** — não existem; não criar sem decisão de domínio.
- **Cross-channel linking** — fail-closed no slice atual.
- **TTL / expiração** — sem evidência de necessidade.
- **Identidade de pessoa física** — não requerida por PA-2.
- **SPA / ATC / CDP** — propostas, não decisões.
- **Track B — GLiNER tuning** — FROZEN.
- **`approved=True` em aliases** — PARKED.

> **PA-1 Commercial Identity Authority** está **IMPLEMENTED** desde `90a412d` (`pipeline/pa1_authority.py`).

---

## MECANISMOS REUTILIZÁVEIS

| Mecanismo | Onde vive | Uso |
|---|---|---|
| `make_guarded_resolve_operation` | `pipeline/command_safety_guard.py` | Wrapper sobre `resolve_operation` com short-circuit. |
| `make_pa1_authority_wrapper` | `pipeline/pa1_authority.py` | Wrapper PA-1 Authority. |
| `pre_resolved_product_id` | `pipeline/resolution_pipeline.py` | Kwarg keyword-only para identidade pré-resolvida (ADD_ITEM). |
| `HistoricalAssociationRecord` | `pipeline/pa2_association.py` | Record factual de associação validada. |
| `PA2AssociationStore` | `pipeline/pa2_association.py` | Contrato de armazém factual por referência. |
| `TelegramControlledExecution` | `pipeline/telegram_execution.py` | Harness de execução supervisionada Telegram→`orchestrate_command`. |
| `CommunicableResponse` | `pipeline/telegram_response.py` | Representação mínima de resposta (`destination`, `text`). |
| `compose_response` | `pipeline/telegram_response.py` | Composição mínima de resposta por outcome. `NOT_ELIGIBLE` → `None`. |
| `TelegramTransport.send_message` | `pipeline/telegram_transport.py` | Delivery puro. Recebe `(chat_id, text)`; não interpreta. |
| `Evidence v0` | `order/evidence.py` | Representação factual de retrieval. |
| `ChannelIdentity` | `pipeline/channel_identity.py` | Referência observável de canal. |
| `ConversationId` | `pipeline/conversation_session.py` | Identidade interna de conversa. |
| In-memory stores | vários | Mapping, session, idempotency, PA2 association. |

---

## EVIDÊNCIA HISTÓRICA

| Fonte | Onde | Uso |
|---|---|---|
| Domain Elicitation D-01 → D-14 | DOCUMENTATION GAP — evidence exists in project history but has not yet been consolidated into a repository artifact. | Comportamento do vendedor. |
| Relationship Scope R-01 → R-04 | DOCUMENTATION GAP — evidence exists in project history but has not yet been consolidated into a repository artifact. | Scope comercial. |
| Gap Analysis corpus (247 queries) | `diag_track_c.json` | Comportamento Track C. |
| Evidence Preservation corpus | `tests/fixtures/track_a_evidence_preservation_corpus.json` | Track A. |
| Observability Audit | `diag_observability_audit.json` | Estado das identidades. |

---

## BENCHMARK HISTORY

Resultados históricos imutáveis.

**DEV V2:** 9/10.
**HOLDOUT-1 V2:** 9/10.
**Wrong Executable Operation Rate:** 0.

DEV/HOLDOUT-1 já são conhecidos; não são prova independente de generalização. DEV-09 permanece `GROUND_TRUTH_QUESTIONABLE`. HOLDOUT-01 é dívida conhecida; investigação não é pré-requisito para nenhuma decisão atual.

**HOLDOUT-2:**

RAW BLIND                 11/20 = 55%
POST-BLIND Track 9A       13/20 = 65%
POST-BLIND Track 9B.2     12/20 = 60%
Wrong Executable Operation = 0

---

## COMMITS PRINCIPAIS

Referência de navegação.

- Baseline v0 — `5702f2b4af59560b40bae4ec8c6666b3f16e562a`
- Benchmark v1 — `2e9de0cf319b65a045e0b7c77a6fc7f2dc6e391d`
- Target Stage 1 — `92c3581c754660c1579f44d8a70a639f2a266575`
- Pending Stage 2 — `204a729ce4052de75c7d2dac1bad4393b05bf74c`
- Composer Stage 3 — `05f05389b133d277fa5ed59b2a1a9d7e9eabd38c`
- REPLACE Stage 4 — `680783af268f9ec08c22d878c296ebf52a2faf76`
- Operation Resolver — `e1bfb5d9f452279682d38afcf2e94bab48ba58e9`
- Benchmark V2 — `de07dcaeadecbdc5e0f99ecfa7ac887b6a9e57ab`
- Scripts V2 — `9f70f0df64d756af6b128a6890c88053af033c0f`
- Track 9B.2 — `c18ec6b20eda62af5d4746c310ed504ef01c5f73`
- Track A — `4096b86c9e6e1871a339c26c228295a7facbe3e1`
- Evidence Contract v0 — `c94bd4e92e93c6f251560b058a25f34b3271e44b`
- PA-1 Stage 1 — `3c2b9768b6fb6b27191492098df7a12e3d1dd55b`
- PA-1 Authority — `90a412de42aba32a78fccd32b05180d2aad75075`
- PA-2 Stage 1 — `983485d3104220627dea8b46119a27d736b27bb6`
- Telegram Controlled Execution v1 — `7ed31d35706186c5717049c0f4b6b1e937315a3a`
- Telegram Conversation Loop Closure v1 — `c306c1378d966c5734cb74aa8dacc37c28814313`

---

## CLASSIFICAÇÃO DE QUESTÕES

Ao encontrar uma questão durante trabalho:

- **REUSE** — já conhecido; usar.
- **REGRESSION** — já provado; verificar se mudança pode quebrar.
- **NEW** — realmente não respondido e necessário para o objetivo.
- **REOPEN** — decisão fechada contradita por nova evidência concreta.
- **PARK** — válido, mas desnecessário para a etapa atual.

**Missing from memory ≠ missing from project.**
Antes de investigar, consultar este documento.