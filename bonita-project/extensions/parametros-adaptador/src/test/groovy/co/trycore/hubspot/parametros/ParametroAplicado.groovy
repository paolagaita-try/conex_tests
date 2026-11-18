package co.trycore.hubspot.parametros

import java.time.OffsetDateTime

/** Doble de la entidad `ParametroAplicado` del BDM del proyecto (mismo paquete que el expediente, como en el motor). */
class ParametroAplicado {
    String definicion, codigoPadre, valor, origen, ambito, actividadCodigo, campoORegla
    Long versionValor
    OffsetDateTime fecha
}
