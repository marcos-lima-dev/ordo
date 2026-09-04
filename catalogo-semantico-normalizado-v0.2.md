# CATÁLOGO SEMÂNTICO NORMALIZADO v0.2
**ESPECIFICAÇÃO DE ENGENHARIA SEMÂNTICA DO CATÁLOGO — CASA DOS QUEIJOS**

Este documento consolida a arquitetura, schemas, regras operacionais e testes de validação para a normalização do catálogo da distribuidora **Casa dos Queijos** [31]. O objetivo desta especificação é servir como a "camada inteligente" (NLP) que converte linguagem humana e mensagens informais (especialmente do WhatsApp) em dados comerciais estruturados, compatíveis com as regras determinísticas e faturamento fiscal do negócio [31, 41].

---

## 1. DIAGNÓSTICO DO CSV (AUDITORIA DA ESTRUTURA DO CATÁLOGO)

A análise minuciosa de todas as linhas da tabela original de Janeiro de 2024 revela que a base é um instrumento puramente comercial e visual, repleto de irregularidades e ambiguidades estruturais que impedem sua leitura direta por sistemas automatizados [31, 43]:

1. **Mistura de Entidades nas Colunas:**
   * **Marca em Cabeçalhos:** A tabela original usa linhas isoladas apenas com o nome do fabricante como um separador visual (ex: `SÃO VICENTE`, `COYOTE`, `GRAN PARMA`) [43]. Esses nomes de marcas não estão associados aos produtos em cada registro individual, o que causa a perda da informação do fabricante quando os dados são filtrados [33, 43].
   * **Marcas Embutidas nos Nomes:** Sob a seção `PRODUTOS DIVERSOS`, as marcas estão escritas dentro do próprio nome do produto (ex: `Cream cheese Polenghi balde`, `Cream Cheese Catupiry`, `Cream Cheese Roseli bisnaga 1,2kg`, `Creme de Leite fresco 35% Larisol`) [43].
   * **Unidades Físicas na Descrição:** Características físicas e pesos aparecem amalgamados ao texto do nome (ex: `Emmental São Vicente forma 12 kg`, `Grana Padano Gran Mestri 16 KG`, `Maturado Forma Seritinga 5 kg`) [43].
   * **Irregularidades no Campo "PESO":** O campo apresenta representações variadas que misturam quantidade de faturamento, quantidade física secundária e peso. Por exemplo:
     * Multiplicadores de caixa fechada (ex: `3 x 1,1kg`, `8 x 125g`, `36 x 160g`, `24 x 0,250`, `6 x 1,006kg`) [43].
     * Representação de pesos unitários flutuantes sem indicativo de unidade (ex: `0,5` para Mussarela bola 40g, `0,2` para Burrata) [43].
     * Unidades misturadas (ex: `0,500g` para Minas Padrão Riqueza e Mussarela bola 10G; `0,3 kg` para Ricota fresca 200g; `12 KG` para Maasdam) [43].
     * String irregular `1 x 10 110g` para Emmental/Gouda/Gruyere Skin Pack 220g [43].
     * Espaços e caracteres soltos (ex: `2, kg`, `3,kg`) [43].

2. **Divergências na Coluna "UND" (Unidade de Venda):**
   * A unidade de precificação comercial às vezes contradiz a apresentação física. Por exemplo, `MAASDAM FORMA 12 KG` possui `UND` cadastrado como `FORMA` [43], enquanto outros itens vendidos em formas inteiras (como `Emmental` ou `Gruyere`) possuem `UND` cadastrado como `KG` [43]. Isso gera confusão sobre se o faturamento é por unidade ou por peso real na balança [7].

3. **Inconsistências de Grafia e Erros de Digitação:**
   * Foram identificadas palavras escritas com erros de grafia que dificultam buscas por palavra-chave simples, exigindo correspondência semântica ou fonética. Exemplos: `Mnas Padrao Riqueza` (falta a letra "i" em Minas) [43], `Requeijaõ Roseli` (acordo ortográfico e til na posição incorreta) [43].

4. **Metadados Soltos e Ruídos:**
   * A linha final da planilha apresenta valores como `76` na coluna 7 e registros vazios que precisam ser descartados na sanitização de dados [43].

---

## 2. SCHEMA NORMALIZADO v0.2 (ARQUITETURA DE DADOS CORRIGIDA)

Para eliminar os problemas identificados e atender às prioridades de auditoria, estabelecemos uma arquitetura de dados com tipagem forte e separação rígida das características físicas e unidades comerciais [34, 40]:

### Atributos do Schema do Catálogo Normalizado

1. `product_id` (String - Chave Primária): Identificador exclusivo do produto no formato `CQ-XX`.
2. `original_name` (String): Nome bruto conforme extraído da tabela comercial de Janeiro de 2024.
3. `normalized_name` (String): Nome comercial limpo e padronizado, livre de erros ortográficos e ruídos.
4. `brand` (String): Marca oficial do fabricante (ex: `São Vicente`, `Coyote`, `Catupiry`).
5. `unidade_precificacao` (String): Unidade oficial para faturamento e cálculo do preço na tabela (`KG`, `UND` ou `FORMA`) [6, 43].
6. `apresentacao_individual` (String): Forma física ou apresentação de uma única unidade (ex: `forma`, `barra`, `bloco`, `bisnaga`, `peça`, `cartela`, `pote`, `saco`, `fração`, `vácuo`, `balde`, `pacote`, etc.) [7, 8].
7. `peso_referencia_individual` (String): O peso de referência ou nominal de uma única unidade individual (ex: `1.100 kg` para Brie forma, `0.115 kg` para Brie triângulo, `1.200 kg` para Cream Cheese Catupiry).
8. `embalagem_master` (String): O tipo de embalagem agregadora utilizada no transporte e atacado (ex: `caixa` ou `DESCONHECIDO` se não especificado na fonte).
9. `quantidade_unidades_master` (Integer/String): Quantidade de unidades físicas individuais contidas na embalagem master de atacado (ex: 3, 8, 12, ou `NÃO INFORMADO` se não for aplicável/especificado).
10. `preco_vista` (String): Preço comercial unitário na condição de pagamento à vista/cartão [43].
11. `preco_prazo` (String): Preço comercial unitário na condição de pagamento faturado a prazo (7dd/14dd) [43].

### Diretrizes de Unidades e Multiplicadores (Sem Suposição Automática de Venda)
* **Embalagens Master (ex: Caixas):** Multiplicadores como `8 x 1,2kg` ou `12 x 1,1kg` contidos na coluna `PESO` representam a distribuição logística do fabricante, e **NÃO** constituem prova ou autorização de que "caixa" é uma unidade de medida aceita para venda direta no catálogo.
* **Status de Unidade Desconhecida:** Caso o cliente faça um pedido expressando quantidades em "caixas" (ex: "2 caixas de requeijão"), a IA de NLP **não deve** converter automaticamente esse pedido para unidades individuais ou KG sem confirmação explícita do cliente sobre a quantidade pretendida. O sistema deve emitir o status **AMBIGUOUS** ou **NECESSITA CONFIRMAÇÃO**.

---

## 3. CATÁLOGO NORMALIZADO COMPLETO (77 PRODUTOS DO CSV)

Abaixo é apresentada a normalização estrita de **todos os 77 produtos válidos** mapeados no CSV comercial da distribuidora [43], separando rigorosamente cada campo físico e comercial:

