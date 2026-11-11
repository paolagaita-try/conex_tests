"""Validaciones de la spec que añaden los hilos del Plan 5, una por módulo.

Cada módulo `generadores/validar/<hilo>.py` expone `validar(spec: dict, atributos: dict, err: list[str]) -> None`
(`atributos` es lo que devuelve `_validar_bdm`: objeto -> atributo -> definición) y añade sus errores a `err`.
`spec.validar_spec` los llama, en orden alfabético, tras `_validar_caminos`. Sin módulos no hace nada.
"""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def VALIDADORES() -> list[ModuleType]:
    """Los módulos de este paquete, en orden alfabético."""
    return [importlib.import_module(f"{__name__}.{m.name}")
            for m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name)]
