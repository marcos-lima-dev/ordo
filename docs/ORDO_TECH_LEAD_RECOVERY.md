# ORDO — TECH LEAD RECOVERY PACK

> **Documento de bootstrap / navegação.** NÃO substitui
> `docs/ORDO_CURRENT_STATE.md`, `docs/TECH_LEAD_LOG.md` ou
> `docs/ORDO_MASTER_HANDOFF.md`. Em caso de conflito, as fontes
> autoritativas (documentos + código + testes) prevalecem.

**Propósito:** permitir que um novo ChatGPT/Tech Lead assuma o projeto
em um chat vazio, recebendo apenas este arquivo + acesso ao repositório.

**HEAD:** `4096b86c9e6e1871a339c26c228295a7facbe3e1`
**origin/master:** idem. Confirmado `HEAD == origin/master`.
**Última atualização:** após Track A (Same-SKU Evidence Preservation)
e Multi-turn Re-Audit.

---

## 1. PROJECT IDENTITY

**ORDO — Conversational Order Intelligence Engine.** Transformar
conversas de WhatsApp de clientes da **Casa dos Queijos** (queijos
finos) em pedidos estruturados.

> A conversa deixa de ser o pedido. A conversa produz um pedido.

Princípios de base: segurança > recall; determinismo; ambiguidade
explícita; separação reconhecimento ↔ resolução ↔ execução; modelos
fornecem sinais; software determinístico valida e resolve; nenhuma
inferência comercial silenciosa.

**WhatsApp** é o alvo final; **Telegram** é o proving ground. ORDO é
independente de canal.

---

## 2. CANONICAL ARCHITECTURE

### 2.1 Processing
message -> ApplicationProcessor.process(message) -> ProcessingResult
├─ QueryIntentProvider.predict(message) -> QueryIntentSignal
├─ CommandEvidenceProvider.predict(message) -> CommandEvidence
└─ plan(SignalObservation) -> DispatchPlan

text

`SignalObservation(query, command)` independentes. `DispatchPlan` tem
exatamente 1 decisão por domínio (QUERY + COMMAND). Compor não resolve,
não executa.

### 2.2 COMMAND path
CallerResult.command -> compose_command_execution(caller_result, state, engine)
├─ to_resolved_operation(result) -> ResolvedOperation | None
└─ execute_resolution(state, result, engine)
└─ OrderEngine.apply(state, operation) # muta state in-place
-> CommandExecutionResult(status, resolution_result, state, events)

text

`resolve_operation(message, state)` orquestra
`ReferenceResolver → PendingResolver → OperationResolver → TargetResolver
→ CatalogRetriever → ProductResolver → ResolutionComposer`.

`OrderEngine.apply` é a **única autoridade de mutação** de `OrderState`.

### 2.3 QUERY path
CallerResult.query -> compose_query_read_side(caller_result)
├─ to_resolved_query(query_resolution) -> ResolvedQuery | None
└─ retrieve_fact(resolved_query) -> FactRetrievalResult
-> QueryReadSideResult

text

`FactRetrievalResult.status ∈ {FACT_FOUND, FACT_NOT_FOUND, SOURCE_UNAVAILABLE}`.
Hoje só `SOURCE_UNAVAILABLE` é produzido — não há fonte autoritativa
de PRICE ou AVAILABILITY integrada.

### 2.4 Identity / Session
ChannelIdentity(channel, external_conversation_id)
-> InMemoryConversationMappingStore.get_or_create -> ConversationId
-> InMemoryConversationSessionStore.get_or_create -> OrderState

text

Mapping (identity) e Session (state) são stores separados (P80).
`ConversationId` é opaco, gerado internamente.

### 2.5 Idempotency

`IdempotencyKey(ConversationId, ExternalMessageId)` →
`InMemoryIdempotencyStore.claim(key) -> CLAIMED | ALREADY_CLAIMED` →
processamento → `complete(key)`. `claim` é atômico por contrato (P75),
implementado com `threading.Lock`. `CLAIMED ≠ COMPLETED` (P76).

### 2.6 Application Orchestration
orchestrate_command(cid, emid, message, observation, plan, engine,
session_store, idempotency_store, *,
resolve_operation_fn=resolve_operation)
├─ idempotency.claim(key)
├─ session_store.get_or_create(cid) -> state
├─ application_caller.invoke(...)
├─ compose_command_execution(caller_result, state, engine)
├─ session_store.save(cid, state)
└─ idempotency.complete(key)

text

### 2.7 Telegram Shadow
TelegramTransport.get_updates(offset) -> list[dict]
-> TelegramAdapter.parse(update) -> ParseResult
-> process_update(...) -> ObservationRecord | None

text

