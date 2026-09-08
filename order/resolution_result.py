from order.resolved_operation import OperationType

REQUIRED_FIELDS_BY_TYPE = {
    OperationType.ADD_ITEM: ["product_id"],
    OperationType.REMOVE_ITEM: ["target_item_id"],
    OperationType.CHANGE_QUANTITY: ["target_item_id", "quantity_value"],
    OperationType.REPLACE_ITEM: ["target_item_id", "replacement_product_id"],
    OperationType.CONFIRM_ORDER: [],
    OperationType.CANCEL_ORDER: [],
}

OPTIONAL_FIELDS = {
    "quantity_value",
    "quantity_unit",
}