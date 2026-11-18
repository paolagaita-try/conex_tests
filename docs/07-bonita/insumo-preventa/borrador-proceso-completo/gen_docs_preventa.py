# -*- coding: utf-8 -*-
"""Emite docs/07-bonita/{bpmn,contratos,matriz-formularios}.md del proceso GestionPreventa a partir de un modelo
unico, para que IDs, compuertas, transiciones, contratos y formularios sean consistentes entre si.
Fuente: docs/07-bonita/insumo-preventa/Proceso_Preventa_Bonita.bpmn + manual (docx)."""
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
POOL, VER, HOY = "GestionPreventa", "1.0", "2026-11-12"
P = "`" + POOL + "` " + VER
FILL = lambda n: "| " + " | ".join(["—"] * n) + " |"

L_CLI, L_COM, L_ORQ, L_CON, L_LT, L_IA, L_INT = ("Cliente", "Comercial", "Orquestador", "Consultor Preventa",
                                                 "Líder Técnico", "Agente IA", "Equipo interno")
ACTOR = {L_CLI: "Comercial", L_COM: "Comercial", L_ORQ: "Orquestador", L_CON: "ConsultorPreventa",
         L_LT: "LiderTecnico", L_IA: "—", L_INT: "EquipoInterno"}
ROL = {L_CLI: "comercial", L_COM: "comercial", L_CON: "consultor", L_LT: "liderTecnico", L_INT: "procesos"}

RV = ("requiereViabilidad", "BOOLEAN", False, "pv requiereViabilidad", "Radio buttons (sí / no)",
      "¿Requiere validar la viabilidad técnica?")


def inp(nombre, tipo, oblig, destino, widget, etiqueta):
    return (nombre, tipo, oblig, destino, widget, etiqueta)


# id, nombre, tipo, lane, fuente BPMN, fase, inputs, constraints, literales, estado, familia
T = []


def tarea(id_, nombre, tipo, lane, src, fase, inputs=(), cons=(), lit=None, fam=None, nota=""):
    T.append(dict(id=id_, nombre=nombre, tipo=tipo, lane=lane, src=src, fase=fase, inputs=list(inputs),
                  cons=list(cons), lit=lit, fam=fam, nota=nota))


SI_NO = "Radio buttons (sí / no)"
tarea("3_consultarTicket", "Consultar el ticket de preventa en HubSpot", "service", L_ORQ, "A03", 1)
tarea("4_verificarDisponibilidad", "Verificar disponibilidad de consultores", "script", L_ORQ, "A04", 1)
tarea("5_asignarConsultor", "Asignar consultor preventa (round robin)", "script", L_ORQ, "A05", 1)
tarea("6_actualizarTicket", "Actualizar estado y responsable del ticket en HubSpot", "service", L_ORQ, "A06", 1)
tarea("7_analizarRequerimiento", "Analizar MEDDPICC y requerimiento", "human", L_CON, "A07", 1, [
    inp("tipoAtencion", "TEXT", True, "Preventa.tipoAtencion", "Radio buttons (demo / licitacion / propuesta)",
        "Tipo de atención"),
    inp("informacionSuficiente", "BOOLEAN", True, "pv informacionSuficiente", SI_NO,
        "¿La información es suficiente para la propuesta?"), RV],
      [("tipoAtencion_valido", "tipoAtencion es demo, licitacion o propuesta",
        "El tipo de atención debe ser demo, licitacion o propuesta")], fam="FAM-consultor-decision")
tarea("8_identificarProducto", "Identificar producto del demo (DocFly / Oriuno)", "human", L_CON, "A08", 2, [
    inp("productoDemo", "TEXT", True, "Preventa.productoDemo", "Radio buttons (docfly / oriuno)", "Producto del demo"),
    inp("origenDocumentosDemo", "TEXT", True, "Preventa.origenDocumentosDemo",
        "Radio buttons (cliente / guia / ejemplo)", "Documentos con los que se prepara la demo")],
      [("productoDemo_valido", "productoDemo es docfly u oriuno", "El producto debe ser docfly u oriuno"),
       ("origenDocumentosDemo_valido", "origenDocumentosDemo es cliente, guia o ejemplo",
        "El origen de los documentos debe ser cliente, guia o ejemplo")], fam="FAM-consultor-decision")
tarea("9_prepararDemoCliente", "Preparar demo con documentos del cliente", "human", L_CON, "A09", 2,
      fam="FAM-consultor-confirmacion")
tarea("10_prepararDemoGuia", "Preparar demo con documentos guía", "human", L_CON, "A10", 2,
      fam="FAM-consultor-confirmacion")
tarea("11_construirDocumentosEjemplo", "Construir documentos de ejemplo para el caso", "human", L_CON, "A11", 2,
      fam="FAM-consultor-confirmacion")
tarea("12_ejecutarDemo", "Ejecutar demo con el cliente", "human", L_CON, "A12", 2, [
    inp("clienteAvanza", "BOOLEAN", True, "pv clienteAvanza", SI_NO, "¿El cliente avanza?"),
    inp("informacionSuficiente", "BOOLEAN", True, "pv informacionSuficiente", SI_NO,
        "¿La información es suficiente para la propuesta?"),
    inp("observacionDemo", "TEXT", False, "Preventa.observacionDemo", "Text area", "Observaciones de la demo"), RV],
      fam="FAM-consultor-decision")
tarea("13_registrarNoContinua", "Actualizar estado en HubSpot (no continúa)", "human", L_COM, "A13", 2, [
    inp("motivoDescarte", "TEXT", True, "Preventa.motivoDescarte", "Text area", "Motivo por el que no continúa")],
      lit="descartada", fam="FAM-comercial-captura")
tarea("32_analizarLicitacion", "Analizar insumos de la licitación (pliegos / TDR)", "human", L_CON, "A32", 3, [
    inp("requierePreguntas", "BOOLEAN", True, "pv requierePreguntas", SI_NO, "¿Requiere preguntas aclaratorias?"),
    RV], fam="FAM-consultor-decision")
tarea("33_elaborarPreguntas", "Elaborar preguntas y cargarlas en el ticket", "human", L_CON, "A33", 3, [
    inp("preguntasAclaratorias", "TEXT", True, "Preventa.preguntasAclaratorias", "Text area",
        "Preguntas aclaratorias")], fam="FAM-consultor-captura")
tarea("37_radicarPreguntas", "Radicar o enviar preguntas a la entidad", "human", L_COM, "A37", 3,
      lit="enEsperaRespuestas", fam="FAM-comercial-confirmacion")
tarea("34_esperarRespuestas", "Esperar y registrar las respuestas de la entidad", "human", L_CON, "RT1", 3, [
    inp("respuestasCompletas", "BOOLEAN", True, "pv respuestasCompletas", SI_NO, "¿Las respuestas son completas?"),
    inp("respuestasEntidad", "TEXT", False, "Preventa.respuestasEntidad", "Text area", "Respuestas de la entidad"),
    RV], fam="FAM-consultor-decision",
      nota="Sustituye a la receive task `RT1` del insumo (ver Pendientes de definición); lleva el timer de borde "
           "interruptor `evTimer_1`")
tarea("35_definirSupuestos", "Definir supuestos para la propuesta", "human", L_CON, "A35", 3, [
    inp("supuestos", "TEXT", True, "Preventa.supuestos", "Text area", "Supuestos de la propuesta"), RV],
      fam="FAM-consultor-captura")
tarea("14_realizarLevantamiento", "Realizar sesión de levantamiento y solicitar documentación de referencia",
      "human", L_CON, "A14", 4, [
          inp("entregaDocumentos", "BOOLEAN", True, "pv entregaDocumentos", SI_NO,
              "¿El cliente entrega documentos de referencia?"),
          inp("enlaceGrabacion", "TEXT", False, "Preventa.enlaceGrabacion", "Input (texto)",
              "Enlace a la grabación y transcripción"), RV],
      lit="enLevantamiento", fam="FAM-consultor-decision")
tarea("42_analizarDocumentos", "Analizar documentos e insumos de referencia del cliente", "human", L_CON, "A42", 4,
      [RV], fam="FAM-consultor-captura")