Shadow é **stateless semanticamente**. Não chama `orchestrate_command`,
não usa `OrderState`, não adquire idempotency claim, não toca Engine.
Token vive só no `TelegramTransport`.

### 2.8 Command Safety Guard

`CommandSafetyGuard.check(message) -> SafetyResult` detecta
**REPRESENTATIONAL_OVERFLOW** (P59–P67). Deve ser injetado via
`resolve_operation_fn`. Não vive no `ApplicationProcessor`.

---

## 3. FROZEN PRINCIPLES

### 3.1 Track 10 (QUERY)

| ID | Wording | Origem |
|---|---|---|
| T10-P1 | QUERY ≠ COMMAND | Track 10 |
| T10-P2 | ResolvedQuery ≠ ResolvedOperation | Track 10 |
| T10-P3 | QUERY MUST NOT MUTATE OrderState | Track 10 |
| T10-P4 | ResolutionResult remains COMMAND-only | Track 10 |
| T10-P5 | QUERY INTENT ≠ PERMISSION TO GUESS PRODUCT | Track 10 |
| T10-P6 | RESOLVED QUERY ≠ ANSWERED QUERY | Track 10 |
| T10-P7 | QUERY BOUNDARY ≠ RESOLVER | Track 10 |
| T10-P8 | RECOGNITION ≠ RESOLUTION | Track 10 |
| T10-P9 | PROVIDER SIGNAL ≠ SEMANTIC INTENT | Track 10 |
| T10-P10 | NOT_QUERY IS A POSITIVE NEGATIVE CLASSIFICATION | Track 10 |
| T10-P11 | ABSENCE OF QUERY EVIDENCE ≠ NOT_QUERY | Track 10 |
| T10-P12 | UNRESOLVED ≠ PROVIDER FAILURE | Track 10 |
| T10-P13 | UNRESOLVED ≠ NOT_QUERY | Track 10 |
| T10-P14 | QUERY PROVIDER DOES NOT VETO ON COMMAND SEMANTICS | Track 10 |
| T10-P15 | STRUCTURAL PUNCTUATION ≠ SEMANTIC CONFLICT EVIDENCE | Stage 4G |
| T10-P16 | SINGLE SIGNAL OUTPUT ≠ SINGLE INTENT ASSUMPTION | Stage 4H |
| T10-P17 | SINGLE-VALUE CONTRACT ≠ MESSAGE-LEVEL COLLAPSE | Stage 4H |
| T10-P18 | RESOLUTION COMPOSITION ≠ SEMANTIC SIGNAL COMPOSITION | Stage 4H |
| T10-P19 | RESOLUTION PIPELINE ≠ APPLICATION ORCHESTRATOR | Stage 4H |
| T10-P20 | QUERY/COMMAND COORDINATION MUST PRECEDE DOMAIN-SPECIFIC RESOLUTION | Stage 4H |
| T10-P21 | COORDINATION IS AN APPLICATION-LAYER RESPONSIBILITY | Stage 4H |
| T10-P22 | COORDINATION ≠ EXECUTION | Stage 4H |
| T10-P23 | PRESERVE INDEPENDENT SIGNALS BEFORE COLLAPSE | Stage 4H |
| T10-P24 | DISPATCH TARGET ≠ PIPELINE FUNCTION | Stage 4H |
| T10-P25 | DOMAIN DISPATCH DOES NOT NEGATE UNRESOLVED SIBLING SIGNALS | Stage 4H |
| T10-P26 | COMMAND EVIDENCE ≠ COMMAND INTENT | Stage 4I.4c |
| T10-P27 | UNKNOWN recognition ≠ ABSENT | Stage 4I.4c |
| T10-P28 | ABSENT requires positive negative evidence | Stage 4I.4c |
| T10-P29 | OBSERVATION ≠ PLAN STORAGE | Stage 4I.5 |
| T10-P30 | DISPATCH PLAN IS NEVER EXECUTION AUTHORIZATION | Stage 4I.5 |
| T10-P31 | UNKNOWN VALUE ≠ UNKNOWN CLASSIFICATION | Stage 4I.4b |
| T10-P32 | EVIDENCE PROVIDER ≠ RECOGNIZER OWNER | Stage 4I.4c |
| T10-P33 | LEGACY RECOGNIZER ≠ COMMAND EVIDENCE PROVIDER | Stage 4I.3 |
| T10-P34 | INFORMATION LOSS MUST OCCUR AFTER CONTRACT ENFORCEMENT | Stage 4I.3 |
| T10-P35 | INVALID PROVIDER INPUT IS NOT A SEMANTIC OUTCOME | Stage 4I.4b |
| T10-P36 | CHARACTERIZATION PRESERVES VALID BEHAVIOR, NOT LEGACY CONTRACT VIOLATIONS | Stage 4I.4a |
| T10-P37 | UNSUPPORTED EVIDENCE ≠ FORBIDDEN SYMBOL | Stage 4I.4c |
| T10-P38 | DOMAIN ABSENCE IS EXPLICIT PLAN STATE | Stage 4I.5 |
| T10-P39 | COORDINATION DECISION ≠ DOMAIN INVOCATION DATA | Stage 4I.5 |
| T10-P40 | INFORMATION LOSS MUST PRESERVE AN AUTHORITATIVE SOURCE | Stage 4I.5 |
| T10-P41 | QUERY INVOCATION DATA HAS AN AUTHORITATIVE SOURCE | Stage 4J.1 |
| T10-P42 | QUERY SIGNAL TRANSLATION IS MECHANICAL, NOT SEMANTIC RESOLUTION | Stage 4J.1 |
| T10-P43 | DISPATCH AUTHORIZES INVOCATION, NOT THE OBSERVATION ALONE | Stage 4J.1 |
| T10-P44 | NON-DISPATCHABLE QUERY SIGNAL IS A CONTRACT VIOLATION | Stage 4J.1 |
| T10-P45 | APPLICATION CALLER INVOKES; IT DOES NOT RESOLVE OR EXECUTE | Stage 4J.2 |
| T10-P46 | DOMAIN INVOCATION RESULTS REMAIN DOMAIN-SEPARATED | Stage 4J.2 |
| T10-P47 | CROSS-CONTRACT INCONSISTENCY FAILS AT THE CONSUMPTION BOUNDARY | Stage 4J.2 |
| T10-P48 | APPLICATION CALLER DOES NOT OWN CONVERSATION STATE | Stage 4J.2 |
| T10-P49 | FACT RETRIEVAL STATUS DESCRIBES THE FACT RETRIEVAL OUTCOME | Stage 4J.3 |
| T10-P50 | SOURCE_UNAVAILABLE ≠ FACT_NOT_FOUND | Stage 4J.3 |
| T10-P51 | INVALID QUERY TYPE IS CONTRACT VIOLATION | Stage 4J.3 |
| T10-P52 | BUSINESS FACT SHAPE FOLLOWS SOURCE AUTHORITY | Stage 4J.3 |
| T10-P53 | QUERY RESOLUTION FAILURE PRECEDES FACT RETRIEVAL | Stage 4J.4 |
| T10-P54 | READ-SIDE COMPOSITION DOES NOT CHANGE DOMAIN SEMANTICS | Stage 4J.4 |
| T10-P55 | FACT RETRIEVAL REQUIRES A RESOLVED QUERY | Stage 4J.4 |

