"""Recursos y configuración de los temas gráficos."""

import tkinter as tk
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from ..piezas import Color

type Imagenes[Clave] = dict[Clave, tk.PhotoImage]

PerfilTipografico = dict[str, str | int | float | list[str]]

ParametrosGeometricos = dict[str, str | int | float | list[float]]

type UsoMarca = Literal["seleccion", "estrategia", "estado"]
type CapaMarca = Literal["resaltado", "marca"]


@dataclass(frozen = True)
class EstiloMarca:
   """Separa la capa visual de la finalidad usada para limpiar el dibujo."""

   capa: CapaMarca
   uso: UsoMarca


ESTILOS_MARCAS: dict[str, EstiloMarca] = {
   "seleccion": EstiloMarca("marca", "seleccion"),
   "foco": EstiloMarca("marca", "estrategia"),
   "atencion": EstiloMarca("marca", "estrategia"),
   "destino_legal": EstiloMarca("marca", "estado"),
   "captura_legal": EstiloMarca("marca", "estado"),
   "jaque": EstiloMarca("resaltado", "estado"),
   "atacante_jaque": EstiloMarca("marca", "estado"),
   "promocion_pendiente": EstiloMarca("resaltado", "estado"),
   "ultima_jugada_origen": EstiloMarca("resaltado", "estado"),
   "ultima_jugada_destino": EstiloMarca("resaltado", "estado"),
   **{f"circulo_{color}": EstiloMarca("marca", "estrategia")
      for color in ("rojo", "azul", "verde", "ambar")},
   **{f"fondo_{color}": EstiloMarca("resaltado", "estrategia")
      for color in ("rojo", "azul", "verde", "ambar")},
}


class TemaGrafico:
   def __init__(self,
                identificador: str,
                #Representa el tema (p. ej: "club.microfibra")

                dimension_casilla: int,
                casillas: Imagenes[str],
                piezas: Imagenes[tuple[str, Color, str]],
                #La tercera cadena indica si la silueta es normal o reforzada

                proyecciones: Imagenes[tuple[str, Color]],
                #La primera cadena indica la pieza

                marcas: Imagenes[str],
                flechas: Imagenes[tuple[str, str]],
                #La primera cadena indica si es continua o discontinua

                distintivos: Imagenes[str],
                secuencias: Imagenes[int],
                iconos: Imagenes[tuple[str, str]],
                #Símbolos de acciones y sus variantes cromáticas; por ejemplo, ("anotar", grafito) -> icono oscuro de anotación

                fondos: Imagenes[str],
                controles: Imagenes[str],
                glifos: Imagenes[tuple[str, str]],
                #La segunta cadena indica la variante cromática del carácter

                tipografia: dict[str, PerfilTipografico],
                #La cadena indica el contexto en que serán utilizados los tipos

                colores: dict[str, str],
                #La segunda cadena indica el código del color

                geometria: dict[str, ParametrosGeometricos],
                *,
                estilos_marcas: dict[str, EstiloMarca] | None = None):
      self._identificador = identificador
      self._dimension_casilla = dimension_casilla
      self._casillas = casillas
      self._piezas = piezas
      self._proyecciones = proyecciones
      self._marcas = dict(marcas)
      # Identidad propia para no borrar un círculo estratégico del usuario.
      # El tema puede proporcionar un recurso específico; si no, reutiliza uno.
      if "atacante_jaque" not in self._marcas:
         for recurso in ("circulo_ambar", "atencion", "jaque"):
            if recurso in self._marcas:
               self._marcas["atacante_jaque"] = self._marcas[recurso]
               break
      estilos = {**ESTILOS_MARCAS, **(estilos_marcas or {})}
      self._estilos_marcas = {
         clave: estilos.get(clave, EstiloMarca("marca", "estrategia"))
         for clave in self._marcas
      }
      self._flechas = flechas
      self._distintivos = distintivos
      self._secuencias = secuencias
      self._iconos = iconos
      self._fondos = fondos
      self._controles = controles
      self._glifos = glifos
      self._tipografia = tipografia
      # Colores predeterminados; los recibidos del tema tienen prioridad.
      self._colores = {
         "marfil": "#FAF7EE",
         "ambar": "#D49A28",
         "flecha_estrategica": "#2C455B",
         "flecha_estrategica_seleccionada": "#527FA7",
         **colores,
      }
      # Valores predeterminados en píxeles, proporcionados al tamaño de casilla.
      # Las opciones recibidas del tema tienen prioridad sobre estos valores.
      escala_flecha = dimension_casilla / 60
      geometria_flecha = {
         "width": 4.0 * escala_flecha,
         "arrowshape": [12.0 * escala_flecha,
                        16.0 * escala_flecha,
                        5.0 * escala_flecha],
         **geometria.get("flecha", {})
      }
      self._geometria = {**geometria, "flecha": geometria_flecha}

   @property
   def identificador(self) -> str:
      return self._identificador

   @property
   def dimension_casillas(self) -> int:
      return self._dimension_casilla

   @property
   def casillas(self) -> Imagenes[str]:
      return self._casillas

   @property
   def piezas(self) -> Imagenes[tuple[str, Color, str]]:
      return self._piezas

   @property
   def proyecciones(self) -> Imagenes[tuple[str, Color]]:
      return self._proyecciones

   @property
   def marcas(self) -> Imagenes[str]:
      return self._marcas

   @property
   def estilos_marcas(self) -> dict[str, EstiloMarca]:
      return self._estilos_marcas

   @property
   def flechas (self) -> Imagenes[tuple[str, str]]:
      return self._flechas

   @property
   def distintivos(self) -> Imagenes[str]:
      return self._distintivos

   @property
   def secuencias(self) -> Imagenes[int]:
      return self._secuencias

   @property
   def iconos(self) -> Imagenes[tuple[str, str]]:
      return self._iconos

   @property
   def fondos(self) -> Imagenes[str]:
      return self._fondos

   @property
   def controles(self) -> Imagenes[str]:
      return self._controles

   @property
   def glifos(self) -> Imagenes[tuple[str, str]]:
      return self._glifos

   @property
   def tipografia(self) -> dict[str, PerfilTipografico]:
      return self._tipografia

   @property
   def colores(self) -> dict[str, str]:
      return self._colores

   @property
   def geometria(self) -> dict[str, ParametrosGeometricos]:
      return self._geometria


