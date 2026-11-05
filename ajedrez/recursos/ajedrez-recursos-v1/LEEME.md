# Recursos visuales de ajedrez — v1

Recursos utilizados por `TemaGrafico` y `Casillero`. El catálogo relaciona las imágenes y los datos de estilo; `cargar_tema` crea las imágenes de Tkinter y conserva sus referencias.

## Qué contiene

- Los cuatro acabados acordados: **liso mate, microfibra, veta fina y mineral suave**.
- 48 imágenes de piezas: seis tipos × dos bandos × cuatro acabados.
- 48 proyecciones de esas piezas, con contornos discontinuos y rellenos tenues.
- 12 piezas adicionales con contorno reforzado.
- Casillas claras/oscuras en los cuatro acabados y las tres paletas: 24 materiales compuestos.
- Fondos, selección, foco, último movimiento, destino/captura legal, atención, jaque y promoción pendiente.
- Flechas continuas, discontinuas y de caballo en rojo, azul, verde y ámbar; círculos y tintes de esos colores.
- Iconos de anotar, ocultar y limpiar en grafito y marfil; fondos de botón y divisor.
- Letras a–h y números 1–8 como imágenes auxiliares; distintivos de secuencia 1–10.
- Estilos de letra, colores y textos de interfaz como datos configurables.
- Seis texturas originales generadas con ImageGen y sus instrucciones de generación.

Las señales de análisis son compartidas por los cuatro acabados, deliberadamente: cambiar de madera a mineral no debe cambiar el significado de un aviso.

## Por dónde empezar

