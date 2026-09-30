# ORDO — ACTIVE STAGE

## STATUS

**Stage ativo:** TELEGRAM CONTROLLED EXECUTION v1

**Checkpoint base:** `821d2ffea3de619a735f2fb89aef69d12b60b3de`

---

## STAGE — TELEGRAM CONTROLLED EXECUTION v1

### OBJECTIVE

Ligar o caminho Telegram existente ao `orchestrate_command`, permitindo que uma
mensagem de chat explicitamente autorizado, com execução globalmente habilitada
e comando canonicamente executável, mute `OrderState` dentro do domínio ORDO.

### QUESTION THIS STAGE ANSWERS

> É possível permitir execução real de comandos via Telegram, restrita a chats
> autorizados e a um kill switch global, sem violar nenhum contrato ou gate de
> segurança existente?

### SUCCESS CONDITION

Todos os sete cenários abaixo, provados por teste, com `OrderState` como única
superfície de mutação:

1. **Chat autorizado + execução habilitada + comando executável**
   → `OrderState` muda pelo caminho canônico.
2. **Execução desabilitada (kill switch OFF)**
   → `OrderState` não muda.
3. **Chat não autorizado (fora da allowlist)**
   → `OrderState` não muda.
4. **Safety block (representational overflow)**
   → `OrderState` não muda.
5. **Clarification / não executável** (ex.: `NEEDS_CLARIFICATION` do composer)
   → `OrderState` não muda.
6. **Mensagem duplicada (mesmo `ExternalMessageId`)**
   → não provoca segunda execução; `ALREADY_CLAIMED` observável.
7. **Nenhum external commercial side effect**
   → nenhuma chamada a ERP, faturamento, estoque, reserva, logística,
     pagamento, emissão de pedido externo. Verificado por isolamento
     estrutural (AST guard) no harness e nos módulos que ele importa.

### OUT OF SCOPE

- PA-2 Stage 2 (applicability, matcher, CIA).
- Relationship Scope mechanism.
- `CustomerId` / `RelationshipId`.
- Cross-channel linking.
- TTL / expiração.
- ERP, faturamento, estoque, logística, pagamento, emissão de pedido externo.
- UI, dashboard, painel administrativo.
- Aprovação humana por mensagem (decidido: não nesta versão).
- Log-only execution.
- Ampliar PA-1.
- Track B.
- SPA / ATC / CDP.
- `approved=True` em aliases.
- Multi-tenant, multi-org, cross-account.
- Persistência durável (in-memory é suficiente para v1).

### REUSE

Mecanismos e contratos já existentes que o Stage pode usar diretamente:

- `TelegramTransport.get_updates`, `TelegramAdapter.parse`, `allowed_chat_ids`
  (`pipeline/telegram_transport.py`, `pipeline/telegram_adapter.py`) — transporte,
  parse e allowlist de chat.
- `ChannelIdentity`, `InMemoryConversationMappingStore` (`pipeline/channel_identity.py`,
  `pipeline/conversation_mapping.py`) — referência observável e mapeamento.
- `InMemoryConversationSessionStore` (`pipeline/conversation_session.py`) — sessão.
- `InMemoryIdempotencyStore`, `IdempotencyKey`, `ExternalMessageId`
  (`pipeline/idempotency.py`) — idempotência.
- `orchestrate_command` (`pipeline/application_orchestrator.py`) — já existe,
  testado, nunca chamado em produção.
- `OrderEngine` (`order/engine.py`) — mutação de `OrderState`.
- `make_guarded_resolve_operation`, `CommandSafetyGuard`
  (`pipeline/command_safety_guard.py`) — **Safety gate obrigatório**.
- `make_pa1_authority_wrapper` (`pipeline/pa1_authority.py`) — PA-1 Authority,
  composicional, opcional no caminho.
- `ApplicationProcessor` (`pipeline/application_processing.py`) — se aplicável
  para obter `SignalObservation` + `DispatchPlan`.
- `OrchestrationOutcome` (`pipeline/application_orchestrator.py`) — outcomes
  existentes para observabilidade mínima.

### REGRESSION

Contratos e princípios já provados que não podem ser quebrados:

