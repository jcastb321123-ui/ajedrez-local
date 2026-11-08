# Contribuir a Ajedrez local

La prioridad es consolidar la partida local y sus herramientas de análisis.
Consulta el [alcance y las limitaciones](readme.md#limitaciones-y-próximos-pasos)
antes de proponer una modalidad nueva.

## Preparar el entorno

Utiliza Python 3.13 con Tkinter. Las instrucciones de
[instalación](readme.md#instalación) crean el entorno `.venv`.
Para trabajar sobre las fuentes, ejecuta desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m ajedrez.aplicacion
```

El lanzador instalado utiliza una copia del paquete. Después de modificar las
fuentes, hay que reinstalar para actualizar esa copia; no es necesario hacerlo
para ejecutar las fuentes con el comando anterior.

## Preparar un cambio

1. Identifica el comportamiento que quieres modificar y la capa responsable.
   La [guía de arquitectura](docs/arquitectura.md) describe sus relaciones.
2. Si corriges un fallo, reproduce primero el caso con una prueba concreta.
   Comprueba las precondiciones existentes antes de añadir comprobaciones nuevas.
3. Implementa el cambio y conserva las convenciones del módulo: nombres
   descriptivos en castellano, atributos de instancia definidos en el constructor
   y anotaciones de tipos cuando aclaren el contrato.
4. Añade pruebas del comportamiento que pueda fallar y actualiza la documentación
   si cambian los controles, requisitos o resultados de la aplicación.

Las coordenadas lógicas se expresan como `(fila, columna)`, con índices de 0 a 7.
`a1` corresponde a `(0, 0)` y las blancas avanzan hacia filas mayores.
Los identificadores del Canvas son referencias gráficas; no identifican piezas
del modelo ni deben utilizarse para reconstruir una partida guardada.

## Verificar

Durante el desarrollo, ejecuta las pruebas relacionadas con el cambio. Por ejemplo,
para el arranque y la creación de una partida:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest pruebas.test_aplicacion -v
```

Antes de integrar un cambio que afecte al funcionamiento:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s pruebas -t . -p "test_*.py"
```

Si cambian la distribución, los recursos o los puntos de entrada, ejecuta también
la [comprobación del paquete instalado](readme.md#comprobar-el-paquete-distribuible).
Una prueba gráfica omitida por falta de pantalla no cuenta como verificación de
la interfaz. El comprobador de instalación exige que Tkinter pueda arrancar.

Las demostraciones actuales están documentadas en [pruebas/README.md](pruebas/README.md).
Los entornos virtuales, paquetes construidos, copias de sincronización y ejercicios
históricos excluidos por `.gitignore` no forman parte de la entrega.

## Describir un fallo o una propuesta

Incluye los pasos para reproducirlo, el resultado esperado, el resultado observado
y la versión de Python y del sistema operativo. Para una regla de ajedrez,
especifica la posición, el turno y los movimientos implicados. El enroque, la
captura al paso y las reglas de tablas pueden necesitar también sus metadatos
o el historial.

En una solicitud de cambios, explica qué problema resuelve, qué comportamiento
cambia y qué pruebas se han ejecutado. Las modalidades remota y contra IA, la
base de datos de usuarios y el menú de preferencias siguen pendientes de diseño
e integración. El formato de archivos de partida está documentado en
[docs/persistencia.md](docs/persistencia.md).

## Publicar una versión

1. Actualiza `project.version` en `pyproject.toml` y revisa los comandos de
   instalación del README.
2. Añade `docs/versiones/v<versión>.md` con las novedades, la instalación y las
   limitaciones de esa entrega.
3. Integra los cambios en `main` e inicia el flujo **Pruebas y paquete de la
   versión local** desde Actions, con la opción `publicar` activada. También se
   puede solicitar la publicación incluyendo `[publicar version]` en el mensaje
   del último commit enviado a `main`.
4. Comprueba que ambos trabajos, `comprobar` y `publicar`, terminan correctamente
   y que la entrega contiene el paquete y `SHA256SUMS.txt`.

El flujo obtiene la versión de `pyproject.toml`. La etiqueta `v<versión>` señala
el commit comprobado y la entrega incluye el mismo paquete que se instaló y probó.
La publicación sólo está habilitada desde `main` y no se ejecuta en solicitudes
de cambios. Sólo el trabajo de publicación recibe permiso de escritura.

No se sustituyen versiones ya publicadas: si una entrega necesita cambios,
incrementa la versión y prepara unas nuevas notas. Una entrega no implica que
estén implementadas las funcionalidades que siguen documentadas como pendientes.
