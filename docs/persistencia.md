# Guardado y recuperación del modelo de partida

`ajedrez.persistencia` no depende de Tkinter ni de claves de autenticación. Sus
funciones permiten guardar una `Partida` y construir otra instancia independiente:

```python
from ajedrez.persistencia import guardar_partida, cargar_partida

guardar_partida(partida, "partida.json")
recuperada = cargar_partida("partida.json")
```

`partida_a_datos` y `partida_desde_datos` realizan la conversión sin acceder al
sistema de archivos. Esta separación permite reutilizar el formato desde otro
medio de almacenamiento.

## Repositorio SQLite

`ajedrez.repositorio_partidas.RepositorioPartidasSQLite` permite guardar,
actualizar, listar, cargar y eliminar partidas en una base de datos. La carpeta del archivo
debe existir:

```python
from ajedrez.repositorio_partidas import RepositorioPartidasSQLite

repositorio = RepositorioPartidasSQLite("biblioteca.sqlite3")
id_partida = repositorio.guardar_partida(partida, "Mi partida")
recuperada = repositorio.cargar_partida(id_partida)

# Después de continuar jugando con la partida recuperada:
repositorio.actualizar_partida(id_partida, recuperada, "Mi partida")

for resumen in repositorio.listar_partidas():
    print(resumen.id_partida, resumen.titulo, resumen.fecha_actualizacion)
```

`guardar_partida` inserta una copia nueva, aunque se repita el título, y devuelve su
identificador. Las fechas de creación y actualización coinciden al insertar y
se almacenan en UTC con formato ISO 8601. Una escritura fallida revierte la
transacción.

`actualizar_partida(id_partida, partida, titulo) -> None` modifica el contenido,
el título y la fecha de actualización del registro indicado. Conserva su
identificador y su fecha de creación. El título es obligatorio; para conservarlo,
se pasa el mismo título. La fecha de actualización se toma de la hora actual en
UTC, también cuando se guarda el mismo contenido.

Si el identificador no existe, lanza `KeyError` y no crea un registro. Una promoción
pendiente provoca `ErrorArchivoPartida` antes de escribir. La actualización se
confirma en una sola transacción; ante un fallo de escritura, el registro anterior
permanece intacto y la conexión se cierra. Recibe únicamente el modelo `Partida`,
sin depender de la modalidad de juego ni modificar la instancia recibida.

`eliminar_partida(id_partida) -> None` borra sólo ese registro. Si no existe,
lanza `KeyError`. Un error de escritura revierte el borrado. Las instancias de
`Partida` que ya se hubieran cargado no resultan alteradas por esa eliminación.

`listar_partidas()` devuelve una `tuple[ResumenPartida, ...]`. Cada resumen es una
dataclass inmutable con `id_partida`, `titulo`, `fecha_creacion` y
`fecha_actualizacion`; ambas fechas son objetos `datetime` con zona horaria UTC.
El resultado se ordena por última actualización descendente y, en caso de empate,
por identificador descendente. Una biblioteca vacía devuelve `()`.

El listado consulta únicamente esos cuatro campos: no lee el JSON ni reconstruye
historiales. Por ello, un historial dañado puede aparecer en la biblioteca; su
validación se realiza al cargarlo. El resultado es una instantánea independiente,
disponible tras cerrar la conexión, y la consulta no modifica los registros.

La carga busca por identificador, reconstruye una `Partida` independiente y no
modifica el registro ni sus fechas. Reutiliza `partida_desde_datos` para recuperar
la posición inicial, el turno, el historial y el resultado. Un identificador
inexistente provoca `KeyError`; un JSON o modelo inválido provoca
`ErrorArchivoPartida`. Los errores de acceso a SQLite se propagan como
`sqlite3.Error` o una de sus subclases. Las conexiones se cierran también cuando
hay errores.

El repositorio no construye sesiones. El nivel superior elige qué sesión usa la
partida recuperada y cuándo permite guardarla. Reanudar una modalidad remota o
contra IA requerirá además sus propios datos de conexión o configuración; estos
no forman parte del modelo guardado. La interfaz permite utilizar la biblioteca
y sigue admitiendo archivos JSON para transportar partidas entre equipos.

## Formato 1

El documento contiene estas claves:

| Clave | Contenido |
| --- | --- |
| `formato` | La cadena `ajedrez-local`. |
| `version` | El entero `1`; identifica el formato, no la versión de la aplicación. |
| `posicion_inicial` | Distribución de piezas, turno inicial, peón capturable al paso y contador de medios movimientos. |
| `jugadas` | Lista ordenada de movimientos confirmados: origen, destino y elección de promoción, o `null` si no la hubo. |
| `resultado` | `EN_CURSO`, `VICTORIA_BLANCA`, `VICTORIA_NEGRA` o `TABLAS`. |

Cada pieza inicial indica `casilla`, `tipo`, `color` y `ha_movido`. Este último
es booleano para peones, torres y reyes; en las demás piezas es `null`. Los tipos
son `peon`, `caballo`, `alfil`, `torre`, `reina` y `rey`. Los colores son `Blanco`
y `Negro`. Todas las casillas son listas `[fila, columna]` entre 0 y 7: `a1` es
`[0, 0]`.

