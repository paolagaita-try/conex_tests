#!/usr/bin/env node
/**
 * Empaquetador de un formulario como recurso de Bonita.
 *
 * Lo que resuelve:
 *
 *  - Una plantilla ingenua escribe el nombre del recurso FIJO en el descriptor
 *    (`name=custompage_newForm`, `displayName=newForm`). Con varios formularios, cada
 *    despliegue sobrescribía el anterior en el runtime, porque el nombre ES la
 *    identidad del recurso para la plataforma. Aquí sale del manifiesto.
 *  - Declarar solo `resources=[POST|bpm/process]` es insuficiente. La doc es explícita:
 *    sin declarar cada recurso REST que la página consume, el usuario no recibe el
 *    permiso al iniciar sesión y el formulario falla en runtime. Aquí los permisos
 *    son por formulario, tomados del manifiesto.
 *  - Parchear el HTML con expresiones regulares para arreglar las rutas no
 *    hace falta: el build ya emite rutas relativas (`base: './'`).
 *
 * Uso:  node scripts/build-form.js <id> | --all [--solo-empaquetar]
 *
 * Antes de compilar corre la verificación de tipos del proyecto (`npm run check`) y aborta si
 * falla: Vite no verifica tipos, y la barrera de origen de las cifras es un
 * tipo. Sin esto, `importe(numeroCalculado)` «no compilaba» y el ZIP salía igual. La corre
 * también con `--solo-empaquetar` (así «no compila» sigue siendo «no se construye»): los pasos salen de `lib/pasos.js`.
 *
 * Salida: dist-zips/<custompage>.zip  →  page.properties + resources/**
 *
 * El `contentType` del descriptor sale del `tipo` de la entrada (`lib/descriptor.js`): `form`, `page`
 * para una página propia de una aplicación y `theme` para un tema. Un tema (`tipo: tema`) no se
 * compila con Vite: su paquete es `resources/theme.css` = Bootstrap 3.4.1 + `src/forms/<id>/tema.css`,
 * las fuentes de Bootstrap y `src/forms/<id>/images/` si existe (`lib/tema.js`).
 */

import { execFileSync } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import fs from 'fs-extra';
import archiver from 'archiver';
import { descriptorDeRecurso, validarManifiesto } from './lib/descriptor.js';
import { cssDelTema, ficheroDeEntrada } from './lib/tema.js';
import { fuentesDe, huellaDeFuentes } from './lib/huella.js';
import { pasosDelBuild } from './lib/pasos.js';
import { comprobarSinSecretos, secretosDeDesarrollo } from './lib/sinSecretos.js';
import { verificarTipos } from './lib/verificaTipos.js';

const RAIZ = path.resolve(import.meta.dirname, '..');
// `FORMS_MANIFEST` permite apuntar a un manifiesto alterno. Existe para poder
// verificar el empaquetado (por ejemplo, que dos formularios no se sobrescriben)
// sin tocar el manifiesto real del proyecto.
const MANIFIESTO = process.env.FORMS_MANIFEST
  ? path.resolve(process.env.FORMS_MANIFEST)
  : path.join(RAIZ, 'forms.manifest.json');
const SALIDA_ZIPS = path.join(RAIZ, 'dist-zips');
const VITE = path.join(RAIZ, 'node_modules', 'vite', 'bin', 'vite.js');
const BOOTSTRAP = path.join(RAIZ, 'node_modules', 'bootstrap', 'dist');

const COLOR = {
  fin: '\x1b[0m',
  rojo: '\x1b[31m',
  verde: '\x1b[32m',
  azul: '\x1b[34m',
  amarillo: '\x1b[33m',
};
const info = (m) => console.log(`${COLOR.azul}·${COLOR.fin} ${m}`);
const bien = (m) => console.log(`${COLOR.verde}✓${COLOR.fin} ${m}`);
const mal = (m) => console.error(`${COLOR.rojo}⛔${COLOR.fin} ${m}`);
const aviso = (m) => console.log(`${COLOR.amarillo}⚠${COLOR.fin} ${m}`);

/** Lee el manifiesto de identidad y lo valida (la validación es verificable aparte). */
async function leerManifiesto() {
  if (!(await fs.pathExists(MANIFIESTO))) {
    throw new Error(`No existe el manifiesto: ${path.relative(RAIZ, MANIFIESTO)}`);
  }
  return validarManifiesto(await fs.readJson(MANIFIESTO));
}

