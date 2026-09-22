# ORDO — TECH LEAD DECISION LOG

Este documento registra decisões técnicas e de governança tomadas
durante a evolução do Ordo.

Ele NÃO substitui:

- `ORDO_MASTER_HANDOFF.md` — histórico consolidado do projeto;
- `ORDO_CURRENT_STATE.md` — estado operacional atual;
- código, contratos, datasets e manifests versionados — fonte técnica verificável.

## Regra de uso

Registrar aqui somente decisões que alterem ou preservem:

- arquitetura;
- contratos;
- políticas semânticas;
- segurança;
- benchmarks;
- freezes;
- autorização de etapas;
- STOP POINTS;
- interpretação de resultados relevantes.

Não usar este arquivo como transcrição dos chats.

---

# 2026-09-19 — Recuperação do Track 9B.2

## Contexto

Durante a preparação da migração da Equipe de Engenharia para um novo
chat, foi constatado que o chat anterior terminou durante trabalho ainda
não commitado relacionado ao Track 9B.2 — Safe Catalog Retrieval.

HEAD encontrado:

`3a82007783f4e7abcb2e4804e7fe5a9d3670d89f`

O working tree não estava clean.

Foram encontrados arquivos modificados relacionados a:

- CatalogRetriever;
- ProductResolver;
- ResolutionPipeline;
- testes de ReferenceResolver;
- testes de REPLACE_ITEM.

Também foram encontrados novos arquivos relacionados à segurança de
Catalog Retrieval e handoff do 9B.2.

## Decisão do Tech Lead

O working tree NÃO deve ser considerado implementação aprovada.

Também NÃO deve ser descartado.

Ele deve ser tratado como:

`9B.2 — UNAPPROVED / UNDER RECOVERY`

A nova Equipe não deverá implementar o Track 9B.2 novamente do zero.

Primeiro deverá reconstruir e auditar o trabalho deixado pela Equipe
anterior.

## Evidências preliminares encontradas

O trabalho interrompido aparentemente inclui:

- normalização de query;
- proteção para query sem evidência de produto;
- candidate provenance;
- combinação de evidência original e normalizada;
- proteção contra fuzzy-only produzir `EXACT_MATCH`;
- testes de segurança para Catalog Retrieval.

Esses mecanismos ainda NÃO estão aprovados.

## Invariantes que continuam governando o Track 9B.2

### CR-01 — EMPTY QUERY

Ausência de evidência lexical de produto não pode produzir candidatos
arbitrários.

### CR-02 — NO EVIDENCE, NO PRODUCT

Sem evidência positiva de produto, nenhum produto pode se tornar
executável.

### CR-03 — NORMALIZATION DOES NOT REPLACE EVIDENCE

Normalização é evidência auxiliar e não deve destruir ou substituir a
evidência original.

## Segurança

Permanece obrigatório:

`Wrong Executable Operation = 0`

Melhoria de recall não justifica introduzir resolução insegura.

## HOLDOUT-2

Resultado histórico RAW BLIND permanece imutável:

`11/20 = 55%`

Resultados posteriores devem ser identificados como:

`POST-BLIND REGRESSION`

e nunca como novo resultado blind.

Após Track 9A, o resultado conhecido é:

`13/20 POST-BLIND REGRESSION`

## Componentes congelados

Continuam congelados:

- Intent Classifier;
- GLiNER;
- Order Engine;
- benchmark histórico RAW BLIND.

Não estão autorizados neste momento:

- fine-tuning;
- novo LLM;
- integração WhatsApp;
- MVP;
- Track 9C;
- alterações específicas para fazer casos do HOLDOUT-2 passarem.

## Próximo passo autorizado

A nova Equipe deverá auditar o working tree existente e produzir:

`ORDO 9B.2 RECOVERY REPORT`

antes de modificar qualquer arquivo.

## STOP POINT

Após o Recovery Report:

**PARAR E AGUARDAR REVISÃO DO TECH LEAD.**

Nenhuma implementação adicional está autorizada antes dessa revisão.

---

# 2026-09-21 — Recuperação e Fechamento do Track 9B.2

## Recovery

O `ORDO 9B.2 RECOVERY REPORT` foi revisado e aprovado.

Track 9B.2 passou por:

-   `UNAPPROVED / UNDER RECOVERY`
-   `RECOVERED / UNDER TECHNICAL AUDIT`
-   `RECOVERED / IMPLEMENTATION AUTHORIZED — CONTROLLED SCOPE`
-   `CLOSED / ACCEPTED`

## Autorização de implementação

Escopo autorizado:

-   **R1** — provenance + constraints no mesmo `CatalogRetriever`:
    `retrieve_with_provenance(query, brand=None, presentation=None)`.
-   **R2** — `retrieval evidence != execution authorization evidence`.
-   **R3** — ADD_ITEM propaga `brand` e `presentation`.
-   **R4 — DEFERRED** — não expandir STOPWORDS; não redesenhar
    estruturalmente a detecção de ausência de produto neste patch.
-   **F-06** — propagação legítima de provenance nos callers
    identificados (`ModularAdapter`, `ConversationProcessor`).
-   **R5** — testes de regressão obrigatórios.

## Commit

`c18ec6b20eda62af5d4746c310ed504ef01c5f73`
`fix(ordo): harden catalog retrieval evidence and constraints`

O commit inclui somente os 6 arquivos do escopo autorizado. Alterações
pré-existentes (docstrings, comentários, trailing whitespace) permanecem
fora do commit.

## Status

Track 9B.2: `CLOSED / ACCEPTED`.

## R2 — Evidence vs Authorization

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

## HOLDOUT-2 — regressão pós-blind

Resultados históricos preservados:

```text
RAW BLIND                 11/20 = 55%
POST-BLIND Track 9A       13/20 = 65%
POST-BLIND Track 9B.2     12/20 = 60%
Wrong Executable Operation = 0