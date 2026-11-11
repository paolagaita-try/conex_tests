import { mount } from 'svelte';
// Los tokens de identidad visual: el tema de la Living Application los sobreescribe en runtime.
import '$lib/estilos/tokens.css';
// La marca del proyecto (nombre, logo, colores) es un parámetro del módulo: se aplica sobre los tokens.
import '$lib/estilos/marcaEnVivo';
// Embebida en una bandeja, la pantalla no repite su cabecera.
import '$lib/estilos/enMarco';
import FrmHolaRevisar from './FrmHolaRevisar.svelte';

const destino = document.getElementById('app');
if (!destino) throw new Error('No existe el contenedor #app');

export default mount(FrmHolaRevisar, { target: destino });