tarea("38_validarViabilidad", "Validar viabilidad técnica", "human", L_LT, "A38", 4, [
    inp("esViable", "BOOLEAN", True, "pv esViable", SI_NO, "¿El requerimiento es viable?"),
    inp("conceptoViabilidad", "TEXT", True, "Preventa.conceptoViabilidad", "Text area",
        "Concepto de viabilidad técnica")], fam="FAM-lider")
tarea("39_notificarNoViabilidad", "Notificar y socializar no viabilidad con Comercial", "human", L_CON, "A39", 4,
      lit="noViable", fam="FAM-consultor-confirmacion")
tarea("31_prepararAnalisis", "Preparar análisis de documentos para el agente IA", "human", L_CON, "A31", 4, [
    inp("enlaceInsumos", "TEXT", True, "Preventa.enlaceInsumos", "Input (texto)",
        "Enlace al paquete de insumos estructurado")], lit="enDiseno", fam="FAM-consultor-captura")
tarea("15_cargarInsumos", "Cargar insumos al agente IA", "human", L_CON, "A15", 4, fam="FAM-consultor-confirmacion")
tarea("16_generarArtefactos", "Generar propuesta, estimación y presentación", "service", L_IA, "A16", 5)
tarea("17_revisarArtefactos", "Revisar y ajustar artefactos", "human", L_CON, "A17", 5, [
    inp("enlacePropuesta", "TEXT", True, "Preventa.enlacePropuesta", "Input (texto)", "Enlace a la propuesta"),
    inp("enlacePresentacion", "TEXT", True, "Preventa.enlacePresentacion", "Input (texto)",
        "Enlace a la presentación")], fam="FAM-consultor-captura")
tarea("36_revisarEstimacion", "Revisar y generar estimación con Líder Técnico", "human", L_LT, "A36", 5, [
    inp("enlaceEstimacion", "TEXT", True, "Preventa.enlaceEstimacion", "Input (texto)",
        "Enlace a la estimación validada")], fam="FAM-lider")
tarea("18_cargarArtefactos", "Cargar artefactos en el lead de HubSpot (etapa «Preventa / Solución GH»)", "human",
      L_CON, "A18", 5, fam="FAM-consultor-confirmacion")
tarea("40_entregarAVentas", "Cambiar estado del ticket a «Entregado a ventas»", "service", L_ORQ, "A40", 5)
tarea("19_socializarPropuesta", "Socializar propuesta con Comercial", "human", L_CON, "A19", 6,
      fam="FAM-consultor-confirmacion")
tarea("41_presentarPropuestaTecnica", "Presentar propuesta técnica: alcance, solución y cronograma", "human", L_CON,
      "A41", 6, fam="FAM-consultor-confirmacion")
tarea("20_presentarPropuestaEconomica", "Presentar propuesta económica (presupuesto)", "human", L_COM, "A20", 6,
      fam="FAM-comercial-confirmacion")
tarea("21_validarAlcance", "Validar alcance de la propuesta", "human", L_CLI, "A21", 6, [
    inp("alcanceCorrecto", "BOOLEAN", True, "pv alcanceCorrecto", SI_NO, "¿El cliente valida el alcance?"),
    inp("observacionAlcance", "TEXT", False, "Preventa.observacionAlcance", "Text area",
        "Ajustes solicitados por el cliente")], fam="FAM-comercial-decision",
      nota="La decisión es del cliente; la registra Comercial (el cliente no es usuario de Bonita)")
tarea("22_ajustarPropuesta", "Ajustar propuesta", "human", L_CON, "A22", 6, [
    inp("ajustesPropuesta", "TEXT", True, "Preventa.ajustesPropuesta", "Text area", "Ajustes realizados")],
      fam="FAM-consultor-captura")
tarea("23_validarAjustes", "Validar ajustes («Negociación / Ajustes»)", "human", L_COM, "A23", 6,
      lit="enNegociacion", fam="FAM-comercial-confirmacion")
tarea("24_enviarPropuestaFormal", "Enviar propuesta formal y mover lead a «Propuesta enviada»", "human", L_COM,
      "A24", 6, lit="propuestaEnviada", fam="FAM-comercial-confirmacion")
tarea("25_confirmarPropuesta", "Confirmar propuesta", "human", L_CLI, "A25", 7, [
    inp("propuestaAprobada", "BOOLEAN", True, "pv propuestaAprobada", SI_NO, "¿El cliente aprueba la propuesta?")],
      fam="FAM-comercial-decision",
      nota="La decisión es del cliente; la registra Comercial (el cliente no es usuario de Bonita)")
tarea("26_registrarRechazo", "Registrar rechazo y motivo en HubSpot", "human", L_COM, "A26", 7, [
    inp("motivoRechazo", "TEXT", True, "Preventa.motivoRechazo", "Text area", "Motivo del rechazo")],
      lit="rechazada", fam="FAM-comercial-captura")
tarea("27_cerrarGanado", "Pasar a «Cerrado ganado» y convocar traspaso", "human", L_COM, "A27", 7, lit="ganada",
      fam="FAM-comercial-confirmacion")
tarea("28_presentarAlcanceTraspaso", "Presentar alcance en sesión interna de traspaso", "human", L_CON, "A28", 7,
      fam="FAM-consultor-confirmacion")
tarea("29_entregarCarpeta", "Entregar carpeta de documentación a Procesos", "human", L_CON, "A29", 7, [
    inp("enlaceCarpeta", "TEXT", True, "Preventa.enlaceCarpeta", "Input (texto)",
        "Enlace a la carpeta «Prospectos de Preventa» del cliente")], fam="FAM-consultor-captura")
tarea("30_iniciarEjecucion", "Recibir carpeta e iniciar ejecución del proyecto", "human", L_INT, "A30", 7,
      lit="enEjecucion", fam="FAM-interno")
BY = {t["id"]: t for t in T}

# Compuertas: id, fuente, decide, salidas [(cond, destino)], defecto
G = [
    ("gwXor_1", "G01", "`Preventa.tipoAtencion` (de `ctr_7_analizarRequerimiento`)",
     [("tipoAtencion = demo", "8_identificarProducto"), ("tipoAtencion = licitacion", "32_analizarLicitacion"),
      ("(por defecto)", "gwXor_6")]),
    ("gwXor_2", "G02", "`Preventa.origenDocumentosDemo` (de `ctr_8_identificarProducto`)",
     [("origenDocumentosDemo = cliente", "9_prepararDemoCliente"), ("(por defecto)", "gwXor_3")]),
    ("gwXor_3", "G03", "`Preventa.origenDocumentosDemo` (de `ctr_8_identificarProducto`)",
     [("origenDocumentosDemo = guia", "10_prepararDemoGuia"), ("(por defecto)", "11_construirDocumentosEjemplo")]),
    ("gwXor_5", "G05", "`clienteAvanza` (process variable, de `ctr_12_ejecutarDemo`)",
     [("clienteAvanza = no", "13_registrarNoContinua"), ("(por defecto)", "gwXor_6")]),
    ("gwXor_6", "G06", "`informacionSuficiente` (process variable, de `ctr_7_analizarRequerimiento` o "
                       "`ctr_12_ejecutarDemo`)",
     [("informacionSuficiente = no", "14_realizarLevantamiento"), ("(por defecto)", "gwXor_13")]),
    ("gwXor_9", "G09", "`requierePreguntas` (process variable, de `ctr_32_analizarLicitacion`)",
     [("requierePreguntas = sí", "33_elaborarPreguntas"), ("(por defecto)", "gwXor_13")]),
    ("gwXor_10", "G10", "`respuestasCompletas` (process variable, de `ctr_34_esperarRespuestas`)",
     [("respuestasCompletas = no", "35_definirSupuestos"), ("(por defecto)", "gwXor_13")]),
    ("gwXor_16", "G16", "`entregaDocumentos` (process variable, de `ctr_14_realizarLevantamiento`)",
     [("entregaDocumentos = sí", "42_analizarDocumentos"), ("(por defecto)", "gwXor_13")]),
    ("gwXor_13", "G13", "`requiereViabilidad` (process variable, de la última tarea del consultor antes de la "
                        "compuerta)",
     [("requiereViabilidad = sí", "38_validarViabilidad"), ("(por defecto)", "31_prepararAnalisis")]),
    ("gwXor_14", "G14", "`esViable` (process variable, de `ctr_38_validarViabilidad`)",
     [("esViable = no", "39_notificarNoViabilidad"), ("(por defecto)", "31_prepararAnalisis")]),
    ("gwXor_7", "G07", "`alcanceCorrecto` (process variable, de `ctr_21_validarAlcance`)",
     [("alcanceCorrecto = no", "22_ajustarPropuesta"), ("(por defecto)", "24_enviarPropuestaFormal")]),
    ("gwXor_8", "G08", "`propuestaAprobada` (process variable, de `ctr_25_confirmarPropuesta`)",
     [("propuestaAprobada = sí", "27_cerrarGanado"), ("(por defecto)", "26_registrarRechazo")]),
]
GID = {g[0]: g for g in G}

