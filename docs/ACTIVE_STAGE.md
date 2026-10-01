# ORDO — ACTIVE STAGE

## STATUS

**PROPOSTA — AGUARDANDO STAGE OPEN**

**Contrato proposto:** TELEGRAM CONVERSATION LOOP CLOSURE v1

**Checkpoint base:** `12ca86b7a8897e5060019cab1469b6e5926e4992`

> Este documento descreve o contrato do próximo Stage. O Stage ainda **não
> está aberto**. A abertura formal ocorre após aceite explícito do Tech Lead.

---

## STAGE — TELEGRAM CONVERSATION LOOP CLOSURE v1

### OBJECTIVE

Fechar o ciclo conversacional Telegram permitindo que resultados já produzidos
pelo ORDO sejam convertidos em respostas mínimas verdadeiras e entregues ao
mesmo chat de origem, sem ampliar autoridade comercial ou semântica.

### QUESTION THIS STAGE ANSWERS

> O ORDO consegue receber uma mensagem Telegram, processá-la/executá-la pelo
> caminho canônico existente e devolver ao mesmo chat uma resposta mínima
> coerente com o resultado observado, preservando todos os boundaries e gates
> existentes?

### PRINCÍPIOS

```
Internal Result
  → Communicable Response
  → Channel Delivery
```

**Response Composition ≠ Response Delivery.**  
O componente que decide **o que comunicar** não possui Telegram.

**Channel Delivery ≠ Domain Interpretation.**  
O `TelegramTransport` sabe **como entregar**; não interpreta outcomes do ORDO.

**Communication describes the result; it does not create a new result.**

### SUCCESS CONDITION

Todos os cenários abaixo, provados por teste:

1. **`EXECUTED`** → resposta mínima entregue ao chat correto.
2. **`CLARIFICATION`** → resposta verdadeira, sem inventar resolução.
3. **`SAFETY_BLOCKED`** → resposta sem execução.
4. **`EXECUTION_DISABLED`** → resposta sem mutação.
5. **`DUPLICATE`** → comportamento definido e testado, sem segunda execução.
6. **`ERROR`** → resposta mínima sem vazar detalhes internos.
7. **Destination** → exatamente o chat correspondente à mensagem recebida.
8. **`TelegramTransport.send_message`** → realiza somente delivery; guards existentes preservados.
9. **Composer** → não executa domínio, não chama Telegram, não cria autoridade.
10. **E2E controlado:**
    `Telegram update → ORDO → response composition → Telegram delivery`
    comprovado por teste, sem external commercial side effect.

### `NOT_ELIGIBLE` — DECISÃO DECLARADA

> **NOT_ELIGIBLE → NO RESPONSE**

Racional:

A allowlist do adapter é **boundary de elegibilidade**. Mensagem de chat não
autorizado **não deve** fazer o ORDO iniciar interação de saída.

**Not eligible for processing ≠ eligible for response.**

Isso também evita transformar a allowlist em mecanismo que confirma
presença/comportamento do ORDO para chats não autorizados.

Teste correspondente: chat fora da allowlist → nenhum envio.

### OUT OF SCOPE

- LLM response generation.
- Personalidade do bot.
- Copy rica.
- Templates complexos.
- i18n.
- WhatsApp.
- Outbound multicanal genérico.
- Retries sofisticados.
- Delivery queue.
- Webhook.
- Delivery receipts.
- Typing indicator.
- Edição de mensagem.
- Mídia.
- Botões.
- PA-2 Stage 2.
- Matcher.
- Relationship Scope.
- `CustomerId` / `RelationshipId`.
- Cross-channel linking.
- TTL / expiração.
- Track B.
- SPA / ATC / CDP.
- ERP.
- Estoque externo.
- Faturamento.
- Pagamento.
- Logística.
- Qualquer external commercial side effect.
- Persistência durável.
- Dashboard.
- Aprovação humana por mensagem.
- Multi-tenant.

### REUSE

- `TelegramTransport.get_updates`, `next_offset`, `TransportFailure`.
- `TelegramAdapter.parse`, `ParseResult`, `ParsedMessage`, `allowed_chat_ids`.
- `ChannelIdentity`, `InMemoryConversationMappingStore`.
- `InMemoryConversationSessionStore`.
- `InMemoryIdempotencyStore`, `IdempotencyKey`, `ExternalMessageId`.
- `orchestrate_command`, `OrchestrationResult`, `OrchestrationOutcome`.
- `CommandSafetyGuard`, `make_guarded_resolve_operation`.
- `OrderEngine`.
- `TelegramControlledExecution`, `UpdateOutcome`, `ExecutionOutcome`.
- `ResolutionResult` (`outcome`, `operation`, `reason_code`, `evidence`).
- `CallerResult`.
- Todos os 9 testes de `test_telegram_controlled_execution.py`.
- Todos os testes de `test_telegram_transport.py`, `test_telegram_adapter.py`.

### REGRESSION

- Os 9 testes de Telegram Controlled Execution.
- Kill switch (`execution_enabled`).
- Safety (`CommandSafetyGuard` como gate obrigatório).
- Idempotência (`IdempotencyKey`, atomic claim).
- Isolamento AST do harness.
- `_ALLOWED_IMPORTS` do `TelegramTransport` (não alterar).
- `test_tt06_imports_only_allowed`.
- `test_tt06b_no_or_do_or_adapter_imports`.
- `test_tt02b_token_not_exposed_as_attribute_by_name`.
- Boundaries fechados: `CallerResult`, `ProcessingResult`, `OrchestrationResult`.
- `ChannelIdentity`, `OrderState`, `resolve_operation`, `OrderEngine`.
- PA-1 Authority, PA-2 Stage 1.
- Track B FROZEN.
- Ausência de external commercial side effects.

