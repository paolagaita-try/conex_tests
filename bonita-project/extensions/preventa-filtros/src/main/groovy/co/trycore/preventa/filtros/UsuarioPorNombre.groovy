package co.trycore.preventa.filtros

import org.bonitasoft.engine.connector.ConnectorValidationException
import org.bonitasoft.engine.filter.AbstractUserFilter
import org.bonitasoft.engine.filter.UserFilterException

/**
 * Actor filter `usuario-por-nombre`: la tarea llega solo al usuario de Bonita cuyo nombre de usuario es la entrada
 * `usuario`. El proceso calcula ese nombre desde el owner de HubSpot que eligió el reparto (`ownerElegido`) y
 * `param_consultores` (expresiones.md, `flt_filtroConsultoraDelCaso.usuario`). Si el usuario no existe, la tarea
 * queda en fallo (no se reparte a todo el actor): es mejor un fallo visible que una tarea a la consultora equivocada.
 */
class UsuarioPorNombre extends AbstractUserFilter {

    static String normalizar(Object valor) {
        return valor == null ? "" : valor.toString().trim()
    }

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        if (normalizar(getInputParameter("usuario")).isEmpty()) {
            throw new ConnectorValidationException("usuario-por-nombre: la entrada usuario está vacía")
        }
    }

    @Override
    List<Long> filter(String actorName) throws UserFilterException {
        String usuario = normalizar(getInputParameter("usuario"))
        try {
            return [getAPIAccessor().getIdentityAPI().getUserByUserName(usuario).getId()]
        } catch (Exception e) {
            throw new UserFilterException("usuario-por-nombre: el usuario «" + usuario + "» no existe en la organización", e)
        }
    }

    @Override
    boolean shouldAutoAssignTaskIfSingleResult() {
        return true
    }
}