- P59–P67 (Safety Gate).
- P75, P76, P77 (Idempotency).
- P101–P105 (Track A, Evidence).
- Boundaries com guards: `CallerResult`, `ProcessingResult`, `OrchestrationResult`.
- Evidence Contract v0.
- PA-1 Authority (não alterar).
- PA-2 Stage 1 (não alterar).
- Track B FROZEN.

> Itens como `normalize_query`, `ProductResolver`, `catalog.json`, `aliases.json`
> estão **fora da superfície autorizada de mudança** neste Stage (não aparecem
> em `ALLOWED FILES`), mas **não são tratados como invariantes congelados**.
> Not allowed in this Stage ≠ FROZEN architecture.

### SAFETY E PA-1 — COMPOSIÇÃO

O caminho de Controlled Execution **deve preservar `CommandSafetyGuard` /
`make_guarded_resolve_operation` como gate obrigatório**.

`PA-1 Authority` pode ser composta no caminho quando aplicável, reutilizando
`make_pa1_authority_wrapper`. **PA-1 Authority não substitui Safety Authority.**

Nenhum dos dois mecanismos pode ser alterado neste Stage.

### KILL SWITCH v1

Kill switch = **configuração booleana explícita no harness de execução**.

Conceitualmente:

`execution_enabled: bool`

Quando `False`:

**nenhuma mensagem Telegram pode alcançar mutação de `OrderState`.**

Não criar:

- env var;
- arquivo de flag;
- módulo auxiliar;
- dashboard;
- configuração persistente;
- mecanismo administrativo.

Se posteriormente precisarmos de operação dinâmica, isso é outro problema.
Para v1 queremos provar o boundary.

### ALLOWED FILES

Lista exata. Qualquer outro arquivo exige STOP.

- `docs/ACTIVE_STAGE.md` — este contrato.
- `pipeline/telegram_execution.py` — novo (harness de execução supervisionada).
- `tests/test_telegram_controlled_execution.py` — novo (7 cenários da SUCCESS CONDITION).

**Exatamente três arquivos.** Qualquer quarto arquivo: STOP FOR TECH LEAD REVIEW.

### STOP CONDITION

- Qualquer arquivo fora do `ALLOWED FILES`.
- Necessidade de alterar `orchestrate_command`, `OrderState`, `OrderEngine`,
  `CallerResult`, `ProcessingResult`, `OrchestrationResult`, `CommandSafetyGuard`,
  `ProductResolver`, `Evidence v0`, `normalize_query`, `catalog.json`, `aliases.json`,
  PA-1 Authority, PA-2 Stage 1.
- Necessidade de novo mecanismo não previsto em REUSE.
- Necessidade de decisão de domínio não coberta pela DECISION SUPERVISED v1.
- Algum dos 7 cenários não conseguir ser provado sem violar FROZEN.
- SUCCESS CONDITION satisfeita.

### CLASSIFICAÇÃO

| Item | Classificação |
|---|---|
| TelegramTransport, TelegramAdapter, allowed_chat_ids | **REUSE** |
| ChannelIdentity, ConversationMapping, ConversationSession | **REUSE** |
| Idempotency Stage 1 | **REUSE** |
| orchestrate_command | **REUSE** |
| OrderEngine | **REUSE** |
| CommandSafetyGuard / make_guarded_resolve_operation | **REUSE** (obrigatório) |
| ApplicationProcessor | **REUSE** |
| PA-1 Authority | **REUSE** (composicional, opcional no caminho) |
| Harness de produção Telegram→orchestrate_command | **NEW** |
| Wiring de OrderEngine + stores no ponto de produção | **NEW** |
| Kill switch (parâmetro booleano no harness) | **NEW** (mínimo) |
| Observable outcome sobre `OrchestrationResult` | **REUSE** (via outcomes existentes) |
| P59–P67, P75–P77, P101–P105, boundaries com guards | **REGRESSION** |
| Evidence Contract v0, PA-1 Authority, PA-2 Stage 1 | **REGRESSION** (não alterar) |
| Track B | **PARK** (FROZEN) |
| PA-2 Stage 2, matcher, Relationship Scope, CustomerId, cross-channel, TTL, ERP, dashboard | **PARK** |
| SPA / ATC / CDP | **PARK** |
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