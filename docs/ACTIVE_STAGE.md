# ORDO — ACTIVE STAGE

## STATUS

Nenhuma etapa funcional ativa.

Checkpoint oficial: `983485d3104220627dea8b46119a27d736b27bb6`

---

## TEMPLATE — quando uma etapa for aberta

Toda etapa ativa DEVE declarar:

### OBJECTIVE

Uma frase. O que a etapa pretende entregar.

### QUESTION THIS STAGE ANSWERS

Uma pergunta única e específica. Não uma lista.

### SUCCESS CONDITION

Condição objetiva e verificável. Quando satisfeita, a etapa termina.

### OUT OF SCOPE

O que explicitamente não pertence a esta etapa.

### REUSE

Mecanismos, contratos e evidências já fechados que a etapa pode usar.
Referência a `ORDO_CURRENT_STATE.md`.

### ALLOWED FILES

Lista exata dos arquivos que podem ser criados ou modificados.
Qualquer outro arquivo exige STOP.

### STOP CONDITION

O que dispara parada obrigatória:
- arquivo fora do ALLOWED FILES;
- decisão de domínio nova;
- conflito com FROZEN;
- SUCCESS CONDITION satisfeita.

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