| ID | Nome Normalizado | Marca | UND Preço | Apres. Individual | Peso Ref. Individual | Embalagem Master | Qty Master | Preço À Vista | Preço Prazo |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| CQ-01 | Brie forma | São Vicente | KG | forma | 1.100 kg | DESCONHECIDO | 3 | R$ 59.54 | R$ 60.91 |
| CQ-02 | Brie triangulo | São Vicente | UND | triângulo | 0.115 kg | caixa | 8 | R$ 8.22 | R$ 8.41 |
| CQ-03 | Brie Specialitte (Montagnar) | São Vicente | KG | forma | 3.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 76.22 | R$ 77.37 |
| CQ-04 | Camembert | São Vicente | UND | peça | 0.125 kg | caixa | 8 | R$ 9.98 | R$ 10.21 |
| CQ-05 | Camembleu | São Vicente | KG | peça | 0.125 kg | DESCONHECIDO | 8 | R$ 11.14 | R$ 11.40 |
| CQ-06 | Queijo Azul cartão (tipo gorgonzola) | São Vicente | KG | cartela | 0.160 kg | DESCONHECIDO | 36 | R$ 54.46 | R$ 55.28 |
| CQ-07 | Queijo Azul forma (tipo gorgonzola) | São Vicente | KG | forma | 3.100 kg | DESCONHECIDO | 2 | R$ 51.61 | R$ 52.80 |
| CQ-08 | Emmental São Vicente forma 12 kg | São Vicente | KG | forma | 12.000 kg | DESCONHECIDO | 1 | R$ 69.25 | R$ 70.85 |
| CQ-09 | Emmental São Vicente barra 3 kg | São Vicente | KG | barra | 3.000 kg | DESCONHECIDO | 2 | R$ 73.02 | R$ 74.12 |
| CQ-10 | Emmental São Vicente forma 5 kg | São Vicente | KG | forma | 5.000 kg | DESCONHECIDO | 1 | R$ 71.42 | R$ 72.50 |
| CQ-11 | Gruyere Forma São Vicente 12kg | São Vicente | KG | forma | 12.000 kg | DESCONHECIDO | 1 | R$ 71.42 | R$ 73.07 |
| CQ-12 | Gruyere Forma São Vicente 6 kg | São Vicente | KG | forma | 6.000 kg | DESCONHECIDO | 1 | R$ 73.06 | R$ 73.06 |
| CQ-13 | Gruyere Forma São Vicente barra 3kg | São Vicente | KG | barra | 3.000 kg | DESCONHECIDO | 2 | R$ 74.47 | R$ 75.59 |
| CQ-14 | Gouda São Vicente | São Vicente | KG | forma | 3.000 kg | DESCONHECIDO | 2 | R$ 66.23 | R$ 67.23 |
| CQ-15 | Gouda Provence | São Vicente | KG | forma | 3.000 kg | DESCONHECIDO | 2 | R$ 72.87 | R$ 73.97 |
| CQ-16 | Gouda Tomate seco | São Vicente | KG | saco | 1.250 kg | caixa | 12 | R$ 73.54 | R$ 74.64 |
| CQ-17 | Emmental Skin Pack 220g | São Vicente | UND | unidade | 0.220 kg | caixa | DESCONHECIDO | R$ 9.54 | R$ 9.68 |
| CQ-18 | Gouda Skin Pack 220g | São Vicente | UND | unidade | 0.220 kg | caixa | DESCONHECIDO | R$ 9.54 | R$ 9.68 |
| CQ-19 | Gruyere Skin Pack 220g | São Vicente | UND | unidade | 0.220 kg | caixa | DESCONHECIDO | R$ 9.54 | R$ 9.68 |
| CQ-20 | Massa para fondue tradicional | São Vicente | UND | unidade | 0.400 kg | caixa | 6 | R$ 20.91 | R$ 21.22 |
| CQ-21 | MAASDAM FORMA 12 KG | São Vicente | FORMA | forma | 12.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 77.58 | R$ 78.75 |
| CQ-22 | Minas Padrão São vicente | São Vicente | KG | forma | 0.250 kg | DESCONHECIDO | 24 | R$ 52.46 | R$ 53.24 |
| CQ-23 | Esferico São Vicente | São Vicente | KG | forma | 2.000 kg | DESCONHECIDO | 4 | R$ 39.90 | R$ 40.50 |
| CQ-24 | Reino bola sem lata | São Vicente | KG | forma | 1.000 kg | DESCONHECIDO | 4 | R$ 66.14 | R$ 67.14 |
| CQ-25 | Reino bola lata | São Vicente | KG | forma | 1.000 kg | DESCONHECIDO | 12 | R$ 81.32 | R$ 82.54 |
| CQ-26 | REQUEIJAO SÃO VICENTE | São Vicente | UND | bisnaga | 1.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 47.88 | R$ 48.60 |
| CQ-27 | Queijo processado sabor cheddar | São Vicente | UND | bisnaga | 1.006 kg | caixa | 6 | R$ 51.87 | R$ 53.07 |
| CQ-28 | Manteiga c/sal | Coyote | KG | bloco | 5.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 41.23 | R$ 41.85 |
| CQ-29 | Manteiga s/sal | Coyote | KG | bloco | 5.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 41.23 | R$ 41.85 |
| CQ-30 | Mussarela | Coyote | KG | vácuo | 4.000 kg | DESCONHECIDO | 6 | R$ 33.25 | R$ 33.75 |
| CQ-31 | Grana  1/2 FORMA | Gran Parma | KG | meia forma | 16.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 107.60 | R$ 109.22 |
| CQ-32 | Grana 1/8 | Gran Parma | KG | forma | 4.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 107.60 | R$ 109.22 |
| CQ-33 | Grana Padano | Gran Parma | KG | peça | 0.200 kg | DESCONHECIDO | NÃO INFORMADO | R$ 121.36 | R$ 123.19 |
| CQ-34 | PRESUNTO CRU MEC 6 KG | Villani | KG | forma | 6.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 130.21 | R$ 132.17 |
| CQ-35 | PRESUNTO FATIADA 250G | Villani | UND | peça | 0.250 kg | DESCONHECIDO | 12 | R$ 43.74 | R$ 44.40 |
| CQ-36 | Mussarela Bola Ovo s/ soro | Bianco Latte | KG | vácuo | 0.370 kg | DESCONHECIDO | 28 | R$ 74.88 | R$ 76.01 |
| CQ-37 | Mussarela Bola Cereja s/ soro | Bianco Latte | KG | vácuo | 0.370 kg | DESCONHECIDO | 28 | R$ 74.88 | R$ 76.01 |
| CQ-38 | Mussarela Forma Barra | Bianco Latte | KG | forma | 3.000 kg | DESCONHECIDO | 8 | R$ 60.58 | R$ 61.49 |
| CQ-39 | Mussarela no soro bola 40g | Borghese | UND | pacote | 0.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 33.62 | R$ 34.13 |
| CQ-40 | Mussarela no soro bola 10G | Borghese | UND | pacote | 0.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 33.62 | R$ 34.13 |
| CQ-41 | BURRATA 200G | Borghese | UND | pote | 0.200 kg | DESCONHECIDO | NÃO INFORMADO | R$ 21.48 | R$ 21.80 |
| CQ-42 | Parmesão curado | Tânia | KG | fração | 0.250 kg | DESCONHECIDO | 40 | R$ 71.16 | R$ 72.23 |
| CQ-43 | Parmesão curado | Tânia | KG | forma | 7.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 66.37 | R$ 67.37 |
| CQ-44 | Provolone curado defumado | Tânia | KG | forma | 5.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 52.54 | R$ 53.33 |
| CQ-45 | Ricota defumada s/ pimenta | Tânia | KG | peça | 1.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 35.11 | R$ 35.64 |
| CQ-46 | Provolone forma 5 kg | Riqueza De Minas | KG | forma | 5.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 47.88 | R$ 48.60 |
| CQ-47 | Mnas Padrao Riqueza | Riqueza De Minas | KG | peça | 0.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 46.55 | R$ 47.25 |
| CQ-48 | Ricota fresca 200g | Riqueza De Minas | KG | peça | 0.300 kg | DESCONHECIDO | NÃO INFORMADO | R$ 17.96 | R$ 18.23 |
| CQ-49 | Parmesão Tropical | Riqueza De Minas | KG | forma | 5.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 45.22 | R$ 45.90 |
| CQ-50 | Minas frescal Espelho D'agua | Riqueza De Minas | KG | forma | 0.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 29.26 | R$ 29.70 |
| CQ-51 | Saint Chevrollin (Tipo BOURSIN) c/ ervas finas | Cabriola | UND | balde | 1.000 kg | caixa | 4 | R$ 104.94 | R$ 106.52 |
| CQ-52 | Saint Chevrollin (Tipo BOURSIN) natural  (pasta) | Cabriola | UND | pote | 1.000 kg | caixa | 4 | R$ 88.45 | R$ 89.78 |
| CQ-53 | Feta fracionado | Cabriola | KG | fração | 0.150 kg | DESCONHECIDO | NÃO INFORMADO | R$ 140.45 | R$ 142.56 |
| CQ-54 | Feta forma | Cabriola | KG | forma | 1.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 131.54 | R$ 133.52 |
| CQ-55 | Frescal pote | Cabriola | KG | pote | 0.250 kg | DESCONHECIDO | NÃO INFORMADO | R$ 80.47 | R$ 81.68 |
| CQ-56 | Cheddar | Sun Valley | KG | barra | 1.300 kg | DESCONHECIDO | 4 | R$ 62.91 | R$ 63.86 |
| CQ-57 | Tilsit c/Kümmel | Sun Valley | KG | barra | 1.300 kg | DESCONHECIDO | 4 | R$ 62.91 | R$ 63.86 |
| CQ-58 | Cream cheese Polenghi balde | DESCONHECIDO | UND | balde | 3.600 kg | DESCONHECIDO | 1 | R$ 159.93 | R$ 162.34 |
| CQ-59 | Coalho barra  Serta Norte 2 kg | DESCONHECIDO | KG | forma | 2.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 47.88 | R$ 48.60 |
| CQ-60 | Ricota Estrela da Mantiqueira | DESCONHECIDO | KG | peça | 0.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 17.29 | R$ 17.55 |
| CQ-61 | PARMESAO Estrela da Mantiqueira | DESCONHECIDO | KG | peça | 5.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 47.88 | R$ 48.60 |
| CQ-62 | Cream Cheese Catupiry | DESCONHECIDO | UND | bisnaga | 1.200 kg | caixa | 8 | R$ 43.15 | R$ 43.79 |
| CQ-63 | Requeijão Catupiry | DESCONHECIDO | UND | bisnaga | 1.500 kg | caixa | 12 | R$ 59.90 | R$ 60.80 |
| CQ-64 | Creme de Leite fresco 35% Larisol | DESCONHECIDO | UND | garrafa | 1.100 kg | caixa | 12 | R$ 35.18 | R$ 35.71 |
| CQ-65 | Iogurte Natural integral Larisol | DESCONHECIDO | UND | garrafa | 0.900 kg | caixa | 12 | R$ 10.44 | R$ 10.60 |
| CQ-66 | Requeijaõ Roseli bisnaga 1,8 kg | DESCONHECIDO | UND | bisnaga | 1.800 kg | caixa | 8 | R$ 21.84 | R$ 22.17 |
| CQ-67 | Cream Cheese Roseli bisnaga 1,2kg | DESCONHECIDO | UND | bisnaga | 1.200 kg | caixa | 12 | R$ 26.44 | R$ 26.84 |
| CQ-68 | Grana Padano Gran Mestri 16 KG | DESCONHECIDO | KG | peça | 16.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 107.80 | R$ 110.28 |
| CQ-69 | Grana Padano Gran Mestri | DESCONHECIDO | KG | peça | 0.150 kg | caixa | 53 | R$ 143.61 | R$ 145.77 |
| CQ-70 | Cheddar MGV Schereiber | DESCONHECIDO | KG | pacote | 2.270 kg | caixa | 8 | R$ 45.41 | R$ 46.09 |
| CQ-71 | Tomate seco Villagio | DESCONHECIDO | UND | saco | 1.250 kg | caixa | 12 | R$ 65.66 | R$ 66.65 |
| CQ-72 | Maturado Forma Seritinga 5 kg | DESCONHECIDO | KG | forma | 5.000 kg | DESCONHECIDO | 1 | R$ 68.50 | R$ 69.53 |
| CQ-73 | Coalho Forma Dona Rosa | Dona Rosa | KG | barra | 3.000 kg | caixa | 6 | R$ 40.83 | R$ 41.45 |
| CQ-74 | Prato forma | Dona Rosa | KG | forma | 3.000 kg | DESCONHECIDO | NÃO INFORMADO | R$ 37.37 | R$ 37.94 |
| CQ-75 | Parmesão 12 meses forma 5 kg Dona Rosa | Dona Rosa | KG | forma | 5.000 kg | caixa | 4 | R$ 54.13 | R$ 54.95 |
| CQ-76 | Minas Padrao meia lua | Dona Rosa | KG | peça | 0.500 kg | DESCONHECIDO | NÃO INFORMADO | R$ 49.21 | R$ 49.95 |
| CQ-77 | Esferico  forma Dona Rosa | Dona Rosa | KG | forma | 3.300 kg | DESCONHECIDO | NÃO INFORMADO | R$ 52.63 | R$ 53.42 |

