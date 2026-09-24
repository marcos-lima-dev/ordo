import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.resolved_operation import OperationType
from order.operation_fields import (
    EXECUTION_REQUIREMENTS,
    REQUIRED_FIELDS_BY_TYPE,
    NON_EXECUTABLE_OPERATION_TYPES,
)


# =============================================
# Conjunto canônico de operações executáveis
# =============================================
# Definido explicitamente neste teste para que a intenção seja legível.
# Não derivado de EXECUTION_REQUIREMENTS — se um tipo for adicionado ou
# removido em apenas uma das tabelas, o teste deve falhar.

EXECUTABLE_OPERATION_TYPES = [
    OperationType.ADD_ITEM,
    OperationType.REMOVE_ITEM,
    OperationType.CHANGE_QUANTITY,
    OperationType.REPLACE_ITEM,
    OperationType.CONFIRM_ORDER,
    OperationType.CANCEL_ORDER,
]


# =============================================
# ECA-1 — executable requirements synchronized
# =============================================

@pytest.mark.parametrize("op_type", EXECUTABLE_OPERATION_TYPES)
def test_eca1_execution_and_evaluation_requirements_are_synchronized(op_type):
    """
    Para cada OperationType executável, os campos exigidos em
    EXECUTION_REQUIREMENTS (runtime) devem ser idênticos aos exigidos
    em REQUIRED_FIELDS_BY_TYPE (evaluator).

    Comparação independente de ordem (set). Se uma tabela for alterada
    sem a outra, este teste falha e expõe o drift contratual.
    """
    runtime_fields = EXECUTION_REQUIREMENTS.get(op_type)
    evaluator_fields = REQUIRED_FIELDS_BY_TYPE.get(op_type)

    assert runtime_fields is not None, (
        f"{op_type.name} presente na lista canônica de executáveis mas "
        f"ausente de EXECUTION_REQUIREMENTS."
    )
    assert evaluator_fields is not None, (
        f"{op_type.name} presente na lista canônica de executáveis mas "
        f"ausente de REQUIRED_FIELDS_BY_TYPE."
    )

    assert set(runtime_fields) == set(evaluator_fields), (
        f"{op_type.name}: runtime exige {sorted(set(runtime_fields))} "
        f"mas evaluator exige {sorted(set(evaluator_fields))}. "
        f"Contratos divergentes."
    )


# =============================================
# ECA-2 — UNKNOWN remains non-executable
# =============================================

def test_eca2a_unknown_is_not_in_execution_requirements():
    """
    OperationType.UNKNOWN é declaradamente não-executável.
    Deve estar em NON_EXECUTABLE_OPERATION_TYPES e ausente de
    EXECUTION_REQUIREMENTS.
    """
    assert OperationType.UNKNOWN in NON_EXECUTABLE_OPERATION_TYPES
    assert OperationType.UNKNOWN not in EXECUTION_REQUIREMENTS


def test_eca2b_unknown_has_no_evaluation_contract_as_executable():
    """
    UNKNOWN não possui contrato avaliativo de operação executável em
    REQUIRED_FIELDS_BY_TYPE. A ausência é intencional e explícita.
    """
    assert OperationType.UNKNOWN not in REQUIRED_FIELDS_BY_TYPE


# =============================================
# ECA-3 — executable type coverage
# =============================================

def test_eca3a_no_executable_type_missing_from_execution_requirements():
    """
    Nenhum tipo executável pode desaparecer silenciosamente de
    EXECUTION_REQUIREMENTS. A cobertura deve ser exata.
    """
    runtime_keys = set(EXECUTION_REQUIREMENTS.keys())
    expected = set(EXECUTABLE_OPERATION_TYPES)

    assert runtime_keys == expected, (
        f"EXECUTION_REQUIREMENTS tem {sorted(t.name for t in runtime_keys)} "
        f"mas a lista canônica de executáveis é "
        f"{sorted(t.name for t in expected)}."
    )


def test_eca3b_no_executable_type_missing_from_required_fields():
    """
    Nenhum tipo executável pode desaparecer silenciosamente de
    REQUIRED_FIELDS_BY_TYPE. A cobertura deve ser exata.
    """
    evaluator_keys = set(REQUIRED_FIELDS_BY_TYPE.keys())
    expected = set(EXECUTABLE_OPERATION_TYPES)

    assert evaluator_keys == expected, (
        f"REQUIRED_FIELDS_BY_TYPE tem "
        f"{sorted(t.name for t in evaluator_keys)} "
        f"mas a lista canônica de executáveis é "
        f"{sorted(t.name for t in expected)}."
    )


def test_eca3c_unknown_is_the_only_declared_non_executable():
    """
    NON_EXECUTABLE_OPERATION_TYPES deve conter apenas UNKNOWN hoje.
    Se outro tipo for adicionado lá, o teste falha e exige atualização
    explícita da lista canônica acima.
    """
    assert NON_EXECUTABLE_OPERATION_TYPES == {OperationType.UNKNOWN}, (
        f"NON_EXECUTABLE_OPERATION_TYPES contém "
        f"{sorted(t.name for t in NON_EXECUTABLE_OPERATION_TYPES)}. "
        f"Se um novo tipo foi declarado como não-executável, "
        f"EXECUTABLE_OPERATION_TYPES no teste precisa ser revisada."
    )