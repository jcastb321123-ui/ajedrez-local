"""Tablero independiente de análisis manual, anotación y edición de posiciones."""

import tkinter as tk
from tkinter import ttk, messagebox

from ..analisis_partida import AnalisisPartida
from ..editor_posicion import EditorPosicion
from ..partida import EstadoPosicion
from ..piezas import Color
from ..sesion import SesionAnalisis
from .graficos_tablero import Casillero
from .interfaz_partida import InterfazPartida


class PanelAnalisis(InterfazPartida):
    def __init__(self, 
                 master, 
                 estado,
                 tamanno_casilla, 
                 turno, 
                 tema, 
                 volver, 
                 opciones,
                 *, 
                 obtener_posicion_original):
        # Estado de la edición y referencias para restaurar el tablero.
        self.editor: EditorPosicion | None = None
        self._origen_edicion: tuple[int, int] | None = None
        self._casillero_antes_de_editar: Casillero | None = None
        self._flecha_antes_de_editar: int | None = None
        self._obtener_posicion_original = obtener_posicion_original

        # Contenedores propios del panel.
        contenedor = tk.Frame(master)
        self._herramientas = tk.Frame(contenedor)
        self._panel_editor = tk.Frame(contenedor)

        # Variables de control de las herramientas de anotación.
        self.herramienta = tk.StringVar(master = contenedor)
        self.marca = tk.StringVar(master = contenedor)
        self.proyeccion = tk.StringVar(master = contenedor)
        self.distintivo = tk.StringVar(master = contenedor)
        self.secuencia = tk.StringVar(master = contenedor)
        self.color_flecha = tk.StringVar(master = contenedor)
        self._proyecciones = {
            f"{nombre} {color.name}": (nombre, color)
            for nombre, color in tema.proyecciones
        }

        # Variables de control del editor de posiciones.
        self.accion_edicion = tk.StringVar(master = contenedor)
        self.pieza_edicion = tk.StringVar(master = contenedor)
        self.color_edicion = tk.StringVar(master = contenedor)
        self.turno_edicion = tk.StringVar(master = contenedor)
        self.enroques_edicion: dict[tuple[Color, int], tk.BooleanVar] = {}
        self.al_paso_edicion = tk.StringVar(master = contenedor)
        self.mensaje = tk.StringVar(master = contenedor)

        # Cabecera, interfaz común y construcción de los controles.
        cabecera = tk.Frame(contenedor)
        cabecera.pack(fill = "x")
        tk.Button(cabecera, text = "⇄ Partida original", 
                  command = volver).pack(side = "left")
        tk.Button(cabecera, text = "Copiar posición del tablero principal",
                  command = self.copiar_posicion_original).pack(side = "right")
        tk.Label(cabecera, 
                 text = "Análisis independiente · ambos colores").pack(side = "left", 
                                                                               padx = 8)
        sesion = SesionAnalisis(estado, 
                                turno)
        casillero = Casillero(contenedor, 
                              tema, 
                              tamanno_casilla = tamanno_casilla,
                              distribucion = {})
        super().__init__(sesion, 
                         casillero, 
                         contenedor = contenedor,
                         opciones_visuales = opciones, 
                         solo_analisis = True)
        self.mostrar_estado(sesion.estado_actual)
        self._crear_herramientas()
        self._crear_editor()

    def copiar_posicion_original(self):
        if self.promocion_pendiente or self.editor is not None:
            return
        if not messagebox.askyesno("Nuevo análisis", "¿Sustituir este análisis y sus notas por la posición mostrada en el tablero principal?",
                                  parent = self.contenedor):
            return
        
        estado, turno = self._obtener_posicion_original()

        self._sesion = SesionAnalisis(estado, 
                                      turno)
        
        self._analisis = AnalisisPartida(self.sesion.partida)

        self.mostrar_estado(self.sesion.estado_actual)
        
        self.mensaje.set("Nuevo análisis desde la posición del tablero principal.")

    def _selector(self, 
                  fila, 
                  etiqueta, 
                  valores, 
                  variable: tk.StringVar) -> None:
        tk.Label(fila, 
                 text = etiqueta).pack(side = "left")
        
        variable.set(valores[0] 
                     if valores 
                     else "")
        
        ttk.Combobox(fila, 
                     textvariable = variable, 
                     values = valores, 
                     state = "readonly",
                     width = 17).pack(side = "left", 
                                      padx=(0, 8))

    def _crear_herramientas(self):
        tema = self.casillero.tema

        herramientas = self._herramientas

        herramientas.pack(fill="x", 
                          pady=5)

        fila = tk.Frame(herramientas)

        fila.pack(fill = "x")

        self._selector(fila, "Clic izquierdo:",
            ("Jugar", "Marca", "Proyección", "Distintivo", "Secuencia", "Borrar anotación"),
            self.herramienta)
        
        tk.Button(fila, 
                  text = "Deshacer anotación", 
                  command = lambda: self._borrar_ultima_anotacion(None)).pack(side="left")
        
        tk.Button(fila, 
                  text = "Limpiar notas", 
                  command = self.limpiar_anotaciones).pack(side = "left")
        
        fila = tk.Frame(herramientas)

        fila.pack(fill = "x")

        marcas = tuple(clave for clave, estilo in tema.estilos_marcas.items() 
                       if estilo.uso == "estrategia")

        self._selector(fila, 
                       "Marca:", 
                       marcas, 
                       self.marca)
        
        self._selector(fila, 
                       "Silueta:", 
                       tuple(self._proyecciones), 
                       self.proyeccion)
        
        fila = tk.Frame(herramientas)

        fila.pack(fill = "x")

        self._selector(fila, 
                       "Distintivo:", 
                       tuple(tema.distintivos), 
                       self.distintivo)
        
        self._selector(fila, 
                       "Secuencia:", 
                       tuple(str(n) for n in tema.secuencias), self.secuencia)
        
        fila = tk.Frame(herramientas)

        fila.pack(fill = "x")

        colores = tuple(c for c in ("flecha_estrategica", 
                                    "rojo", 
                                    "verde", 
                                    "ambar") 
                        if c in tema.colores)
        
        self._selector(fila, "Flecha:", 
                       colores, 
                       self.color_flecha)
        
        tk.Button(fila, 
                  text = "Editar posición", 
                  command = self.iniciar_edicion).pack(side = "left")
        
        tk.Label(herramientas, 
                 text = "Botón derecho: arrastrar = flecha; pulsar = marca. Supr: borrar flecha seleccionada.",
                 anchor = "w").pack(fill = "x")
        
        tk.Label(self.contenedor, 
                 textvariable = self.mensaje,
                 anchor = "w", 
                 wraplength = 520).pack(fill = "x")

    def _crear_editor(self):
        fila = tk.Frame(self._panel_editor)

        fila.pack(fill = "x")

        self._selector(fila, 
                       "Acción:", 
                       ("Colocar", "Quitar", "Mover"), 
                       self.accion_edicion)
        
        self._selector(fila, 
                       "Pieza:", 
                       ("peon", "caballo", "alfil", "torre", "dama", "rey"),
                       self.pieza_edicion)
        
        fila = tk.Frame(self._panel_editor)

        fila.pack(fill = "x")

        self._selector(fila, 
                       "Color:", ("Blanco", "Negro"), 
                       self.color_edicion)
        
        self._selector(fila, 
                       "Turno:", 
                       ("Blanco", "Negro"), 
                       self.turno_edicion)
        
        fila = tk.Frame(self._panel_editor)

        fila.pack(fill = "x")

        tk.Label(fila, 
                 text = "Derechos de enroque:").pack(side="left")
        
        for color in Color:
            for columna, nombre in ((7, "corto"), (0, "largo")):
                valor = tk.BooleanVar(master = self.contenedor)

                self.enroques_edicion[color, columna] = valor

                tk.Checkbutton(fila, 
                               text = f"{color.name} {nombre}", 
                               variable = valor).pack(side = "left")
                
        fila = tk.Frame(self._panel_editor)

        fila.pack(fill = "x")

        tk.Label(fila, 
                 text = "Peón capturable al paso (casilla, p. ej. d5; vacío = ninguno):").pack(side="left")
        
        tk.Entry(fila, 
                 textvariable = self.al_paso_edicion, 
                 width = 4).pack(side="left")
        
        fila = tk.Frame(self._panel_editor)

        fila.pack(fill = "x")

        for texto, comando in (("Deshacer edición", self.deshacer_edicion),
                               ("Vaciar", self.vaciar_borrador),
                               ("Aplicar como nuevo análisis", self.aplicar_edicion),
                               ("Cancelar", self.cancelar_edicion)):
            tk.Button(fila, 
                      text = texto, 
                      command = comando).pack(side = "left")

    def gestionar_clic_izquierdo(self, 
                                 evento):
        if self.promocion_pendiente:
            return
        
        self.casillero.canvas.focus_set()

        posicion = self.casillero.obtener_coordenadas_logicas((evento.x, 
                                                               evento.y))
        
        if posicion is None:
            return
        
        if self.editor is not None:
            self._editar_casilla(posicion)

            return
        herramienta = self.herramienta.get()

        if herramienta == "Jugar":
            return super().gestionar_clic_izquierdo(evento)
        
        self._cancelar_seleccion()

        if herramienta == "Marca":
            self._alternar_resaltado_estrategico(posicion)
        elif herramienta == "Proyección" and self.proyeccion.get():
            self.casillero.aplicar_proyeccion(posicion, self._proyecciones[self.proyeccion.get()])
        elif herramienta == "Distintivo" and self.distintivo.get():
            self.casillero.aplicar_distintivo(posicion, self.distintivo.get())
        elif herramienta == "Secuencia" and self.secuencia.get():
            self.casillero.aplicar_marcador_de_secuencia(posicion, int(self.secuencia.get()))
        elif herramienta == "Borrar anotación":
            actuales = self.casillero.canvas.find_withtag("current")

            if actuales and actuales[0] in self.casillero.anotaciones_estrategicas:
                identificador = actuales[0]

                if "flecha" in self.casillero.canvas.gettags(identificador):
                    self.casillero.borrar_flecha(identificador)

                    if identificador == self.flecha_seleccionada:
                        self._flecha_seleccionada = None
                else:
                    self.casillero.borrar_elemento(posicion, 
                                                   identificador)

    def _alternar_resaltado_estrategico(self, 
                                        posicion):
        clave = self.marca.get()
        if not clave:
            return
        if f"marca:{clave}" in self.casillero.casillas[posicion].ids_elementos_por_clave:
            self.casillero.borrar_marca(posicion, 
                                        clave)
        else:
            self.casillero.aplicar_marca(posicion, 
                                         clave)

    def _dibujar_flecha(self, 
                        origen, 
                        destino):
        self.casillero.aplicar_flecha(origen, 
                                      destino, 
                                      self.color_flecha.get())

    def _establecer_origen_anotacion(self, evento):
        if self.editor is None:
            super()._establecer_origen_anotacion(evento)

    def _definir_anotacion(self, evento):
        if self.editor is None:
            super()._definir_anotacion(evento)

    def limpiar_anotaciones(self):
        if not self.promocion_pendiente and self.editor is None:
            self.casillero.limpiar_anotaciones_temporales()

            self._flecha_seleccionada = None

    def retroceder_movimiento(self):
        if self.editor is None:
            super().retroceder_movimiento()

    def avanzar_movimiento(self):
        if self.editor is None:
            super().avanzar_movimiento()

    def volver_al_estado_actual(self):
        if self.editor is None and not self.promocion_pendiente:
            self.mostrar_estado(self.sesion_movimientos.estado_actual)

    def iniciar_edicion(self):
        if self.promocion_pendiente or self.editor is not None:
            return
        
        self._cancelar_seleccion()

        self._origen_anotacion = None

        self._origen_edicion = None

        self._cancelar_parpadeo_jaque()

        self.editor = EditorPosicion(self.estado_mostrado, 
                                     self._analisis.obtener_turno(self.estado_mostrado))

        # El borrador tiene su propio Canvas: cancelar conserva incluso IDs y notas.
        self._casillero_antes_de_editar = self.casillero

        self._flecha_antes_de_editar = self.flecha_seleccionada

        self.casillero.contenedor.pack_forget()

        self._casillero = Casillero(self.contenedor,
                                    self.casillero.tema,
                                    distribucion = self._obtener_distribucion(self.estado_mostrado),
                                    tamanno_casilla = self.casillero.tamanno_casilla)
        
        self.casillero.contenedor.pack(before = self.panel_navegacion)

        self.casillero.canvas.bind("<Button-1>", 
                                   self.gestionar_clic_izquierdo)
        
        self._herramientas.pack_forget()

        self._panel_editor.pack(fill = "x", 
                                pady = 5)
        
        self._actualizar_campos_editor()

        self.mensaje.set("Borrador: no modifica ninguna partida. Aplicar inicia un análisis nuevo y limpia las notas.")

    def _actualizar_campos_editor(self):
        self.turno_edicion.set(self.editor.turno.name)

        derechos = self.editor.derechos_enroque()

        for clave, variable in self.enroques_edicion.items():
            variable.set(clave in derechos)

        posicion = self.editor.tablero.posicion_de_captura_al_paso

        self.al_paso_edicion.set("" if posicion is None else f"{chr(97 + posicion[1])}{posicion[0] + 1}")

    def _editar_casilla(self, 
                        posicion):
        self.editor.turno = Color[self.turno_edicion.get()]

        accion = self.accion_edicion.get()

        if accion == "Colocar":
            self.editor.colocar(posicion, self.pieza_edicion.get(), Color[self.color_edicion.get()])
        elif accion == "Quitar":
            self.editor.quitar(posicion)
        elif self._origen_edicion is None:
            if self.editor.tablero.pieza_en(posicion):
                self._origen_edicion = posicion

                self.casillero.aplicar_marca(posicion, 
                                             "seleccion")
            return
        else:
            self.editor.mover(self._origen_edicion, 
                              posicion)

            self._origen_edicion = None

        self._mostrar_borrador()

    def _mostrar_borrador(self):
        estado = EstadoPosicion(tablero=self.editor.tablero)

        self.casillero.mostrar_posicion(self._obtener_distribucion(estado))

        self._flecha_seleccionada = None

        self._actualizar_campos_editor()

    def deshacer_edicion(self):
        if self.editor is not None:
            self.editor.deshacer()

            self._origen_edicion = None

            self._mostrar_borrador()

    def vaciar_borrador(self):
        if self.editor is not None:
            self.editor.vaciar()

            self._origen_edicion = None

            self._mostrar_borrador()

    def aplicar_edicion(self):
        if self.editor is None:
            return
        try:
            casilla = self.al_paso_edicion.get().strip().lower()

            if casilla and (
                len(casilla) != 2 or 
                casilla[0] not in "abcdefgh" or 
                casilla[1] not in "12345678"
            ):
                raise ValueError("La casilla del peón al paso debe ser, por ejemplo, d5.")
            
            posicion = (int(casilla[1]) - 1, ord(casilla[0]) - 97) if casilla else None

            turno = Color[self.turno_edicion.get()]

            estado = self.editor.construir_estado(turno = turno, 
                                                  enroques = {k for k, v in self.enroques_edicion.items() 
                                                              if v.get()},
                                                  peon_al_paso = posicion)
            
        except ValueError as error:
            self.mensaje.set(str(error))
            
            return
        
        self._sesion = SesionAnalisis(estado, 
                                      turno)
        
        self._analisis = AnalisisPartida(self.sesion.partida)

        self._cerrar_editor()

        self.mostrar_estado(self.sesion.estado_actual)

        self.mensaje.set("Posición aplicada al análisis independiente. La partida original no ha cambiado.")

    def cancelar_edicion(self):
        if self.editor is not None:
            self._cerrar_editor()

            self.actualizar_resaltado_jaque()
            
            self.mensaje.set("Edición cancelada.")

    def _cerrar_editor(self):
        borrador = self.casillero

        self._casillero = self._casillero_antes_de_editar

        self._flecha_seleccionada = self._flecha_antes_de_editar

        borrador.contenedor.destroy()

        self.casillero.contenedor.pack(before = self.panel_navegacion)

        self.editor = None

        self._origen_edicion = None

        self._panel_editor.pack_forget()

        self._herramientas.pack(fill = "x", 
                                pady = 5)