---

## 4. CAMADA/DICIONÁRIO SEMÂNTICO DO CATÁLOGO (ALIASES LINGUÍSTICOS REVISADOS)

Em total conformidade com a prioridade 4 da auditoria, os aliases foram rigorosamente revisados para eliminar repetições artificiais, redundâncias desnecessárias e impropriedades linguísticas. Mantemos apenas correspondências altamente prováveis e naturais que refletem a comunicação real no WhatsApp [13, 35]:

| ID | Nome Normalizado | Marca | Apres. Individual | Aliases Linguísticos Naturais Recomendados |
| :--- | :--- | :--- | :--- | :--- |
| CQ-01 | Brie forma | São Vicente | forma | `brie forma`, `queijo brie grande`, `brie são vicente` |
| CQ-02 | Brie triangulo | São Vicente | triângulo | `brie triangulo`, `fatia de brie`, `brie pequeno` |
| CQ-03 | Brie Specialitte (Montagnar) | São Vicente | forma | `brie montagnar`, `brie specialitte`, `brie de 3kg` |
| CQ-04 | Camembert | São Vicente | peça | `camembert`, `queijo camembert` |
| CQ-05 | Camembleu | São Vicente | peça | `camembleu`, `queijo camembleu` |
| CQ-06 | Queijo Azul cartão (tipo gorgonzola) | São Vicente | cartela | `queijo azul cartela`, `gorgonzola cartela`, `azul são vicente` |
| CQ-07 | Queijo Azul forma (tipo gorgonzola) | São Vicente | forma | `queijo azul forma`, `gorgonzola forma`, `gorgonzola inteiro` |
| CQ-08 | Emmental São Vicente forma 12 kg | São Vicente | forma | `emmental de 12kg`, `emmental forma grande`, `emmental são vicente` |
| CQ-09 | Emmental São Vicente barra 3 kg | São Vicente | barra | `emmental barra`, `emmental de 3kg`, `barra de emmental` |
| CQ-10 | Emmental São Vicente forma 5 kg | São Vicente | forma | `emmental de 5kg`, `emmental forma 5kg`, `emmental são vicente` |
| CQ-11 | Gruyere Forma São Vicente 12kg | São Vicente | forma | `gruyere de 12kg`, `gruyere forma grande`, `gruyere são vicente` |
| CQ-12 | Gruyere Forma São Vicente 6 kg | São Vicente | forma | `gruyere de 6kg`, `gruyere forma 6kg`, `gruyere são vicente` |
| CQ-13 | Gruyere Forma São Vicente barra 3kg | São Vicente | barra | `gruyere barra`, `gruyere de 3kg`, `barra de gruyere` |
| CQ-14 | Gouda São Vicente | São Vicente | forma | `gouda são vicente`, `queijo gouda` |
| CQ-15 | Gouda Provence | São Vicente | forma | `gouda provence`, `gouda de ervas` |
| CQ-16 | Gouda Tomate seco | São Vicente | saco | `gouda tomate seco`, `gouda vermelho` |
| CQ-17 | Emmental Skin Pack 220g | São Vicente | unidade | `emmental fatiado`, `emmental skin pack`, `emmental 220g` |
| CQ-18 | Gouda Skin Pack 220g | São Vicente | unidade | `gouda fatiado`, `gouda skin pack`, `gouda 220g` |
| CQ-19 | Gruyere Skin Pack 220g | São Vicente | unidade | `gruyere fatiado`, `gruyere skin pack`, `gruyere 220g` |
| CQ-20 | Massa para fondue tradicional | São Vicente | unidade | `massa para fondue`, `fondue são vicente`, `queijo fondue` |
| CQ-21 | MAASDAM FORMA 12 KG | São Vicente | forma | `queijo maasdam`, `maasdam forma` |
| CQ-22 | Minas Padrão São vicente | São Vicente | forma | `minas padrão são vicente`, `queijo minas padrão` |
| CQ-23 | Esferico São Vicente | São Vicente | forma | `queijo esférico`, `esferico são vicente` |
| CQ-24 | Reino bola sem lata | São Vicente | forma | `queijo reino sem lata`, `bola de reino sem lata` |
| CQ-25 | Reino bola lata | São Vicente | forma | `queijo reino lata`, `reino na lata`, `bola de reino` |
| CQ-26 | REQUEIJAO SÃO VICENTE | São Vicente | bisnaga | `requeijão de bisnaga são vicente`, `requeijão são vicente` |
| CQ-27 | Queijo processado sabor cheddar | São Vicente | bisnaga | `queijo cheddar bisnaga`, `cheddar processado`, `cheddar de bisnaga` |
| CQ-28 | Manteiga c/sal | Coyote | bloco | `manteiga com sal`, `manteiga coyote com sal` |
| CQ-29 | Manteiga s/sal | Coyote | bloco | `manteiga sem sal`, `manteiga coyote sem sal` |
| CQ-30 | Mussarela | Coyote | vácuo | `mussarela coyote`, `peça de mussarela coyote` |
| CQ-31 | Grana  1/2 FORMA | Gran Parma | meia forma | `meia forma de grana`, `grana meio bloco`, `meia forma grana padano` |
| CQ-32 | Grana 1/8 | Gran Parma | forma | `grana um oitavo`, `grana padano 1/8`, `grana de 4kg` |
| CQ-33 | Grana Padano | Gran Parma | peça | `grana padano pedaço`, `grana padano 200g`, `grana parma` |
| CQ-34 | PRESUNTO CRU MEC 6 KG | Villani | forma | `presunto cru mec`, `presunto cru de 6kg`, `presunto cru villani` |
| CQ-35 | PRESUNTO FATIADA 250G | Villani | peça | `presunto cru fatiado`, `presunto fatiado 250g` |
| CQ-36 | Mussarela Bola Ovo s/ soro | Bianco Latte | vácuo | `mussarela bola ovo`, `mussarela de búfala ovo`, `bola ovo` |
| CQ-37 | Mussarela Bola Cereja s/ soro | Bianco Latte | vácuo | `mussarela bola cereja`, `mussarela de búfala cereja`, `bola cereja` |
| CQ-38 | Mussarela Forma Barra | Bianco Latte | forma | `mussarela barra búfala`, `mussarela forma barra` |
| CQ-39 | Mussarela no soro bola 40g | Borghese | pacote | `mussarela no soro 40g`, `búfala no soro 40g` |
| CQ-40 | Mussarela no soro bola 10G | Borghese | pacote | `mussarela no soro 10g`, `búfala no soro 10g` |
| CQ-41 | BURRATA 200G | Borghese | pote | `burrata 200g`, `burrata de búfala` |
| CQ-42 | Parmesão curado | Tânia | fração | `parmesão curado pedaço`, `parmesão curado 250g`, `parmesão tânia` |
| CQ-43 | Parmesão curado | Tânia | forma | `parmesão curado forma`, `parmesão forma grande`, `parmesão tânia inteiro` |
| CQ-44 | Provolone curado defumado | Tânia | forma | `provolone defumado`, `provolone tânia`, `provolone curado` |
| CQ-45 | Ricota defumada s/ pimenta | Tânia | peça | `ricota defumada sem pimenta`, `ricota defumada tânia` |
| CQ-46 | Provolone forma 5 kg | Riqueza De Minas | forma | `provolone de 5kg`, `provolone forma riqueza`, `provolone riqueza` |
| CQ-47 | Mnas Padrao Riqueza | Riqueza De Minas | peça | `minas padrão riqueza`, `queijo minas padrão riqueza` |
| CQ-48 | Ricota fresca 200g | Riqueza De Minas | peça | `ricota fresca`, `ricota riqueza 200g` |
| CQ-49 | Parmesão Tropical | Riqueza De Minas | forma | `parmesão tropical`, `parmesão tropical riqueza` |
| CQ-50 | Minas frescal Espelho D'agua | Riqueza De Minas | forma | `minas frescal espelho d'agua`, `minas frescal riqueza` |
| CQ-51 | Saint Chevrollin (Tipo BOURSIN) c/ ervas finas | Cabriola | balde | `saint chevrollin ervas`, `boursin de cabra ervas`, `boursin cabriola` |
| CQ-52 | Saint Chevrollin (Tipo BOURSIN) natural  (pasta) | Cabriola | pote | `saint chevrollin natural`, `boursin de cabra natural`, `boursin cabriola natural` |
| CQ-53 | Feta fracionado | Cabriola | fração | `queijo feta fracionado`, `feta de cabra fracionado` |
| CQ-54 | Feta forma | Cabriola | forma | `queijo feta forma`, `feta de cabra forma`, `forma de feta` |
| CQ-55 | Frescal pote | Cabriola | pote | `frescal de cabra`, `frescal pote cabriola` |
| CQ-56 | Cheddar | Sun Valley | barra | `cheddar sun valley`, `queijo cheddar barra` |
| CQ-57 | Tilsit c/Kümmel | Sun Valley | barra | `tilsit com kummel`, `tilsit sun valley` |
| CQ-58 | Cream cheese Polenghi balde | DESCONHECIDO | balde | `cream cheese polenghi`, `balde de cream cheese`, `cream cheese de 3.6kg` |
| CQ-59 | Coalho barra  Serta Norte 2 kg | DESCONHECIDO | forma | `coalho barra serta norte`, `queijo coalho serta norte`, `coalho de 2kg` |
| CQ-60 | Ricota Estrela da Mantiqueira | DESCONHECIDO | peça | `ricota estrela da mantiqueira`, `ricota de 500g` |
| CQ-61 | PARMESAO Estrela da Mantiqueira | DESCONHECIDO | peça | `parmesão estrela da mantiqueira`, `parmesão de 5kg` |
| CQ-62 | Cream Cheese Catupiry | DESCONHECIDO | bisnaga | `cream cheese catupiry`, `cream cheese bisnaga` |
| CQ-63 | Requeijão Catupiry | DESCONHECIDO | bisnaga | `requeijão catupiry`, `requeijão bisnaga catupiry` |
| CQ-64 | Creme de Leite fresco 35% Larisol | DESCONHECIDO | garrafa | `creme de leite fresco larisol`, `creme de leite 35%` |
| CQ-65 | Iogurte Natural integral Larisol | DESCONHECIDO | garrafa | `iogurte natural larisol`, `iogurte de garrafa` |
| CQ-66 | Requeijaõ Roseli bisnaga 1,8 kg | DESCONHECIDO | bisnaga | `requeijão roseli`, `requeijão bisnaga 1.8kg` |
| CQ-67 | Cream Cheese Roseli bisnaga 1,2kg | DESCONHECIDO | bisnaga | `cream cheese roseli`, `cream cheese bisnaga 1.2kg` |
| CQ-68 | Grana Padano Gran Mestri 16 KG | DESCONHECIDO | peça | `grana padano 16kg`, `grana gran mestri inteiro` |
| CQ-69 | Grana Padano Gran Mestri | DESCONHECIDO | peça | `grana padano gran mestri`, `grana pedaço gran mestri` |
| CQ-70 | Cheddar MGV Schereiber | DESCONHECIDO | pacote | `cheddar mqv`, `cheddar schreiber`, `cheddar pacote` |
| CQ-71 | Tomate seco Villagio | DESCONHECIDO | saco | `tomate seco villagio`, `saco de tomate seco` |
| CQ-72 | Maturado Forma Seritinga 5 kg | DESCONHECIDO | forma | `maturado seritinga`, `maturado forma 5kg` |
| CQ-73 | Coalho Forma Dona Rosa | Dona Rosa | barra | `coalho dona rosa`, `queijo coalho dona rosa` |
| CQ-74 | Prato forma | Dona Rosa | forma | `queijo prato forma`, `prato dona rosa` |
| CQ-75 | Parmesão 12 meses forma 5 kg Dona Rosa | Dona Rosa | forma | `parmesão dona rosa`, `parmesão 12 meses` |
| CQ-76 | Minas Padrao meia lua | Dona Rosa | peça | `minas padrão meia lua`, `meia lua dona rosa` |
| CQ-77 | Esferico  forma Dona Rosa | Dona Rosa | forma | `esférico dona rosa`, `esferico forma dona rosa` |

---

## 5. REGRAS OPERACIONAIS EXCLUSIVAMENTE CONHECIDAS (E LACUNAS EXPLICITADAS)

Para garantir que o motor de regras opere de forma 100% determinística e sem inventar dados, diferenciamos as informações estritamente sustentadas das lacunas de processo que devem ser catalogadas como **DESCONHECIDAS** [25, 27]:

### A. O que as Fontes Sustentam (Regras Determinísticas Conhecidas)
1. **Diferenciação de Preços por Canal de Pagamento [43]:** O preço faturado do item é estritamente ditado pelas colunas comerciais da tabela: `preco_vista` ("$ / cartão") ou `preco_prazo` ("7dd/14dd") [43]. Nenhuma outra taxa de crédito ou desconto pode ser inferida.
2. **Preservação da Mensagem Original do Cliente [2, 3]:** O sistema de NLP deve documentar o texto exato digitado pelo cliente para fins de auditabilidade e posterior revisão humana, diferenciando o que o cliente disse do que a IA interpretou.
3. **Não-Equivalência Automática de Grandezas [6, 24]:** Uma quantidade em KG não é automaticamente equivalente a um número inteiro de peças/formas, e vice-versa [26].

### B. Regras de Processo Físico e Comercial Totalmente DESCONHECIDAS
Para evitar decisões arbitrárias da IA que possam acarretar prejuízos de faturamento ou fricção com o cliente, as seguintes regras são declaradas como **DESCONHECIDAS / REGRA NÃO DEFINIDA** e devem ser resolvidas deterministicamente pelo back-end ou intervenção humana [27]:
1. **Regras de Fracionamento:** Não se sabe se a distribuidora fraciona peças fechadas (como cortar uma forma de Provolone de 5 kg para entregar 2 kg solicitados) ou se obriga o cliente a levar apenas a unidade inteira [24, 27].
2. **Margens de Tolerância na Balança:** Não existe informação sobre qual a tolerância aceitável entre o peso nominal de catálogo e o peso real aferido na balança do estoque no faturamento final do pedido [10].
3. **Políticas de Arredondamento:** Se um item de peso variável é separado e pesa mais (ex: uma forma de queijo Brie de 1,1kg pesa 1,210kg na balança), é desconhecido se o faturamento utiliza o peso real de balança de forma direta ou exige autorização prévia de recalculo de valor com o cliente via chat [3, 27].
4. **Tratamento de Rupturas de Estoque:** É desconhecido o processo de substituição automatizada de marcas ou categorias similares se um produto estiver indisponível no estoque físico do galpão [27].

---

## 6. TESTES DE INTERPRETAÇÃO SEMÂNTICA REVISADOS

Em estrito alinhamento com a prioridade 5 da auditoria, revisamos todos os 30 testes de interpretação de linguagem natural. Os resultados esperados representam **exclusivamente**:
1. O que o cliente disse (`Original Text`);
2. A interpretação semântica (`Semantics`);
3. Os candidatos encontrados no catálogo (`Candidates`);
4. Ambiguidades e informações ausentes (`Ambiguities/Missing Info`).

Não incluímos nenhuma suposição operacional, arredondamentos ou decisões automáticas de conversão de unidade [5, 22].

### Cenários Adversariais e Resultados Esperados de Interpretação (NLP)

### Casos de Teste - TEST-01
* **O que o Cliente Disse (Mensagem):** "Quero 10 quilos da manteiga sem sal"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"manteiga sem sal"`
  * `quantity_value`: `10.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-29']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada (cartão vs. prazo). Regras operacionais de pesagem, tolerância ou fracionamento de bloco de 5kg são desconhecidas.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-02
* **O que o Cliente Disse (Mensagem):** "Me manda duas manteigas"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"manteigas"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-28', 'CQ-29']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre com sal (CQ-28) e sem sal (CQ-29). Unidade de medida não informada (pode representar 2 kg, 2 blocos ou 2 caixas). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-03
* **O que o Cliente Disse (Mensagem):** "Quero 6 bisnagas de Catupiry"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Catupiry"`
  * `quantity_value`: `6.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"bisnaga"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-62', 'CQ-63']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Cream Cheese Catupiry (CQ-62) e Requeijão Catupiry (CQ-63), ambos em bisnaga no catálogo. Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-04
* **O que o Cliente Disse (Mensagem):** "Coloca 3 provolones"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"provolones"`
  * `quantity_value`: `3.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-44', 'CQ-46']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Provolone curado defumado Tânia (CQ-44) e Provolone forma Riqueza de Minas (CQ-46). Unidade de medida não informada (3 kg ou 3 formas). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-05
* **O que o Cliente Disse (Mensagem):** "Quero 5 kg daquele Brie"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Brie"`
  * `quantity_value`: `5.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-01', 'CQ-03']`