### 3.2 Post-Track-10

| ID | Wording | Origem |
|---|---|---|
| P56 | COMMAND EXECUTION STATUS COMES FROM CONTROL FLOW, NOT ENGINE EVENTS | Canonical Command Execution |
| P57 | EXECUTION COMPOSITION DOES NOT OWN STATE | Canonical Command Execution |
| P58 | BOUNDARY RECHECK DOES NOT CREATE A SECOND AUTHORITY | Canonical Command Execution |
| P59 | REPRESENTATIONAL OVERFLOW MUST FAIL CLOSED | Safety Gate |
| P60 | MULTIPLICITY MUST BE DETECTED BEFORE LOSSY COLLAPSE | Safety Gate |
| P61 | SAFE GUARD ≠ MULTI-OPERATION RESOLUTION | Safety Gate |
| P62 | SAFETY EVIDENCE ≠ SEMANTIC RESOLUTION | Safety Gate |
| P63 | FALSE NEGATIVE DOMINATES FALSE POSITIVE AT THE EXECUTION SAFETY BOUNDARY | Safety Gate |
| P64 | COMPOUND ENTITY IS SAFETY EVIDENCE, NOT MODEL INTENT | Safety Gate |
| P65 | REPRESENTATIONAL_OVERFLOW BLOCKS COMMAND EXECUTION BEFORE SINGULAR RESOLUTION | Safety Gate |
| P66 | SAFETY GUARD FAILURE MUST FAIL CLOSED | Safety Gate |
| P67 | SAFETY EVIDENCE IS DIAGNOSTIC, NOT COMMERCIAL DATA | Safety Gate |
| P68 | CONVERSATION IDENTITY ≠ CHANNEL IDENTITY | Channel Boundary |
| P69 | CONVERSATION BOUNDARY RESOLVES IDENTITY; SESSION STORE OWNS STATE | Channel Boundary |
| P70 | SESSION STORE PRESERVES STATE; DOMAIN EXECUTION MUTATES COMMERCIAL STATE | Session |
| P71 | MESSAGE IDENTITY ≠ IDEMPOTENCY | Idempotency |
| P72 | CHANNEL INTEGRATION MUST NOT OWN ORDER LIFECYCLE | Channel Boundary |
| P73 | RED TESTS INVALIDATE THE CHECKPOINT, NOT THE EVIDENCE | Red Master Recovery |
| P74 | DELIVERY AUTOMATION MUST FAIL CLOSED | Script Hygiene |
| P75 | IDEMPOTENCY CLAIM IS ATOMIC BY CONTRACT, NOT BY IMPLEMENTATION ACCIDENT | Idempotency Stage 1 |
| P76 | CLAIMED ≠ COMPLETED | Idempotency Stage 1 |
| P77 | UNCERTAIN EXECUTION MUST NOT BE SILENTLY REPLAYED OR REPORTED AS COMPLETED | Idempotency Stage 1 |
| P78 | CHANNEL IDENTITY ≠ MESSAGE IDENTITY | Channel Boundary Stage 1 |
| P79 | CONVERSATION MAPPING DEPENDS ONLY ON CHANNEL IDENTITY | Channel Boundary Stage 1 |
| P80 | CONVERSATION MAPPING ≠ CONVERSATION STATE | Channel Boundary Stage 1 |
| P81 | CONVERSATION MAPPING CREATION IS ATOMIC BY CONTRACT | Channel Boundary Stage 1 |
| P82 | APPLICATION PROCESSING COMPOSES SIGNALS; IT DOES NOT EXECUTE DOMAIN WORK | Application Processing |
| P83 | SHADOW OBSERVES POTENTIAL DISPATCH WITHOUT EXERCISING APPLICATION AUTHORITY | Application Processing |
| P84 | SHADOW v1 ENDS AT THE DISPATCH PLAN | Application Processing |
| P85 | TRANSPORT EVENT IDENTITY ≠ MESSAGE IDENTITY | Telegram Shadow |
| P86 | CHANNEL TRANSPORT ≠ CHANNEL ADAPTER | Telegram Shadow |
| P87 | SHADOW IDENTITY STATE ≠ COMMERCIAL STATE | Telegram Shadow |
| P88 | SHADOW OBSERVATION MUST NOT CONSUME EXECUTION IDEMPOTENCY | Telegram Shadow |
| P89 | OPERATIONAL SHADOW EVIDENCE ≠ EXECUTION EVIDENCE | Shadow Operational Validation |
| P90 | REAL TRAFFIC MUST BE OBSERVED BEFORE IT IS TUNED | Shadow Evidence Track |
| P91 | OBSERVED PHRASES ARE EVIDENCE, NOT PATCH TARGETS | Recognition Robustness |
| P92 | LEXICAL ROBUSTNESS ≠ CONTEXTUAL INFERENCE | Recognition Robustness |
| P93 | STRUCTURED COMMERCIAL CONTENT ≠ COMMAND AUTHORIZATION | Recognition Robustness |
| P94 | LEXICAL GENERALIZATION MAY REMAIN LEXICAL | Recognition Robustness |
| P95 | ROBUSTNESS MAY IMPROVE IN INCREMENTS | Recognition Robustness |
| P96 | RETRIEVAL UNIQUENESS ≠ COMMERCIAL IDENTITY | Natural Product Resolution |
| P97 | E2E DEPTH MUST BE STATED EXPLICITLY | Natural Product Resolution |
| P98 | 9B.2 IS NOT THE FAILURE | Natural Product Resolution |
| P99 | RETRIEVAL CAN PRODUCE EXACT EVIDENCE THAT THE FULL PIPELINE LOSES | Natural Product Resolution |
| P100 | INFORMATION LOSS ≠ LEGITIMATE AMBIGUITY | Natural Product Resolution |
| P101 | SAME-SKU POSITIVE EVIDENCE MUST NOT BE DISCARDED BY AGGREGATION | Track A |
| P102 | AGGREGATION MUST NEVER MANUFACTURE EVIDENCE | Track A |
| P103 | AGGREGATION MUST NEVER CROSS SKU BOUNDARIES | Track A |
| P104 | CONTEXTUAL EVIDENCE ≠ TARGET AUTHORITY | Multi-turn Re-Audit |