`peon_capturable_al_paso` indica la casilla ocupada por el peón que acaba de avanzar
dos pasos, no la casilla de destino de una eventual captura. Vale `null` cuando
no existe. `jugadas_sin_captura_ni_peon` cuenta medios movimientos desde la última
captura o movimiento de peón; se conserva también para raíces personalizadas.

No se guardan sólo las piezas de la última posición: eso perdería las repeticiones
y la navegación histórica. Se almacena la raíz y se reproducen las jugadas usando
`Partida.procesar_solicitud` y, cuando corresponde, `Partida.promocionar`. El modelo
reconstruye `registro_turnos`, `ultima_jugada`, `anterior`, `siguiente` y
`estado_anterior`, así como los contadores y los derechos resultantes.

Una raíz tomada de otra partida se conserva como posición inicial independiente:
no se importa el historial anterior a esa raíz ni su último movimiento gráfico.
Sus derechos al paso, enroque y contador sí se mantienen. El turno se almacena
explícitamente, por lo que también puede comenzar el negro.

El resultado se almacena por separado porque un abandono, acuerdo o reclamación
puede terminar una posición que aún admite movimientos. Si la reproducción ya
produce mate o tablas automáticas, el resultado guardado debe coincidir.

## Integración con la aplicación

**Biblioteca** abre el listado por último guardado. **Guardar partida actual**
crea una entrada con el título solicitado o actualiza la entrada asociada a la
partida abierta. **Guardar copia** crea otra entrada y la convierte en el destino
del guardado habitual. La selección del listado sólo se usa para **Abrir** y
**Eliminar**; guardar la partida actual nunca sobrescribe otra fila seleccionada.

Al abrir desde la biblioteca, **Guardar partida** actualiza el mismo registro.
Sin un registro asociado, conserva el guardado por archivo JSON. **Abrir archivo**
permite importar una partida y después guardarla en la biblioteca. **Exportar
archivo** crea una copia JSON sin cambiar el destino del guardado habitual ni
marcar como guardados los avances pendientes en ese destino.

Antes de abrir otra partida, iniciar una nueva o cerrar, el diálogo de cambios
pendientes permite guardar, descartar o cancelar. Si se va a abrir el mismo
registro que se acaba de actualizar desde ese diálogo, se vuelve a leer su
contenido. Un error de carga o escritura conserva la partida abierta.

Eliminar requiere confirmación. Si se elimina el registro de la partida abierta,
la partida permanece en pantalla, pierde su asociación con el registro eliminado
y pasa a estar sin guardar. Puede guardarse de nuevo o exportarse.

En Windows, la ruta predeterminada es
`%LOCALAPPDATA%\ajedrez-local\biblioteca.sqlite3`. Se crea al utilizar la biblioteca
por primera vez. Sin `LOCALAPPDATA`, se utiliza
`~/.local/share/ajedrez-local/biblioteca.sqlite3`. La base de datos no está dentro
del paquete ni del repositorio Git. Para respaldar la biblioteca completa, cierra
la aplicación y copia ese archivo; para trasladar una partida, expórtala como JSON.
Las fechas se almacenan en UTC y se muestran con la hora local del equipo.

La aplicación reconstruye la partida antes de sustituir la vista. Crea una
`SesionLocal(..., partida=recuperada)` con nuevas claves de sesión y muestra su
estado vigente mediante `InterfazPartida.mostrar_estado`. Una partida terminada
sigue permitiendo navegación y análisis, sin reabrir el juego original.

`Sesion.admite_guardado_local` devuelve `False` por defecto y `SesionLocal` la
redefine como `True`. Las futuras modalidades podrán decidir su propia política.
La biblioteca consulta esa capacidad para habilitar sus botones de guardado.
La aplicación guarda `interfaz_partida.sesion.partida`: consultar una posición
histórica o abrir una variante no cambia la partida que se escribe.

Se compara el contenido de la partida con el último guardado para ofrecer
guardar, descartar o cancelar antes de sustituirla o cerrar. Una promoción
pendiente debe resolverse antes de guardar. El guardado no incluye la elección
pendiente, anotaciones, variantes, widgets, identificadores de dibujos,
preferencias ni propuestas de tablas aún no respondidas.

## Validación y escritura

Los archivos son datos externos: se comprueban el formato, los tipos, las casillas,
las piezas y la coherencia básica de la raíz, reutilizando las comprobaciones del
editor de posiciones. Cada movimiento debe ser aceptado por el modelo. Las
versiones desconocidas se rechazan mediante `ErrorArchivoPartida`, sin adivinar
cómo interpretarlas. El archivo JSON no ejecuta código y no utiliza `pickle`.

La escritura se realiza en un archivo temporal dentro de la carpeta de destino.
Sólo se reemplaza el archivo anterior cuando se ha terminado de escribir y
sincronizar el nuevo. Si falla la escritura o el reemplazo, el guardado anterior
permanece intacto. Los errores de acceso se comunican como `OSError`.

El formato no es PGN ni FEN y no incluye firmas para verificar la autoría de una
partida. Se utiliza tanto en los archivos individuales como en los registros SQLite.

Las pruebas están en `pruebas/test_persistencia.py`,
`pruebas/test_persistencia_aplicacion.py`, `pruebas/test_repositorio_partidas.py`
y `pruebas/test_biblioteca_aplicacion.py`.