* **Ambiguidades e Informações Ausentes:** Referência histórica/contextual ('daquele') não disponível nas fontes. Produto ambíguo entre Brie forma (CQ-01) e Brie Specialitte (CQ-03) comercializados em KG. Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-06
* **O que o Cliente Disse (Mensagem):** "Me manda um Camembert"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Camembert"`
  * `quantity_value`: `1.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-04']`
* **Ambiguidades e Informações Ausentes:** Unidade de medida e apresentação física não informadas (pode ser 1 kg, 1 peça individual de 125g ou 1 caixa master fechada). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-07
* **O que o Cliente Disse (Mensagem):** "Gorgonzola 4 kg"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Gorgonzola"`
  * `quantity_value`: `4.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-06', 'CQ-07']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Queijo Azul cartão (CQ-06) e Queijo Azul forma (CQ-07), ambos descritos como tipo gorgonzola no catálogo. Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-08
* **O que o Cliente Disse (Mensagem):** "2 formas de Emmental de 5kg"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Emmental de 5kg"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"forma"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-10']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada. Regras determinísticas sobre conversão de unidades físicas para faturamento ou restrições de fracionamento são desconhecidas.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-09
* **O que o Cliente Disse (Mensagem):** "Quero Gruyere 12kg"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Gruyere 12kg"`
  * `quantity_value`: `12.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-11']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada. Conversão lógica ou automatizada de KG para formas físicas é desconhecida.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-10
* **O que o Cliente Disse (Mensagem):** "Gouda São Vicente 2 formas"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Gouda São Vicente"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"forma"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-14', 'CQ-15', 'CQ-16']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Gouda São Vicente (CQ-14), Gouda Provence (CQ-15) e Gouda Tomate seco (CQ-16). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-11
* **O que o Cliente Disse (Mensagem):** "Massa para fondue 3 caixas"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Massa para fondue"`
  * `quantity_value`: `3.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"caixa"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-20']`