---

## 4. EPISTEMIC RULES

Classificações: **FACT** (verificável em código/execução/teste),
**EVIDENCE** (saída real), **INFERENCE** (derivada, marcada),
**HYPOTHESIS** (a testar), **PROPOSAL** (não autorizada),
**DECISION** (Tech Lead), **GAP** (evidência insuficiente).

Regras:

1. Não transformar INFERENCE em FACT sem evidência nova.
2. Benchmark post-blind não é blind retroativo.
3. Shadow evidence é de `ProcessingResult`, **não** de execução.
4. Teste é E2E só entre boundaries que efetivamente exercita (P97).
5. Falha deve ser atribuída à **primeira camada realmente divergente**.
6. Resultado seguro ≠ resolução correta. `NEEDS_CLARIFICATION` pode ser
   correto (ambiguidade) ou errado (perda).
7. `SOURCE_UNAVAILABLE` é resposta honesta, não falha.

---

## 5. GOVERNANCE PRECEDENCE

Ordem oficial:

1. `docs/ORDO_CURRENT_STATE.md`
2. `docs/TECH_LEAD_LOG.md`
3. `docs/ORDO_MASTER_HANDOFF.md`

Este Recovery Pack é **bootstrap/navigation**. Não substitui. Em
conflito, documentos + código + testes prevalecem.

