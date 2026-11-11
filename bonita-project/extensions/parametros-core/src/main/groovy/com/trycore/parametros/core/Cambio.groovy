package com.trycore.parametros.core

/** Lo que llega en POST parametros/cambios. El ámbito global y «sin valor» son '*'. */
class Cambio {
    String accion
    String definicion
    String proceso = "*"
    String actividad = "*"
    String codigoPadre = "*"
    String codigo = "*"
    Map<String, Object> datos = [:]
    Long persistenceVersion
    String motivo
    String origen = "PANTALLA"
    String lote
}
