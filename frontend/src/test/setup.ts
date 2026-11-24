import '@testing-library/jest-dom/vitest';

// El registro de sombras se instala ANTES de cualquier test: envuelve
// `Element.prototype.attachShadow` para que toda raíz creada durante un render —las `closed`
// incluidas— quede expuesta a `foto()`/`raicesDeSombra()`. Sin
// esta línea, `sombraDe` GRITA en vez de medir a medias.
import { instalarRegistroDeSombras } from '../pruebas/registroDeSombras';

instalarRegistroDeSombras();
