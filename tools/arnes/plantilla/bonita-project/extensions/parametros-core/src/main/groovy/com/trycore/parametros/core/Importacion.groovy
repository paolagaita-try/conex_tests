package com.trycore.parametros.core

/** Lo que llega en POST parametros/importaciones, con el CSV ya leído por {@link Csv}. */
class Importacion {
    List<Map<String, Object>> filas = []
    boolean confirmar
    String motivo
    String huella
    /** Fila a fila, si quien importa puede escribir ese cambio (un delegado, solo en su alcance). */
    Closure<Boolean> permite = { Cambio c -> true }
    /** Los cambios que {@link #permite} denegó, para registrarlos como intentos al confirmar. */
    List<Cambio> fueraDeAlcance = []
}