Fluxo: Evidence → Tech Lead Review → Atomic Commit → Push → Remote
Verification → Stage Closed → Next Stage.

Comandos: **STOP FOR TECH LEAD REVIEW** / **STOP AT CHECKPOINT <sha>**.

---

## 6. CHECKPOINT HISTORY

| Commit | Stage | Significado |
|---|---|---|
| `8152837` | Stage 4F | QueryIntentProvider contract (3-way) |
| `223f1ec` | Stage 4F.1 | QueryIntentSignal → 4-way (UNRESOLVED) |
| `b5cd740` | Stage 4G | QueryIntentBootstrap |
| `925cdbb` | Stage 4I.1 | CommandEvidence + Observation types |
| `e3904b7` | Stage 4I.2 | CommandEvidenceProvider ABC |
| `31cf8dc` | Stage 4I.4a | Characterization freeze do recognizer legado |
| `311df3a` | Stage 4I.4b | CommandRecognizer independente |
| `6465206` | Stage 4I.4c | RecognizerCommandEvidenceProvider |
| `03be3c2` | Stage 4I.5 | DispatchPlan contract |
| `135b8d6` | Stage 4I.6 | Pure dispatch planner |
| `516561b` | Stage 4J.1 | Query signal → SemanticIntent translation |
| `44664e2` | Stage 4J.2 | Application caller |
| `77ae948` | Stage 4J.3 | Business fact read-side boundary |
| `17614fc` | Stage 4J.4 | Canonical query read-side composition |
| `f264e0f` | Canonical Command Execution | compõem até OrderEngine |
| `e81ffd1` | Multi-item Safety Guard v1 | R4 overflow guard |
| `ce9d6c1` | Session State (RED / non-checkpoint) | teste vermelho |
| `5129e75` | Session State fix | checkpoint oficial pós-recovery |
| `4f8e4e9` | Idempotency Stage 1 | claim atômico |
| `6d5b786` | Channel Boundary Stage 1 | ChannelIdentity + Mapping |
| `fd79e48` | Application Processing Boundary | ApplicationProcessor |
| `6361a61` | Telegram Shadow Pilot | transport + adapter + shadow |
| `e035890` | Recognition Robustness Stage 1 | classes novas; `quanto tá` |
| `4096b86` | Track A — Same-SKU evidence preservation | **checkpoint atual** |

---

## 7. WHAT IS ACTUALLY PROVEN

### 7.1 PROVEN

- **Canonical command composition/execution** funciona quando recebe
  `ResolutionResult(OPERATION)` válido: `to_resolved_operation` →
  `execute_resolution` → `OrderEngine.apply` → `ITEM_ADDED` →
  `OrderState` populado.
- **Telegram Shadow operacional real**: mensagens processadas em
  produção controlada, `ObservationRecord` produzido, token não vazado,
  Zero Authority confirmada.
- **Idempotência**: `claim` atômico testado com concorrência, mesmo
  `(cid, emid)` retorna `ALREADY_CLAIMED`.
- **NATURAL E2E — COMMAND**: `manda provolone defumado` → `OPERATION`
  → `ITEM_ADDED` → CQ-44 no `OrderState`, **sem fake resolver**. Provado
  em Track A para 6 casos (provolone defumado, curado, tânia, forma
  riqueza, riqueza, Camembert). Ambiguidade legítima preservada:
  `manda provolone` e `manda brie` continuam `AMBIGUOUS_PRODUCT`.
- **MULTI-TURN — CURRENT ORDER STATE**: `tira`, `tira ele`,
  `muda para 3`, `tira aquele` resolvem corretamente quando existe 1
  item no `OrderState`, pelo caminho natural. Com 2+ itens, retorna
  `AMBIGUOUS_TARGET` sem escolha silenciosa.
- **P1 — `UNIQUE_ORDER_ITEM_MATCH`**: PROVEN E2E — NATURAL PATH.

### 7.2 NOT PREVIOUSLY PROVEN (até Track A)

