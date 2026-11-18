package com.trycore.parametros.core

/**
 * Las membresías vigentes de un usuario ([grupo: ruta, rol: nombre]), leídas en vivo en cada petición.
 * En el runtime, el adaptador de identityAPI.getUserMemberships paginado hasta agotar.
 */
interface Membresias {
    List<Map<String, String>> de(String usuario)
}
