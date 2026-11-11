/**
 * Marca el documento cuando la pantalla se abre DENTRO del marco de una bandeja.
 *
 * Por qué existe: embebida, la pantalla repetía su propia cabecera —sobretítulo, título grande y
 * «Quién la usa»— justo debajo de la que ya pinta la bandeja, y empujaba el formulario media
 * pantalla hacia abajo (el primer campo aparecía a 300 px del borde del marco). Suelta, esa cabecera es quien dice de qué pantalla se trata y se queda.
 *
 * Se marca el `<html>` y no cada componente porque la decisión es del DOCUMENTO: «estoy embebido».
 * Las reglas cuelgan de `[data-en-marco]` en `tokens.css`, que es lo que ya cargan todas.
 */
import { estaEnMarcoDeBonita } from '$lib/bonita/config';

if (estaEnMarcoDeBonita()) document.documentElement.dataset.enMarco = '';
