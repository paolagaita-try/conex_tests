package com.trycore.parametros.core

/**
 * Lo que el motor tiene desplegado: nombre de proceso → nombres de TODOS sus flow
 * nodes con nombre, en cualquiera de sus versiones. En el runtime lo da un adaptador de processAPI.
 */
interface Motor {
    Map<String, Set<String>> nodosPorProceso()
}