* **Ambiguidades e Informações Ausentes:** Caixa não é unidade de faturamento válida automaticamente. O catálogo indica venda por UND (caixas de 400g). Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-12
* **O que o Cliente Disse (Mensagem):** "Quero 1 Maasdam"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Maasdam"`
  * `quantity_value`: `1.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-21']`
* **Ambiguidades e Informações Ausentes:** Unidade de faturamento não informada (pode representar 1 kg ou 1 forma inteira de 12kg). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-13
* **O que o Cliente Disse (Mensagem):** "Minas Padrão São Vicente 10 peças"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Minas Padrão São Vicente"`
  * `quantity_value`: `10.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"peça"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-22']`
* **Ambiguidades e Informações Ausentes:** Incompatibilidade de apresentação (catálogo indica 'forma' de 0.250kg para CQ-22, enquanto cliente pediu 'peça'). Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-14
* **O que o Cliente Disse (Mensagem):** "Reino sem lata 2 kg"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Reino sem lata"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-24']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada. Conversão determinística de KG para formas é desconhecida.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-15
* **O que o Cliente Disse (Mensagem):** "Requeijão São Vicente"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Requeijão São Vicente"`
  * `quantity_value`: `None`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-26']`
* **Ambiguidades e Informações Ausentes:** Quantidade, unidade de medida e condição de pagamento não informadas.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-16
* **O que o Cliente Disse (Mensagem):** "Mussarela Coyote 1 caixa"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Mussarela Coyote"`
  * `quantity_value`: `1.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"caixa"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-30']`
