# order/operation_fields.py
from order.resolved_operation import OperationType

# Campos obrigatórios por tipo de operação
# None significa que o campo é obrigatório, mas pode ser vazio
REQUIRED_FIELDS_BY_TYPE = {
    OperationType.ADD_ITEM: ["product_id"],
    OperationType.REMOVE_ITEM: ["target_item_id"],
    OperationType.CHANGE_QUANTITY: ["target_item_id", "quantity_value"],
    OperationType.REPLACE_ITEM: ["target_item_id", "replacement_product_id"],
    OperationType.CONFIRM_ORDER: [],
    OperationType.CANCEL_ORDER: [],
}

# Campos que também devem ser verificados quando presentes (semântica opcional)
OPTIONAL_FIELDS = {
    "quantity_value",
    "quantity_unit",
}