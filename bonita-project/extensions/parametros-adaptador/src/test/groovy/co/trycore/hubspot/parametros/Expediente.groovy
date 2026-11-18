package co.trycore.hubspot.parametros

/** Doble del objeto raíz del caso: lleva la colección `parametrosAplicados` que el adaptador espera. */
class Expediente {
    List<ParametroAplicado> parametrosAplicados = []
    void addToParametrosAplicados(Object f) { parametrosAplicados << f }
}
