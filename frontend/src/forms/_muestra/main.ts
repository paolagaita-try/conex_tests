import { mount } from 'svelte';
// Los tokens de identidad visual se cargan con la pantalla: el tema de la Living
// Application los sobreescribe en runtime. Sin este import la
// pantalla se dibuja solo con los valores de reserva de cada `var(...)`, que es un fallo
// silencioso: se ve «casi bien».
import '$lib/estilos/tokens.css';
import Muestra from './Muestra.svelte';

const destino = document.getElementById('app');
if (!destino) throw new Error('No existe el contenedor #app');

export default mount(Muestra, { target: destino });