* **Ambiguidades e Informações Ausentes:** Caixa não é unidade de faturamento válida automaticamente. O catálogo indica faturamento por KG e apresentação individual em vácuo (peças de 4kg). Necessita de confirmação se o cliente deseja 1 caixa master fechada (6 peças = 24kg) ou 1 peça individual de 4kg. Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-17
* **O que o Cliente Disse (Mensagem):** "Grana Padano peça"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Grana Padano"`
  * `quantity_value`: `None`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-33', 'CQ-69']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Grana Padano peça 200g Gran Parma (CQ-33) e Grana Padano peça 150g Gran Mestri (CQ-69). Quantidade e condição de pagamento não informadas.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-18
* **O que o Cliente Disse (Mensagem):** "Fatiado Villani 5"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Fatiado Villani"`
  * `quantity_value`: `5.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-35']`
* **Ambiguidades e Informações Ausentes:** Unidade de medida não informada (5 kg ou 5 pacotes de 250g). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-19
* **O que o Cliente Disse (Mensagem):** "Mussarela bola ovo 2 kg"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Mussarela bola ovo"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-36']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada. Conversão determinística de KG para unidades físicas de 370g é desconhecida.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-20
* **O que o Cliente Disse (Mensagem):** "Burrata 4 potes"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Burrata"`
  * `quantity_value`: `4.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"pote"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-41']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-21
* **O que o Cliente Disse (Mensagem):** "Parmesão curado 2 peças"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Parmesão curado"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"peça"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-42', 'CQ-43']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Parmesão curado fracionado (CQ-42, em peças de 250g) e Parmesão curado forma (CQ-43, em formas de 7kg). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-22
* **O que o Cliente Disse (Mensagem):** "Ricota defumada"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Ricota defumada"`
  * `quantity_value`: `None`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-45']`
* **Ambiguidades e Informações Ausentes:** Quantidade, unidade de faturamento e condição de pagamento não informadas.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-23
* **O que o Cliente Disse (Mensagem):** "Minas frescal Espelho D'agua 3 formas"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Minas frescal Espelho D'agua"`
  * `quantity_value`: `3.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"forma"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-50']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada. Conversão para KG de referência (0.500 kg por forma) é desconhecida.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-24
* **O que o Cliente Disse (Mensagem):** "Saint Chevrollin de ervas 2"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Saint Chevrollin de ervas"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-51']`
* **Ambiguidades e Informações Ausentes:** Unidade de medida não informada (2 baldes ou 2 kg). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-25
* **O que o Cliente Disse (Mensagem):** "Feta 2 kg"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Feta"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"KG"`
  * `quantity_explicit`: `True`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-53', 'CQ-54']`
