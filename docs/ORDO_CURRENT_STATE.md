# ORDO --- CURRENT STATE

**Checkpoint:** `c18ec6b20eda62af5d4746c310ed504ef01c5f73` --- Track 9B.2 `CLOSED / ACCEPTED` (2026-09-21).

**Nota histórica:** o checkpoint anterior era `2026-09-18 — antes do HOLDOUT-2`. Esse estado está superado e não é mais o estado operacional.

## Produto

**Ordo --- Conversational Order Intelligence Engine**

> **Transformar conversas comerciais do WhatsApp em operações
> estruturadas de venda.**

> **A conversa deixa de ser o pedido. A conversa produz um pedido.**

Modelos fornecem sinais; software resolve e valida; ambiguidade é
explicitada; Order Engine executa somente operações resolvidas.

## Arquitetura atual

`Message → sinais → message_intent → OperationResolver → resolved_operation_type → Reference/Pending/Target Resolution → Catalog Retrieval/Product Resolution → ResolutionComposer → ResolvedOperation | NEEDS_CLARIFICATION → Safety → Order Engine → OrderState`

Regras: - `message_intent ≠ resolved_operation_type` - OperationResolver
não resolve target/product - CatalogRetriever recupera; ProductResolver
decide - Order Engine não interpreta linguagem

## Track 9B.2 — Safe Catalog Retrieval

Status: `CLOSED / ACCEPTED`

Commit: `c18ec6b20eda62af5d4746c310ed504ef01c5f73`
Mensagem: `fix(ordo): harden catalog retrieval evidence and constraints`

Escopo entregue:

-   provenance-aware catalog retrieval: `retrieve_with_provenance(query, brand=None, presentation=None)`;
-   preservação de `brand` e `presentation` em ADD_ITEM;
-   separação entre retrieval evidence e execution authorization;
-   `TOKEN`, `SUBSET` e `FUZZY` sem autoridade isolada para `EXACT_MATCH`;
-   `evidence=None` sem autoridade para `EXACT_MATCH`;
-   propagação legítima de provenance nos callers identificados em F-06;
-   candidate ordering determinístico;
-   testes de segurança/regressão associados ao 9B.2.

## Política R2 — Evidence vs Authorization

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

## CR-01 / CR-02

-   `CR-02 = structurally protected by authorization policy.`
-   `CR-01 = NOT structurally guaranteed against every future catalog/alias mutation.`

CR-01 não é declarado estruturalmente resolvido pelo 9B.2.

## Política P1

`UNIQUE_ELIGIBLE_TARGET` pode resolver target somente **depois** de o
OperationType estar resolvido, para operação que exige item existente,
com exatamente um target elegível e sem evidência conflitante.

P1 não transforma `"coloca 3"` em CHANGE só porque há um item.

## Commits principais

-   Baseline v0: `5702f2b4af59560b40bae4ec8c6666b3f16e562a`
-   Benchmark v1: `2e9de0cf319b65a045e0b7c77a6fc7f2dc6e391d`
-   Target Stage1: `92c3581c754660c1579f44d8a70a639f2a266575`
-   Pending Stage2: `204a729ce4052de75c7d2dac1bad4393b05bf74c`
-   Composer Stage3: `05f05389b133d277fa5ed59b2a1a9d7e9eabd38c`
-   REPLACE Stage4: `680783af268f9ec08c22d878c296ebf52a2faf76`
-   Operation Resolver: `e1bfb5d9f452279682d38afcf2e94bab48ba58e9`
-   Benchmark V2: `de07dcaeadecbdc5e0f99ecfa7ac887b6a9e57ab`
-   Scripts V2: `9f70f0df64d756af6b128a6890c88053af033c0f`
-   **Track 9B.2:** `c18ec6b20eda62af5d4746c310ed504ef01c5f73`

## Benchmark

-   **DEV V2: 9/10**
-   **HOLDOUT-1 V2: 9/10**
-   **Wrong Executable Operation Rate: 0**

DEV/HOLDOUT-1 já são conhecidos; não são prova independente de
generalização.

DEV-09 permanece `GROUND_TRUTH_QUESTIONABLE`.

HOLDOUT-01 é dívida conhecida; investigação não é pré-requisito para
nenhuma decisão atual.

### HOLDOUT-2 — resultados históricos imutáveis

```text
RAW BLIND                 11/20 = 55%
POST-BLIND Track 9A       13/20 = 65%
POST-BLIND Track 9B.2     12/20 = 60%
Wrong Executable Operation = 0