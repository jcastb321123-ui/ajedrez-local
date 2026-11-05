import tkinter as tk
from enum import Enum, auto
from pathlib import Path
from typing import Literal, cast, get_args
from ..piezas import Color
from collections.abc import Callable
from .temas_graficos import TemaGrafico, UsoMarca

type Estado = Literal["seleccion", "ultima_jugada", "jaque"]

capas_por_etiqueta = {
   "casilla_clara" : 1,
   "casilla_oscura" : 1,
   "resaltado" : 2,
   "pieza" : 3,
   "proyeccion" : 4,
   "marca" : 5,
   "flecha" : 6,
   "distintivo" : 7,
   "secuencia" : 8
}

class CasillaVisual:
   def __init__(self,
                contenedor: tk.Canvas,
                id_imagen: int,
                id_pieza: int | None,
                coordenadas: tuple[int, int]):
      self._contenedor = contenedor
      self._id_imagen = [id_imagen]
      self._id_marca = [None]
      self._id_pieza = [id_pieza]
      self._id_proyeccion = [None]
      self._id_resaltado = [None]
      # El índice 0 conserva el elemento aplicado sin clave (p. ej., la pieza).
      # Los elementos con clave individual se añaden detrás en la misma lista.
      self._ids_elementos_por_clave: dict[str, int] = {}
      self._id_marcador_de_secuencia = [None]
      self._id_distintivo = [None]
      self._ids_flechas: set[int] = set()
      self._coordenadas = coordenadas
      self._variables_id = {
         "imagen": self._id_imagen,
         "resaltado" : self._id_resaltado,
         "pieza" : self._id_pieza,
         "proyeccion" : self._id_proyeccion,
         "marca" : self._id_marca,
         "distintivo" : self._id_distintivo,
         "secuencia": self._id_marcador_de_secuencia
      }
      self._capas = {
         1 : self._id_imagen,
         2 : self._id_resaltado,
         3 : self._id_pieza,
         4 : self._id_proyeccion,
         5 : self._id_marca,
         6 : self.ids_flechas,
         7 : self._id_distintivo,
         8 : self._id_marcador_de_secuencia
      }


   @property
   def contenedor(self) -> tk.Canvas:
      return self._contenedor

   @property
   def id_imagen(self) -> int:
      return self._id_imagen[0]

   @property
   def id_marca(self) -> int | None:
      return self._id_marca[0]

   @id_marca.setter
   def id_marca(self,
                nuevo_id: int) -> None:
      self._id_marca[0] = nuevo_id

   @property
   def id_pieza(self) -> int | None:
      return self._id_pieza[0]

   @id_pieza.setter
   def id_pieza(self,
                nuevo_id: int) -> None:
      self._id_pieza[0] = nuevo_id

   @property
   def id_proyeccion(self) -> int | None:
      return self._id_proyeccion[0]

   @id_proyeccion.setter
   def id_proyeccion(self,
                     nuevo_id: int) -> None:
      self._id_proyeccion[0] = nuevo_id

   @property
   def id_resaltado(self) -> int | None:
      return self._id_resaltado[0]

   @id_resaltado.setter
   def id_resaltado(self,
                    nuevo_id: int) -> None:
      self._id_resaltado[0] = nuevo_id

   @property
   def id_marcador_de_secuencia(self) -> int | None:
      return self._id_marcador_de_secuencia[0]

   @id_marcador_de_secuencia.setter
   def id_marcador_de_secuencia(self,
                                nuevo_id: int) -> None:
      self._id_marcador_de_secuencia[0] = nuevo_id

   @property
   def id_distintivo(self) -> int | None:
      return self._id_distintivo[0]

   @id_distintivo.setter
   def id_distintivo(self,
                     nuevo_id: int) -> None:
      self._id_distintivo[0] = nuevo_id 

   @property
   def ids_flechas(self) -> set[int]:
      return self._ids_flechas

   @property
   def coordenadas(self) -> tuple[int, int]:
      return self._coordenadas

   @property
   def variables_id(self) -> dict[str, list[int | None]]:
         return self._variables_id

   @property
   def ids_elementos_por_clave(self) -> dict[str, int]:
      """IDs de imágenes con clave individual, no de los elementos del índice 0.

      Cada clave es única dentro de esta casilla, independientemente de la capa.
      Casillero utiliza, por ejemplo, 'marca:seleccion' para una marca del tema.
      """
      return self._ids_elementos_por_clave

   @property
   def capas(self) -> dict[int, list[int | None] | set[int]]:
      return self._capas

   def aplicar_elemento(self,
                        elemento: tk.PhotoImage,
                        etiqueta_capa: str,
                        *,
                        clave_elemento: str | None = None,
                        etiquetas_adicionales: tuple[str, ...] = ()) -> tuple[int, int | None]:
      """Dibuja una imagen y registra su ID sin interpretar su finalidad.

      Sin clave_elemento, reemplaza el elemento del índice 0 de esa capa.
      Con clave_elemento, reemplaza sólo esa clave y conserva las demás,
      incluso si comparten capa. Las etiquetas adicionales las decide quien llama.
      """
      ids_capa = self.variables_id[etiqueta_capa]
      x, y = self.contenedor.coords(self.id_imagen)

      anclaje = self.contenedor.itemcget(self.id_imagen,
                                         "anchor")

      if clave_elemento is None:
         id_elemento_anterior = ids_capa[0]
         if id_elemento_anterior is not None:
            self.contenedor.delete(id_elemento_anterior)
            ids_capa[0] = None
      else:
         id_elemento_anterior = self.ids_elementos_por_clave.get(clave_elemento)

         self.borrar_elemento(self.ids_elementos_por_clave.get(clave_elemento))

      id_elemento_nuevo = self.contenedor.create_image(
         x, y,
         image = elemento,
         anchor = anclaje,
         tags = (etiqueta_capa, *etiquetas_adicionales)
      )

      if clave_elemento is None:
         ids_capa[0] = id_elemento_nuevo
      else:
         self.ids_elementos_por_clave[clave_elemento] = id_elemento_nuevo
         # Se modifica la lista compartida con capas, sin sustituirla.
         ids_capa.append(id_elemento_nuevo)

      return (id_elemento_nuevo, id_elemento_anterior)

   def borrar_elemento(self,
                       id: int | None) -> None:
      if id is None:
         return
      for elementos in self.variables_id.values():
         if id in elementos:
            indice = elementos.index(id)
            if indice == 0:
               elementos[0] = None
            else:
               elementos.pop(indice)
            break

      for clave_elemento, id_elemento in tuple(self.ids_elementos_por_clave.items()):
         if id_elemento == id:
            del self.ids_elementos_por_clave[clave_elemento]
            break

      self.contenedor.delete(id)

   def resaltada(self) -> bool:
      return any(id is not None for id in self.variables_id["resaltado"])
   
