# Guardado y recuperación de partidas locales

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

La aplicación reconstruye la partida antes de sustituir la vista. Crea una
`SesionLocal(..., partida=recuperada)` con nuevas claves de sesión y muestra su
estado vigente mediante `InterfazPartida.mostrar_estado`. Una partida terminada
sigue permitiendo navegación y análisis, sin reabrir el juego original.

`Sesion.admite_guardado_local` devuelve `False` por defecto y `SesionLocal` la
redefine como `True`. Las futuras modalidades podrán decidir su propia política.
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
partida. La biblioteca de partidas en base de datos sigue siendo una ampliación
posterior; esta versión permite transportar y recuperar archivos individuales.

Las pruebas están en `pruebas/test_persistencia.py` y
`pruebas/test_persistencia_aplicacion.py`.
