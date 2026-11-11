import { mount } from 'svelte';
// Sin este import la pantalla cae a los valores de reserva y el tema del proyecto no la
// alcanza.
import '$lib/estilos/tokens.css';
// La marca del proyecto (nombre, logo, colores) es un parámetro del módulo: se aplica sobre los tokens.
import '$lib/estilos/marcaEnVivo';
import Semilla from './Semilla.svelte';

const destino = document.getElementById('app');
if (!destino) throw new Error('No existe el contenedor #app');

export default mount(Semilla, { target: destino });
