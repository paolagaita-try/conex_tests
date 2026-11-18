# custom-init.d de la imagen oficial: corre en cada arranque, antes de Tomcat (se ejecuta con `.`: nada de `exit`).
# El instalador del motor busca el archive en el classpath (`classpath*:/my-application/*.zip` y `*.bconf`);
# `${catalina.home}/lib` es raíz del common.loader de Tomcat. Misma técnica que el proyecto piloto.
DESTINO_APP=/opt/bonita/server/lib/my-application
rm -rf "$DESTINO_APP"
mkdir -p "$DESTINO_APP"
if ls /srv/my-application/*.zip >/dev/null 2>&1; then
  cp /srv/my-application/*.zip "$DESTINO_APP/"
  cp /srv/my-application/*.bconf "$DESTINO_APP/" 2>/dev/null || true
  echo "my-application: $(ls "$DESTINO_APP" | tr '\n' ' ')"
else
  echo "my-application: /srv/my-application vacío — arranque sin aplicación propia"
fi
