package com.trycore.preventa.contexto

/** HubSpot respondió con un código no 2xx (distinto de 404) o no respondió (`estado` null). Sin cuerpo: no se filtra. */
class FalloHubspot extends RuntimeException {
    final Integer estado

    FalloHubspot(Integer estado, String mensaje, Throwable causa = null) {
        super(mensaje, causa)
        this.estado = estado
    }
}