1. Abrir **VISTA_GENERAL.png** para ver las piezas y señales reales del paquete.
2. Consultar **catalogo.json**, el índice que relaciona nombres, archivos y propiedades.
3. Para el tablero actual de 480 × 480, elegir casillas y piezas de **png/60/**: cada casilla mide 60 × 60.
4. Empezar por el preajuste **club.liso_mate**. Los otros tres acabados de referencia son **club.microfibra**, **taller.veta_fina** y **pizarra.mineral_suave**.
5. Mantener el paquete completo junto. Sus rutas son relativas a esta carpeta, no al directorio desde el que se ejecute Python.

También se suministran exportaciones para casillas de 120 y 240 px. El nombre de la carpeta indica la escala de referencia del tablero; las imágenes de flechas, botones, glifos e iconos tienen las dimensiones propias anotadas en el catálogo.

## La terminología, aplicada al paquete

| Término | Qué significa aquí |
| --- | --- |
| Recurso gráfico / asset | Imagen, fuente descrita, color o geometría reutilizable |
| Textura | Imagen que proporciona un acabado natural |
| Sprite | Imagen individual de una pieza o elemento visual |
| Canal alfa | Transparencia de un PNG; permite ver la casilla alrededor de la pieza |
| Superposición / overlay | Marca dibujada encima de otra imagen, sin reemplazarla |
| Vector / SVG | Formas y trazos descritos matemáticamente, editables y escalables |
| Raster / PNG | Imagen formada por píxeles, lista para cargar |
| Manifiesto / catálogo | Archivo que identifica recursos y sus propiedades |
| Token de diseño | Valor con nombre, por ejemplo rojo de atención o grosor de una flecha |
| Tema | Asociación coordinada de recursos; no es una clase del motor |
| Glifo | Representación gráfica de un carácter, como “a” o “7” |

## Relación con los objetos Python

El **archivo PNG** permanece en disco. Al cargarlo, la biblioteca gráfica crea un **objeto de imagen** en memoria. Una instancia de PiezaVisual puede conservar una referencia a ese objeto y decidir dónde representarlo. Varias piezas pueden compartir la misma imagen: no hace falta copiar el archivo ni cargar una imagen por peón.

El catálogo JSON puede cargarse como diccionarios y listas de Python. No impone todavía una jerarquía de clases. Cada recurso tiene un identificador estable, tipo, archivos por escala, dimensiones y las propiedades pertinentes. Por ejemplo:

- pieza.liso_mate.blanca.rey
- pieza.veta_fina.negra.caballo
- proyeccion.mineral_suave.blanca.dama
- casilla.club.microfibra.oscura
- marca.seleccion
- flecha.azul.discontinua
- glifo.grafito.a

Los colores se encuentran en **colores** y **paletas**; las fuentes en **tipografia**; los recorridos adaptables en **geometria**; las etiquetas editables en **textos**.

No se ha escrito un cargador, modificado MaterialVisual ni conectado imágenes a tu programa. Ese será un ejercicio separado.

## Qué cargar en Tkinter

Usar los **PNG** para las imágenes de esta primera GUI. PhotoImage documenta soporte PNG; SVG no es su formato de carga directo.

Los maestros **SVG** se conservan para modificar o volver a exportar los dibujos. Los SVG de materiales texturados son híbridos: formas vectoriales con textura raster incrustada. Sus contornos escalan; la textura conserva una resolución finita.

Es importante mantener referencias a los objetos PhotoImage durante su uso: mostrar la imagen en Canvas no debe ser su única referencia Python. Al cambiar tamaño, reutilizar/cargar la escala apropiada; no estirar cada pieza de forma independiente.

El constructor auxiliar `fuentes/construir.cjs` conserva la exportación inicial. Requiere Node.js y el módulo `sharp`, que debe estar disponible para `require("sharp")`. No es una regeneración completa de las incorporaciones posteriores al catálogo: antes de reexportar, hay que integrarlas en el generador y trabajar sobre una copia de los recursos. No hace falta ejecutarlo ni instalar sus dependencias para utilizar los PNG. Las seis texturas originales permanecen intactas; las exportaciones son composiciones de color base, textura y silueta.

## Tipografía y texto: recursos, pero no todo debe aplanarse

Se han fijado fuentes concretas: **Segoe UI** para interfaz/coordenadas y **Georgia** para títulos, con alternativas documentadas. Los bocetos generados no identificaban una fuente digital exacta; estos perfiles normalizan su intención tipográfica para la GUI.

El catálogo define familia, tamaño, peso, color y, cuando procede, proporción respecto a la casilla. No se redistribuyen archivos de fuentes de Windows. Se comprobó que sus archivos están presentes en este equipo.

Los PNG de letras/números permiten usarlos como imágenes si se desea. Para etiquetas, turnos, nombres, coordenadas escalables y traducciones, es preferible **texto dinámico con un estilo**: sigue siendo un recurso asociable a un objeto Python y conserva selección, accesibilidad y posibilidad de cambiar el contenido.

Las muestras tipográficas no son botones ni sustituyen las etiquetas dinámicas.

## Flechas y anotaciones adaptables

Los PNG de flechas son recursos independientes con una orientación/longitud determinada. Sus extremos y dimensiones están registrados. No se deben estirar para conectar cualquier par de casillas: se deformarían cabeza, grosor y guiones.

Para recorridos arbitrarios, el recurso adecuado es la **definición geométrica** del catálogo, junto con color, trazo, halo y coordenadas de origen/destino. `Casillero` dibuja las flechas con Canvas y utiliza las propiedades proporcionadas por el tema. El SVG sirve de maestro de referencia.

Círculos, marcos, tintes e indicadores de una sola casilla sí pueden usarse directamente como PNG a la escala correcta. Las letras/números y distintivos pequeños tienen lienzos más pequeños, documentados individualmente.

Las marcas manuales no certifican legalidad ni amenazas; el jaque sólo debe anunciarse desde el estado del juego. Una proyección no altera el tablero aceptado. La promoción reutiliza las imágenes existentes de dama, torre, alfil y caballo y mantiene su contrato modal.

## Criterios y verificación

- PNG decodificados, dimensiones contrastadas con el manifiesto y transparencias comprobadas automáticamente.
- Piezas reales y proyectadas tienen exterior transparente y márgenes; no llevan la casilla pegada.
- Casillas compuestas con una intensidad de textura acotada. VALIDACION.json recoge su variación de luminancia respecto al color base y las huellas de los archivos.
- Se inspeccionó visualmente el montaje de piezas y ayudas sobre las casillas.
- Los originales de textura son útiles como fuente, pero no se garantiza que sus bordes sean matemáticamente periódicos. Los materiales finales están pensados para casillas individuales y variación discreta.
- La integración actual con Tkinter se comprueba en `pruebas/test_cargar_tema.py` y `pruebas/test_aplicacion.py`. `herramientas/comprobar_instalacion.py` verifica además el arranque y los movimientos con las imágenes de una instalación nueva. Las instrucciones están en el [README del proyecto](../../../readme.md#pruebas).
- No se han evaluado formalmente lectores de pantalla, comodidad prolongada ni todas las combinaciones gráficas.

`VALIDACION.json` conserva las comprobaciones de la exportación inicial. No sustituye las pruebas actuales de integración ni certifica la accesibilidad.

## Organización

- catalogo.json: datos utilizables desde Python.
- png/: exportaciones listas para cargar, por escala.
- svg/: maestros de las formas y materiales.
- originales/texturas/: seis imágenes originales.
- fuentes/: definición de las formas y herramienta de exportación; instrucciones de ImageGen.
- VISTA_GENERAL.png: hoja de inspección.
- VALIDACION.json: dimensiones, transparencia, variación y huellas.
- LEEME.md: esta guía.

No se han copiado sprites de Chess.com ni Lichess. Las siluetas y señales son trazados originales para este paquete; las texturas se crearon con ImageGen integrado. El código y los programas históricos de tu proyecto permanecen sin modificar.

