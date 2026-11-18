#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/lib/state-io.sh
# state-io.sh — en el original: rutas y patch atómico del fichero de estado local (la fuente de
# verdad de los modos legacy/dual). En el arnés Bonita el estado vive SOLO en el hub (U16): no
# hay fichero de estado local, así que `state_path` y `state_atomic_patch` se retiraron. Queda
# como compatibilidad de sourcing: un hook copiado del original que haga
# `source lib/state-io.sh` para usar `config_get` sigue funcionando sin cambios.
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
