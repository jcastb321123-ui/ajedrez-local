# Ejecución y pruebas del proyecto

El código de la aplicación está en el paquete `ajedrez`. Dentro están los módulos
del modelo y de sesión, el subpaquete `gráficos` y la carpeta `recursos` con las
imágenes y el catálogo. Las pruebas y los programas de demostración están fuera,
en `pruebas`.

Los siguientes comandos se ejecutan desde la carpeta exterior del proyecto,
la que contiene tanto `ajedrez` como `pruebas`. Se han verificado con Python 3.13
y Tkinter disponible. La interfaz requiere un entorno gráfico.

## Ejecutar la aplicación

```powershell
python -m ajedrez.aplicacion
```

Este comando, ejecutado desde la raíz del proyecto, utiliza el código fuente.
No ejecutes directamente el archivo interior `ajedrez/aplicacion.py`: sus
importaciones relativas necesitan el contexto del paquete. El proyecto también
puede instalarse y dispone del lanzador `ajedrez`; consulta las instrucciones de
[instalación y ejecución del README principal](../readme.md).

Los recursos se localizan a partir del archivo `temas_graficos.py`, no de una ruta
personal ni del directorio desde el que se carga el tema. `cargar_tema` sigue
permitiendo indicar otra carpeta de recursos explícitamente.

## Programas de demostración

El repositorio incluye dos demostraciones actuales:

- `main_prueba2.py`: sesión local real en consola, dos emisores, claves
  automáticas, reparto de colores, promoción en dos pasos y resultado.
- `gui_prueba4.py`: montaje de una sesión local y un tablero gráfico.

`test_main_prueba2.py` comprueba la consola con entrada simulada y clases reales
del juego. Algunos finales usan posiciones preparadas.

## Ejecutar la segunda consola

Desde la carpeta exterior del proyecto:

```powershell
python -m pruebas.main_prueba2
```

1. Elige reparto aleatorio (1 o Intro), jugador 1 con blancas (2), o jugador 1
   con negras (3). El otro jugador recibe el color restante.
2. La consola indica quién juega. Introduce primero origen y después destino,
   en preguntas separadas: por ejemplo `e2` y `e4`.
3. También admite `1,4` o `(1, 4)`: fila y columna de 0 a 7. `a1 = (0, 0)`,
   `e2 = (1, 4)`, `e4 = (3, 4)`; las blancas avanzan hacia filas mayores.
4. Una entrada mal formada o un movimiento rechazado se descarta sin mensaje
   de error, sin cambiar el turno. Se vuelve a pedir origen.
5. Al promocionar, sólo se admite elegir dama (`d`), torre (`t`), alfil (`a`) o
   caballo (`c`). Una elección inválida vuelve a pedir la pieza, no un movimiento.
6. Tras terminar la partida se muestra el resultado y no se recoge otra jugada.

`salir` funciona en cualquier pregunta. Fin de entrada y Ctrl+C durante una
pregunta también cierran la consola. Cerrar no equivale a rendirse ni a declarar
tablas; esta versión no guarda partidas. Si hay promoción pendiente, no se confirma.

Las claves se generan y adjuntan automáticamente, sin imprimirse. En un teclado
compartido se confía en que escriba la persona indicada: las claves identifican
al emisor habilitado, no a la persona física que está delante del equipo.

## Ejecutar las pruebas

Desde la carpeta del proyecto:

```powershell
python -B -m unittest discover -s pruebas -t . -p "test_*.py"
```

Para ejecutar sólo las pruebas de arranque:

```powershell
python -B -m unittest pruebas.test_aplicacion -v
```

Estas comprueban la importación sin abrir ventanas, el punto de entrada como módulo,
la localización de recursos y el arranque real con un movimiento e2-e4. Las pruebas
gráficas pueden omitirse si Tkinter no dispone de pantalla; las del catálogo fallan
si faltan los recursos incluidos.

Las pruebas no certifican todas las reglas de ajedrez. Esta consola presenta los
resultados que determina el modelo actual; no añade reglas de tablas, persistencia,
IA ni juego en red.

## Relación con la interfaz gráfica

La conversión de texto queda en `convertir_posicion`. El bucle sólo consulta el
estado y llama a `EmisorJugador.enviar_solicitud` o `elegir_promocion`: no modifica
tableros, turnos, claves ni historial directamente. La consola recibe funciones de
lectura y escritura para que sus interacciones puedan probarse sin teclado.

La aplicación utiliza eventos de Tkinter y la misma capa de sesión. La demostración
gráfica actual también puede ejecutarse como módulo:

```powershell
python -m pruebas.gui_prueba4
```

Los ejercicios anteriores y las copias de sincronización se conservan en el
equipo de desarrollo y se excluyen mediante `.gitignore`. No se necesitan para
ejecutar la aplicación ni esta batería de pruebas.

## Preferencias gráficas

Para comprobar conjuntamente el diálogo, el cambio de tema y la recuperación
de la configuración al reiniciar:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest pruebas.test_dialogo_preferencias pruebas.test_cambio_tema pruebas.test_preferencias_graficas -v
```

Estas pruebas utilizan widgets reales y archivos temporales. Incluyen el
historial, las variantes, el editor, la promoción pendiente y los errores de
lectura o escritura, sin modificar las preferencias personales del equipo.
El comprobador del paquete instalado reproduce también Aplicar → cerrar → abrir.
