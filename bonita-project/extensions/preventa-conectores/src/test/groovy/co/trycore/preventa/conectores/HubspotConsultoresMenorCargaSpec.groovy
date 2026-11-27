package co.trycore.preventa.conectores

import spock.lang.Specification
import spock.lang.Unroll

/**
 * Pruebas de la ponderación por prioridad del reparto (situación 1): la carga mide capacidad y prioridad.
 * Se prueba pesoDe (el mapeo nuevo) y la suma ponderada que decide a quién se asigna.
 */
class HubspotConsultoresMenorCargaSpec extends Specification {

    @Unroll
    def "pesoDe(#prioridad) = #esperado"() {
        expect:
        HubspotConsultoresMenorCarga.pesoDe(prioridad) == esperado

        where:
        prioridad   | esperado
        'URGENT'    | 4
        'HIGH'      | 3
        'MEDIUM'    | 2
        'LOW'       | 1
        'high'      | 3          // no distingue mayúsculas/minúsculas
        ' High '    | 3          // tolera espacios
        ''          | 2          // sin prioridad -> MEDIUM
        null        | 2          // ausente -> MEDIUM
        'RARA'      | 2          // valor desconocido -> MEDIUM
    }

    def "la carga ponderada mide capacidad Y prioridad: gana quien tiene menor suma, no menor conteo"() {
        given: "Viviana con 5 altos (5x3=15) y Linda con 2 altos + 3 bajos (2x3+3x1=9)"
        def tickets = [
            // Viviana (89450377): 5 HIGH
            tk('89450377', 'HIGH'), tk('89450377', 'HIGH'), tk('89450377', 'HIGH'),
            tk('89450377', 'HIGH'), tk('89450377', 'HIGH'),
            // Linda (89450376): 2 HIGH + 3 LOW
            tk('89450376', 'HIGH'), tk('89450376', 'HIGH'),
            tk('89450376', 'LOW'),  tk('89450376', 'LOW'), tk('89450376', 'LOW')
        ]
        def candidatos = ['89450376', '89450377']

        when:
        def carga = cargaPonderada(tickets, candidatos)

        then: "aunque ambas tienen 5 tickets (capacidad igual), Linda pesa menos -> gana Linda"
        carga['89450377'] == 15
        carga['89450376'] == 9
        menorCarga(carga, candidatos) == '89450376'
    }

    def "con prioridades iguales se comporta como conteo (reparte por capacidad)"() {
        given: "todo HIGH: Linda 1, Viviana 2"
        def tickets = [tk('89450376', 'HIGH'), tk('89450377', 'HIGH'), tk('89450377', 'HIGH')]
        def candidatos = ['89450376', '89450377']

        when:
        def carga = cargaPonderada(tickets, candidatos)

        then:
        carga['89450376'] == 3
        carga['89450377'] == 6
        menorCarga(carga, candidatos) == '89450376'
    }

    def "el ticket que se está asignando no cuenta en la carga de su dueño anterior (prueba real v2)"() {
        given: "el ticket 90000000001 (HIGH) quedó en stage 3 a nombre de Linda tras una corrida fallida; nadie más tiene carga"
        def candidatos = ['89450376', '89450377']
        def resultados = [tkId('90000000001', '89450376', 'HIGH')]

        expect: "sin excluirlo, Linda carga 3 y el reparto se va a Viviana (lo que pasó en la corrida 2)"
        HubspotConsultoresMenorCarga.cargaPonderada(resultados, candidatos, '') == ['89450376': 3, '89450377': 0]
        HubspotConsultoresMenorCarga.elegir(['89450376': 3, '89450377': 0], candidatos, '') == '89450377'

        and: "excluyéndolo, ambas cargan 0 y decide el desempate determinista (primera en el orden, sin último asignado)"
        def carga = HubspotConsultoresMenorCarga.cargaPonderada(resultados, candidatos, '90000000001')
        carga == ['89450376': 0, '89450377': 0]
        HubspotConsultoresMenorCarga.elegir(carga, candidatos, '') == '89450376'
    }

    @Unroll
    def "el resultado no depende del dueño previo del propio ticket (dueño previo #duenoPrevio, stage #stage)"() {
        given:
        def candidatos = ['89450376', '89450377']
        def resultados = [
            tkId('90000000001', duenoPrevio, 'HIGH'),     // el que se asigna: no cuenta
            tkId('900', '89450377', 'LOW'),               // carga real de Viviana: 1
            tkId('901', '88449388', 'URGENT')             // el bot no es candidato: no cuenta
        ]
        expect:
        HubspotConsultoresMenorCarga.cargaPonderada(resultados, candidatos, '90000000001') == ['89450376': 0, '89450377': 1]
        HubspotConsultoresMenorCarga.elegir(
            HubspotConsultoresMenorCarga.cargaPonderada(resultados, candidatos, '90000000001'), candidatos, '') == '89450376'
        where:
        duenoPrevio | stage
        '89450376'  | '3'
        '89450377'  | '2'
        null        | '2'
    }

    def "desempate circular respecto del último asignado"() {
        expect:
        HubspotConsultoresMenorCarga.elegir(['a': 0, 'b': 0, 'c': 0], ['a', 'b', 'c'], 'b') == 'c'
        HubspotConsultoresMenorCarga.elegir(['a': 0, 'b': 0, 'c': 0], ['a', 'b', 'c'], 'c') == 'a'
        HubspotConsultoresMenorCarga.elegir(['a': 0, 'b': 5, 'c': 0], ['a', 'b', 'c'], 'a') == 'c'
        HubspotConsultoresMenorCarga.elegir(['a': 0, 'b': 0], ['a', 'b'], 'zz') == 'a'
    }

    private static Map tkId(String id, String owner, String prioridad) {
        [id: id, properties: [hubspot_owner_id: owner, hs_ticket_priority: prioridad]]
    }

    // --- helpers que reproducen la suma del conector sin levantar el motor Bonita ---

    private static Map tk(String owner, String prioridad) {
        [properties: [hubspot_owner_id: owner, hs_ticket_priority: prioridad]]
    }

    private static Map<String, Integer> cargaPonderada(List tickets, List<String> candidatos) {
        Map<String, Integer> carga = [:]
        candidatos.each { carga[it] = 0 }
        tickets.each { t ->
            def owner = t?.properties?.hubspot_owner_id
            if (owner != null && carga.containsKey(owner.toString())) {
                carga[owner.toString()] = carga[owner.toString()] + HubspotConsultoresMenorCarga.pesoDe(t?.properties?.hs_ticket_priority)
            }
        }
        return carga
    }

    private static String menorCarga(Map<String, Integer> carga, List<String> candidatos) {
        int minima = candidatos.collect { carga[it] }.min()
        return candidatos.find { carga[it] == minima }
    }
}
