import { mount } from 'svelte';
// Los tokens de identidad visual se cargan con la pantalla: el tema de la Living
// Application los sobreescribe en runtime (sin recompilar).
import '$lib/estilos/tokens.css';
// La marca de la organización (nombre, logo, colores) es un parámetro del módulo: se aplica sobre los tokens.
import '$lib/estilos/marcaEnVivo';
import { crearKit } from './api';
import Parametros from './Parametros.svelte';

const destino = document.getElementById('app');
if (!destino) throw new Error('No existe el contenedor #app');

export default mount(Parametros, { target: destino, props: { kit: crearKit() } });