# Transiciones simples (las de compuerta se insertan tras la que llega a la compuerta por primera vez)
SIMPLES = [
    ("inicio", "3_consultarTicket"), ("3_consultarTicket", "4_verificarDisponibilidad"),
    ("4_verificarDisponibilidad", "5_asignarConsultor"), ("5_asignarConsultor", "6_actualizarTicket"),
    ("6_actualizarTicket", "7_analizarRequerimiento"), ("7_analizarRequerimiento", "gwXor_1"),
    ("8_identificarProducto", "gwXor_2"),
    ("9_prepararDemoCliente", "12_ejecutarDemo"), ("10_prepararDemoGuia", "12_ejecutarDemo"),
    ("11_construirDocumentosEjemplo", "12_ejecutarDemo"), ("12_ejecutarDemo", "gwXor_5"),
    ("13_registrarNoContinua", "fin_descartada"),
    ("32_analizarLicitacion", "gwXor_9"), ("33_elaborarPreguntas", "37_radicarPreguntas"),
    ("37_radicarPreguntas", "34_esperarRespuestas"), ("34_esperarRespuestas", "gwXor_10"),
    ("evTimer_1", "35_definirSupuestos"), ("35_definirSupuestos", "gwXor_13"),
    ("14_realizarLevantamiento", "gwXor_16"), ("42_analizarDocumentos", "gwXor_13"),
    ("38_validarViabilidad", "gwXor_14"), ("39_notificarNoViabilidad", "fin_noViable"),
    ("31_prepararAnalisis", "15_cargarInsumos"), ("15_cargarInsumos", "16_generarArtefactos"),
    ("16_generarArtefactos", "17_revisarArtefactos"), ("17_revisarArtefactos", "36_revisarEstimacion"),
    ("36_revisarEstimacion", "18_cargarArtefactos"), ("18_cargarArtefactos", "40_entregarAVentas"),
    ("40_entregarAVentas", "19_socializarPropuesta"), ("19_socializarPropuesta", "41_presentarPropuestaTecnica"),
    ("41_presentarPropuestaTecnica", "20_presentarPropuestaEconomica"),
    ("20_presentarPropuestaEconomica", "21_validarAlcance"), ("21_validarAlcance", "gwXor_7"),
    ("22_ajustarPropuesta", "23_validarAjustes"), ("23_validarAjustes", "41_presentarPropuestaTecnica"),
    ("24_enviarPropuestaFormal", "25_confirmarPropuesta"), ("25_confirmarPropuesta", "gwXor_8"),
    ("26_registrarRechazo", "fin_rechazada"), ("27_cerrarGanado", "28_presentarAlcanceTraspaso"),
    ("28_presentarAlcanceTraspaso", "29_entregarCarpeta"), ("29_entregarCarpeta", "30_iniciarEjecucion"),
    ("30_iniciarEjecucion", "fin_ejecucion"),
]
TR, hechas = [], set()


def emitir_compuerta(gid):
    if gid in hechas:
        return
    hechas.add(gid)
    for cond, dest in GID[gid][3]:
        TR.append((gid, dest, cond))
        if dest in GID:
            emitir_compuerta(dest)


for d, h in SIMPLES:
    TR.append((d, h, "—"))
    if h in GID:
        emitir_compuerta(h)
PRED = {}
for d, h, _ in TR:
    PRED.setdefault(h, []).append(d)

FINES = [("fin_descartada", "EE1", "Oportunidad descartada"), ("fin_rechazada", "EE2", "Propuesta rechazada"),
         ("fin_ejecucion", "EE3", "Proyecto en ejecución"), ("fin_noViable", "EE4", "Requerimiento no viable")]

# Conectores: tarea, conector, definicion, momento, entradas [(nombre, texto)], salidas [(destino, salida)], fallo
HS = [("urlBase", "la dirección base de la API de HubSpot del entorno"),
      ("rutaTickets", "la ruta de tickets de la API de HubSpot del entorno"),
      ("ticketId", "el identificador del ticket del caso")]


def actualizar(tarea_, momento, stage_txt, owner_txt, fallo):
    return (tarea_, "conn_hubspotActualizar", "hubspot-ticket-actualizar", momento,
            HS + [("stageId", stage_txt), ("ownerId", owner_txt)], [], fallo)


SIN_OWNER = "vacío (no cambia el responsable)"
IGN = "`IGNORE`: el caso sigue si HubSpot falla; lo corrige la reconciliación"
FAIL = "la tarea queda en fallo (comportamiento por defecto de Bonita) y se reintenta desde la administración"
C = [
    ("3_consultarTicket", "conn_hubspotLeer", "hubspot-ticket-leer", "entrada", HS,
     [("Preventa.asunto", "asunto"), ("Preventa.descripcion", "descripcion"),
      ("Preventa.comercialCreador", "comercialCreador"), ("Preventa.tipoRequerimiento", "tipoRequerimiento"),
      ("Preventa.medpicc", "medpicc"), ("Preventa.linkRepositorio", "linkRepositorio")], FAIL),
    actualizar("6_actualizarTicket", "entrada", "el stage «En validación» del entorno",
               "el owner de HubSpot del consultor asignado", FAIL),
    actualizar("13_registrarNoContinua", "salida", "el stage «Closed» del entorno", SIN_OWNER, IGN),
    actualizar("37_radicarPreguntas", "salida", "el stage «En espera información del lead» del entorno", SIN_OWNER,
               IGN),
    actualizar("14_realizarLevantamiento", "entrada", "el stage «En espera información del lead» del entorno",
               SIN_OWNER, IGN),
    actualizar("39_notificarNoViabilidad", "salida", "el stage «Closed» del entorno", SIN_OWNER, IGN),
    actualizar("31_prepararAnalisis", "entrada", "el stage «Asignado/En diseño» del entorno", SIN_OWNER, IGN),
    ("16_generarArtefactos", "conn_agenteIA", "agente-ia-preventa", "entrada",
     [("url", "la dirección del servicio del Agente IA de Preventa del entorno"),
      ("ticketId", "el identificador del ticket del caso"),
      ("enlaceInsumos", "el enlace al paquete de insumos del caso")],
     [("Preventa.enlacePropuesta", "enlacePropuesta"), ("Preventa.enlaceEstimacion", "enlaceEstimacion"),
      ("Preventa.enlacePresentacion", "enlacePresentacion")], FAIL),
    actualizar("40_entregarAVentas", "entrada", "el stage «Entregado a ventas» del entorno", SIN_OWNER, FAIL),
    actualizar("26_registrarRechazo", "salida", "el stage «Closed» del entorno", SIN_OWNER, IGN),
    actualizar("30_iniciarEjecucion", "salida", "el stage «Closed» del entorno", SIN_OWNER, IGN),
]
CONN_DE = {}
for c in C:
    CONN_DE.setdefault(c[0], []).append(c[1])

