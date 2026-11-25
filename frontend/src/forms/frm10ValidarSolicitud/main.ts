import { mount } from 'svelte';
// Los tokens de identidad visual: el tema de la Living Application los sobreescribe en runtime.
import '$lib/estilos/tokens.css';
// La marca del proyecto (nombre, logo, colores) es un parámetro del módulo: se aplica sobre los tokens.
import '$lib/estilos/marcaEnVivo';
// Embebida en una bandeja, la pantalla no repite su cabecera.
import '$lib/estilos/enMarco';
// Tema corporativo Trycore (sobre los tokens).
import '$lib/preventa/tema.css';
import { propsDeDemo } from '$lib/preventa/demo';
import Frm10ValidarSolicitud from './Frm10ValidarSolicitud.svelte';

const destino = document.getElementById('app');
if (!destino) throw new Error('No existe el contenedor #app');

export default mount(Frm10ValidarSolicitud, { target: destino, props: propsDeDemo() });
