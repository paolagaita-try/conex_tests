package com.trycore.parametros.core

/**
 * Punto de inyección de fallos de la escritura: se invoca justo después de cada
 * paso 1…6. Solo las pruebas lo sustituyen; en producción es {@link #NINGUNO}. El fallo del paso 7
 * es un commit que falla y se prueba con una conexión cuyo commit() falla.
 */
interface Fallos {
    Fallos NINGUNO = { int paso -> } as Fallos

    void tras(int paso)
}