PV = [("informacionSuficiente", "BOOLEAN", "—", "`gwXor_6` (de `ctr_7_analizarRequerimiento` y `ctr_12_ejecutarDemo`)"),
      ("requiereViabilidad", "BOOLEAN", "`false`", "`gwXor_13` (la fija la última tarea del consultor antes de la compuerta)"),
      ("clienteAvanza", "BOOLEAN", "—", "`gwXor_5` (de `ctr_12_ejecutarDemo`)"),
      ("requierePreguntas", "BOOLEAN", "—", "`gwXor_9` (de `ctr_32_analizarLicitacion`)"),
      ("respuestasCompletas", "BOOLEAN", "—", "`gwXor_10` (de `ctr_34_esperarRespuestas`)"),
      ("entregaDocumentos", "BOOLEAN", "—", "`gwXor_16` (de `ctr_14_realizarLevantamiento`)"),
      ("esViable", "BOOLEAN", "—", "`gwXor_14` (de `ctr_38_validarViabilidad`)"),
      ("alcanceCorrecto", "BOOLEAN", "—", "`gwXor_7` (de `ctr_21_validarAlcance`)"),
      ("propuestaAprobada", "BOOLEAN", "—", "`gwXor_8` (de `ctr_25_confirmarPropuesta`)"),
      ("totalDisponibles", "INTEGER", "—", "`4_verificarDisponibilidad` (salida) y `5_asignarConsultor` (round robin)")]

FASES = {1: "Fase 1 — Inicio, registro y asignación", 2: "Fase 2 — Demo", 3: "Fase 3 — Licitación",
         4: "Fase 4 — Validación de información, viabilidad técnica y preparación de insumos",
         5: "Fase 5 — Construcción y estimación de la oferta", 6: "Fase 6 — Socialización, sustentación y ajustes",
         7: "Fase 7 — Confirmación, cierre y traspaso a ejecución"}
SERV_OPS = {
    "3_consultarTicket": ("`asignacion-directa` / ninguno; las salidas del conector escriben los datos del ticket "
                          "(`bpmn.md` → Conectores por tarea)",
                          "`Preventa.asunto`, `Preventa.descripcion`, `Preventa.comercialCreador`, "
                          "`Preventa.tipoRequerimiento`, `Preventa.medpicc`, `Preventa.linkRepositorio`", "—"),
    "4_verificarDisponibilidad": ("`asignacion-directa` / ninguno; script `pv totalDisponibles` ← `cantidad de "
                                  "consultores activos del catálogo ConsultorPreventa` "
                                  "(`op_4_verificarDisponibilidad.totalDisponibles`)", "—", "`totalDisponibles`"),
    "5_asignarConsultor": ("`asignacion-directa` / `Preventa.estado` = `asignada`; script `Preventa.consultor` ← "
                           "`usuario del consultor activo que sigue en el turno: posición (ultimoIndice + 1) módulo "
                           "totalDisponibles sobre los activos ordenados por usuario` "
                           "(`op_5_asignarConsultor.consultor`); script `Preventa.consultorOwnerId` ← `owner de "
                           "HubSpot del consultor elegido` (`op_5_asignarConsultor.consultorOwnerId`); script "
                           "`TurnoAsignacion.ultimoIndice` ← `posición del consultor elegido` "
                           "(`op_5_asignarConsultor.ultimoIndice`)",
                           "`Preventa.estado`, `Preventa.consultor`, `Preventa.consultorOwnerId`, "
                           "`TurnoAsignacion.ultimoIndice`", "—"),
    "6_actualizarTicket": ("— (sin escritura)", "—", "—"),
    "16_generarArtefactos": ("`asignacion-directa` / ninguno; las salidas del conector escriben los enlaces de los "
                             "borradores (`bpmn.md` → Conectores por tarea)",
                             "`Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, "
                             "`Preventa.enlacePresentacion`", "—"),
    "40_entregarAVentas": ("`asignacion-directa` / `Preventa.estado` = `entregadaAVentas`", "`Preventa.estado`",
                           "—"),
}


def bt(x):
    return "`" + x + "`"


def humanas():
    return [t for t in T if t["tipo"] == "human"]


def pagina(id_):
    partes = id_.split("_")
    return "frm" + "".join(p[:1].upper() + p[1:] for p in partes)