> Itens fora do `ALLOWED FILES` **não são FROZEN por isso**.
> `not allowed in this Stage ≠ FROZEN architecture`.

### NEW

Somente:

- `TelegramTransport.send_message(chat_id, text)` — delivery capability.
- Representação mínima / composer de resposta (`CommunicableResponse(destination, text)`).
- Preservação do destination até Delivery (envelope próprio no boundary do harness).

### REOPEN

Nenhum.

### PARK

- LLM response generation.
- Personalidade, copy rica, templates complexos, i18n.
- WhatsApp, outbound multicanal genérico.
- Retries sofisticados, delivery queue, webhook, receipts, typing, edição, mídia, botões.
- PA-2 Stage 2, matcher, Relationship Scope, `CustomerId`, `RelationshipId`, cross-channel, TTL.
- SPA / ATC / CDP.
- Track B.
- ERP, estoque externo, faturamento, pagamento, logística.
- Dashboard, persistência durável, multi-tenant.
- `approved=True` em aliases.
- Notificação de `NOT_ELIGIBLE` (allowlist é boundary de interação).

### ALLOWED FILES

Exatamente 7 arquivos:

- `docs/ACTIVE_STAGE.md` — este contrato.
- `pipeline/telegram_transport.py` — adicionar `send_message`.
- `pipeline/telegram_execution.py` — envelope de retorno com destino.
- `pipeline/telegram_response.py` — **novo** (composer + `CommunicableResponse`).
- `tests/test_telegram_transport.py` — teste para `send_message`.
- `tests/test_telegram_response.py` — **novo** (testes do composer).
- `tests/test_telegram_controlled_execution.py` — ajuste pelo novo retorno.

**Nenhum oitavo arquivo.**

### STOP CONDITION

STOP se:

- surgir necessidade de oitavo arquivo;
- boundary fechado precisar mudar;
- novo dado semântico precisar ser criado;
- guard do `TelegramTransport` precisar ser enfraquecido;
- composer precisar reinterpretar domínio;
- delivery precisar conhecer domínio;
- external commercial side effect for necessário;
- mecanismo não previsto aparecer;
- SUCCESS CONDITION for satisfeita.

### CLASSIFICAÇÃO

| Item | Classificação |
|---|---|
| `TelegramTransport.get_updates`, `next_offset`, `TransportFailure` | **REUSE** |
| `TelegramAdapter.parse`, `ParsedMessage`, `allowed_chat_ids` | **REUSE** |
| `ChannelIdentity`, `InMemoryConversationMappingStore` | **REUSE** |
| `InMemoryConversationSessionStore` | **REUSE** |
| `InMemoryIdempotencyStore` | **REUSE** |
| `orchestrate_command`, `OrchestrationResult` | **REUSE** |
| `CommandSafetyGuard`, `make_guarded_resolve_operation` | **REUSE** |
| `OrderEngine`, `TelegramControlledExecution`, `ExecutionOutcome` | **REUSE** |
| `ResolutionResult`, `CallerResult` | **REUSE** |
| `TelegramTransport.send_message` | **NEW** |
| Composer mínimo + `CommunicableResponse` | **NEW** |
| Preservação do destination até Delivery | **NEW** |
| Kill switch, idempotência, Safety, boundaries fechados, guards do transport | **REGRESSION** |
| PA-1 Authority, PA-2 Stage 1, Evidence v0 | **REGRESSION** (não alterar) |
| Track B | **PARK** (FROZEN) |
| PA-2 Stage 2, matcher, Relationship Scope, `CustomerId`, cross-channel, TTL | **PARK** |
| WhatsApp, outbound multicanal, LLM, copy rica, i18n, templates | **PARK** |
| ERP, estoque, faturamento, pagamento, logística | **PARK** |
| SPA / ATC / CDP | **PARK** |
| Notificação de `NOT_ELIGIBLE` | **PARK** (allowlist é boundary de interação) |
| Nenhum | **REOPEN** |

---

## REGRAS

1. **A etapa termina quando a SUCCESS CONDITION for satisfeita.**
   Encontrar outro assunto interessante durante o trabalho **não
   prolonga automaticamente a etapa**.

2. **Questões encontradas durante o trabalho são classificadas:**
   - `REUSE` — já conhecido; usar.
   - `REGRESSION` — já provado; verificar.
   - `NEW` — realmente não respondido e necessário para o objetivo.
   - `REOPEN` — decisão fechada contradita por nova evidência concreta.
   - `PARK` — válido, mas desnecessário para a etapa atual.

3. **NEW que não bloqueia a etapa:** vira `PARK`, registrado no
   `ORDO_CURRENT_STATE.md` como questão pendente.

4. **NEW que bloqueia a etapa:** STOP FOR TECH LEAD REVIEW.

5. **NEW ≠ authorization to investigate.**
   Uma questão classificada como NEW somente pode ser investigada
   se for **necessária para satisfazer a SUCCESS CONDITION** da
   etapa ativa.
   Caso contrário:
   `NEW → PARK` e a etapa continua.
   Isso evita recursão investigativa.

6. **REGRESSION:** executar testes focais; se verde, seguir.

7. **REOPEN:** somente com evidência nova concreta. STOP antes de
   alterar contrato congelado.

8. **Missing from memory ≠ missing from project.**
   Consultar `ORDO_CURRENT_STATE.md` antes de investigar.

   