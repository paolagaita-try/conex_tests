# Imagen oficial Community 2026.2 + el script que pone el application archive en el classpath.
FROM --platform={{PLATAFORMA}} {{IMAGEN_BONITA}}
COPY --chown=bonita:bonita 10-application.sh /opt/custom-init.d/10-application.sh
# Permisos REST del proyecto (p. ej. los de la API de parámetros para el perfil User): solo el fichero, en la
# configuración inicial del tenant, que la imagen aplica en el primer arranque. `permisos` es el contexto adicional
# del compose (fuera de compose: docker build --build-context permisos=../../bonita-project/app/permisos ...).
COPY --from=permisos --chown=bonita:bonita custom-permissions-mapping.properties /opt/bonita/setup/platform_conf/initial/tenant_portal/custom-permissions-mapping.properties