# =============================================================================================== bpmn.md
def bpmn():
    o = []
    a = o.append
    a("---\nactualizado: " + HOY + "\ncapa: 1\nmotor: Bonita\nderiva_de: docs/07-bonita/insumo-preventa/"
      "Proceso_Preventa_Bonita.bpmn, docs/07-bonita/insumo-preventa/Documento Proceso Diseño de soluciones.docx, "
      "docs/07-bonita/bdm.md\npool: " + POOL + "\nversion: " + VER + "\n---\n")
    a("# Capa 1 — Proceso BPMN para Bonita — Gestión de Preventa\n")
    a("> Fuente: el flujo de diseño de soluciones (preventa) entregado el 2026-11-12: `insumo-preventa/"
      "Proceso_Preventa_Bonita.bpmn` (grafo) y el manual «Gestión de Preventa» (paso a paso). Cada nodo cita su ID "
      "del insumo (`A07`, `G01`, `EE1`…) en la columna «Fuente». Nada aquí se inventa: lo que el insumo no define "
      "está en «Pendientes de definición».\n")
    a("## Convenciones\n")
    a("- **IDs**: tareas `<N>_<accion>`, donde `N` es el número de la actividad del insumo (`A07` → "
      "`7_analizarRequerimiento`); compuertas `gwXor_<n>`, donde `n` es el número de la compuerta del insumo (`G01` "
      "→ `gwXor_1`); eventos `inicio`, `evTimer_1` y `fin_*`.\n"
      "- **Uniones**: las compuertas del insumo que solo unen caminos (`G04`, `G11`, `G12`, `G15`, `G17`) no son "
      "nodos: su unión se expresa con varias transiciones de entrada al nodo siguiente (unión exclusiva implícita "
      "de BPMN). No cambia el comportamiento.\n"
      "- **Antes del caso**: `SE1`, `A01` (registrar oportunidad y MEDDPICC) y `A02` (generar ticket) ocurren en "
      "HubSpot antes de que exista el caso: el caso se instancia cuando se crea el ticket (webhook `ticket.creation` "
      "+ middleware Ofelia). Son el disparador del evento `inicio`, no tareas del pool.\n"
      "- **Tipo de tarea** (nombres de Bonita): `human`, `service`, `script`, `call activity`.\n"
      "- **Compuertas**: `exclusive (XOR)`. Toda exclusiva declara una **salida por defecto**.\n"
      "- **Salidas de compuerta**: «condición → destino» (destino entre backticks) separadas por «; », en orden de "
      "evaluación; la salida por defecto va al final con la condición «(por defecto)». La condición es el mismo "
      "texto que la columna «Condición» de la transición; su Groovy está en `docs/08-construccion/expresiones.md`.\n"
      "- **Ticket y lead son objetos distintos de HubSpot**: Bonita solo escribe el **ticket** (pipeline «Mesa de "
      "preventa»). Las etapas del **lead** («Preventa / Solución GH», «Propuesta enviada», «Negociación/Ajustes», "
      "«Cerrado ganado») las mueve Comercial a mano en HubSpot, como dice el manual.\n")
    a("## Pool y lanes\n")
    a("### " + P + "\n")
    a("| Lane | Actor (actores-proceso.md) | Grupo/rol (bdm.md → Organización) | Actor Bonita | Actor filter |")
    a("|---|---|---|---|---|")
    a("| Cliente | Comercial | `/trycore/comercial`; rol `comercial` | `comercial` | — |")
    a("| Comercial | Comercial | `/trycore/comercial`; rol `comercial` | `comercial` | — |")
    a("| Orquestador | Orquestador | `/trycore/integracion`; rol `integracion` | `orquestador` | — |")
    a("| Consultor Preventa | ConsultorPreventa | `/trycore/preventa`; rol `consultor` | `consultorPreventa` | "
      "`filtroConsultorDelCaso` |")
    a("| Líder Técnico | LiderTecnico | `/trycore/tecnologia`; rol `liderTecnico` | `liderTecnico` | — |")
    a("| Agente IA | Sistema | — | — | No aplica |")
    a("| Equipo interno | EquipoInterno | `/trycore/operaciones`; rol `procesos` | `equipoInterno` | — |\n")
    a("**Iniciador**: `Orquestador`.\n")
    a("Los 7 carriles del insumo se conservan. `Cliente` no tiene usuarios en Bonita: sus dos tareas (`21_"
      "validarAlcance`, `25_confirmarPropuesta`) las completa Comercial, que registra la decisión del cliente. "
      "`Orquestador` es el carril «Orquestador Ofelia + HubSpot»: su actor es el usuario técnico con el que el "
      "middleware instancia el caso. `Agente IA` solo tiene una tarea de servicio y no lleva actor.\n")
    a("## Diagrama\n")
    a("### " + P + "\n")
    a("```mermaid\nflowchart LR")
    a("  inicio([inicio])")
    for t in T:
        a("  n" + t["id"] + "[\"" + t["id"] + "\\n(" + t["tipo"] + ")\"]")
    for g in G:
        a("  n" + g[0] + "{\"" + g[0] + "\"}")
    a("  nevTimer_1((\"evTimer_1\\n(timer)\"))")
    for f in FINES:
        a("  n" + f[0] + "(((" + f[2] + ")))")
    a("  n34_esperarRespuestas -. \"borde (interruptor)\" .- nevTimer_1")
    for d, h, c in TR:
        dd = "inicio" if d == "inicio" else "n" + d
        a("  " + dd + (" --> " if c == "—" else " -- \"" + c.replace("(por defecto)", "default") + "\" --> ")
          + "n" + h)
    a("```\n")
    a("## Inventario de tareas\n")
    a("### " + P + "\n")
    a("| ID | Nombre | Tipo Bonita | Lane / actor | Fuente en §12 | Contrato (capa 2) | Conector / comunicación | "
      "Operaciones previstas | Notas |")
    a("|---|---|---|---|---|---|---|---|---|")
    for t in T:
        ctr = bt("ctr_" + t["id"]) if t["tipo"] == "human" else "—"
        con = "; ".join(bt(x) + " (síncrono)" for x in sorted(set(CONN_DE.get(t["id"], [])))) or "—"
        nota = t["nota"] or ("Lane técnica" if t["tipo"] != "human" else "—")
        a("| " + bt(t["id"]) + " | " + t["nombre"] + " | " + t["tipo"] + " | " + t["lane"] + " | insumo `"
          + t["src"] + "` (" + FASES[t["fase"]].split(" — ")[0] + ") | " + ctr + " | " + con
          + " | según plantilla | " + nota + " |")
    a("\n## Compuertas\n")
    a("### " + P + "\n")
    a("| ID | Tipo | Después de | Variable o atributo que decide | Salidas (condición → destino) | Salida por "
      "defecto |")
    a("|---|---|---|---|---|---|")
    for gid, src, decide, sal in G:
        desp = "; ".join(bt(x) for x in sorted(PRED[gid]))
        sals = "; ".join(c + " → " + bt(d) for c, d in sal)
        a("| " + bt(gid) + " | exclusive (XOR) | " + desp + " | " + decide + " | " + sals + " | " + bt(sal[-1][1])
          + " |")
    a("\nTrazabilidad con el insumo: " + ", ".join(bt(g[0]) + " = `" + g[1] + "`" for g in G) + ".\n")
    a("## Eventos\n")
    a("### " + P + "\n")
    a("| ID | Tipo | Posición (inicio / intermedio / borde de `<tarea>` / fin) | Disparador o duración | Fuente en "
      "§12 | Destino |")
    a("|---|---|---|---|---|---|")
    a("| `inicio` | none | inicio | instanciación por el actor `Orquestador` al crearse el ticket en HubSpot "
      "(`ctr_instanciacion`) | insumo `SE1`, `A01`, `A02` | `3_consultarTicket` |")
    a("| `evTimer_1` | timer | borde de `34_esperarRespuestas` (interruptor) | `param_plazoRespuestasMs` | insumo "
      "`BE1` (vence plazo de respuestas) | `35_definirSupuestos` |")
    for f in FINES:
        a("| " + bt(f[0]) + " | none | fin | — | insumo `" + f[1] + "` (" + f[2] + ") | — |")
    a("\n## Transiciones\n")
    a("### " + P + "\n")
    a("| Desde | Hacia | Condición (si aplica) | Variable que la evalúa | Δestado (catalogo-estados.md) |")
    a("|---|---|---|---|---|")
    for d, h, c in TR:
        var = "—"
        if d in GID:
            var = GID[d][2].split(" (")[0]
        a("| " + bt(d) + " | " + bt(h) + " | " + c + " | " + var + " | — |")
    a("\n## Conectores por tarea\n")
    a("### " + P + "\n")
    a("| Tarea | Conector (catalogo-conectores.md) | Modo | Momento (entrada / salida de la tarea) | Entrada (process "
      "variable o atributo) | Salida (destino) | Manejo de fallo |")
    a("|---|---|---|---|---|---|---|")
    for tar, cid, defi, mom, ents, sals, fallo in C:
        e = "; ".join(bt(n) + " ← " + bt(tx) + " (" + bt(cid + "." + tar + "." + n) + ")" for n, tx in ents)
        s = "; ".join(bt(d) + " ← " + bt(x) for d, x in sals) or "—"
        a("| " + bt(tar) + " | " + bt(cid) + " (propio " + bt(defi) + ") | síncrono | " + mom + " | " + e + " | " + s
          + " | " + fallo + " |")
    a("\nLos tres conectores son **propios** del proyecto (`bonita-project/extensions/preventa-conectores`): REST "
      "nativo de Bonita hacia HubSpot y hacia el servicio del Agente IA; no se usa el conector oficial "
      "Bonita–HubSpot (Beta, sin tickets). El token de la Private App de HubSpot **no es una entrada**: la "
      "implementación lo lee de la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN` (nunca en el repositorio ni en "
      "parámetros). En «Salida (destino)», la parte derecha de cada `←` es la salida del conector.\n")
    a("### Mapa estado del caso → stage del ticket (propuesta, pendiente de confirmación)\n")
    a("| Momento del caso | Tarea que sincroniza | Stage del ticket (pipeline «Mesa de preventa», id `0`) | "
      "`stageId` real | Parámetro |")
    a("|---|---|---|---|---|")
    a("| Ticket creado (caso instanciado) | — (lo crea HubSpot) | Solicitud recibida | `1` | — |")
    a("| Consultor asignado | `6_actualizarTicket` (además fija `hubspot_owner_id`) | En validación | `2` | "
      "`param_stageEnValidacion` |")
    a("| Levantamiento con el cliente o espera de respuestas de la entidad | `14_realizarLevantamiento`, "
      "`37_radicarPreguntas` | En espera información del lead | `1425810257` | `param_stageEnEspera` |")
    a("| Preparación de insumos y construcción de la oferta | `31_prepararAnalisis` | Asignado/En diseño | `3` | "
      "`param_stageEnDiseno` |")
    a("| Artefactos cargados en el lead | `40_entregarAVentas` | Entregado a ventas | `1425810258` | "
      "`param_stageEntregado` |")
    a("| Fin del caso (descartada, no viable, rechazada, en ejecución) | `13_registrarNoContinua`, "
      "`39_notificarNoViabilidad`, `26_registrarRechazo`, `30_iniciarEjecucion` | Closed | `4` | "
      "`param_stageCerrado` |\n")
    a("El manual solo nombra dos escrituras automáticas (`A06` y `A40`); las demás filas aplican la regla del "
      "proyecto «cada transición se refleja como stage del ticket, incluidas las rutas de retorno» sobre los 6 "
      "stages reales de la Fase 0. Los `stageId` son parámetros de proceso: cambiar el mapa no toca el diagrama.\n")
    a("## Process variables (insumo de construcción)\n")
    a("### " + P + "\n")
    a("| Variable | Tipo | Valor por defecto | Transitoria | Justificación (compuerta, conector o transición que la "
      "necesita) |")
    a("|---|---|---|---|---|")
    for n, tp, d, j in PV:
        a("| " + bt(n) + " | " + tp + " | " + d + " | no | " + j + " |")
    a("\n## Documentos del proceso\n")
    a("### " + P + "\n")
    a("| Documento | Múltiple | Tarea que lo aporta | Tareas que lo leen | Fuente en §12 |")
    a("|---|---|---|---|---|")
    a(FILL(5))
    a("\nLos artefactos (insumos, propuesta, estimación, presentación, carpeta) se guardan como **enlaces** al "
      "repositorio de preventa (propiedad `link_repositorio_preventa` del ticket), no como documentos de Bonita.\n")
    a("## Verificaciones de diseño (las revisa el gate)\n")
    a("- [x] Toda actividad, espera y conector del insumo tiene fila en el inventario (42 actividades: 40 tareas, y "
      "`A01`/`A02` como disparador del inicio; `RT1` como `34_esperarRespuestas`).\n"
      "- [ ] Ninguna lane con dos tareas humanas consecutivas. **No se cumple por diseño del insumo**: el carril "
      "Consultor Preventa encadena, p. ej., `9→12`, `31→15`, `19→41` y `28→29`. Se conserva el insumo aprobado; "
      "fusionar tareas sería cambiar el proceso (ver Pendientes).\n"
      "- [x] Toda compuerta con todas sus salidas y una por defecto.\n"
      "- [x] Toda transición condicional nombra la variable que la evalúa.\n"
      "- [x] Toda tarea humana tiene su `ctr_*` reservado.\n"
      "- [x] Toda tarea de servicio cita un conector con su modo.\n")
    a("## Pendientes de definición\n")
    a("- **Espera de respuestas de la entidad (`RT1`)**: el insumo la modela como *receive task* con mensaje; el "
      "generador solo soporta tareas `human`, `service`, `script` y `call activity`. Se modela como tarea humana "
      "`34_esperarRespuestas` (el consultor registra las respuestas cuando llegan) con el timer de borde interruptor "
      "`evTimer_1`. **Requiere confirmación** (parada del arnés: elemento no soportado).\n"
      "- **Plazo de respuestas**: `param_plazoRespuestasMs` es un valor por entorno; en la práctica el plazo es de "
      "cada licitación. Falta decidir si basta un plazo fijo o debe capturarse por caso. `[no verificado]`\n"
      "- **Mapa estado → stage del ticket**: propuesta de este documento; lo confirma el líder técnico / Laura.\n"
      "- **Regla de disponibilidad de consultores (`A04`)**: el manual dice «regla de negocio» sin definirla. Se "
      "toma «consultor activo en el catálogo `ConsultorPreventa`» (excluye al bot `88449388`). Sin camino en el "
      "insumo para «ningún consultor disponible»: la tarea `5_asignarConsultor` quedaría en fallo.\n"
      "- **Agente IA (`A16`)**: el insumo no define cómo se invoca a Claude (servicio, contrato, tiempos). Se modela "
      "un conector propio hacia `param_urlAgenteIA`. `[no verificado]`\n"
      "- **Versión de la API de HubSpot**: la Fase 0 respondió 200 en `/crm/v3/...`; `2026-09` figura como vigente. "
      "La ruta es el parámetro `param_hubspotRutaTickets`. `[no verificado]`\n"
      "- **Job de reconciliación diaria** Bonita vs HubSpot (arquitectura acordada): no es parte de este pool; "
      "falta decidir dónde vive (middleware Ofelia o proceso propio con inicio por timer, que el generador no "
      "soporta).\n"
      "- **Dos tareas humanas consecutivas en una lane**: regla de diseño que el insumo no cumple; decidir si se "
      "acepta el insumo tal cual (lo documentado) o se fusionan tareas.")
    return "\n".join(o) + "\n"


