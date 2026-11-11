package com.trycore.parametros.core

/**
 * La organización de Bonita, leída EN VIVO: lo que una delegación guarda por ID se
 * resuelve en cada petición, así que renombrar un grupo no la rompe. En el runtime lo da un
 * adaptador de identityAPI.
 */
interface Organizacion {

    /** La ruta vigente de un grupo («/padre/grupo»), o null si no existe. */
    String rutaDeGrupo(Long grupoId)

    /** El ID de un usuario por su nombre, o null. */
    Long idDeUsuario(String usuario)

    boolean existeUsuario(Long usuarioId)

    boolean existeRol(Long rolId)

    /** Para enseñar a quién se delegó sin dar IDs: el nombre de usuario o de rol, o null. */
    String nombreDeUsuario(Long usuarioId)

    String nombreDeRol(Long rolId)

    /** Buscar en la organización (solo la superadministración): [id, nombre] de usuarios, grupos (su ruta) o roles. */
    List<Map<String, Object>> buscar(String tipo, String q)

    /** ¿Es solo de la familia cliente? Entonces ninguna delegación le alcanza (ver Familia.soloCliente). */
    boolean soloCliente(Autor autor)

    /** Sin organización: nadie existe y ningún grupo tiene ruta (solo la superadministración escribe). */
    static final Organizacion NINGUNA = [rutaDeGrupo: { Long id -> null }, idDeUsuario: { String u -> null },
                                         existeUsuario: { Long id -> false }, existeRol: { Long id -> false },
                                         nombreDeUsuario: { Long id -> null }, nombreDeRol: { Long id -> null },
                                         buscar: { String tipo, String q -> [] }, soloCliente: { Autor a -> false }] as Organizacion
}