- `natural-language message → real resolve_operation → ResolutionResult(OPERATION)`.
- E2E antigos usaram **fake resolver** que retornava
  `ResolutionResult(OPERATION)` pré-montado — provaram composição +
  execução, **não** resolução natural. Track A fechou o gap.

### 7.3 NOT PROVEN BY SHADOW

- Execução, mutação de `OrderState`, `OrderEngine`.
- Multi-turn (Shadow v1 é stateless).

### 7.4 FAMILY STATUS (multi-turn)

- **FAMILY A — CURRENT COMMERCIAL STATE**: CHARACTERIZED / E2E PROVEN
  para os comportamentos testados.
- **FAMILY B — RECENT / GENERIC CONVERSATIONAL REFERENCE**: PARTIALLY
  CHARACTERIZED. Referências genéricas sobre o pedido atual funcionam
  dentro das políticas existentes. **`ele` continua fora do léxico.**
  Sucesso de `tira ele` com 1 item vem de `ONLY_ITEM` /
  `UNIQUE_ORDER_ITEM_MATCH`, não de compreensão semântica de `ele`.
- **FAMILY C — HISTORICAL COMMERCIAL REFERENCE**: SOURCE UNAVAILABLE.
  `de ontem`, `de sempre`, `último pedido` não têm fonte autoritativa.

---

## 8. CURRENT NATURAL PRODUCT FINDINGS

Três causas-raiz distintas foram identificadas investigando por que
mensagens naturais com identidade comercial suficiente podem não chegar
a uma resolução executável.

### 8.1 Track A — Evidence Merge

**CLOSED / ACCEPTED em `4096b86`.**

`retrieve_with_provenance` chamava `_retrieve_core` duas vezes: ORIGINAL
(mensagem crua) e NORMALIZED (após `normalize_query`). O merge era
first-seen winner, sem comparação de strength. Para
`manda provolone defumado`, ORIGINAL produzia `ORIGINAL_ALIAS_SUBSET`
e NORMALIZED produzia `NORMALIZED_ALIAS_EXACT`. O merge mantinha
SUBSET → não autorizava.

Critical experiment confirmou (4/4): `*_EXACT` era realmente produzida,
para o mesmo SKU, independente, e perdida exclusivamente no merge.

Fix (P101–P103): preservar a positive evidence já produzida quando o
mesmo SKU é recuperado por múltiplos streams.

### 8.2 Track B — GLiNER Extraction Failure

**FROZEN. Não implementar.**

GLiNER classifica o primeiro token de construção multi-token como
`marca` em vez de `produto` quando não reconhece o conjunto inteiro.

Exemplos: `manda Brie triangulo` → `explicit_brand="Brie"`,
`product_term=None`. Idem `Brie forma` (score 0.338),
`Provolone forma 5 kg` (score 0.639).

`resolve_operation` propaga `brand`. Filtro de brand busca
`brand_lower in p["brand"]`. Nenhum produto tem "brie" ou "provolone"
em brand → 0 candidatos → `NOT_FOUND` → `MISSING_PRODUCT`.

### 8.3 Track C — Normalization Discriminator Loss

**FROZEN. Não implementar.**

`normalize_query` remove quantidade (regex), stopwords (`de`, `da`),
apresentação (`PRESENTATION_TERMS`) e tokens < 3 chars. Resultado:
`provolone de 5kg` → `provolone`. `provolone forma 5kg` → `provolone`.

Quantidade e apresentação às vezes **são parte da identidade comercial**
do SKU. `provolone de 5kg` é alias legítimo de CQ-46. Após
normalização, colide com `provolone` genérico.

---

## 9. 9B.2 SAFETY CONTRACT

**9B.2 NÃO é problema.** Não enfraquecer.
POSITIVE_EVIDENCE_SOURCES = {
"ALIAS_EXACT", "NAME_EXACT", "ORIGINAL_EXACT",
"APPROVED_ALIAS", "ENTITY_SIGNAL",
}

text

Decisão: 0 cands → `NOT_FOUND`; 1 cand + evidence=None →
`AMBIGUOUS`; 1 cand + positive evidence → `EXACT_MATCH`; 1 cand +
non-positive evidence → `AMBIGUOUS`; 2+ cands → `AMBIGUOUS`.

**Nunca**: `1 candidate = EXACT`; promoção `TOKEN` → `EXACT`;
promoção `FUZZY` → `EXACT`; threshold relaxado.

P96: **retrieval uniqueness ≠ commercial identity**.
P98: **9B.2 is not the failure**.

---

## 10. MULTI-TURN STATUS

**CHARACTERIZED — CURRENT ORDER STATE.**

Multi-turn sobre o **pedido comercial atual** está provado E2E pelo
caminho natural para os comportamentos caracterizados.

