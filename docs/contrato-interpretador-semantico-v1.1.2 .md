# CONTRATO DO INTERPRETADOR SEMÂNTICO v1.1.2 — FROZEN
**SISTEMA DE PEDIDOS CONVERSACIONAIS — CASA DOS QUEIJOS**

Este documento estabelece a versão final e auditada da interface, especificações e limites do **Interpretador Semântico v1.1** (camada NLP), servindo como especificação para homologação e congelamento antes do desenvolvimento técnico.

O interpretador semântico atua como um tradutor cognitivo puro, cuja única responsabilidade é **transformar mensagens brutas de clientes em dados semânticos estruturados**.

---

## A. JSON SCHEMA v1.1

O schema JSON abaixo foi projetado para garantir tipagem forte, alta confiabilidade sintática em LLMs de pequeno porte (SLMs), e separação rígida de origens para quantidades e unidades:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SemanticInterpreterOutputV1_1",
  "type": "object",
  "properties": {
    "intent": {
      "type": "string",
      "enum": [
        "ADD_ITEM",
        "REMOVE_ITEM",
        "CHANGE_QUANTITY",
        "QUERY_PRICE",
        "QUERY_AVAILABILITY",
        "CONFIRM_ORDER",
        "CANCEL_ORDER",
        "REPLACE_ITEM",
        "UNKNOWN"
      ]
    },
    "product_term": { "type": ["string", "null"] },
    "quantity": {
      "type": "object",
      "properties": {
        "value": { "type": ["number", "null"] },
        "value_origin": { "type": "string", "enum": ["EXPLICIT", "INFERRED", "NOT_INFORMED"] },
        "unit": { "type": ["string", "null"] },
        "unit_origin": { "type": "string", "enum": ["EXPLICIT", "INFERRED", "NOT_INFORMED"] }
      },
      "required": ["value", "value_origin", "unit", "unit_origin"]
    },
    "explicit_presentation": { "type": ["string", "null"] },
    "explicit_brand": { "type": ["string", "null"] },
    "contextual_references": {
      "type": "array",
      "items": { "type": "string" }
    },
    "missing_information": {
      "type": "array",
      "items": { "type": "string" }
    },
    "catalog_candidates": {
      "type": "array",
      "items": { "type": "string" }
    },
    "product_resolution_status": {
      "type": "string",
      "enum": ["EXACT_MATCH", "HIGH_CONFIDENCE", "AMBIGUOUS", "NOT_FOUND"]
    }
  },
  "required": [
    "intent",
    "product_term",
    "quantity",
    "explicit_presentation",
    "explicit_brand",
    "contextual_references",
    "missing_information",
    "catalog_candidates",
    "product_resolution_status"
  ]
}
```

---

## B. DICIONÁRIO DOS CAMPOS

Abaixo está o detalhamento conceitual de cada atributo definido no Contrato v1.1, valores permitidos e regras estritas para nulidade:

*   **`intent`** (String, Obrigatório): A intenção conversacional primária identificada na fala do cliente.
    *   *Enums Permitidos:*
        *   `ADD_ITEM`: Solicitação de adição de produto (ex: *"Quero provolone"*).
        *   `REMOVE_ITEM`: Solicitação de remoção de item (ex: *"Tira o queijo"*).
        *   `CHANGE_QUANTITY`: Alteração de quantidade (ex: *"Ficam só 2"*).
        *   `QUERY_PRICE`: Dúvida sobre preços (ex: *"Quanto fica?"*).
        *   `QUERY_AVAILABILITY`: Dúvida sobre estoque (ex: *"Tem aquele iogurte?"*).
        *   `CONFIRM_ORDER`: Gatilho linguístico de finalização (ex: *"Pode fechar"*).
        *   `CANCEL_ORDER`: Solicitação de cancelamento integral.
        *   `REPLACE_ITEM`: Solicitação de troca ou substituição de item.
        *   `UNKNOWN`: Intenção não determinada linguisticamente.
*   **`product_term`** (String ou `null`, Obrigatório): Termo bruto de produto extraído do texto do cliente (ex: `"manteiga"`, `"Brie"`). Deve ser `null` se a intenção for não-produto (ex: *"Pode fechar"*, *"Deixa quieto"*).
*   **`quantity`** (Object, Obrigatório): Contêiner para dados numéricos de quantidade e unidades físicas:
    *   **`value`** (Number ou `null`): O número de quantidade extraído. Deve ser `null` se nenhum dado numérico estiver na mensagem (ex: *"Quero ricota"*).
    *   **`value_origin`** (String, enum: `EXPLICIT`, `INFERRED`, `NOT_INFORMED`):
        *   `EXPLICIT`: Quando o número foi textualmente expresso por algarismo ou palavra numérica (ex: `"1"`, `"2"`, `"duas"`, `"um"`).
        *   `INFERRED`: Quando a quantidade numérica não foi expressa verbalmente, mas é implicitada gramaticalmente.
        *   `NOT_INFORMED`: Quando nenhuma quantidade foi informada na mensagem.
    *   **`unit`** (String ou `null`): Unidade de medida ou apresentação informada adjacente ao número (ex: `"KG"`, `"bisnaga"`, `"garrafa"`, `"forma"`). Deve ser `null` se nenhuma unidade for descrita (ex: *"Quero 2 provolones"*).
    *   **`unit_origin`** (String, enum: `EXPLICIT`, `INFERRED`, `NOT_INFORMED`):
        *   `EXPLICIT`: Unidade dita textualmente.
        *   `INFERRED`: Derivada sintaticamente da estrutura gramatical.
        *   `NOT_INFORMED`: Unidade não informada de forma alguma.
*   **`explicit_presentation`** (String ou `null`, Obrigatório): Tipo de formato físico ou embalagem dita de forma explícita pelo cliente (ex: `"bisnaga"`, `"forma"`, `"saco"`, `"pote"`, `"peça"`, `"cartela"`, `"balde"`). Deve ser `null` se nenhuma apresentação for explicitada.
*   **`explicit_brand`** (String ou `null`, Obrigatório): Nome bruto da marca dita explicitamente (ex: `"Catupiry"`, `"Coyote"`, `"Larisol"`, `"Roseli"`). Deve ser `null` se a marca não for descrita na mensagem.
*   **`contextual_references`** (Array of Strings, Obrigatório): Lista de deíticos ou termos que remetam a histórico ou mensagens anteriores (ex: `["daquele"]`, `["o de costume"]`, `["do outro"]`, `["mais"]`). Se inexistirem, retorna `[]`.
*   **`missing_information`** (Array of Strings, Obrigatório): Lacunas linguísticas/semânticas exclusivamente necessárias para a correspondência do produto contra o catálogo.
    *   *Valores permitidos:* `"brand"` (falta marca), `"presentation"` (falta apresentação para desempate), `"quantity"` (pedido sem quantidade), `"unit"` (quantidade sem unidade física), `"product_specification"` (nome do produto muito genérico).
    *   **Não deve conter** lacunas financeiras, comerciais ou operacionais de retaguarda (como `"condicao_pagamento"`, `"faturamento"`, `"logistica"`, `"estoque"`, etc.). Se a resolução do produto for completa, retorna `[]`.
*   **`catalog_candidates`** (Array of Strings, Obrigatório): Códigos SKU cadastrados (`CQ-XX`) mapeados após cruzamento semântico com os aliases. Se não houver candidatos compatíveis, retorna `[]`.
*   **`product_resolution_status`** (String, Obrigatório): Status linguístico final da resolução do produto.
    *   `EXACT_MATCH`: Aponta exclusivamente para um único SKU do catálogo.
    *   `HIGH_CONFIDENCE`: Encontrou um candidato muito provável a partir de tradução de alias ou fonética.
    *   `AMBIGUOUS`: Mapeou múltiplos candidatos do catálogo e necessita de desambiguação linguística.
    *   `NOT_FOUND`: Nenhum SKU correspondente ou provável localizado.

---

## C. REGRAS DE INTERPRETAÇÃO

1.  **Preservação Semântica Inviolável:** O interpretador deve representar estritamente e somente o que foi dito pelo cliente. Ele **nunca** deve tentar resolver problemas operacionais ou completar informações faltantes por conta própria.
2.  **Separação de Proveniência:** Quantidade e unidade são tratadas de forma isolada. A frase *"quero duas manteigas"* possui `value = 2.0` (origem `EXPLICIT`), mas `unit = null` (origem `NOT_INFORMED`). A IA nunca deve assinalar automaticamente `"KG"` ou `"unidade"` por dedução do catálogo.
3.  **Não-Interferência Comercial:** Condições de faturamento, prazos, preços, meios de pagamento ou status do estoque não entram na análise semântica e são completamente ignorados pelo interpretador de NLP.
4.  **Ausência de Suposições Físicas:** O interpretador não calcula equivalências operacionais, não deduz conversões de KG para blocos ou formas de queijo, e não converte multiplicadores de caixas de atacado (`8 x 1.2kg`) em unidades soltas.

---

## D. LIMITES DE RESPONSABILIDADE

*   **Responsabilidade da IA (Interpretador):**
    *   Extrair intenções lógicas do diálogo.
    *   Aferir e rotular termos de produtos, marcas e formatos textuais.
    *   Documentar as deíticos contextuais.
    *   Fornecer a lista crua de candidatos compatíveis com base em aliases semânticos.
    *   Catalogar lacunas puramente linguísticas na fala.
*   **Responsabilidade da Aplicação (Motor Determinístico Back-End):**
    *   Realizar qualquer cálculo aritmético, soma de totais e aplicação de tabelas de preços à vista ou a prazo.
    *   Validar limites de crédito e aprovações financeiras.
    *   Converter KG para formas físicas, blocos ou peças no romaneio.
    *   Verificar saldos reais de estoque físico no galpão.
    *   Resolver exceções logísticas de transporte e tratamento de rupturas.
    *   Redigir e disparar as respostas conversacionais de saída no WhatsApp.

---

## E. GOLDEN DATASET CONVERTIDO v1.1

A suíte completa contendo **todos os 30 casos de teste adversariais** foi convertida e validada integralmente contra o novo schema V1.1:

```json
[
  {
    "id_teste": "TEST-01",
    "mensagem": "Quero 10 quilos da manteiga sem sal",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "manteiga sem sal",
      "quantity": {
        "value": 10.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-29"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-02",
    "mensagem": "Me manda duas manteigas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "manteigas",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "product_specification",
        "unit"
      ],
      "catalog_candidates": [
        "CQ-28",
        "CQ-29"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-03",
    "mensagem": "Quero 6 bisnagas de Catupiry",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Catupiry",
      "quantity": {
        "value": 6.0,
        "value_origin": "EXPLICIT",
        "unit": "bisnaga",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "bisnaga",
      "explicit_brand": "Catupiry",
      "contextual_references": [],
      "missing_information": [
        "product_specification"
      ],
      "catalog_candidates": [
        "CQ-62",
        "CQ-63"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-04",
    "mensagem": "Coloca 3 provolones",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "provolones",
      "quantity": {
        "value": 3.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "brand",
        "unit"
      ],
      "catalog_candidates": [
        "CQ-44",
        "CQ-46"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-05",
    "mensagem": "Quero 5 kg daquele Brie",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Brie",
      "quantity": {
        "value": 5.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [
        "daquele"
      ],
      "missing_information": [
        "product_specification"
      ],
      "catalog_candidates": [
        "CQ-01",
        "CQ-03"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-06",
    "mensagem": "Me manda um Camembert",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Camembert",
      "quantity": {
        "value": 1.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-04"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-07",
    "mensagem": "Gorgonzola 4 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Gorgonzola",
      "quantity": {
        "value": 4.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "product_specification"
      ],
      "catalog_candidates": [
        "CQ-06",
        "CQ-07"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-08",
    "mensagem": "2 formas de Emmental de 5kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Emmental de 5kg",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "forma",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "forma",
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-10"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-09",
    "mensagem": "Quero Gruyere 12kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Gruyere",
      "quantity": {
        "value": 12.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "product_specification"
      ],
      "catalog_candidates": [
        "CQ-11",
        "CQ-12",
        "CQ-13",
        "CQ-19"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-10",
    "mensagem": "Gouda São Vicente 2 formas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Gouda",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "forma",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "forma",
      "explicit_brand": "São Vicente",
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-14"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-11",
    "mensagem": "Massa para fondue 3 caixas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Massa para fondue",
      "quantity": {
        "value": 3.0,
        "value_origin": "EXPLICIT",
        "unit": "caixa",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "caixa",
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-20"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-12",
    "mensagem": "Quero 1 Maasdam",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Maasdam",
      "quantity": {
        "value": 1.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-21"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-13",
    "mensagem": "Minas Padrão São Vicente 10 peças",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Minas Padrão",
      "quantity": {
        "value": 10.0,
        "value_origin": "EXPLICIT",
        "unit": "peça",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "peça",
      "explicit_brand": "São Vicente",
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-22"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-14",
    "mensagem": "Reino sem lata 2 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Reino sem lata",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-24"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-15",
    "mensagem": "Requeijão São Vicente",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Requeijão",
      "quantity": {
        "value": null,
        "value_origin": "NOT_INFORMED",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": "São Vicente",
      "contextual_references": [],
      "missing_information": [
        "quantity"
      ],
      "catalog_candidates": [
        "CQ-26"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-16",
    "mensagem": "Mussarela Coyote 1 caixa",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Mussarela",
      "quantity": {
        "value": 1.0,
        "value_origin": "EXPLICIT",
        "unit": "caixa",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "caixa",
      "explicit_brand": "Coyote",
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-30"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-17",
    "mensagem": "Grana Padano peça",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Grana Padano",
      "quantity": {
        "value": null,
        "value_origin": "NOT_INFORMED",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": "peça",
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "quantity",
        "brand"
      ],
      "catalog_candidates": [
        "CQ-33",
        "CQ-69"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-18",
    "mensagem": "Fatiado Villani 5",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Fatiado",
      "quantity": {
        "value": 5.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": "Villani",
      "contextual_references": [],
      "missing_information": [
        "unit"
      ],
      "catalog_candidates": [
        "CQ-35"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-19",
    "mensagem": "Mussarela bola ovo 2 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Mussarela bola ovo",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-36"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-20",
    "mensagem": "Burrata 4 potes",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Burrata",
      "quantity": {
        "value": 4.0,
        "value_origin": "EXPLICIT",
        "unit": "pote",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "pote",
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-41"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-21",
    "mensagem": "Parmesão curado 2 peças",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Parmesão curado",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "peça",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "peça",
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "product_specification"
      ],
      "catalog_candidates": [
        "CQ-42",
        "CQ-43"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-22",
    "mensagem": "Ricota defumada",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Ricota defumada",
      "quantity": {
        "value": null,
        "value_origin": "NOT_INFORMED",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "quantity"
      ],
      "catalog_candidates": [
        "CQ-45"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-23",
    "mensagem": "Minas frescal Espelho D'agua 3 formas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Minas frescal Espelho D'agua",
      "quantity": {
        "value": 3.0,
        "value_origin": "EXPLICIT",
        "unit": "forma",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "forma",
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-50"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-24",
    "mensagem": "Saint Chevrollin de ervas 2",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Saint Chevrollin de ervas",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "unit"
      ],
      "catalog_candidates": [
        "CQ-51"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-25",
    "mensagem": "Feta 2 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Feta",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "KG",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": null,
      "explicit_brand": null,
      "contextual_references": [],
      "missing_information": [
        "product_specification"
      ],
      "catalog_candidates": [
        "CQ-53",
        "CQ-54"
      ],
      "product_resolution_status": "AMBIGUOUS"
    }
  },
  {
    "id_teste": "TEST-26",
    "mensagem": "Coalho Serta Norte",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Coalho",
      "quantity": {
        "value": null,
        "value_origin": "NOT_INFORMED",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": "Serta Norte",
      "contextual_references": [],
      "missing_information": [
        "quantity"
      ],
      "catalog_candidates": [
        "CQ-59"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-27",
    "mensagem": "Creme de leite Larisol 2 caixas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Creme de leite",
      "quantity": {
        "value": 2.0,
        "value_origin": "EXPLICIT",
        "unit": "caixa",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "caixa",
      "explicit_brand": "Larisol",
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-64"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-28",
    "mensagem": "Iogurte Larisol 6 garrafas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Iogurte",
      "quantity": {
        "value": 6.0,
        "value_origin": "EXPLICIT",
        "unit": "garrafa",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "garrafa",
      "explicit_brand": "Larisol",
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-65"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-29",
    "mensagem": "Requeijão Roseli 4",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Requeijão",
      "quantity": {
        "value": 4.0,
        "value_origin": "EXPLICIT",
        "unit": null,
        "unit_origin": "NOT_INFORMED"
      },
      "explicit_presentation": null,
      "explicit_brand": "Roseli",
      "contextual_references": [],
      "missing_information": [
        "unit"
      ],
      "catalog_candidates": [
        "CQ-66"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  },
  {
    "id_teste": "TEST-30",
    "mensagem": "Tomate seco Villagio 1 saco",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_term": "Tomate seco",
      "quantity": {
        "value": 1.0,
        "value_origin": "EXPLICIT",
        "unit": "saco",
        "unit_origin": "EXPLICIT"
      },
      "explicit_presentation": "saco",
      "explicit_brand": "Villagio",
      "contextual_references": [],
      "missing_information": [],
      "catalog_candidates": [
        "CQ-71"
      ],
      "product_resolution_status": "EXACT_MATCH"
    }
  }
]
```

---

## F. MATRIZ DE AUDITORIA E HISTÓRICO DE CORREÇÕES (v1 -> v1.1)

Abaixo é apresentada a auditoria detalhada de cada caso mapeado, identificando as discrepâncias de regras do contrato anterior e as devidas correções executadas nesta versão:

| Caso | Mensagem do Cliente | Problemas Identificados na v1 | Correções Realizadas na v1.1 |
| :---: | :--- | :--- | :--- |
| **TEST-01** | "Quero 10 quilos da manteiga sem sal" | Mapeava `"condicao_pagamento"` em `missing_information`. | Removida lacuna de pagamento da IA. `missing_information` = `[]`. |
| **TEST-02** | "Me manda duas manteigas" | `quantity.origin` era `"NOT_INFORMED"` e mapeava `"condicao_pagamento"`. | Separados origins: `value_origin` corrigido para `"EXPLICIT"` (pois "duas" é verbalizado), `unit_origin` = `"NOT_INFORMED"`. Limpo pagamento e unificado gaps de resolução em `["product_specification", "unit"]`. |
| **TEST-03** | "Quero 6 bisnagas de Catupiry" | Mapeava `"condicao_pagamento"` e `"nome_produto_especifico"`. | Removidos gaps comerciais. `missing_information` limitado a `["product_specification"]`. |
| **TEST-04** | "Coloca 3 provolones" | `quantity.origin` era `"NOT_INFORMED"` e mapeava `"condicao_pagamento"`. | `value_origin` corrigido para `"EXPLICIT"`. `unit_origin` = `"NOT_INFORMED"`. `missing_information` reduzido a `["brand", "unit"]`. |
| **TEST-05** | "Quero 5 kg daquele Brie" | Mapeava `"condicao_pagamento"` e `"apresentacao"`. | Removido pagamento. `missing_information` limitado a `["product_specification"]` para o desempate linguístico de Bries em KG. |
| **TEST-06** | "Me manda um Camembert" | `quantity.origin` era `"NOT_INFORMED"`, mapeava `"condicao_pagamento"` e `"unidade"`. | `value_origin` corrigido para `"EXPLICIT"` (pois "um" é verbalizado), `unit_origin` = `"NOT_INFORMED"`. Como o produto resolve diretamente para `CQ-04`, `missing_information` = `[]`. |
| **TEST-07** | "Gorgonzola 4 kg" | Mapeava `"condicao_pagamento"` e `"apresentacao"`. | Removido pagamento. `missing_information` reduzido para `["product_specification"]` (gorgonzola tipo cartela vs. tipo forma). |
| **TEST-08** | "2 formas de Emmental de 5kg" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |
| **TEST-09** | "Quero Gruyere 12kg" | `quantity.origin` era `"NOT_INFORMED"`, mapeava `"unidade_comercial"` e `"condicao_pagamento"`. | `value_origin` = `"EXPLICIT"` (12.0), `unit_origin` = `"EXPLICIT"` ("KG"). `product_term` = "Gruyere" para representar a ambiguidade com os demais Gruyeres do catálogo (CQ-11, CQ-12, CQ-13, CQ-19). `missing_information` = `["product_specification"]`. Status de Resolução alterado para `AMBIGUOUS`. |
| **TEST-10** | "Gouda São Vicente 2 formas" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |
| **TEST-11** | "Massa para fondue 3 caixas" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |
| **TEST-12** | "Quero 1 Maasdam" | `quantity.origin` era `"NOT_INFORMED"`, mapeava `"unidade"` e `"condicao_pagamento"`. | `value_origin` corrigido para `"EXPLICIT"`. `unit_origin` = `"NOT_INFORMED"`. `missing_information` = `[]` (resolução direta do único Maasdam `CQ-21`). |
| **TEST-13** | "Minas Padrão São Vicente 10 peças" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |
| **TEST-14** | "Reino sem lata 2 kg" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |
| **TEST-15** | "Requeijão São Vicente" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `["quantity"]`. |
| **TEST-16** | "Mussarela Coyote 1 caixa" | Mapeava `"condicao_pagamento"`. | Removido faturamento. `missing_information` = `[]`. |
| **TEST-17** | "Grana Padano peça" | `quantity.value` era `1.0` por suposição arbitrária, mapeava `"condicao_pagamento"`. | Corrigido para `value = null`, `value_origin` = `"NOT_INFORMED"`, `unit_origin` = `"NOT_INFORMED"`. `missing_information` reduzido para `["quantity", "brand"]` (desempate entre marcas). |
| **TEST-18** | "Fatiado Villani 5" | `quantity.origin` era `"NOT_INFORMED"` e mapeava `"condicao_pagamento"`. | `value_origin` = `"EXPLICIT"`. `unit_origin` = `"NOT_INFORMED"`. `missing_information` reduzido a `["unit"]`. |
| **TEST-19** | "Mussarela bola ovo 2 kg" | Mapeava `"condicao_pagamento"`. | Removido faturamento. `missing_information` = `[]`. |
| **TEST-20** | "Burrata 4 potes" | Mapeava `"condicao_pagamento"`. | Removido faturamento. `missing_information` = `[]`. |
| **TEST-21** | "Parmesão curado 2 peças" | Mapeava `"condicao_pagamento"` e `"marca"`. | Removido pagamento. `missing_information` limitado a `["product_specification"]` (desempate de fracionado vs. forma). |
| **TEST-22** | "Ricota defumada" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` limitado a `["quantity"]`. |
| **TEST-23** | "Minas frescal Espelho D'agua 3 formas" | Mapeava `"condicao_pagamento"`. | Removido faturamento. `missing_information` = `[]`. |
| **TEST-24** | "Saint Chevrollin de ervas 2" | `quantity.origin` era `"NOT_INFORMED"` e mapeava `"condicao_pagamento"`. | `value_origin` = `"EXPLICIT"`. `unit_origin` = `"NOT_INFORMED"`. `missing_information` limitado a `["unit"]`. |
| **TEST-25** | "Feta 2 kg" | Mapeava `"condicao_pagamento"` e `"apresentacao"`. | Removido pagamento. `missing_information` limitado a `["product_specification"]` (fração vs. forma). |
| **TEST-26** | "Coalho Serta Norte" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` limitado a `["quantity"]`. |
| **TEST-27** | "Creme de leite Larisol 2 caixas" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |
| **TEST-28** | "Iogurte Larisol 6 garrafas" | Mapeava `"condicao_pagamento"`. | Removido faturamento. `missing_information` = `[]`. |
| **TEST-29** | "Requeijão Roseli 4" | `quantity.origin` era `"NOT_INFORMED"` e mapeava `"condicao_pagamento"`. | `value_origin` = `"EXPLICIT"`. `unit_origin` = `"NOT_INFORMED"`. `missing_information` limitado a `["unit"]`. |
| **TEST-30** | "Tomate seco Villagio 1 saco" | Mapeava `"condicao_pagamento"`. | Removido pagamento. `missing_information` = `[]`. |


## G. REGRAS SINTÁTICAS ADICIONAIS (CONSOLIDANTE v1.1.1)

Como resultado da microauditoria de congelamento, duas regras complementares foram adicionadas à especificação de NLP para eliminar hipóteses não-declaradas:

1. **Regra de Qualificação de Apresentação vs. Unidade de Quantidade (Diferenciação Peça vs. Quantidade):**
   * **Se o termo de apresentação** (como `"peça"`, `"forma"`, `"bisnaga"`, `"bloco"`, `"garrafa"`) aparecer isolado na mensagem, sem associação sintática direta com um numeral precedente, ele deve ser classificado unicamente como `explicit_presentation` (com quantidade `value = null` e `value_origin = "NOT_INFORMED"`).
     * *Exemplo:* `"Grana Padano peça"` $\rightarrow$ `explicit_presentation = "peça"`, `quantity.value = null`, `quantity.value_origin = "NOT_INFORMED"`.
   * **Se o termo for precedido ou associado diretamente** a um numeral ou palavra de contagem (como *"2 peças"*, *"um bloco"*, *"três formas"*), o numeral correspondente vira `quantity.value` com origem `EXPLICIT`, e o termo de apresentação é extraído em `quantity.unit` com origem `EXPLICIT`.
     * *Exemplo:* `"2 peças de Grana Padano"` $\rightarrow$ `quantity.value = 2.0`, `quantity.value_origin = "EXPLICIT"`, `quantity.unit = "peça"`, `quantity.unit_origin = "EXPLICIT"`.

2. **Regra de Ambiguidade de Peso no Nome do Produto:**
   * Se um peso nominal fizer parte da descrição usual do catálogo e o cliente escrever apenas essa expressão (ex: `"Gruyere 12kg"`), o interpretador linguístico **não deve** deduzir de forma cega a quantidade de `1` unidade física daquele SKU.
   * O interpretador deve extrair a quantidade explícita (`value = 12.0`, `unit = "KG"`, origens = `EXPLICIT`) e manter o `product_term` como o nome base (`"Gruyere"`), deixando os candidatos associados como `["CQ-11", "CQ-12", "CQ-13", "CQ-19"]` com o status de resolução **`AMBIGUOUS`**. Isto obriga o motor de regras a solicitar a confirmação física ou de variedade ao cliente, evitando erros de faturamento.

---

## H. VEREDITO FINAL DE CONGELAMENTO (FREEZE VERDICT)

A microauditoria foi realizada de forma exaustiva e todos os 30 casos do Golden Dataset foram sanitizados. Com a remoção da inferência cega de quantidade do `TEST-09`, o alinhamento da regra sintática de qualificação de apresentação do `TEST-17` e o ajuste dos conceitos de desambiguação do `TEST-07`, declaramos o seguinte veredito técnico:

**VEREDITO:** 🟢 **FREEZE_APROVADO**

Este documento e sua respectiva suíte de testes em JSON estão oficialmente congelados e homologados sob a designação final **CONTRATO DO INTERPRETADOR SEMÂNTICO v1.1.2 — FROZEN**. Qualquer alteração de contrato posterior deverá iniciar um novo fluxo de versionamento (`v1.2` ou superior).
