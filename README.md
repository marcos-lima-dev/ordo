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