Claim precisa permanecer precisa: **não** registrar genericamente
"multi-turn completo funciona". Registrar:

> Multi-turn over current commercial OrderState is proven E2E through
> the natural path for the characterized behaviors.

**Findings:**

- `UNIQUE_ORDER_ITEM_MATCH` (P1) — PROVEN E2E.
- `ONLY_ITEM` (`ReferenceResolver`) — cobre casos com 1 item.
- `GENERIC_REFERENCE` (`aquele`, `esse`, `o outro`, `o mesmo`) —
  resolvido com 1 item, recusado com 2+.
- `ele` continua **fora do léxico**. Não adicionar sem evidência própria.
- `ref_signal` **não** é consumido no branch ADD de `resolve_operation`.
- `PendingResolution` é clarificação comercial estreita
  (brand/presentation), **não** memória conversacional.
- Fonte histórica comercial: **não existe** no repositório.
- `last_message`, `turn_count`, `pending_clarifications`: **UNUSED BY
  CURRENT CANONICAL PATH**. Não chamar de "dead code" — podem ter uso
  legacy.

**Safety fact (P104):** `LAST_ITEM` do `ReferenceResolver` **não** é
autorização de execução. Com múltiplos itens, `TargetResolver` preserva
`AMBIGUOUS_TARGET`. Nenhuma seleção silenciosa.

**Cases caracterizados:**

| Case | Setup | Probe | outcome | state after |
|---|---|---|---|---|
| A | CQ-44 | `tira ele` | REMOVE_ITEM / item_1 | `[]` |
| B | CQ-44 | `tira` | REMOVE_ITEM / item_1 | `[]` |
| C | CQ-44 | `muda para 3` | CHANGE_QUANTITY / qty=3.0 | 1 item |
| D | CQ-44 | `tira aquele` | REMOVE_ITEM / item_1 | `[]` |
| E | CQ-44 + CQ-04 | `tira` | AMBIGUOUS_TARGET | 2 itens preservados |
| F | CQ-44 + CQ-04 | `tira aquele` | AMBIGUOUS_TARGET | 2 itens preservados |

---

## 11. CURRENT STAGE

**Nenhum Stage técnico ativo.** Estado de fechamento:

### Track A — Same-SKU Positive Evidence Preservation

**CLOSED / ACCEPTED.**

- Commit: `4096b86c9e6e1871a339c26c228295a7facbe3e1`
- Subject: `fix(catalog): preserve same-sku positive retrieval evidence`
- Full suite: 973 passed
- Natural E2E real: 6/6 positivos (`ITEM_ADDED`), 2/2 negativos
  (`AMBIGUOUS_PRODUCT`)

### Multi-turn Re-Audit

**CHARACTERIZED — CURRENT ORDER STATE.** Sem production change. Sem
commit. P1 PROVEN E2E. P104 frozen.

---

## 12. CURRENT FROZEN INVARIANTS

**P101** — SAME-SKU POSITIVE EVIDENCE MUST NOT BE DISCARDED BY AGGREGATION

Quando o MESMO SKU for recuperado por múltiplos streams e pelo menos
um deles produzir provenance já reconhecida como positive evidence,
a agregação deve preservar essa evidência. **Evidence preservation**,
não evidence creation.

**P102** — AGGREGATION MUST NEVER MANUFACTURE EVIDENCE

Se nenhum stream produziu positive evidence para aquele SKU, merge não
promove.

**P103** — AGGREGATION MUST NEVER CROSS SKU BOUNDARIES

Evidence de CQ-44 só afeta CQ-44. Ambiguidade entre SKUs permanece.

**P104** — CONTEXTUAL EVIDENCE ≠ TARGET AUTHORITY

`ReferenceResolver` pode produzir contextual/reference evidence, mas
essa evidência não tem autoridade, sozinha, para selecionar
silenciosamente um target comercial. `TargetResolver` decide.

---

## 13. CURRENT IMPLEMENTATION AUTHORIZATION

**Nada autorizado.**

Escopos congelados: Track B (FROZEN), Track C (FROZEN), `ele` fora do
léxico (não adicionar), `ReferenceResolver`/`TargetResolver` (não
alterar), ConversationMemory/ContextManager/historical store (não
criar), `ref_signal` em ADD (não consumir), `PendingResolution` (não
alterar), `ProductResolver` (FROZEN), `normalize_query` (FROZEN),
GLiNER (FROZEN), Catálogo (FROZEN), Telegram Controlled Execution (NÃO
AUTORIZADO), WhatsApp adapter (NÃO AUTORIZADO).

---

## 14. ACCEPTANCE GATE — Track A

