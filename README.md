# Ordo

**Conversational Order Intelligence Engine**

Ordo é um motor para transformar conversas comerciais em operações estruturadas de pedido.

O projeto nasce a partir de um caso real da **Casa dos Queijos**, onde vendedores recebem pedidos principalmente por WhatsApp em linguagem natural, informal, incremental e frequentemente ambígua.

A premissa central do projeto é:

> **A conversa deixa de ser o pedido. A conversa produz um pedido.**

---

## Problema

Pedidos comerciais recebidos por WhatsApp possuem características difíceis de tratar diretamente por sistemas tradicionais:

* linguagem informal;
* abreviações;
* erros de digitação;
* produtos mencionados parcialmente;
* marcas omitidas;
* unidades omitidas;
* alterações incrementais;
* referências a mensagens anteriores;
* múltiplos produtos em uma conversa;
* ambiguidades entre produto, apresentação e quantidade.

Exemplo:

```text
Me manda duas manteigas
```

A mensagem contém uma quantidade explícita (`2`), mas não informa necessariamente:

* qual manteiga;
* qual marca;
* qual unidade física.

O sistema não deve completar essas informações arbitrariamente.

---

## Princípio arquitetural

O Ordo separa interpretação probabilística de execução determinística.

```text
IA interpreta
     ↓
Catálogo fornece candidatos
     ↓
Software valida
     ↓
Incerteza é explicitada
     ↓
Regras determinísticas executam
```

Princípio:

> **IA interpreta. Software decide e executa.**

A IA não deve:

* inventar produtos;
* inventar unidades;
* calcular preços;
* escolher condições comerciais;
* consultar ou presumir estoque;
* converter automaticamente kg em peças, blocos ou caixas;
* executar alterações de pedido sem validação.

O contrato atual define o interpretador como um tradutor cognitivo cuja responsabilidade é transformar mensagens brutas em dados semânticos estruturados.

---

## Arquitetura conceitual

```text
Cliente / WhatsApp
        ↓
Semantic Interpreter
        ↓
Product Resolver
        ↓
Request Validator
        ↓
Order State Engine
        ↓
Commercial Rules
        ↓
Structured Order
```

### Semantic Interpreter

Responsável pela interpretação linguística.

Exemplos de dados:

```text
intent
product_term
quantity.value
quantity.value_origin
quantity.unit
quantity.unit_origin
explicit_presentation
explicit_brand
contextual_references
```

O contrato atual possui tipagem e enums formais para esses campos.

### Product Resolver

Responsável por relacionar o termo interpretado aos produtos disponíveis no catálogo.

Possíveis estados:

```text
EXACT_MATCH
HIGH_CONFIDENCE
AMBIGUOUS
NOT_FOUND
```

### Request Validator

Determina se a solicitação pode seguir para execução ou se precisa de esclarecimento.

A identificação de um produto não significa automaticamente que a operação solicitada seja válida.

### Deterministic Engine

Responsável por:

* preços;
* cálculos;
* condições comerciais;
* estoque;
* conversões físicas;
* crédito;
* regras operacionais;
* estado do pedido.

Essas responsabilidades estão explicitamente fora da camada NLP.

---

# Fase atual

## FASE 1 — Foundation

Objetivo:

Transformar as especificações e bases atualmente documentadas em artefatos estruturados, versionáveis e consumíveis por software.

### Entregáveis

```text
/contracts
  semantic_interpreter_v1_1_2.schema.json

/data
  catalog.json
  aliases.json

/tests
  golden_dataset.jsonl
```

---

## Contrato congelado

Versão atual:

```text
CONTRATO DO INTERPRETADOR SEMÂNTICO v1.1.2 — FROZEN
```

Alterações futuras incompatíveis devem gerar nova versão do contrato.

O contrato define formalmente que quantidade e unidade possuem proveniência independente, permitindo distinguir informação explícita, inferida e não informada.

---

## Golden Dataset

A primeira versão do Golden Dataset possui 30 casos adversariais de interpretação.

Esses casos serão usados inicialmente para:

* regressão;
* desenvolvimento do benchmark;
* avaliação de modelos;
* comparação entre abordagens determinísticas e probabilísticas.

Os testes congelados estão incorporados ao contrato atual.

O Golden Dataset não representa ainda qualidade de produção.

Ele é a primeira suíte controlada para experimentação.

---

## Filosofia de avaliação

O sistema será desenvolvido de forma **model-agnostic**.

Nenhum modelo será incorporado à arquitetura antes de ser avaliado empiricamente.

Candidatos podem incluir:

```text
Tucano
outros SLMs/LLMs
parser determinístico
arquiteturas híbridas
```

Todos serão avaliados contra o mesmo contrato e os mesmos datasets.

Um erro de falsa certeza é considerado mais grave que uma solicitação de esclarecimento.

Exemplo:

```text
Cliente:
"Quero 2 provolones"

Ruim:
EXACT_MATCH → SKU arbitrário

Preferível:
AMBIGUOUS
```

---

# Roadmap

## FASE 1 — Foundation

* schema executável;
* catálogo normalizado;
* aliases estruturados;
* Golden Dataset.

## FASE 2 — Benchmark Infrastructure

* benchmark runner;
* validação JSON Schema;
* scoring campo a campo;
* relatórios de erro.

## FASE 3 — Baselines

* parser determinístico;
* primeiro SLM;
* comparação de modelos.

## FASE 4 — Architecture Decision

Definir empiricamente:

* o que pertence ao modelo;
* o que pertence ao resolver;
* o que pertence ao motor determinístico.

## FASE 5 — Robustness

Expandir datasets com:

* variações linguísticas;
* erros de digitação;
* abreviações;
* múltiplos produtos;
* alterações de pedidos;
* referências contextuais;
* conversas reais anonimizadas.

## FASE 6 — Order Engine

Implementar:

* estado do pedido;
* itens;
* alteração;
* remoção;
* regras comerciais;
* cálculo;
* validação.

## FASE 7 — MVP

Fluxo operacional:

```text
WhatsApp
   ↓
Ordo
   ↓
Pedido estruturado
   ↓
Operação / Separação
```

---

# Status

```text
Semantic Contract      FROZEN
Golden Dataset         v0
Benchmark Runner       TODO
Deterministic Baseline TODO
Model Benchmark        TODO
Order Engine           TODO
WhatsApp Integration   TODO
```

---

## Regra de engenharia

> **Não construímos o Ordo ao redor de um modelo.
> O modelo é um componente substituível do Ordo.**
