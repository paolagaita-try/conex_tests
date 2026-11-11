package com.trycore.consultas

import org.bonitasoft.engine.api.APIClient
import org.bonitasoft.engine.bpm.process.ProcessInstanceNotFoundException
import org.bonitasoft.engine.business.data.SimpleBusinessDataReference
import org.slf4j.Logger
import org.slf4j.LoggerFactory

/**
 * El objeto raíz de un caso, por el DAO del motor: el `storageId` sale del contexto de ejecución del caso —vivo o
 * archivado— y la entidad, del `<Tipo>DAO.findByPersistenceId`. Nunca por JNDI ni por la API del BDM.
 *
 * No nombra ninguna clase del BDM de forma estática (la extensión sirve a cualquier proyecto): carga el tipo y su DAO
 * por nombre con el cargador del runtime, que es quien trae el modelo. La variable de negocio es la que indica
 * `caso.variable` de la configuración o, si falta, la única que tenga el caso.
 */
class LectorBonita implements LectorDeCaso {

    private static final Logger LOG = LoggerFactory.getLogger(LectorBonita)

    private final APIClient api
    private final String variable

    LectorBonita(APIClient api, String variable = "") {
        this.api = api
        this.variable = variable
    }

    @Override
    Map<String, Object> objetoRaiz(long caso) {
        Object bean = objeto(caso)
        bean == null ? null : Proyeccion.aMapa(bean)
    }

    @Override
    List<Map<String, Object>> ejecucionesServicio(long caso) {
        Object bean = objeto(caso)
        if (bean == null || !bean.metaClass.hasProperty(bean, "ejecucionesServicio")) return []
        (bean.metaClass.getMetaProperty("ejecucionesServicio").getProperty(bean) ?: []).collect { Proyeccion.aMapa(it) }
    }

    private Object objeto(long caso) {
        Map<String, Serializable> contexto
        try {
            contexto = api.processAPI.getProcessInstanceExecutionContext(caso)
        } catch (ProcessInstanceNotFoundException ignorada) {
            long archivado = api.processAPI.getFinalArchivedProcessInstance(caso).id
            contexto = api.processAPI.getArchivedProcessInstanceExecutionContext(archivado)
        }
        def ref
        if (variable) {
            ref = contexto[variable + "_ref"]
        } else {
            def refs = contexto.findAll { it.value instanceof SimpleBusinessDataReference }.values()
            if (refs.size() > 1) {
                LOG.warn("consultas: el caso {} tiene {} variables de negocio y `caso.variable` está vacía: no se sabe cuál servir; se responde sin objeto", caso, refs.size())
            }
            ref = refs.size() == 1 ? refs.first() : null
        }
        if (!(ref instanceof SimpleBusinessDataReference) || ref.storageId == null) return null
        ClassLoader cl = Thread.currentThread().contextClassLoader ?: LectorBonita.classLoader
        Class dao = Class.forName(ref.type + "DAO", true, cl)
        api.getDAO(dao).findByPersistenceId(ref.storageId)
    }
}