# ========================================================================================== contratos.md
def lectura(t):
    base = ["`Preventa.ticketId`", "`Preventa.asunto`", "`Preventa.estado`"]
    extra = {
        "7_analizarRequerimiento": ["`Preventa.descripcion`", "`Preventa.medpicc`", "`Preventa.tipoRequerimiento`",
                                    "`Preventa.comercialCreador`", "`Preventa.linkRepositorio`"],
        "37_radicarPreguntas": ["`Preventa.preguntasAclaratorias`"],
        "34_esperarRespuestas": ["`Preventa.preguntasAclaratorias`"],
        "35_definirSupuestos": ["`Preventa.preguntasAclaratorias`", "`Preventa.respuestasEntidad`"],
        "38_validarViabilidad": ["`Preventa.descripcion`", "`Preventa.medpicc`"],
        "39_notificarNoViabilidad": ["`Preventa.conceptoViabilidad`"],
        "15_cargarInsumos": ["`Preventa.enlaceInsumos`"],
        "17_revisarArtefactos": ["`Preventa.enlacePropuesta`", "`Preventa.enlaceEstimacion`",
                                 "`Preventa.enlacePresentacion`"],
        "36_revisarEstimacion": ["`Preventa.enlacePropuesta`", "`Preventa.enlaceEstimacion`"],
        "18_cargarArtefactos": ["`Preventa.enlacePropuesta`", "`Preventa.enlaceEstimacion`",
                                "`Preventa.enlacePresentacion`"],
        "19_socializarPropuesta": ["`Preventa.enlacePropuesta`", "`Preventa.enlaceEstimacion`",
                                   "`Preventa.enlacePresentacion`"],
        "41_presentarPropuestaTecnica": ["`Preventa.enlacePropuesta`", "`Preventa.enlacePresentacion`"],
        "20_presentarPropuestaEconomica": ["`Preventa.enlacePropuesta`", "`Preventa.enlaceEstimacion`"],
        "21_validarAlcance": ["`Preventa.enlacePropuesta`"],
        "22_ajustarPropuesta": ["`Preventa.observacionAlcance`", "`Preventa.enlacePropuesta`"],
        "23_validarAjustes": ["`Preventa.ajustesPropuesta`", "`Preventa.enlacePropuesta`"],
        "24_enviarPropuestaFormal": ["`Preventa.enlacePropuesta`"],
        "25_confirmarPropuesta": ["`Preventa.enlacePropuesta`"],
        "28_presentarAlcanceTraspaso": ["`Preventa.enlacePropuesta`", "`Preventa.enlaceEstimacion`"],
        "30_iniciarEjecucion": ["`Preventa.enlaceCarpeta`"],
    }
    return base + extra.get(t["id"], [])


