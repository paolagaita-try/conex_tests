package co.trycore.preventa.conectores

import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import org.bonitasoft.engine.bpm.document.Document
import org.bonitasoft.engine.connector.AbstractConnector
import org.bonitasoft.engine.connector.ConnectorException
import org.bonitasoft.engine.connector.ConnectorValidationException

/**
 * hubspot-archivo-subir — sube documentos de Bonita a HubSpot (Files API) y los adjunta en una nota asociada al
 * Negocio y al ticket.
 *  1. Por cada documento: POST {urlBase}{rutaArchivos} (por defecto «/files/v3/files»), multipart/form-data con
 *     file, fileName, folderPath y options {"access":"PRIVATE"}; HubSpot responde 201 con el «id» del archivo.
 *  2. POST {urlBase}{rutaObjetos}/notes con hs_attachment_ids = ids separados por «;», asociada al ticket (228) y
 *     al Negocio (214) — ver HubspotNotaCrear.
 * Fuentes: https://developers.hubspot.com/docs/api-reference/files-files-v3/guide y
 *          https://developers.hubspot.com/docs/api-reference/legacy/files/files/upload-file (scopes files | files.write).
 *
 * Entrada «documentos» (java.util.List); cada elemento puede ser:
 *  - un Map {nombre, mime, contenido} con contenido byte[] (o texto Base64);
 *  - un org.bonitasoft.engine.bpm.document.Document del caso (el contenido se lee con ProcessAPI.getDocumentContent);
 *  - cualquier objeto con getFileName()/getContent() y getContentType() o getMimeType() (FileInputValue de un
 *    contrato, DocumentValue). [no verificado] contra la doc de Bonita: el paso de List<Document> a un conector.
 * Salidas: fileIds (String, ids separados por «;», listo para hs_attachment_ids) y noteId (String).
 */
class HubspotArchivoSubir extends AbstractConnector {

    static final String RUTA_ARCHIVOS_DEFECTO = '/files/v3/files'
    static final String CARPETA_DEFECTO = '/preventa'

    @Override
    void validateInputParameters() throws ConnectorValidationException {
        ['urlBase', 'dealId', 'ticketId'].each { String n ->
            def v = getInputParameter(n)
            if (v == null || v.toString().trim().isEmpty()) {
                throw new ConnectorValidationException(this, "La entrada «${n}» es obligatoria")
            }
        }
        def docs = getInputParameter('documentos')
        if (!(docs instanceof List) || ((List) docs).isEmpty()) {
            throw new ConnectorValidationException(this, 'La entrada «documentos» debe ser una lista con al menos un documento')
        }
    }

    /** Normaliza un elemento de «documentos» a {nombre, mime, contenido(byte[])}. */
    Map normalizar(Object d) {
        if (d instanceof Map) {
            def c = d.contenido
            byte[] bytes = (c instanceof byte[]) ? (byte[]) c : (c == null ? null : c.toString().decodeBase64())
            return [nombre: d.nombre, mime: d.mime, contenido: bytes]
        }
        if (d instanceof Document) {
            Document doc = (Document) d
            byte[] bytes = doc.hasContent() ? apiAccessor.processAPI.getDocumentContent(doc.contentStorageId) : null
            return [nombre: doc.contentFileName, mime: doc.contentMimeType, contenido: bytes]
        }
        if (d != null && d.respondsTo('getContent') && d.respondsTo('getFileName')) {
            def mime = d.respondsTo('getContentType') ? d.contentType : (d.respondsTo('getMimeType') ? d.mimeType : null)
            return [nombre: d.fileName, mime: mime, contenido: d.content]
        }
        throw new IllegalArgumentException("Documento no soportado: ${d == null ? 'null' : d.getClass().name}")
    }

    static String subir(String url, Map doc, String carpeta) {
        if (doc.contenido == null || ((byte[]) doc.contenido).length == 0) {
            throw new IllegalArgumentException("El documento «${doc.nombre}» no tiene contenido")
        }
        String nombre = (doc.nombre == null || doc.nombre.toString().trim().isEmpty()) ? 'documento' : doc.nombre.toString().trim()
        def partes = [
            [nombre: 'file', nombreArchivo: nombre, mime: doc.mime ?: 'application/octet-stream', contenido: doc.contenido],
            [nombre: 'fileName', valor: nombre],
            [nombre: 'folderPath', valor: carpeta],
            [nombre: 'options', valor: JsonOutput.toJson([access: 'PRIVATE'])]
        ]
        def resp = new JsonSlurper().parseText(Http.postMultipart(url, partes))
        if (resp?.id == null) {
            throw new IllegalStateException("HubSpot no devolvió el id del archivo «${nombre}»")
        }
        return resp.id.toString()
    }

    @Override
    protected void executeBusinessLogic() throws ConnectorException {
        String urlBase = getInputParameter('urlBase').toString().trim()
        String rutaArchivos = HubspotNegocioActualizar.ruta(getInputParameter('rutaArchivos'), RUTA_ARCHIVOS_DEFECTO)
        String rutaObjetos = HubspotNegocioActualizar.ruta(getInputParameter('rutaObjetos'),
                HubspotNegocioActualizar.RUTA_OBJETOS_DEFECTO)
        String carpeta = HubspotNegocioActualizar.ruta(getInputParameter('carpeta'), CARPETA_DEFECTO)
        String dealId = getInputParameter('dealId').toString().trim()
        String ticketId = getInputParameter('ticketId').toString().trim()
        def textoNota = getInputParameter('cuerpoNota')
        String cuerpo = (textoNota == null || textoNota.toString().trim().isEmpty()) ? null : textoNota.toString()
        try {
            List<String> ids = ((List) getInputParameter('documentos')).collect { subir(urlBase + rutaArchivos, normalizar(it), carpeta) }
            String fileIds = ids.join(';')
            if (cuerpo == null) {
                cuerpo = 'Adjuntos de preventa: ' + ids.size() + ' archivo(s).'
            }
            String noteId = HubspotNotaCrear.crear(urlBase, rutaObjetos, cuerpo, ticketId, dealId, fileIds)
            setOutputParameter('fileIds', fileIds)
            setOutputParameter('noteId', noteId)
        } catch (Exception e) {
            throw new ConnectorException('No se pudieron subir los archivos a HubSpot: ' + e.message, e)
        }
    }
}
