package com.trycore.parametros.api

import org.bonitasoft.engine.api.IdentityAPI
import org.bonitasoft.engine.identity.UserMembership
import org.bonitasoft.engine.identity.UserMembershipCriterion
import spock.lang.Specification

/**
 * Las membresías de quien llama. El usuario técnico (`install`, id -1) no tiene ninguna: preguntarle al motor por
 * ellas hace que Bonita 2026.2 (motor 11.1.0) lance una query que no existe (`getUserMembershipsWithRole`) y la API
 * respondería 500 en vez de 403.
 */
class MembresiasBonitaSpec extends Specification {

    IdentityAPI identidad = Mock()

    def "el usuario técnico no tiene membresías y no se le pregunta al motor"() {
        when:
        def todas = new MembresiasBonita(identidad, -1L).de("install")

        then:
        0 * identidad._
        todas == []
    }

    def "un usuario de la organización: sus membresías, con la ruta completa del grupo y los IDs"() {
        given:
        UserMembership m = Stub() {
            getGroupParentPath() >> "/acme"
            getGroupName() >> "becas"
            getRoleName() >> "member"
            getGroupId() >> 11L
            getRoleId() >> 21L
        }

        when:
        def todas = new MembresiasBonita(identidad, 4L).de("walter.bates")

        then:
        1 * identidad.getUserMemberships(4L, 0, MembresiasBonita.PAGINA, UserMembershipCriterion.ROLE_NAME_ASC) >> [m]
        todas == [[grupo: "/acme/becas", rol: "member", grupoId: 11L, rolId: 21L]]
    }
}
