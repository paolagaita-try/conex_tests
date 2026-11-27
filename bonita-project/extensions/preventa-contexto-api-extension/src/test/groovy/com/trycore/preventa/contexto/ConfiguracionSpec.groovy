package com.trycore.preventa.contexto

import spock.lang.Specification

class ConfiguracionSpec extends Specification {

    def "por defecto apunta a HubSpot real"() {
        expect:
        Configuracion.de(new Properties(), [:]).with {
            urlBase == "https://api.hubapi.com" && timeoutMs == 10000 && maximoContactos == 20 && ownersExcluidos == []
        }
    }

    def "el fichero apunta al mock y la variable de entorno gana; sin barra final"() {
        given:
        Properties p = new Properties().tap { putAll(["hubspot.urlBase": "http://localhost:8089/hubspot/", "owners.excluidos": "88449388, 1",
                                       "contactos.maximo": "5", "hubspot.timeoutMs": "nada"]) }

        expect:
        Configuracion.de(p, [:]).urlBase == "http://localhost:8089/hubspot"
        Configuracion.de(p, [:]).ownersExcluidos == ["88449388", "1"]
        Configuracion.de(p, [:]).maximoContactos == 5
        Configuracion.de(p, [:]).timeoutMs == 10000
        Configuracion.de(p, [HUBSPOT_BASE_URL: "http://otro:1/hubspot"]).urlBase == "http://otro:1/hubspot"
    }

    def "la configuración del zip trae la raíz del entorno del build y el bot excluido"() {
        given:
        Properties p = new Properties()
        getClass().getResourceAsStream("/configuration.properties").withCloseable { p.load(it) }
        String esperado = System.getProperty("contexto.hubspotUrlBase.esperado")

        expect: "filtrada (sin marcador) y la del entorno: el mock en Local, api.hubapi.com en Qualification/Production"
        esperado
        Configuracion.de(p, [:]).urlBase == esperado
        !p.getProperty("hubspot.urlBase").contains('${')
        "88449388" in Configuracion.de(p, [:]).ownersExcluidos
    }

    def "un build Local (el de por defecto) nunca apunta a HubSpot real"() {
        given:
        Properties p = new Properties()
        getClass().getResourceAsStream("/configuration.properties").withCloseable { p.load(it) }
        String entorno = System.getProperty("bonita.environment")

        expect:
        (entorno && !(entorno in ["local", "Local"])) || Configuracion.de(p, [:]).urlBase == "http://localhost:8099/hubspot"
    }
}