# Recursos incluidos en el paquete; no dependen del directorio de ejecución.
# cargar_tema permite indicar otra carpeta explícitamente.
CARPETA_RECURSOS_PREDETERMINADA = (
   Path(__file__).resolve().parent.parent / "recursos" / "ajedrez-recursos-v1"
)


def cargar_tema(
   master: tk.Misc,
   *,
   identificador: str = "club.liso_mate",
   dimension_casilla: int = 60,
   carpeta_recursos: str | Path = CARPETA_RECURSOS_PREDETERMINADA,
   colores: dict[str, str] | None = None,
   tipografia: dict[str, PerfilTipografico] | None = None,
   geometria: dict[str, ParametrosGeometricos] | None = None,
   estilos_marcas: dict[str, EstiloMarca] | None = None,
) -> TemaGrafico:
   """Carga un tema completo, modificando sólo las opciones pasadas por nombre.

   Debe llamarse después de crear la ventana de Tkinter. ``master`` sólo se usa
   para crear sus PhotoImage; TemaGrafico conserva las referencias a las imágenes.
   No se crea ninguna ventana ni se cambia un Casillero ya existente.

   ``carpeta_recursos`` es la carpeta que contiene catalogo.json, no png/60.
   El catálogo actual admite 12 temas y tamaños de casilla de 60, 120 y 240 px.
   Las imágenes se cargan a su escala nativa, sin redimensionar ni recolorear PNG.

   Los colores se combinan por clave. La tipografía y la geometría se combinan
   también dentro de cada perfil: geometria={"flecha": {"width": 6}} conserva
   la punta predeterminada. width y arrowshape son píxeles del tamaño elegido;
   si se omiten, TemaGrafico calcula sus valores proporcionados a la casilla.
   Los campos terminados en _s del catálogo siguen siendo proporciones.

   Claves de imágenes: flechas (forma, color), iconos (acción, color), glifos
   (carácter, color) y fondos por nombre de paleta. Las piezas incluyen las
   variantes "normal" del acabado elegido y "reforzada" compartida.

   Ejemplos:
       cargar_tema(ventana)
       cargar_tema(ventana, identificador="taller.veta_fina")
       cargar_tema(ventana, dimension_casilla=120, colores={"ambar": "#CCA030"})
   """
   carpeta = Path(carpeta_recursos).expanduser().resolve()
   ruta_catalogo = carpeta / "catalogo.json"
   if not ruta_catalogo.is_file():
      raise FileNotFoundError(
         f"No se encuentra el catálogo: {ruta_catalogo}. "
         "Indica carpeta_recursos con la carpeta que contiene catalogo.json."
      )
   with ruta_catalogo.open(encoding="utf-8") as archivo:
      catalogo = json.load(archivo)

   if identificador not in catalogo["temas"]:
      disponibles = ", ".join(catalogo["temas"])
      raise ValueError(f"Tema desconocido: {identificador!r}. Disponibles: {disponibles}")
   if type(dimension_casilla) is not int or dimension_casilla not in catalogo["tamanos_casilla_px"]:
      raise ValueError(
         f"Tamaño de casilla no disponible: {dimension_casilla!r}. "
         f"Tamaños admitidos: {catalogo['tamanos_casilla_px']}"
      )

   definicion = catalogo["temas"][identificador]
   recursos = catalogo["recursos"]
   escala = str(dimension_casilla)
   imagenes_cargadas: dict[Path, tk.PhotoImage] = {}

   def cargar_imagen(id_recurso: str) -> tk.PhotoImage:
      try:
         ruta_relativa = recursos[id_recurso]["png"][escala]["archivo"]
      except KeyError as error:
         raise ValueError(
            f"El catálogo no incluye el recurso {id_recurso!r} a {escala} px."
         ) from error
      ruta_imagen = (carpeta / ruta_relativa).resolve()
      if not ruta_imagen.is_relative_to(carpeta):
         raise ValueError(f"El recurso {id_recurso!r} queda fuera de carpeta_recursos.")
      if not ruta_imagen.is_file():
         raise FileNotFoundError(f"Falta la imagen {id_recurso!r}: {ruta_imagen}")
      if ruta_imagen not in imagenes_cargadas:
         imagenes_cargadas[ruta_imagen] = tk.PhotoImage(master=master, file=str(ruta_imagen))
      return imagenes_cargadas[ruta_imagen]

   def cargar_grupo(tipo: str) -> Imagenes[str]:
      return {
         id_recurso.removeprefix(f"{tipo}."): cargar_imagen(id_recurso)
         for id_recurso, recurso in recursos.items()
         if recurso["tipo"] == tipo
      }

   casillas = {
      color: cargar_imagen(definicion[f"casilla_{color}"])
      for color in ("clara", "oscura")
   }
   piezas: Imagenes[tuple[str, Color, str]] = {}
   proyecciones: Imagenes[tuple[str, Color]] = {}
   for nombre in ("peon", "caballo", "alfil", "torre", "dama", "rey"):
      for bando, color in (("blanca", Color.Blanco), ("negra", Color.Negro)):
         piezas[nombre, color, "normal"] = cargar_imagen(
            f"{definicion['familia_piezas']}.{bando}.{nombre}"
         )
         piezas[nombre, color, "reforzada"] = cargar_imagen(
            f"pieza.reforzada.{bando}.{nombre}"
         )
         proyecciones[nombre, color] = cargar_imagen(
            f"{definicion['proyecciones']}.{bando}.{nombre}"
         )

   flechas = {}
   for clave, imagen in cargar_grupo("flecha").items():
      color, forma = clave.split(".")
      flechas[forma, color] = imagen
   iconos = {}
   for clave, imagen in cargar_grupo("icono").items():
      accion, color = clave.split(".")
      iconos[accion, color] = imagen
   glifos = {}
   for clave, imagen in cargar_grupo("glifo").items():
      color, caracter = clave.split(".")
      glifos[caracter, color] = imagen

   colores_tema = {
      **catalogo["colores"],
      **catalogo["paletas"][definicion["paleta"]],
      **(colores or {}),
   }
   # La entrada "nota" del catálogo es texto explicativo, no un perfil.
   tipografia_tema = {
      nombre: perfil for nombre, perfil in catalogo["tipografia"].items()
      if isinstance(perfil, dict)
   }
   for nombre, cambios in (tipografia or {}).items():
      tipografia_tema[nombre] = {**tipografia_tema.get(nombre, {}), **deepcopy(cambios)}
   geometria_tema = catalogo["geometria"]
   for nombre, cambios in (geometria or {}).items():
      geometria_tema[nombre] = {**geometria_tema.get(nombre, {}), **deepcopy(cambios)}

   return TemaGrafico(
      identificador=identificador,
      dimension_casilla=dimension_casilla,
      casillas=casillas,
      piezas=piezas,
      proyecciones=proyecciones,
      marcas=cargar_grupo("marca"),
      flechas=flechas,
      distintivos=cargar_grupo("distintivo"),
      secuencias={int(numero): imagen for numero, imagen in cargar_grupo("secuencia").items()},
      iconos=iconos,
      fondos={definicion["paleta"]: cargar_imagen(definicion["fondo"])},
      controles=cargar_grupo("control"),
      glifos=glifos,
      tipografia=tipografia_tema,
      colores=colores_tema,
      geometria=geometria_tema,
      estilos_marcas=estilos_marcas,
   )
