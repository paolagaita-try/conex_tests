package com.trycore.consultas

/**
 * Lo que la extensión pregunta al motor de Bonita para decidir quién lee qué. Lo implementa `MotorBonita` sobre
 * `ProcessAPI`; los tests usan dobles de este puerto.
 */
interface Motor {

    /** Definición de proceso del caso, vivo o archivado; `null` si el caso no existe. */
    Long procesoDelCaso(long caso)

    /** Implicado en el caso: lo inició, o tiene o tuvo una tarea humana suya (abierta o archivada). */
    boolean involucrado(long usuario, long caso)

    /** Usuarios mapeados al actor en esa definición (directos, por grupo, rol o membresía). */
    Collection<Long> usuariosDelActor(long proceso, String actor)
}