/** Compila el formulario con Vite, en un subproceso aislado. */
function compilar(id) {
  info(`vite build (FORM_ID=${id})`);
  execFileSync(process.execPath, [VITE, 'build'], {
    cwd: RAIZ,
    stdio: 'inherit',
    env: { ...process.env, FORM_ID: id },
  });
}

/** Empaqueta el resultado del build como recurso ZIP de la plataforma. */
async function empaquetar(formulario, version) {
  const dist = path.join(RAIZ, 'dist', formulario.id);
  if (!(await fs.pathExists(path.join(dist, 'index.html')))) {
    throw new Error(
      `El build de "${formulario.id}" no produjo index.html en ${path.relative(RAIZ, dist)}`,
    );
  }

  // La clave de desarrollo nunca viaja en un ZIP (QA y Producción reciben estos mismos ZIP).
  await comprobarSinSecretos(dist, secretosDeDesarrollo(RAIZ));

  const temporal = path.join(RAIZ, 'temp_build', formulario.id);
  await fs.remove(temporal);
  await fs.ensureDir(temporal);

  // Puente al tema de la Living Application: la
  // plataforma expone su tema a la página en `../theme/theme.css`. Enlazarlo DESPUÉS de
  // los estilos propios permite que el proyecto reparametrice su marca cambiando el tema,
  // sin recompilar los formularios. Se inyecta aquí para que ninguna pantalla tenga que
  // acordarse de hacerlo.
  const indice = path.join(dist, 'index.html');
  const html = await fs.readFile(indice, 'utf-8');
  if (!html.includes('../theme/theme.css')) {
    await fs.writeFile(
      indice,
      html.replace(
        '</head>',
        '    <link rel="stylesheet" href="../theme/theme.css" />\n  </head>',
      ),
    );
  }

  // Estructura que exige la plataforma (doc ROOT:resource-management):
  // el descriptor en la raíz del archivo y el índice dentro de `resources/`.
  await fs.copy(dist, path.join(temporal, 'resources'));
  await fs.writeFile(
    path.join(temporal, 'page.properties'),
    descriptorDeRecurso(formulario, version),
  );

  for (const requerido of ['page.properties', 'resources/index.html']) {
    if (!(await fs.pathExists(path.join(temporal, requerido)))) {
      throw new Error(`Falta ${requerido} en el paquete de "${formulario.id}"`);
    }
  }

  return comprimir(temporal, formulario);
}

/** Comprime la carpeta temporal del paquete en dist-zips/<custompage>.zip y la borra. */
async function comprimir(temporal, formulario) {
  await fs.ensureDir(SALIDA_ZIPS);
  const zip = path.join(SALIDA_ZIPS, `${formulario.custompage}.zip`);
  await fs.remove(zip);
  await new Promise((resolver, rechazar) => {
    const salida = createWriteStream(zip);
    const archivo = archiver('zip', { zlib: { level: 9 } });
    salida.on('close', resolver);
    archivo.on('error', rechazar);
    archivo.pipe(salida);
    archivo.directory(temporal, false);
    archivo.finalize();
  });
  await fs.remove(temporal);

  const { size } = await fs.stat(zip);
  bien(
    `${formulario.custompage}.zip (${(size / 1024).toFixed(1)} KB) — recurso de "${formulario.id}"`,
  );
  return zip;
}

/**
 * Empaqueta un tema propio (`tipo: tema`): sin Vite. `resources/theme.css` = Bootstrap 3 + la
 * hoja del proyecto, `resources/fonts/` (las de Bootstrap) y `resources/images/` si el proyecto
 * la tiene. Bootstrap es lo que espera el layout de Bonita, igual que el tema por defecto.
 */