class Casillero:
   def __init__(self,
                master: tk.Misc,
                tema: TemaGrafico,
                *,
                tamanno_casilla: int = 60,
                distribucion: dict[tuple[int, int], 
                                   tuple[str, Color, str]] |
                                   None
                                   = None):
      self._tamanno_casilla = tamanno_casilla
      self._tema = tema
      self._contenedor = tk.Frame(master)
      self.contenedor.pack()
      self._canvas = tk.Canvas(self.contenedor,
                               width = self.tamanno_casilla*8,
                               height = self.tamanno_casilla*8)
      self.canvas.pack()
      self._casillas = self._crear_casillas()
      self._anotaciones_estrategicas = []
      if distribucion is None:
         self._inicializar_tablero()
      elif distribucion:
         self.mostrar_posicion(distribucion)
      else:
         pass

   @property
   def tamanno_casilla(self) -> int:
      return self._tamanno_casilla

   @property
   def tema(self) -> TemaGrafico:
      return self._tema

   @property
   def contenedor(self) -> tk.Frame:
      return self._contenedor

   @property
   def canvas(self) -> tk.Canvas:
      return self._canvas

   @property
   def casillas(self) -> dict[tuple[int, int],
                              CasillaVisual]:
      return self._casillas

   @property
   def anotaciones_estrategicas(self) -> list[int]:
      return self._anotaciones_estrategicas

   def _crear_casillas(self) -> dict[tuple[int, int],
                                     CasillaVisual]:
      x = 0
      y = 0
      casillas = {}
      for i in range(7, -1, -1):
         x = 0

         for j in range(8):
            if (i + j) % 2 == 0:
               color = "oscura"

            else:
               color = "clara"

            casilla = CasillaVisual(self.canvas,
                                    self.canvas.create_image(x, y,
                                                             image = self.tema.casillas[color],
                                                             anchor = "nw",
                                                             tags = f"casilla_{color}"),
                                    None,
                                    (i, j))
            
            casillas |= {(i, j): casilla}
            x += self.tamanno_casilla

         y += self.tamanno_casilla

      return casillas

   def obtener_casilla(self,
                       id: int) -> CasillaVisual | None:
      for casilla in self.casillas.values():
         if any(id in ids for ids in casilla.variables_id.values()):
            return casilla

      return

   def mostrar_posicion(self,
                        distribucion: dict[tuple[int, int],
                                           tuple[str, Color, str]]) -> None:
      self.limpiar_casillero()

      for clave, valor in distribucion.items():
         self.casillas[clave].aplicar_elemento(self.tema.piezas[valor],
                                               "pieza")

      self._ordenar_capas()


   def limpiar_casillero(self) -> None:
      for casilla in self.casillas:
         for clave in self.casillas[casilla].variables_id:
            if clave == "imagen":
               continue

            for id in tuple(self.casillas[casilla].variables_id[clave]):
               self.borrar_elemento(casilla, id)

      self._borrar_todas_las_flechas()

   def aplicar_marca(self,
                     coordenadas: tuple[int, int],
                     clave: str) -> None:
      imagen_marca = self.tema.marcas[clave]

      estilo_marca = self.tema.estilos_marcas[clave]

      clave_elemento = f"marca:{clave}"

      casilla = self.casillas[coordenadas]

      if estilo_marca.uso == "seleccion":
         self.borrar_seleccion()

      ids = casilla.aplicar_elemento(
         imagen_marca,
         etiqueta_capa = estilo_marca.capa,
         clave_elemento = clave_elemento,
         etiquetas_adicionales = (clave_elemento, f"uso:{estilo_marca.uso}")
      )

      if estilo_marca.uso == "estrategia":
         self.anotaciones_estrategicas.append(ids[0])

         if ids[1]:
            self.anotaciones_estrategicas.remove(ids[1])

      self._ordenar_capas()

   def borrar_marca(self,
                    coordenadas: tuple[int, int],
                    clave: str) -> None:
      """Borra una marca concreta sin tocar las demás de la casilla."""
      casilla = self.casillas[coordenadas]

      self.borrar_elemento(coordenadas,
                           casilla.ids_elementos_por_clave.get(f"marca:{clave}"))

   def aplicar_seleccion(self, coordenadas: tuple[int, int]) -> None:
      """Muestra un único origen; InterfazPartida conserva la selección lógica."""
      self.aplicar_marca(coordenadas, "seleccion")

   def borrar_seleccion(self) -> None:
      """Retira sólo el dibujo de selección, sin borrar anotaciones ni piezas."""
      self.limpiar_marcas(uso = "seleccion")

   def limpiar_marcas(self, *, uso: UsoMarca | None = None) -> None:
      """Sin uso borra todas las marcas; con uso, sólo esa finalidad."""
      for casilla in self.casillas.values():
         for clave_elemento, id_elemento in tuple(casilla.ids_elementos_por_clave.items()):
            if not clave_elemento.startswith("marca:"):
               continue
            if uso is None or f"uso:{uso}" in self.canvas.gettags(id_elemento):
               self.borrar_elemento(casilla.coordenadas,
                                    id_elemento)
               
         # Las imágenes genéricas anteriores no tienen clave ni uso del tema:
         # se consideran anotaciones, como antes de esta separación.
         if uso is None or uso == "estrategia":
            for capa in ("resaltado", "marca"):
               self.borrar_elemento(casilla.coordenadas,
                                    casilla.variables_id[capa][0])

   def promocion(self,
                 coordenadas: tuple[int, int],
                 clave: tuple[str, Color, str]) -> None:
      self.casillas[coordenadas].aplicar_elemento(self.tema.piezas[clave],
                                                  "pieza")

      self._ordenar_capas()

   def aplicar_proyeccion(self,
                          coordenadas: tuple[int, int],
                          clave: tuple[str, Color]) -> None:
      ids = self.casillas[coordenadas].aplicar_elemento(self.tema.proyecciones[clave],
                                                        "proyeccion")
      if ids[1]:
         self.anotaciones_estrategicas.remove(ids[1])
      
      self.anotaciones_estrategicas.append(ids[0])

      self._ordenar_capas()

   def aplicar_distintivo(self,
                          coordenadas: tuple[int, int],
                          clave: str) -> None:
      ids = self.casillas[coordenadas].aplicar_elemento(self.tema.distintivos[clave],
                                                        "distintivo")

      if ids[1]:
         self.anotaciones_estrategicas.remove(ids[1])

      self.anotaciones_estrategicas.append(ids[0])

      self._ordenar_capas()

   def aplicar_marcador_de_secuencia(self,
                                     coordenadas: tuple[int, int],
                                     clave: int) -> None:
      ids = self.casillas[coordenadas].aplicar_elemento(self.tema.secuencias[clave],
                                                        "secuencia")
      if ids[1]:
         self.anotaciones_estrategicas.remove(ids[1])

      self.anotaciones_estrategicas.append(ids[0])

      self._ordenar_capas()

   #Precondición: La casilla de origen y de destino son diferentes
   def aplicar_flecha(self,
                      origen: tuple[int, int],
                      destino: tuple[int, int],
                      clave: str) -> None:
      centro_origen = self._obtener_centro_casilla(*origen)

      centro_destino = self._obtener_centro_casilla(*destino)

      relleno = self.tema.colores[clave]
      geometria_flecha = self.tema.geometria["flecha"]
      grosor = cast(float, geometria_flecha["width"])
      punta = cast(list[float], geometria_flecha["arrowshape"])

      if self._es_movimiento_de_caballo(origen,
                                        destino):
         desplazamientos = (abs(destino[0] - origen[0]),
                            abs(destino[1] - origen[1]))
         
         if desplazamientos[0] > desplazamientos[1]:
            punto_intermedio = self._obtener_centro_casilla(destino[0], origen[1])
         else:
            punto_intermedio = self._obtener_centro_casilla(origen[0], destino[1])

         id_flecha  = self.canvas.create_line(centro_origen[0], centro_origen[1],
                                              punto_intermedio[0], punto_intermedio[1],
                                              centro_destino[0], centro_destino[1],
                                              arrow = "last",
                                              width = grosor,
                                              arrowshape = punta,
                                              fill = relleno,
                                              tag = "flecha")
         
      else:
         id_flecha = self.canvas.create_line(centro_origen[0], centro_origen[1],
                                             centro_destino[0], centro_destino[1],
                                             arrow = "last",
                                             width = grosor,
                                             arrowshape = punta,
                                             fill = relleno,
                                             tag = "flecha")

      self._aplicar_flecha_a_casillas(origen,
                                      destino,
                                      id_flecha)

      self.anotaciones_estrategicas.append(id_flecha)

      self.canvas.addtag_withtag(f"color_original:{relleno}", id_flecha)

      self._ordenar_capas()

   def alternar_resaltado_flecha(self,
                                 id_flecha: int) -> None:
      """Alterna los colores estratégicos del tema sin sustituir el dibujo.

      La etiqueta flecha_seleccionada indica el estado visual. No se cambian
      las coordenadas, las capas ni el registro de anotaciones. Los IDs que
      no correspondan a una flecha existente se ignoran.
      """
      etiquetas = self.canvas.gettags(id_flecha)
      if "flecha" not in etiquetas or self.canvas.type(id_flecha) != "line":
         return

      if "flecha_seleccionada" in etiquetas:
         color_original = next((etiqueta.split(":", 1)[1] for etiqueta in etiquetas
                                if etiqueta.startswith("color_original:")),
                               self.tema.colores["flecha_estrategica"])
         self.canvas.itemconfigure(id_flecha,
                                    fill = color_original)
         
         self.canvas.dtag(id_flecha, "flecha_seleccionada")
      else:
         color = self.canvas.itemcget(id_flecha, "fill")
         if not any(etiqueta.startswith("color_original:") for etiqueta in etiquetas):
            self.canvas.addtag_withtag(f"color_original:{color}", id_flecha)
         seleccionado = self.tema.colores["flecha_estrategica_seleccionada"]
         if color != self.tema.colores["flecha_estrategica"]:
            componentes = self.canvas.winfo_rgb(color)
            seleccionado = "#" + "".join(f"{round(c / 257 * .70 + 255 * .30):02x}" for c in componentes)
         self.canvas.itemconfigure(id_flecha,
                                    fill = seleccionado)
         
         self.canvas.addtag_withtag("flecha_seleccionada", id_flecha)

   def borrar_elemento(self,
                       casilla: tuple[int, int],
                       id: int | None) -> None:
      self.casillas[casilla].borrar_elemento(id)

      if id in self.anotaciones_estrategicas:
         self.anotaciones_estrategicas.remove(id)

   def limpiar_anotaciones_temporales(self) -> None:
      """Borra el análisis entre movimientos, conservando selección e indicadores.

      El nivel superior decide si cancela o conserva la preselección y cuándo
      recalcula los indicadores del juego según el nuevo estado del modelo.
      """
      self.limpiar_marcas(uso = "estrategia")

      for casilla in self.casillas:
         for clave in self.casillas[casilla].variables_id:
            if (
               clave == "proyeccion" or
               clave == "distintivo" or
               clave == "secuencia"
            ):
               for id_elemento_temporal in tuple(self.casillas[casilla].variables_id[clave]):
                  self.borrar_elemento(casilla, id_elemento_temporal)

      self._borrar_todas_las_flechas()

   def captura_ordinaria(self,
                         id: int,
                         origen: tuple[int, int],
                         destino: tuple[int, int]) -> None:
      pieza_capturada = self.casillas[destino].id_pieza

      self.desplazar_pieza(id,
                           origen,
                           destino)
      
      self.canvas.delete(pieza_capturada)

   def enroque(self,
               origen_torre: tuple[int, int]) -> None:
      match origen_torre:
         case (0, 0):
            destino_torre = (0, 3)
            origen_rey = (0, 4)
            destino_rey = (0, 2)
         case (0, 7):
            destino_torre = (0, 5)
            origen_rey = (0, 4)
            destino_rey = (0, 6)
         case (7, 0):
            destino_torre = (7, 3)
            origen_rey = (7, 4)
            destino_rey = (7, 2)
         case (7, 7):
            destino_torre = (7, 5)
            origen_rey = (7, 4)
            destino_rey = (7, 6)

      id_torre = self.casillas[origen_torre].id_pieza
      id_rey = self.casillas[origen_rey].id_pieza

      self.desplazar_pieza(id_torre,
                           origen_torre,
                           destino_torre)

      self.desplazar_pieza(id_rey,
                           origen_rey,
                           destino_rey)

   def captura_al_paso(self,
                       id: int,
                       origen: tuple[int, int],
                       destino: tuple[int, int],
                       posicion_pieza_capturada: tuple[int, int]) -> None:
      self.desplazar_pieza(id,
                           origen,
                           destino)

      pieza_capturada = self.casillas[posicion_pieza_capturada].id_pieza

      self.casillas[posicion_pieza_capturada].id_pieza = None

      self.canvas.delete(pieza_capturada)

   def desplazar_pieza(self,
                       id: int,
                       origen: tuple[int, int],
                       destino: tuple[int, int]) -> None:
      self.casillas[origen].id_pieza = None

      self.colocar_pieza(id,
                         destino)

   def colocar_pieza(self,
                     id: int,
                     destino: tuple[int, int]) -> None:
      self.casillas[destino].id_pieza = id

      x, y = self._obtener_centro_casilla(*destino)
      mitad = self.tamanno_casilla / 2

      self.canvas.coords(id,
                         x - mitad,
                         y - mitad)

   def obtener_coordenadas_logicas(self,
                                   centro: tuple[float, float]) -> tuple[int, int] | None:
      if not all(0 <= componente < 8 * self.tamanno_casilla for componente in centro):
         return None
      return (int(7 -centro[1] // self.tamanno_casilla),
               int(centro[0] // self.tamanno_casilla))
   
   

   def _inicializar_tablero(self) -> None:
      self._colocar_primera_fila(Color.Blanco)

      self._colocar_primera_fila(Color.Negro)

      self._colocar_peones(Color.Blanco)

      self._colocar_peones(Color.Negro)

   def _colocar_primera_fila(self,
                             color: Color) -> None:
      if color == Color.Blanco:
         f = 0

      else:
         f = 7

      for c in range(8):
         if c == 0 or c == 7:
            self.casillas[(f, c)].aplicar_elemento(self.tema.piezas["torre",
                                                                    color,
                                                                    "normal"],
                                                   "pieza")
         if c == 1 or c == 6:
            self.casillas[(f, c)].aplicar_elemento(self.tema.piezas["caballo",
                                                                    color,
                                                                    "normal"],
                                                   "pieza")

         if c == 2 or c == 5:
            self.casillas[(f, c)].aplicar_elemento(self.tema.piezas["alfil",
                                                                    color,
                                                                    "normal"],
                                                   "pieza")

         if c == 3:
            self.casillas[(f, c)].aplicar_elemento(self.tema.piezas["dama",
                                                                    color,
                                                                    "normal"],
                                                   "pieza")

         if c == 4:
            self.casillas[(f, c)].aplicar_elemento(self.tema.piezas["rey",
                                                                    color,
                                                                    "normal"],
                                                   "pieza")
   def _colocar_peones(self,
                       color: Color) -> None:
      if color == Color.Blanco:
         f = 1

      else:
         f = 6

      for c in range(8):
         self.casillas[(f, c)].aplicar_elemento(self.tema.piezas["peon",
                                                                 color,
                                                                 "normal"],
                                                "pieza")

   def borrar_flecha(self,
                      id: int) -> None:
      for casilla in self.casillas:
         if id in self.casillas[casilla].ids_flechas:
            self.casillas[casilla].ids_flechas.discard(id)

      self.canvas.delete(id)

      if id in self.anotaciones_estrategicas:
         self.anotaciones_estrategicas.remove(id)

   def _borrar_todas_las_flechas(self) -> None:
      set_flechas = set()

      for casilla in self.casillas:
         set_flechas.update(self.casillas[casilla].ids_flechas)

         self.casillas[casilla].ids_flechas.clear()

      for flecha in set_flechas:
         self.anotaciones_estrategicas.remove(flecha)

         self.canvas.delete(flecha)

   def _obtener_centro_casilla(self,
                               fila: int,
                               columna: int) -> tuple[float, float]:
      return (self.tamanno_casilla * (columna + 1/2),
              self.tamanno_casilla * ((7 - fila) + 1/2))

   def _aplicar_flecha_a_casillas(self,
                                 origen: tuple[int, int],
                                 destino: tuple[int, int],
                                 id: int) -> None:
      self._asignar_flecha_a_casilla((origen[0], origen[1]),
                                       id)

      self._asignar_flecha_a_casilla((destino[0], destino[1]),
                                       id)
      
      if self._es_movimiento_de_caballo(origen,
                                          destino):
         if abs(destino[0] - origen[0]) > abs(destino[1] - origen[1]):
            if destino[0] - origen[0] > 0:
               self._asignar_flecha_a_casilla((origen[0] + 1, origen[1]),
                                                id)

               self._asignar_flecha_a_casilla((origen[0] + 2, origen[1]),
                                                id)

            else:
               self._asignar_flecha_a_casilla((origen[0] - 1, origen[1]),
                                                id)

               self._asignar_flecha_a_casilla((origen[0] - 2, origen[1]),
                                                id)
               
         else:
            if destino[1] - origen[1] > 0:
               self._asignar_flecha_a_casilla((origen[0], origen[1] + 1),
                                                id)

               self._asignar_flecha_a_casilla((origen[0], origen[1] + 2),
                                                id)

            else:
               self._asignar_flecha_a_casilla((origen[0], origen[1] - 1),
                                                id)

               self._asignar_flecha_a_casilla((origen[0], origen[1] - 2),
                                                id)
               
      else:
         coordenadas_atravesadas = self._casillas_atravesadas(origen,
                                                               destino,
                                                               id)

         for coordenadas in coordenadas_atravesadas:
            self._asignar_flecha_a_casilla(coordenadas,
                                             id)

   def _es_movimiento_de_caballo(self,
                                 origen: tuple[int, int],
                                 destino: tuple[int, int]) -> bool:
      desplazamiento_horizontal = abs(destino[0] - origen[0])

      desplazamiento_vertical = abs(destino[1] - origen[1])

      return (
         (
            desplazamiento_horizontal == 2
            ) and (
         desplazamiento_vertical == 1
         )
      ) or (
         (
            desplazamiento_horizontal == 1
         ) and (
            desplazamiento_vertical == 2
         )
      )  

   def _asignar_flecha_a_casilla(self,
                                 coordenadas: tuple[int, int],
                                 id: int) -> None:
      casilla = self.casillas[coordenadas]

      casilla.ids_flechas.add(id)

   def _casillas_atravesadas(self,
                             origen: tuple[int, int],
                             destino: tuple[int, int],
                             id_flecha: int) -> tuple[tuple[int, int], ...]:
      centro_origen = self._obtener_centro_casilla(*origen)

      centro_destino = self._obtener_centro_casilla(*destino)

      lista_casillas =[]

      elementos_atravesados = self.canvas.find_overlapping(*centro_origen,
                                                           *centro_destino)

      for elemento in elementos_atravesados:
         etiquetas = self.canvas.gettags(elemento)

         if ("casilla_clara" in etiquetas or
             "casilla_oscura" in etiquetas):
            x1, y1 = self.canvas.coords(elemento)

            x2 = x1 + self.tamanno_casilla

            y2 = y1 + self.tamanno_casilla

            contenido_casilla = self.canvas.find_overlapping(x1, y1,
                                                             x2, y2)
            if id_flecha in contenido_casilla:
               coordenadas_logicas = self.obtener_coordenadas_logicas((x1, y1))

               if coordenadas_logicas is not None:
                  lista_casillas.append(coordenadas_logicas)

      return tuple(lista_casillas)

   def _ordenar_capas(self) -> None:
      self.canvas.tag_raise("casilla_clara")
      self.canvas.tag_raise("casilla_oscura")
      self.canvas.tag_raise("resaltado")
      self.canvas.tag_raise("pieza")
      self.canvas.tag_raise("proyeccion")
      self.canvas.tag_raise("marca")
      self.canvas.tag_raise("flecha")
      self.canvas.tag_raise("distintivo")
      self.canvas.tag_raise("secuencia")
