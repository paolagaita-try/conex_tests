"""Call activity del `.proc` (`process:CallActivity`): nombre y versión del proceso llamado como constantes y un
`InputMapping` por entrada hacia el contrato de instanciación del hijo (`assignationType="ContractInput"`).

Doc `process/called-processes`: el padre espera al fin del hijo; los datos pasan solo por el mapeo, del mismo tipo
(«You can only map variables or inputs of the same type»), y lo recomendado es mapear al contrato del hijo. El
origen (`bv.atributo` o `pv`) es un script `return <origen>` con el tipo Java del origen. Sin salidas
(`outputMappings`): la spec no las tiene.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc.datos import CLASE_INPUT, INSTANCIACION, Contexto
from generadores.escribir.proc.ids import elemento


def _constante(padre: ET.Element, tag: str, valor: str, ctx: Contexto) -> None:
    elemento(padre, tag, "expression:Expression", ctx.ids,
             {"name": valor, "content": valor, "type": "TYPE_CONSTANT", "returnType": "java.lang.String"})


def llamada(e: ET.Element, nodo: dict, ctx: Contexto, procesos: list[dict] | None, donde: str) -> None:
    """Rellena la call activity `e`. Con `procesos` (todos los de la spec) comprueba que el hijo existe, que cada
    entrada es un input de su contrato de instanciación y que los tipos casan."""
    ll = nodo.get("llamado") or {}
    if not ll.get("proceso") or not ll.get("version"):
        raise ValueError(f"{donde}: la call activity no dice a qué proceso y versión llama")
    inputs = None
    if procesos is not None:
        hijo = next((p for p in procesos if p["nombre"] == ll["proceso"] and p["version"] == ll["version"]), None)
        if hijo is None:
            raise ValueError(f"{donde}: llama a «{ll['proceso']}» {ll['version']}, que no es un proceso de la spec")
        inputs = {i["nombre"]: i for i in hijo.get("contratos", {}).get(INSTANCIACION, {}).get("inputs", [])}
    _constante(e, "calledActivityName", ll["proceso"], ctx)
    _constante(e, "calledActivityVersion", ll["version"], ctx)
    for ent in ll.get("entradas", []):
        origen, destino = ent["origen"], ent["input"]
        aqui = f"{donde} › {origen} → {destino}"
        clase = ctx.clase_java(origen, aqui)
        if inputs is not None:
            if destino not in inputs:
                raise ValueError(f"{aqui}: «{destino}» no es un input del contrato de instanciación de "
                                 f"«{ll['proceso']}» ({', '.join(inputs) or 'sin contrato'})")
            esperado = CLASE_INPUT[inputs[destino]["tipo"]]
            if inputs[destino].get("multiple"):
                esperado = "java.util.List"
            if esperado != clase:
                raise ValueError(f"{aqui}: el origen es {clase} y el input «{destino}» espera {esperado}; el mapeo "
                                 "solo admite el mismo tipo")
        m = elemento(e, "inputMappings", "process:InputMapping", ctx.ids,
                     {"subprocessTarget": destino, "assignationType": "ContractInput"})
        ctx.script(m, "processSource", origen, f"return {origen}", clase)
