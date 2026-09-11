# active_item — Semântica e Evidências

## Definição

`active_item` é o **item do pedido que está atualmente em foco conversacional**, quando essa condição puder ser estabelecida com **evidência suficiente**.

Ele não é determinado por uma única regra, mas por uma combinação de evidências disponíveis no `OrderState`, na mensagem atual e no `ResolutionContext`.

## Evidências para determinar active_item

As seguintes evidências podem ser utilizadas, em ordem de prioridade (da maior para a menor):

| Prioridade | Evidência | Descrição | Exemplo |
|------------|-----------|-----------|---------|
| 1 | **EXPLICIT_REFERENCE** | A mensagem menciona explicitamente um produto ou um item existente. | "tira o provolone" → item com `product_term = provolone` |
| 2 | **PENDING_RESOLUTION** | Existe um item pendente aguardando resolução (ex: ambiguidade). | pending_resolution com `product_family = provolone` |
| 3 | **LAST_MODIFIED_ITEM** | O item que sofreu a última alteração (adição, remoção, quantidade). | Último item que teve `quantity` alterado |
| 4 | **LAST_ADDED_ITEM** | O item adicionado mais recentemente. | Último item da lista |
| 5 | **UNIQUE_COMPATIBLE_ITEM** | Apenas um item no estado é compatível com as restrições da mensagem. | `"da Tânia"` → apenas um item tem marca Tânia |
| 6 | **CONTEXTUAL_HINT** | A mensagem contém termos genéricos de referência ("esse", "aquele") que podem ser associados a um item. | "esse" → item mais recentemente mencionado |

## Quando NÃO há active_item

Se após avaliar todas as evidências disponíveis não for possível determinar um único item com confiança:

- `active_item = None`
- O sistema deve retornar `NEEDS_CLARIFICATION` para operações que dependem de um target.

## Uso no pipeline

O `active_item` é determinado pelo `ReferenceResolver` e usado para:

- **CHANGE_QUANTITY**: alterar a quantidade do `active_item`
- **REMOVE_ITEM**: remover o `active_item`
- **CONFIRM_ORDER**: confirmar o pedido (se não houver pendências)

## Exemplos

### Exemplo 1 — Referência explícita

```text
OrderState:
    item_1 = manteiga
    item_2 = provolone

Mensagem:
"tira o provolone"

Evidência:
    EXPLICIT_REFERENCE → item_2

active_item = item_2