* **Ambiguidades e Informações Ausentes:** Produto ambíguo entre Feta fracionado (CQ-53) e Feta forma (CQ-54). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-26
* **O que o Cliente Disse (Mensagem):** "Coalho Serta Norte"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Coalho Serta Norte"`
  * `quantity_value`: `None`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-59']`
* **Ambiguidades e Informações Ausentes:** Quantidade, unidade de faturamento e condição de pagamento não informadas.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-27
* **O que o Cliente Disse (Mensagem):** "Creme de leite Larisol 2 caixas"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Creme de leite Larisol"`
  * `quantity_value`: `2.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"caixa"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-64']`
* **Ambiguidades e Informações Ausentes:** Caixa não é unidade de faturamento automática no catálogo (venda por UND, garrafa de 1.1kg). Não se pode assumir faturamento em caixas master sem confirmação do número de garrafas (1 caixa = 12 garrafas). Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-28
* **O que o Cliente Disse (Mensagem):** "Iogurte Larisol 6 garrafas"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Iogurte Larisol"`
  * `quantity_value`: `6.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"garrafa"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-65']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


### Casos de Teste - TEST-29
* **O que o Cliente Disse (Mensagem):** "Requeijão Roseli 4"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Requeijão Roseli"`
  * `quantity_value`: `4.0`
  * `quantity_unit`: `"UNDEFINED"`
  * `quantity_explicit`: `False`
  * `presentation`: `"null"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-66']`
* **Ambiguidades e Informações Ausentes:** Unidade de medida não informada (4 kg ou 4 bisnagas de 1.8kg). Condição de pagamento não informada.
* **Status de Resolução:** `AMBIGUOUS`


### Casos de Teste - TEST-30
* **O que o Cliente Disse (Mensagem):** "Tomate seco Villagio 1 saco"
* **Interpretação Semântica (NLP):**
  * `intent`: `ADD_ITEM`
  * `product_query`: `"Tomate seco Villagio"`
  * `quantity_value`: `1.0`
  * `quantity_unit`: `"PRESENTATION"`
  * `quantity_explicit`: `True`
  * `presentation`: `"saco"`
* **Candidato(s) Encontrado(s) no Catálogo:** `['CQ-71']`
* **Ambiguidades e Informações Ausentes:** Condição de pagamento não informada.
* **Status de Resolução:** `EXACT_MATCH`


---

## 7. GOLDEN DATASET COMPLETO (REQUISITO DE ENGENHARIA DE NLP)

Este é o Golden Dataset estruturado contendo a especificação em JSON de **todos os 30 casos de teste adversariais**. Ele fornece o gabarito semântico imutável necessário para validar testes automatizados de regressão na camada de processamento de linguagem natural do sistema:

