/** Datos simulados (no reales) para pruebas y capturas: misma forma que devuelve `preventa/contexto`. */
import type { ContextoPreventa, DatosDelCaso } from './contexto';

export const CONTEXTO_EJEMPLO: ContextoPreventa = {
  ticket: {
    id: '4821',
    properties: {
      subject: 'Automatizar la radicación de facturas de proveedores',
      content: 'El cliente quiere digitalizar la radicación y aprobación de facturas con integración a SAP.',
      hs_pipeline: '0',
      hs_pipeline_stage: '2',
      hs_ticket_priority: 'HIGH',
      hs_ticket_category: 'Preventa',
      source_type: 'FORM',
      createdate: '2026-11-18T14:05:00Z',
      linea_de_negocio: 'Automatización de procesos',
      tipo_de_requerimiento: 'Propuesta técnico-económica',
      complejidad_estimada: 'Media',
      pais_del_cliente: 'Colombia',
      sistemas_involucrados: 'SAP S/4HANA; Outlook',
      alcance_preliminar: 'Radicación, validación y aprobación en 3 niveles.',
      fecha_de_vencimiento: '2026-12-05',
    },
  },
  deal: {
    id: '99120',
    properties: {
      dealname: 'Acme · Facturas digitales',
      amount: '85000000',
      deal_currency_code: 'COP',
      dealstage: 'qualifiedtobuy',
      dealtype: 'newbusiness',
      closedate: '2027-01-30',
      sector: 'Manufactura',
      dolor_principal: 'Retrasos de 20 días en pagos a proveedores',
      meddpicc: 'Champion: Dir. Financiera',
    },
  },
  company: {
    id: '5501',
    properties: { name: 'Acme Industrial S.A.S.', domain: 'acme.example', industry: 'Manufactura', city: 'Medellín' },
  },
  contacts: [
    {
      id: '701',
      properties: {
        firstname: 'Mariana',
        lastname: 'Ríos',
        email: 'mariana.rios@acme.example',
        phone: '+57 300 000 0000',
        jobtitle: 'Directora financiera',
      },
    },
    {
      id: '702',
      properties: { firstname: 'Julián', lastname: 'Pérez', email: 'julian.perez@acme.example', phone: null, jobtitle: 'Jefe de TI' },
    },
  ],
  owner: { id: '123', email: 'comercial@trycore.example', firstName: 'Andrés', lastName: 'Gómez' },
};

export const CASO_EJEMPLO: DatosDelCaso = {
  ticketId: '4821',
  consultor: 'laura.preventa',
  fechaAsignacion: '2026-11-18T14:06:00Z',
  estado: 'En diseño',
  resultadoValidacion: 'viable',
  conceptoViabilidad: 'Aprobado (Viable)',
  notaValidacion: 'Se validó alcance con la directora financiera.',
  supuestos: 'Acceso a ambiente de pruebas de SAP.',
  fechaValidacion: '2026-11-19T10:30:00Z',
};

/** Línea de tiempo simulada del caso para la vista del caso. */
export const HITOS_EJEMPLO = [
  { titulo: 'Ticket creado en HubSpot', detalle: 'Entró por el formulario web', fecha: '2026-11-18T14:05:00Z', estado: 'hecho' },
  { titulo: 'Caso instanciado y asignado', detalle: 'Round robin → laura.preventa', fecha: '2026-11-18T14:06:00Z', estado: 'hecho' },
  { titulo: 'Solicitud validada', detalle: 'Resultado: viable', fecha: '2026-11-19T10:30:00Z', estado: 'hecho' },
  { titulo: 'Diseño de la propuesta', detalle: 'En curso', fecha: null, estado: 'actual' },
  { titulo: 'Propuesta entregada', detalle: 'Pendiente', fecha: null, estado: 'pendiente' },
] as const;
