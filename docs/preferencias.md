# Preferencias gráficas

Desde v0.4.0, el diálogo **Preferencias** permite elegir el tema y el modo de
resaltado del jaque, y conservarlos entre ejecuciones por separado de las partidas.
Para los controles y su efecto sobre el tablero, consulta el
[uso de las preferencias](../readme.md#preferencias-visuales).

En Windows se utiliza `%LOCALAPPDATA%\ajedrez-local\preferencias.json`. Si no
existe `LOCALAPPDATA`, se utiliza `~/.config/ajedrez-local/preferencias.json`.
`AplicacionAjedrez(ruta_preferencias=...)` admite una ruta alternativa. Leer no
crea carpetas ni archivos: se crean cuando se confirma el diálogo.

## Formato 1

```json
{
  "formato": "ajedrez-local-preferencias",
  "version": 1,
  "tema": "club.liso_mate",
  "opciones_visuales": {
    "modo_resaltado_jaque": "rey_permanente",
    "intervalo_parpadeo_jaque_ms": 300,
    "repeticiones_parpadeo_jaque": 3
  }
}
```

El tema se identifica mediante una clave del catálogo. Los modos admitidos son
`rey_permanente`, `intermitente_tras_rechazo` y `rey_y_atacantes`. El intervalo y
las repeticiones son enteros positivos; se conservan aunque el diálogo actual
no los permita editar. La selección de «Restablecer» afecta a los controles
visibles: tema y modo del jaque.

Los marcadores de formato y versión son obligatorios. Dentro de esta versión,
el tema, el objeto de opciones y sus campos omitidos toman los valores
predeterminados. Los valores incorrectos y las versiones incompatibles se
rechazan. Los nuevos campos y cambios de formato deben incorporarse a las
funciones de conversión y a sus pruebas; añadir un atributo Python no modifica
por sí solo el formato persistente.

## Lectura, guardado y errores

- `cargar_preferencias` devuelve valores predeterminados si no existe el archivo;
  comunica errores de formato mediante `ErrorPreferencias` y de lectura mediante
  `OSError`. No modifica el archivo recibido.
- `guardar_preferencias` crea la carpeta si hace falta, escribe y sincroniza un
  temporal en ella, y sustituye el destino sólo al completar la escritura.
  Un fallo conserva el archivo anterior y retira el temporal.
- `preferencias_a_datos` y `preferencias_desde_datos` delimitan el formato. No
  importan Tkinter, el modelo ni las sesiones.
- La aplicación carga la configuración antes de construir el tablero. Si no
  puede utilizar el archivo, avisa y arranca con valores predeterminados sin
  sobrescribirlo. Si sólo falla el tema, conserva las opciones del jaque válidas.
- «Aplicar» guarda y actualiza la vista. Cancelar, Escape o cerrar el diálogo no
  escriben. Un fallo de escritura mantiene abierto el diálogo y deja la vista
  anterior para poder reintentar. «Restablecer» necesita confirmarse con «Aplicar».

El archivo no contiene partidas, sesiones, credenciales, variantes, anotaciones,
imágenes ni rutas a recursos. Guardar o abrir partidas no cambia la configuración
gráfica. Guardar preferencias no confirma los cambios pendientes de una partida.

Las pruebas están en `pruebas/test_preferencias_graficas.py`, junto con las de
temas y del diálogo. Utilizan rutas temporales; el comprobador del paquete
instalado también aísla su configuración de la del usuario.
