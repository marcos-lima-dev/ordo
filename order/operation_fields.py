from order.resolved_operation import OperationType

REQUIRED_FIELDS_BY_TYPE = {
    OperationType.ADD_ITEM: ["product_id"],
    OperationType.REMOVE_ITEM: ["target_item_id"],
    OperationType.CHANGE_QUANTITY: ["target_item_id", "quantity_value"],
    OperationType.REPLACE_ITEM: ["target_item_id", "replacement_product_id"],
    OperationType.CONFIRM_ORDER: [],
    OperationType.CANCEL_ORDER: [],
}

# Campos semanticamente relevantes por tipo (para o evaluator)
FIELDS_BY_TYPE = {
    OperationType.ADD_ITEM: ["product_id", "quantity_value", "quantity_unit"],
    OperationType.REMOVE_ITEM: ["target_item_id"],
    OperationType.CHANGE_QUANTITY: ["target_item_id", "quantity_value", "quantity_unit"],
    OperationType.REPLACE_ITEM: ["target_item_id", "replacement_product_id"],
    OperationType.CONFIRM_ORDER: [],
    OperationType.CANCEL_ORDER: [],
}

OPTIONAL_FIELDS = {
    "quantity_value",
    "quantity_unit",
}

# =============================================
# EXECUTION REQUIREMENTS — Track 9C Stage 1B
# =============================================
# Declaração formal do contrato de execução de cada OperationType.
# Consumido por ResolvedOperation.is_valid() em order/resolved_operation.py.
#
# Regras:
#   - Cada chave mapeia para a lista de campos que PRECISAM estar
#     preenchidos para a operação alcançar o Order Engine.
#   - Campos fora da lista não são obrigatórios para execução.
#   - OperationType ausente desta tabela é tratado como NÃO executável
#     (default conservador).
#
# Semântica especial:
#   - CHANGE_QUANTITY: quantity_unit NÃO é obrigatório. Quando None,
#     significa KEEP_EXISTING_UNIT (preservar unidade do item existente
#     no OrderState). Esta é a única operação com semântica de None
#     dependente do estado.
#
# NÃO confundir com REQUIRED_FIELDS_BY_TYPE, que é contrato do evaluator
# (ver order/resolution_evaluator.py) e permanece inalterado.

EXECUTION_REQUIREMENTS = {
    OperationType.ADD_ITEM: ["product_id"],
    OperationType.REMOVE_ITEM: ["target_item_id"],
    OperationType.CHANGE_QUANTITY: ["target_item_id", "quantity_value"],
    OperationType.REPLACE_ITEM: ["target_item_id", "replacement_product_id"],
    OperationType.CONFIRM_ORDER: [],
    OperationType.CANCEL_ORDER: [],
}

# Tipos que NUNCA alcançam o Order Engine.
# Listados explicitamente para não depender da ausência em
# EXECUTION_REQUIREMENTS — uma tabela vazia de requisitos não pode
# tornar um tipo não-executável em executável por vacuidade.

NON_EXECUTABLE_OPERATION_TYPES = {
    OperationType.UNKNOWN,
}