async function empaquetarTema(formulario, version) {
  const carpeta = path.join(RAIZ, 'src', 'forms', formulario.id);
  const propio = path.join(carpeta, 'tema.css');
  if (!(await fs.pathExists(propio))) {
    throw new Error(`El tema "${formulario.id}" no tiene ${path.relative(RAIZ, propio)}`);
  }
  const css = path.join(BOOTSTRAP, 'css', 'bootstrap.css');
  if (!(await fs.pathExists(css))) {
    throw new Error(
      `Falta Bootstrap 3 en ${path.relative(RAIZ, BOOTSTRAP)} (dependencia de desarrollo de la plantilla): corre npm ci`,
    );
  }
  const temporal = path.join(RAIZ, 'temp_build', formulario.id);
  await fs.remove(temporal);
  await fs.ensureDir(path.join(temporal, 'resources'));
  await fs.writeFile(
    path.join(temporal, 'resources', 'theme.css'),
    cssDelTema(await fs.readFile(css, 'utf-8'), await fs.readFile(propio, 'utf-8')),
  );
  await fs.copy(path.join(BOOTSTRAP, 'fonts'), path.join(temporal, 'resources', 'fonts'));
  if (await fs.pathExists(path.join(carpeta, 'images'))) {
    await fs.copy(path.join(carpeta, 'images'), path.join(temporal, 'resources', 'images'));
  }
  await fs.writeFile(path.join(temporal, 'page.properties'), descriptorDeRecurso(formulario, version));
  return comprimir(temporal, formulario);
}

/**
 * Deja constancia de QUÉ fuentes se empaquetaron, junto a los ZIP.
 *
 * `mvn package` no recompila el front: copia el ZIP que encuentre. Sin esta estampa, un
 * `dist-zips` de otra versión se despliega en silencio y el runtime muestra la pantalla
 * anterior con todo en verde (pasó el 2026-09-09 y otra vez el 2026-09-10). El custodio
 * un custodio de CI puede recalcular la huella y compara: si no coincide, el ZIP no
 * corresponde a las fuentes y no es desplegable.
 */
async function estampar(formulario) {
  const registro = path.join(SALIDA_ZIPS, '.fuentes.json');
  const previo = (await fs.pathExists(registro)) ? await fs.readJson(registro) : {};
  previo[formulario.custompage] = {
    id: formulario.id,
    sha256: await huellaDeFuentes(RAIZ, formulario.id),
    ficheros: (await fuentesDe(RAIZ, formulario.id)).length,
  };
  await fs.writeJson(registro, previo, { spaces: 2 });
}

async function main() {
  const argumentos = process.argv.slice(2);
  const todos = argumentos.includes('--all');
  const pasos = pasosDelBuild(argumentos);
  const idPedido = argumentos.find((a) => !a.startsWith('--'));

  if (!todos && !idPedido) {
    mal('uso: node scripts/build-form.js <id> | --all [--solo-empaquetar]');
    process.exit(2);
  }

  const formularios = await leerManifiesto();
  const { version } = await fs.readJson(path.join(RAIZ, 'package.json'));

  let objetivo;
  if (todos) {
    // Solo los que YA tienen pantalla. Los demás se entregan después, y sin
    // `index.html` el build fallaría con un volcado de rollup ilegible: mejor decir
    // exactamente qué falta.
    const conPantalla = [];
    const sinPantalla = [];
    for (const f of formularios) {
      const existe = await fs.pathExists(path.join(RAIZ, 'src', 'forms', f.id, ficheroDeEntrada(f)));
      (existe ? conPantalla : sinPantalla).push(f);
    }
    if (sinPantalla.length > 0) {
      aviso(
        `sin pantalla todavía (se entregan después): ${sinPantalla
          .map((f) => f.id)
          .join(', ')}`,
      );
    }
    objetivo = conPantalla;
  } else {
    const encontrado = formularios.find((f) => f.id === idPedido);
    if (!encontrado) {
      mal(
        `El formulario "${idPedido}" no está en el manifiesto. Declarados: ${formularios
          .map((f) => f.id)
          .join(', ')}`,
      );
      process.exit(1);
    }
    objetivo = [encontrado];
  }

  // Una vez, antes de compilar nada (también con --all y con --solo-empaquetar): «no compila» =
  // «no se construye», aunque se empaquete el `dist` que ya hay.
  if (pasos.includes('verificar-tipos')) {
    info('verificación de tipos (npm run check)');
    verificarTipos({ cwd: RAIZ });
    bien('tipos verificados');
  }

  const paquetes = [];
  for (const formulario of objetivo) {
    if (formulario.tipo === 'tema') {
      paquetes.push(await empaquetarTema(formulario, version));
    } else {
      if (pasos.includes('compilar')) compilar(formulario.id);
      paquetes.push(await empaquetar(formulario, version));
    }
    await estampar(formulario);
  }

  console.log('');
  bien(`${paquetes.length} recurso(s) en ${path.relative(RAIZ, SALIDA_ZIPS)}/`);
}

main().catch((error) => {
  mal(error.message);
  process.exit(1);
});