```json
[
  {
    "id_teste": "TEST-01",
    "mensagem": "Quero 10 quilos da manteiga sem sal",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "manteiga sem sal",
      "quantity_value": 10.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-29"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada (cartão vs. prazo). Regras operacionais de pesagem, tolerância ou fracionamento de bloco de 5kg são desconhecidas."
    }
  },
  {
    "id_teste": "TEST-02",
    "mensagem": "Me manda duas manteigas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "manteigas",
      "quantity_value": 2.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-28",
        "CQ-29"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre com sal (CQ-28) e sem sal (CQ-29). Unidade de medida não informada (pode representar 2 kg, 2 blocos ou 2 caixas). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-03",
    "mensagem": "Quero 6 bisnagas de Catupiry",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Catupiry",
      "quantity_value": 6.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "bisnaga",
      "candidates": [
        "CQ-62",
        "CQ-63"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Cream Cheese Catupiry (CQ-62) e Requeijão Catupiry (CQ-63), ambos em bisnaga no catálogo. Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-04",
    "mensagem": "Coloca 3 provolones",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "provolones",
      "quantity_value": 3.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-44",
        "CQ-46"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Provolone curado defumado Tânia (CQ-44) e Provolone forma Riqueza de Minas (CQ-46). Unidade de medida não informada (3 kg ou 3 formas). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-05",
    "mensagem": "Quero 5 kg daquele Brie",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Brie",
      "quantity_value": 5.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-01",
        "CQ-03"
      ],
      "ambiguities_or_missing_info": "Referência histórica/contextual ('daquele') não disponível nas fontes. Produto ambíguo entre Brie forma (CQ-01) e Brie Specialitte (CQ-03) comercializados em KG. Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-06",
    "mensagem": "Me manda um Camembert",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Camembert",
      "quantity_value": 1.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-04"
      ],
      "ambiguities_or_missing_info": "Unidade de medida e apresentação física não informadas (pode ser 1 kg, 1 peça individual de 125g ou 1 caixa master fechada). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-07",
    "mensagem": "Gorgonzola 4 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Gorgonzola",
      "quantity_value": 4.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-06",
        "CQ-07"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Queijo Azul cartão (CQ-06) e Queijo Azul forma (CQ-07), ambos descritos como tipo gorgonzola no catálogo. Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-08",
    "mensagem": "2 formas de Emmental de 5kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Emmental de 5kg",
      "quantity_value": 2.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "forma",
      "candidates": [
        "CQ-10"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada. Regras determinísticas sobre conversão de unidades físicas para faturamento ou restrições de fracionamento são desconhecidas."
    }
  },
  {
    "id_teste": "TEST-09",
    "mensagem": "Quero Gruyere 12kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Gruyere 12kg",
      "quantity_value": 12.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-11"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada. Conversão lógica ou automatizada de KG para formas físicas é desconhecida."
    }
  },
  {
    "id_teste": "TEST-10",
    "mensagem": "Gouda São Vicente 2 formas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Gouda São Vicente",
      "quantity_value": 2.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "forma",
      "candidates": [
        "CQ-14",
        "CQ-15",
        "CQ-16"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Gouda São Vicente (CQ-14), Gouda Provence (CQ-15) e Gouda Tomate seco (CQ-16). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-11",
    "mensagem": "Massa para fondue 3 caixas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Massa para fondue",
      "quantity_value": 3.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "caixa",
      "candidates": [
        "CQ-20"
      ],
      "ambiguities_or_missing_info": "Caixa não é unidade de faturamento válida automaticamente. O catálogo indica venda por UND (caixas de 400g). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-12",
    "mensagem": "Quero 1 Maasdam",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Maasdam",
      "quantity_value": 1.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-21"
      ],
      "ambiguities_or_missing_info": "Unidade de faturamento não informada (pode representar 1 kg ou 1 forma inteira de 12kg). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-13",
    "mensagem": "Minas Padrão São Vicente 10 peças",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Minas Padrão São Vicente",
      "quantity_value": 10.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "peça",
      "candidates": [
        "CQ-22"
      ],
      "ambiguities_or_missing_info": "Incompatibilidade de apresentação (catálogo indica 'forma' de 0.250kg para CQ-22, enquanto cliente pediu 'peça'). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-14",
    "mensagem": "Reino sem lata 2 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Reino sem lata",
      "quantity_value": 2.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-24"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada. Conversão determinística de KG para formas é desconhecida."
    }
  },
  {
    "id_teste": "TEST-15",
    "mensagem": "Requeijão São Vicente",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Requeijão São Vicente",
      "quantity_value": null,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-26"
      ],
      "ambiguities_or_missing_info": "Quantidade, unidade de medida e condição de pagamento não informadas."
    }
  },
  {
    "id_teste": "TEST-16",
    "mensagem": "Mussarela Coyote 1 caixa",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Mussarela Coyote",
      "quantity_value": 1.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "caixa",
      "candidates": [
        "CQ-30"
      ],
      "ambiguities_or_missing_info": "Caixa não é unidade de faturamento válida automaticamente. O catálogo indica faturamento por KG e apresentação individual em vácuo (peças de 4kg). Necessita de confirmação se o cliente deseja 1 caixa master fechada (6 peças = 24kg) ou 1 peça individual de 4kg. Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-17",
    "mensagem": "Grana Padano peça",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Grana Padano",
      "quantity_value": null,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-33",
        "CQ-69"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Grana Padano peça 200g Gran Parma (CQ-33) e Grana Padano peça 150g Gran Mestri (CQ-69). Quantidade e condição de pagamento não informadas."
    }
  },
  {
    "id_teste": "TEST-18",
    "mensagem": "Fatiado Villani 5",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Fatiado Villani",
      "quantity_value": 5.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-35"
      ],
      "ambiguities_or_missing_info": "Unidade de medida não informada (5 kg ou 5 pacotes de 250g). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-19",
    "mensagem": "Mussarela bola ovo 2 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Mussarela bola ovo",
      "quantity_value": 2.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-36"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada. Conversão determinística de KG para unidades físicas de 370g é desconhecida."
    }
  },
  {
    "id_teste": "TEST-20",
    "mensagem": "Burrata 4 potes",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Burrata",
      "quantity_value": 4.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "pote",
      "candidates": [
        "CQ-41"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-21",
    "mensagem": "Parmesão curado 2 peças",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Parmesão curado",
      "quantity_value": 2.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "peça",
      "candidates": [
        "CQ-42",
        "CQ-43"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Parmesão curado fracionado (CQ-42, em peças de 250g) e Parmesão curado forma (CQ-43, em formas de 7kg). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-22",
    "mensagem": "Ricota defumada",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Ricota defumada",
      "quantity_value": null,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-45"
      ],
      "ambiguities_or_missing_info": "Quantidade, unidade de faturamento e condição de pagamento não informadas."
    }
  },
  {
    "id_teste": "TEST-23",
    "mensagem": "Minas frescal Espelho D'agua 3 formas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Minas frescal Espelho D'agua",
      "quantity_value": 3.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "forma",
      "candidates": [
        "CQ-50"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada. Conversão para KG de referência (0.500 kg por forma) é desconhecida."
    }
  },
  {
    "id_teste": "TEST-24",
    "mensagem": "Saint Chevrollin de ervas 2",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Saint Chevrollin de ervas",
      "quantity_value": 2.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-51"
      ],
      "ambiguities_or_missing_info": "Unidade de medida não informada (2 baldes ou 2 kg). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-25",
    "mensagem": "Feta 2 kg",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Feta",
      "quantity_value": 2.0,
      "quantity_unit": "KG",
      "quantity_explicit": true,
      "presentation": null,
      "candidates": [
        "CQ-53",
        "CQ-54"
      ],
      "ambiguities_or_missing_info": "Produto ambíguo entre Feta fracionado (CQ-53) e Feta forma (CQ-54). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-26",
    "mensagem": "Coalho Serta Norte",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Coalho Serta Norte",
      "quantity_value": null,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-59"
      ],
      "ambiguities_or_missing_info": "Quantidade, unidade de faturamento e condição de pagamento não informadas."
    }
  },
  {
    "id_teste": "TEST-27",
    "mensagem": "Creme de leite Larisol 2 caixas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Creme de leite Larisol",
      "quantity_value": 2.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "caixa",
      "candidates": [
        "CQ-64"
      ],
      "ambiguities_or_missing_info": "Caixa não é unidade de faturamento automática no catálogo (venda por UND, garrafa de 1.1kg). Não se pode assumir faturamento em caixas master sem confirmação do número de garrafas (1 caixa = 12 garrafas). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-28",
    "mensagem": "Iogurte Larisol 6 garrafas",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Iogurte Larisol",
      "quantity_value": 6.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "garrafa",
      "candidates": [
        "CQ-65"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-29",
    "mensagem": "Requeijão Roseli 4",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Requeijão Roseli",
      "quantity_value": 4.0,
      "quantity_unit": "UNDEFINED",
      "quantity_explicit": false,
      "presentation": null,
      "candidates": [
        "CQ-66"
      ],
      "ambiguities_or_missing_info": "Unidade de medida não informada (4 kg ou 4 bisnagas de 1.8kg). Condição de pagamento não informada."
    }
  },
  {
    "id_teste": "TEST-30",
    "mensagem": "Tomate seco Villagio 1 saco",
    "esperado": {
      "intent": "ADD_ITEM",
      "product_query": "Tomate seco Villagio",
      "quantity_value": 1.0,
      "quantity_unit": "PRESENTATION",
      "quantity_explicit": true,
      "presentation": "saco",
      "candidates": [
        "CQ-71"
      ],
      "ambiguities_or_missing_info": "Condição de pagamento não informada."
    }
  }
]
```

---

## 8. AVALIAÇÃO DE PRONTIDÃO PARA IMPLEMENTAÇÃO (SCORECARD TECNOLÓGICO)

Abaixo é apresentada a análise técnica sobre a viabilidade de colocar o sistema em produção com base no catálogo e nas fontes lógicas analisadas:

### Matriz de Prontidão Operacional

| Dimensão | Classificação / Status | Gargalo Identificado | Ação Corretiva Recomendada |
| :--- | :---: | :--- | :--- |
| **Sanidade dos Dados Comerciais** | 🟠 **Risco Médio** | O CSV bruto possui dados misturados e erros ortográficos severos [43]. | Adotar a tabela normalizada estruturada na Seção 3 como base de dados unificada [34]. |
| **Clareza de Preços e Condições** | 🟢 **Pronto** | Os preços para faturamento à vista e a prazo estão 100% mapeados [43]. | Configurar o motor determinístico para aplicar os preços baseando-se estritamente na forma de pagamento selecionada [23]. |
| **Regras Físicas de Estoque** | 🔴 **Crítico** | As regras físicas de balança, fracionamento, substituições e tolerância são desconhecidas [9, 27]. | Conduzir a entrevista operacional com as 10 perguntas críticas de descoberta para delimitar os fluxos do estoque antes do início do código back-end [25, 27]. |
| **Capacidade de Interpretação (NLP)** | 🟡 **Pronto para Experimentação** | A capacidade de interpretação do modelo linguístico ainda não foi medida empiricamente contra casos reais de clientes no WhatsApp. | Iniciar o desenvolvimento de protótipos de NLP alimentados com os aliases de busca da Seção 4 e o Golden Dataset de 30 casos para medição empírica de acurácia. |

### Conclusão e Princípio Arquitetural
O estado atual da tecnologia está classificado como **PRONTO PARA EXPERIMENTAÇÃO**. Embora as definições estruturais do catálogo e a modelagem semântica de linguagem natural estejam maduras, a capacidade real de NLP deve ser exaustivamente testada em laboratório usando o Golden Dataset antes de qualquer homologação. 

Adicionalmente, as integrações de back-end com o estoque e faturamento físico permanecem **bloqueadas** até que as regras determinísticas de pesagem e fracionamento de peso variável sejam explicitamente acordadas com os gestores do negócio.
