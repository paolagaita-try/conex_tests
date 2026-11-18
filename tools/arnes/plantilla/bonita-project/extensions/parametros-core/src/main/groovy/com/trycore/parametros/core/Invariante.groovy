package com.trycore.parametros.core

import groovy.transform.Immutable

/** Una invariante entre parámetros declarada por una semilla. */
@Immutable
class Invariante {
    String tipo
    List<String> definiciones
}
