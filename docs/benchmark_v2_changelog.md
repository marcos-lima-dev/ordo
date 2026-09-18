# Benchmark V2 — Change Log

## DEV V2

### DEV-04 — POLICY_DECISION_REQUIRED → POLICY_APPLIED
- **V1:** `NEEDS_CLARIFICATION(MISSING_TARGET)`
- **V2:** `OPERATION(CHANGE_QUANTITY, target=item_1, quantity=4)`
- **Reason:** P1 — UNIQUE_ELIGIBLE_TARGET autoriza target quando resolved_operation_type = CHANGE_QUANTITY.

### DEV-07 — GROUND_TRUTH_REVIEW_REQUIRED → CORRECTED
- **V1:** `OPERATION(REPLACE_ITEM, item_2, CQ-06)`
- **V2:** `NEEDS_CLARIFICATION(AMBIGUOUS_PRODUCT)`
- **Reason:** "gorgonzola" mapeia para CQ-06 (cartela) e CQ-07 (forma) sem evidência de desempate.

### DEV-09 — GROUND_TRUTH_QUESTIONABLE → MAINTAINED_WITH_NOTE
- **V1:** `NEEDS_CLARIFICATION(MISSING_TARGET)`
- **V2:** *(inalterado)*
- **Note:** "coloca 3" isolada é ambígua. Ground truth conservador.

## HOLDOUT-1 V2

### HOLDOUT-03 — DATASET_INCOMPLETE → REPLACED
- **V1 message:** "na verdade quero 6kg" (sem turno anterior)
- **V2 message:** "muda para 6kg"

### HOLDOUT-04 — POLICY_DECISION_REQUIRED → POLICY_APPLIED
- **V1:** `NEEDS_CLARIFICATION` (sem reason)
- **V2:** `OPERATION(CHANGE_QUANTITY, target=item_1, quantity=3)`

### HOLDOUT-05 — DATASET_INCOMPLETE → CORRECTED
- **V1 state:** sem pending_resolution
- **V2 state:** pending_resolution para provolone com missing_fields=["presentation"]

### HOLDOUT-07 — GROUND_TRUTH_INVALID → REPLACED
- **V1:** CQ-99 (inexistente)
- **V2:** CQ-28 (Manteiga c/sal, válido)

### HOLDOUT-09 — DATASET_INCOMPLETE → CORRECTED
- **V1:** sem reason_code
- **V2:** `NEEDS_CLARIFICATION(MISSING_PRODUCT)`

### HOLDOUT-10 — DATASET_INCOMPLETE → CORRECTED
- **V1:** sem reason_code
- **V2:** `NEEDS_CLARIFICATION(AMBIGUOUS_TARGET)`