def contratos():
    o = []
    a = o.append
    hs = humanas()
    a("---\nactualizado: " + HOY + "\ncapa: 2\nmotor: Bonita\nderiva_de: docs/07-bonita/bpmn.md, "
      "docs/07-bonita/bdm.md, docs/07-bonita/insumo-preventa/Documento Proceso Diseño de soluciones.docx\n"
      "total_contratos: " + str(len(hs) + 1) + "\n---\n")
    a("# Capa 2 — Contratos y operaciones — Gestión de Preventa\n")
    a("> Fuente: el manual «Gestión de Preventa» (paso a paso por fase, columna «Entregables / Notas») y "
      "`bpmn.md`. Un contrato por tarea humana y uno de instanciación. Los inputs son los datos mínimos que la tarea "
      "debe dejar para que el flujo decida (compuertas) o para que el siguiente actor trabaje; una tarea que solo se "
      "«da por hecha» tiene contrato sin inputs.\n")
    a("## Convenciones\n")
    a("- **ID de contrato**: `ctr_instanciacion` y `ctr_<id-tarea>` (reservados en `bpmn.md`).\n"
      "- **Tipo de input**: `TEXT`, `BOOLEAN` (tipos de contrato de Bonita 2026.2).\n"
      "- **Destino**: el atributo del objeto de negocio (`Objeto.atributo`) o la process variable "
      "(`pv <variable>`) que la operación escribe con ese input.\n"
      "- **Constraint**: expresión sobre los inputs, con nombre y mensaje; su Groovy va en "
      "`docs/08-construccion/expresiones.md` (`ctr_<contrato>.<constraint>`).\n"
      "- **Operación**: igual a la plantilla de persistencia `asignacion-directa` de `bdm.md` salvo los literales "
      "indicados. Un destino escrito por un script lleva su marca (`op_<tarea>.<atributo>`).\n"
      "- **`requiereViabilidad`**: la decisión de `gwXor_13` (`G13`) no tiene tarea propia en el insumo; la fija, "
      "como input opcional, la última tarea del consultor antes de la compuerta. Sin valor, vale `false`.\n")
    a("## Contrato de instanciación — `ctr_instanciacion`\n")
    a("### " + P + "\n")
    a("Formulario asociado (capa 3): `frm_instanciacion` (`No form`). Fuente: el middleware Ofelia instancia el "
      "caso por la API REST al recibir el webhook `ticket.creation` de HubSpot.\n")
    a("| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (Tarea de Proceso → "
      "Entradas) |")
    a("|---|---|---|---|---|---|---|")
    a("| `ticketId` | TEXT | no | sí | — | `Preventa.ticketId` | webhook `ticket.creation` → `objectId` del ticket |\n")
    a("| Constraint | Expresión (lenguaje natural o Groovy) | Mensaje de error | AC que la origina |")
    a("|---|---|---|---|")
    a("| `ticketId_presente` | ticketId no está vacío | El identificador del ticket es obligatorio | manual, Fase 1 "
      "(`A02`, ticket de preventa creado) |\n")
    a("Operaciones al instanciar: según plantilla `asignacion-directa` con literales: `Preventa.estado` = "
      "`recibida`; crea `Preventa` con el `ticketId` del input. La idempotencia por ticket la da la unique "
      "constraint de `Preventa.ticketId` (un segundo caso del mismo ticket no se crea).\n")
    a("## Contratos de tarea humana\n")
    for t in hs:
        actor = {L_CLI: "Comercial (en nombre del Cliente)", L_COM: "Comercial", L_CON: "Consultor Preventa",
                 L_LT: "Líder Técnico", L_INT: "Equipo interno"}[t["lane"]]
        a("### `ctr_" + t["id"] + "` — " + t["nombre"] + "\n")
        a("- **Tarea** (`bpmn.md`): `" + t["id"] + "`, actor " + actor + ".")
        a("- **Formulario asociado** (capa 3): `frm_" + t["id"] + "`.")
        a("- **Tarea de Proceso**: manual «Gestión de Preventa», " + FASES[t["fase"]] + " (`" + t["src"] + "`).")
        a("- **Δestado**: " + ("→ `" + t["lit"] + "`" if t["lit"] else "— (no cambia `Preventa.estado`)") + ".\n")
        a("| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / "
          "Salidas) |")
        a("|---|---|---|---|---|---|---|")
        if t["inputs"]:
            for n, tp, ob, dest, w, et in t["inputs"]:
                a("| " + bt(n) + " | " + tp + " | no | " + ("sí" if ob else "no") + " | — | " + bt(dest)
                  + " | insumo `" + t["src"] + "` → " + et + " |")
        else:
            a(FILL(7))
        a("\n| Constraint | Expresión | Mensaje de error | AC que la origina |")
        a("|---|---|---|---|")
        if t["cons"]:
            for n, ex, msg in t["cons"]:
                a("| " + bt(n) + " | " + ex + " | " + msg + " | insumo `" + t["src"] + "` |")
        else:
            a(FILL(4))
        a("\n**Datos de solo lectura que el formulario consulta** (no son inputs): " + ", ".join(lectura(t))
          + " (business variable `preventa` del caso).\n")
        lit = "`Preventa.estado` = `" + t["lit"] + "`" if t["lit"] else "ninguno"
        attrs = [d for _, _, _, d, _, _ in t["inputs"] if d.startswith("Preventa.")]
        pvs = [d[3:] for _, _, _, d, _, _ in t["inputs"] if d.startswith("pv ")]
        escribe = ("escribe " + ", ".join(bt(x) for x in attrs)) if attrs else "no escribe atributos desde inputs"
        pvt = ("process variables actualizadas: " + ", ".join(bt(x) for x in pvs)) if pvs else \
            "no actualiza process variables"
        a("**Operaciones**: plantilla `asignacion-directa`; literales: " + lit + "; " + escribe + "; " + pvt
          + ". Desviación de la plantilla: ninguna.\n")
    a("## Operaciones de tareas de servicio y script\n")
    a("| Tarea | Conector | Operaciones (plantilla / literales) | Escribe | Process variables |")
    a("|---|---|---|---|---|")
    for t in T:
        if t["tipo"] == "human":
            continue
        ops, esc, pv = SERV_OPS[t["id"]]
        con = ", ".join(bt(x) for x in sorted(set(CONN_DE.get(t["id"], [])))) or "—"
        a("| " + bt(t["id"]) + " | " + con + " | " + ops + " | " + esc + " | " + pv + " |")
    a("\n## Matriz tarea ↔ contrato ↔ formulario (la revisa el gate)\n")
    a("| Tarea humana | Contrato | Formulario (capa 3) | Inputs | Constraints |")
    a("|---|---|---|---|---|")
    a("| (instanciación) | `ctr_instanciacion` | `frm_instanciacion` | 1 | 1 |")
    for t in hs:
        a("| " + bt(t["id"]) + " | " + bt("ctr_" + t["id"]) + " | " + bt("frm_" + t["id"]) + " | "
          + str(len(t["inputs"])) + " | " + str(len(t["cons"])) + " |")
    a("\n## Cobertura de las reglas de validación de los AC\n")
    a("| Tarea de Proceso | Regla del AC | Cubierta por | Tipo |")
    a("|---|---|---|---|")
    a("| `A02` | Un ticket genera un solo caso | unique constraint `Preventa.ticketId` | BDM |")
    for t in hs:
        for n, ex, msg in t["cons"]:
            a("| `" + t["src"] + "` | " + ex + " | " + bt(n) + " | constraint de contrato |")
    a("| Punto de control 3 | Viabilidad validada por el Líder Técnico cuando el requerimiento lo amerita | "
      "`gwXor_13`, `38_validarViabilidad`, `gwXor_14` | flujo |")
    a("| Punto de control 5 | Revisión humana de los artefactos generados por el agente IA | `17_revisarArtefactos` "
      "| flujo |")
    a("| Punto de control 6 | Estimación validada con el Líder Técnico antes de socializar | `36_revisarEstimacion` "
      "antes de `19_socializarPropuesta` | flujo |")
    a("| Punto de control 7 | Propuesta socializada con Comercial antes de presentarla al cliente | "
      "`19_socializarPropuesta` antes de `41_presentarPropuestaTecnica` | flujo |\n")
    a("## Pendientes de definición\n")
    a("- Los inputs de cada tarea son los mínimos que el flujo necesita; el manual no trae criterios de aceptación "
      "por tarea (no hay `docs/04-tareas-proceso/`). Si negocio quiere capturar más datos por tarea, se reabre esta "
      "capa.\n"
      "- `33_elaborarPreguntas`: el manual dice «cargarlas en el ticket»; aquí las preguntas quedan en el caso "
      "(`Preventa.preguntasAclaratorias`). Falta decidir si además Bonita debe escribirlas como nota del ticket en "
      "HubSpot. `[no verificado]`")
    return "\n".join(o) + "\n"