- [x] Corpus congelado antes da implementação.
- [x] Same-SKU positive preservation provado.
- [x] No evidence manufacturing.
- [x] No cross-SKU upgrade.
- [x] Legitimate ambiguity preserved.
- [x] Track B/C non-interference.
- [x] Regressions verdes.
- [x] Full suite verde (973).
- [x] Natural real E2E: ITEM_ADDED, OrderState populado.
- [x] Selective staging.
- [x] Commit: `4096b86`.
- [x] Push.
- [x] `HEAD == origin/master`.

Multi-turn Re-Audit: caracterizado, sem production change, sem commit.

---

## 15. NEXT DECISION TREE

Nenhuma opção abaixo está autorizada automaticamente.

**Opção 1 — Track C (Normalization Discriminator Loss).** Cobre
`provolone de 5kg`, `provolone forma 5kg`, `brie forma`. Requer Stage
próprio.

**Opção 2 — Track B (GLiNER misclassification).** Cobre `Brie
triangulo`, `Brie forma`, `Provolone forma 5 kg`. Mais frágil.

**Opção 3 — Family C (Historical Commercial Reference).** Requer
decisão de negócio sobre **fonte autoritativa**. Não é arquitetura.

**Opção 4 — Telegram Controlled Execution.** NÃO recomendado enquanto
Track B/C estiverem abertos ou sem decisão consciente de aceitá-los.

**Opção 5 — Preservação atual.** Manter gaps conscientemente aceitos.

Tech Lead decide.

---

## 16. KNOWN NON-GOALS

Não autorizado: ContextManager, ConversationMemory, vector DB,
embeddings, CRM, customer history, identity merge, ProductResolver
relaxation, single candidate → EXACT, Telegram Controlled Execution,
WhatsApp adapter, GLiNER tuning, Track C normalization fix.

---

## 17. HISTORICAL ARTIFACT SAFETY

Não apagar automaticamente:

- `docs/entendimento_sprint_foundation.md` — histórico
- `handoff_9b2_diffs.txt` — histórico
- `run_4j4.sh`, `run_app_processing.sh`, `run_channel_boundary.sh`,
  `run_cmd_exec.sh`, `run_idempotency.sh`, `run_multi_turn_audit.sh`,
  `run_recognition_robustness.sh`, `run_safety_guard.sh`,
  `run_session.sh`, `run_telegram_shadow.sh`, `run_track_a.sh`
- `diag_evidence_path.py`, `diag_guard.py`, `diag_multi_turn.py`,
  `diag_multi_turn_reaudit.py`, `diag_multiitem.py`,
  `diag_natural_product.py`, `diag_single_turn.py`,
  `diag_telegram_shadow.py`

**Regra:** NO `git clean`, `git reset`, `git restore`, `git checkout`,
`git stash` genérico. Em dúvida, consultar Tech Lead.

---

## 18. NEW CHAT BOOTSTRAP

Copiar o prompt abaixo em um novo chat, junto com este arquivo:

---
Você está assumindo como Tech Lead do projeto ORDO.

Leia integralmente docs/ORDO_TECH_LEAD_RECOVERY.md.

Trate-o como documento de bootstrap/navegação — NÃO como substituto
das fontes autoritativas:

docs/ORDO_CURRENT_STATE.md

docs/TECH_LEAD_LOG.md

docs/ORDO_MASTER_HANDOFF.md

Verifique, antes de autorizar qualquer alteração:

git rev-parse HEAD

git rev-parse origin/master

git status --short

leitura de docs/ORDO_CURRENT_STATE.md

Preserve os princípios congelados (T10-P1 a T10-P55, P56 a P104) e o
CURRENT STATUS / CURRENT STAGE, quando houver Stage ativo, conforme o
Recovery Pack.

Não implemente nada além do que estiver explicitamente autorizado.

Primeiro reporte sua reconstrução do estado atual:

HEAD e origem;

working tree;

Stage atual;

princípios vigentes;

quaisquer divergências encontradas entre este pack e o código/docs.

Depois:

STOP FOR USER CONFIRMATION.

text

---

## 19. RECOVERY CHECK

Novo Tech Lead recebe este arquivo + repo:

- sabe o que é o ORDO;
- conhece o caminho canônico COMMAND/QUERY/Identity/Idempotency/Shadow;
- conhece princípios congelados (T10-P1 a P104);
- conhece regras epistêmicas;
- sabe HEAD atual e histórico de checkpoints;
- sabe o que é provado, não-provado, pausado;
- conhece as três causas de falha natural (Track A/B/C);
- sabe que 9B.2 é safety contract, não bug;
- sabe o estado do multi-turn;
- sabe o escopo atual (nenhum Stage ativo);
- conhece os non-goals;
- sabe quais arquivos não apagar;
- tem prompt para abrir chat novo.

Se algo faltar, abrir GAP neste documento.

---

**Fim do documento.**