# ================================================================================= matriz-formularios.md
def matriz():
    o = []
    a = o.append
    hs = humanas()
    a("---\nactualizado: " + HOY + "\ncapa: 3\nmotor: Bonita\nderiva_de: docs/07-bonita/contratos.md, "
      "docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/00-parametros/catalogo-parametros.md\n"
      "total_formularios: " + str(len(hs) + 2) + "\numbral_campos_unidad_propia: 10\n---\n")
    a("# Capa 3 — Matriz de formularios y aplicación — Gestión de Preventa\n")
    a("> Fuente: `contratos.md`, `bpmn.md` y `bdm.md`. Un registro por formulario de instanciación, por formulario "
      "de tarea y por case overview. No hay prototipo ni diseño visual todavía (`docs/05-prototipo/` vacío): los "
      "controles son los widgets estándar de la plantilla Svelte.\n")
    a("## Convenciones\n")
    a("- **ID**: `frm_instanciacion`, `frm_<id-tarea>`, `frm_overview`.\n"
      "- **Tipo**: `Instantiation form`, `Task form`, `Case overview`.\n"
      "- **Form mapping**: `Svelte` (página de la Living Application `preventa`, mapeada por URL "
      "`/bonita/portal/resource/app/preventa/<formulario>/content/`) o `No form`. `frm_instanciacion` es `No form`: "
      "el caso lo instancia el middleware por la API REST y ningún usuario lo abre.\n"
      "- **Familia**: formularios con el mismo rol y la misma estructura de contrato.\n"
      "- **Campo**: escribe en un input del contrato o lee de un objeto de `bdm.md`.\n")
    a("## Matriz de formularios\n")
    a("| Formulario | Tipo | Tarea BPMN | Actor | Contrato | Entradas del contrato | Objetos de negocio (lee / "
      "escribe) | Form mapping | Familia | Validaciones (resumen) | Componentes de galería |")
    a("|---|---|---|---|---|---|---|---|---|---|---|")
    a("| `frm_instanciacion` | Instantiation form | (inicio) | — (lo instancia el middleware Ofelia) | "
      "`ctr_instanciacion` | `ticketId` | — / `Preventa` | No form | — | — | — |")
    for t in hs:
        actor = {L_CLI: "Comercial", L_COM: "Comercial", L_CON: "ConsultorPreventa", L_LT: "LiderTecnico",
                 L_INT: "EquipoInterno"}[t["lane"]]
        ents = ", ".join(bt(i[0]) for i in t["inputs"]) or "—"
        esc = "`Preventa`" if (any(i[3].startswith("Preventa.") for i in t["inputs"]) or t["lit"]) else "—"
        val = "; ".join("espeja " + bt(c[0]) for c in t["cons"]) or \
              ("obligatorios del contrato" if any(i[2] for i in t["inputs"]) else "—")
        a("| " + bt("frm_" + t["id"]) + " | Task form | " + bt(t["id"]) + " | " + actor + " | "
          + bt("ctr_" + t["id"]) + " | " + ents + " | `Preventa` / " + esc + " | Svelte | " + t["fam"] + " | " + val
          + " | — |")
    a("| `frm_overview` | Case overview | (pool) | Comercial, ConsultorPreventa, LiderTecnico, EquipoInterno | — | — "
      "| `Preventa` / — | No form | — | — | — |\n")
    a("## Detalle por formulario\n")
    for t in hs:
        actor = {L_CLI: "Comercial", L_COM: "Comercial", L_CON: "ConsultorPreventa", L_LT: "LiderTecnico",
                 L_INT: "EquipoInterno"}[t["lane"]]
        pg = pagina(t["id"])
        a("### `frm_" + t["id"] + "` — " + t["nombre"] + "\n")
        a("- **Tarea / contrato / actor**: `" + t["id"] + "` / `ctr_" + t["id"] + "` / " + actor + ".")
        a("- **Form mapping**: Svelte. Aplicación `preventa`, página `" + pg + "` (URL "
          "`/bonita/portal/resource/app/preventa/" + pg + "/content/`).")
        a("- **Datos que carga al abrir** (solo lectura): " + ", ".join(lectura(t)) + " (business variable "
          "`preventa` del caso, por la REST API extension `consultas/caso`).")
        a("- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por "
          "familia).\n")
        a("| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio "
          "| Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad "
          "restringida |")
        a("|---|---|---|---|---|---|---|---|---|")
        nombres = {"ticketId": "Ticket", "asunto": "Asunto", "estado": "Estado"}
        for ref in lectura(t):
            at = ref.strip("`").split(".")[1]
            a("| " + nombres.get(at, at[:1].upper() + at[1:]) + " | Text (solo lectura) | — | " + ref
              + " | — | — | — | — | — |")
        for n, tp, ob, dest, w, et in t["inputs"]:
            cons = [c[0] for c in t["cons"] if c[0].startswith(n + "_")]
            val = ("espeja " + bt(cons[0])) if cons else ("propia de UI: no vacío" if ob and tp == "TEXT" else
                                                           ("propia de UI: una opción elegida" if ob else "—"))
            a("| " + et + " | " + w + " | " + bt(n) + " | — | " + ("sí" if ob else "no") + " | " + val
              + " | — | — | — |")
        accion = ("Enviar (fija " + ", ".join(bt(i[0]) for i in t["inputs"]) + ")") if t["inputs"] else \
            "Marcar como hecha (envía el contrato vacío)"
        a("\n**Acciones**: " + accion + ".")
        a("**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.\n")
    a("`frm_instanciacion` y `frm_overview` no tienen detalle: son `No form`.\n")
    a("## Familias y unidades de trabajo\n")
    a("| Familia | Formularios | Rol | Campos (cada uno) | Unidad de trabajo propuesta | Justificación |")
    a("|---|---|---|---|---|---|")
    fams = {}
    for t in hs:
        fams.setdefault(t["fam"], []).append(t)
    just = {"decision": "formularios que capturan la decisión de una compuerta",
            "captura": "formularios que capturan texto o enlaces de un entregable",
            "confirmacion": "formularios sin inputs: muestran el caso y dan la tarea por hecha",
            "lider": "los dos formularios del Líder Técnico", "interno": "único formulario del Equipo interno"}
    for f, ts in fams.items():
        campos = sorted({len(lectura(t)) + len(t["inputs"]) for t in ts})
        rango = str(campos[0]) if len(campos) == 1 else str(campos[0]) + "–" + str(campos[-1])
        a("| " + f + " | " + ", ".join(bt("frm_" + t["id"]) for t in ts) + " | " + bt(ROL[ts[0]["lane"]]) + " | "
          + rango + " | una épica | " + just[f.split("-")[-1]] + "; ninguno supera el umbral |")
    a("\n## Aplicación (Living Application)\n")
    a("| Elemento | Valor |")
    a("|---|---|")
    a("| Application descriptor | `preventa` (las páginas Svelte de los formularios; la bandeja es la de la Bonita "
      "User Application) |")
    a("| Perfiles con acceso | `User` (todos los usuarios de la organización) |")
    a("| Página de inicio | `" + pagina(hs[0]["id"]) + "` |")
    a("| Layout / tema | los de la plantilla |\n")
    a("| Página | Tipo | Perfil | Objetos / consultas que muestra | Formularios que lanza | Menú |")
    a("|---|---|---|---|---|---|")
    a("| " + ", ".join(bt(pagina(t["id"])) for t in hs) + " | formulario Svelte | `User` | `Preventa` (por "
      "`consultas/caso`) | — (las abre el portal por el form mapping) | — |\n")
    a("## Acceso al BDM y permisos (decisión tomada en la capa 0, detallada aquí)\n")
    a("Todo lo que un formulario lee se expone con una **REST API extension** (permiso por perfil, solo los "
      "atributos necesarios); el acceso directo a `/API/bdm` está desaconsejado.\n")
    a("| Recurso | Mecanismo (BDM access control / REST API extension / consulta directa) | Perfiles o actores con "
      "acceso | Objetos y atributos expuestos | Fuente (visibilidad-por-familia.md) |")
    a("|---|---|---|---|---|")
    a("| `Preventa` | REST API extension `consultas/caso` (`GET …/API/extension/consultas/caso?caseId=`) | `User`; "
      "actores `Comercial`, `ConsultorPreventa`, `LiderTecnico`, `EquipoInterno` | `Preventa` (el objeto raíz del "
      "caso) | — (no hay restricciones por familia) |\n")
    a("## Verificaciones de diseño (las revisa el gate)\n")
    a("- [x] Un registro por instanciación, por tarea humana y para el overview (o `No form` explícito).\n"
      "- [x] Todo formulario con form mapping fijado y familia asignada.\n"
      "- [x] Todo campo con origen o destino, obligatoriedad, validación, dependencia y catálogo fijados.\n"
      "- [x] Toda constraint del contrato espejada o declarada como solo de servidor.\n"
      "- [x] Toda restricción de visibilidad por familia aplicada (no hay ninguna).\n"
      "- [x] Acceso al BDM decidido antes de construir el primer formulario.\n")
    a("## Pendientes de definición\n")
    a("- No hay prototipo ni referencia visual (`docs/05-prototipo/` vacío): el gate `fidelity` de las unidades de "
      "formularios no tiene contra qué comparar hasta que exista. Confirmación humana pendiente.\n"
      "- Datos de contacto del lead en pantalla (`Preventa.descripcion`, `Preventa.medpicc`): son datos personales "
      "del ticket; falta decidir si algún rol no debe verlos (hoy no hay restricción por familia).")
    return "\n".join(o) + "\n"


OUT.mkdir(parents=True, exist_ok=True)
(OUT / "bpmn.md").write_text(bpmn(), encoding="utf-8", newline="\n")
(OUT / "contratos.md").write_text(contratos(), encoding="utf-8", newline="\n")
(OUT / "matriz-formularios.md").write_text(matriz(), encoding="utf-8", newline="\n")
print("tareas", len(T), "humanas", len(humanas()), "compuertas", len(G), "transiciones", len(TR), "conectores", len(C))
