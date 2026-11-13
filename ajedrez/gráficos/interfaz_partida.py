"""Coordina sesión, tablero, navegación histórica y análisis provisional.

Navegar sólo cambia el estado mostrado. El análisis valida sus jugadas en una
sesión independiente; la sesión recibida conserva el historial original.
El contenedor de tablero y navegación lo organiza el nivel superior.
"""

from __future__ import annotations
from ..sesion import Sesion, PiezaPromocion
from ..analisis_partida import AnalisisPartida
from .graficos_tablero import Casillero
from .temas_graficos import TemaGrafico
from .opciones_visuales import (
    OpcionesVisuales, ModoResaltadoJaque, OPCIONES_VISUALES_PREDETERMINADAS,
)
from ..partida import EstadoPosicion, EstadoPartida, CapturaAlPaso, MotivoRechazoMovimiento
from ..piezas import Color, PeonBlanco, PeonNegro, Caballo, Alfil, Torre, Reina, Rey
import tkinter as tk
from tkinter import messagebox
from typing import Callable

class InterfazPartida:
    def __init__(self,
                 sesion: Sesion,
                 casillero: Casillero,
                 *,
                 opciones_visuales: OpcionesVisuales = OPCIONES_VISUALES_PREDETERMINADAS,
                 contenedor: tk.Misc | None = None,
                 solo_analisis: bool = False):
        # Dependencias y contenedor de la interfaz.
        self._sesion = sesion
        self._casillero = casillero
        if not contenedor:
            self._contenedor = casillero.contenedor.master
        else:
            self._contenedor = contenedor

        # Sesión de análisis y posición mostrada.
        self._analisis = AnalisisPartida(sesion.partida)
        self._solo_analisis = solo_analisis
        self._analizando = solo_analisis
        if self.sesion.partida.ultima_jugada is None:
            self._estado_mostrado = self.sesion.partida.estado_inicial
        else:
            self._estado_mostrado = self.sesion.partida.ultima_jugada.estado_posicion

        # Selección y anotaciones sobre el tablero.
        self._origen_seleccionado: tuple[int, int] | None = None
        self._origen_anotacion: tuple[int, int] | None = None
        self._flecha_seleccionada: int | None = None

        # Preferencias visuales y temporizador del jaque.
        self._opciones_visuales = opciones_visuales
        self._id_parpadeo_jaque: str | None = None

        # Referencias a widgets; None indica que aún no se han creado.
        self._indicador_contexto: tk.Label | None = None
        self._indicador_estado_partida: tk.Label | None = None
        self._boton_modo_analisis: tk.Button | None = None
        self._panel_analisis = None
        self._disposicion_original = []
        self._botones_abandono: dict[Color, tk.Button] = {}
        self._botones_propuesta_tablas: dict[Color, tk.Button] = {}
        self._boton_reclamacion_tablas: tk.Button | None = None
        self._botones_promocion: dict[tuple[str, Color, str], tk.Button] = {}
        self._panel_navegacion = self._crear_panel_navegacion()

        # Conexión de eventos y representación inicial.
        canvas = self.casillero.canvas
        canvas.bind("<Button-1>", self.gestionar_clic_izquierdo)
        canvas.bind("<ButtonPress-3>", self._establecer_origen_anotacion)
        canvas.bind("<ButtonRelease-3>", self._definir_anotacion)
        canvas.bind("<Destroy>", self._al_destruir_canvas, add = "+")
        canvas.bind("<Control-z>", self._borrar_ultima_anotacion)
        canvas.bind("<Delete>", self._borrar_flecha_seleccionada)

        self.actualizar_resaltados_ultimo_movimiento()
        self.actualizar_resaltado_jaque()
        self._actualizar_indicador_contexto()

    @property
    def opciones_visuales(self) -> OpcionesVisuales:
        return self._opciones_visuales

    def aplicar_opciones_visuales(self, opciones: OpcionesVisuales) -> None:
        """Sustituye las preferencias y actualiza sólo los indicadores afectados.

        Para cambios parciales, el llamador puede utilizar dataclasses.replace
        sobre opciones_visuales. No se modifican el tema, la partida ni las notas.
        """
        self._opciones_visuales = opciones

        self.actualizar_resaltado_jaque()

        self._actualizar_indicador_contexto()

        if self._panel_analisis is not None:
            self._panel_analisis.aplicar_opciones_visuales(opciones)

    def aplicar_tema(self, tema: TemaGrafico) -> None:
        """Actualiza esta vista y su análisis sin reconstruir ningún estado."""
        anterior = self.casillero.tema
        self.casillero.aplicar_tema(tema)
        for clave, boton in self._botones_promocion.items():
            resaltado = boton.cget('background') == anterior.colores['ambar']
            boton.configure(image=tema.piezas[clave],
                            background=tema.colores['ambar' if resaltado else 'marfil'])
        if self._panel_analisis is not None:
            self._panel_analisis.aplicar_tema(tema)

    def restablecer_opciones_visuales(self) -> None:
        self.aplicar_opciones_visuales(OPCIONES_VISUALES_PREDETERMINADAS)

    @property
    def sesion(self) -> Sesion:
        return self._sesion

    @property
    def en_analisis(self) -> bool:
        return self._analizando or self.sesion.partida.estado_partida is not EstadoPartida.EN_CURSO

    @property
    def sesion_movimientos(self) -> Sesion:
        if self.en_analisis and self._analisis.sesion_hipotetica is not None:
            return self._analisis.sesion_hipotetica
        return self.sesion

    @property
    def promocion_pendiente(self):
        return self.sesion.jugada_pendiente or self._analisis.jugada_pendiente

    @property 
    def casillero(self) -> Casillero:
        return self._casillero

    @property
    def origen_seleccionado(self) -> tuple[int, int] | None:
        return self._origen_seleccionado

    @origen_seleccionado.setter
    def origen_seleccionado(self,
                            nuevo_origen: tuple[int, int] | None) -> None:
        self._origen_seleccionado = nuevo_origen

    @property
    def estado_mostrado(self) -> EstadoPosicion | None:
        return self._estado_mostrado

    @estado_mostrado.setter
    def estado_mostrado(self,
                        nuevo_estado: EstadoPosicion) -> None:
        self._estado_mostrado = nuevo_estado

    @property
    def origen_anotacion(self) -> tuple[int, int] | None:
        return self._origen_anotacion

    @property
    def flecha_seleccionada(self) -> int | None:
        return self._flecha_seleccionada

    @property
    def contenedor(self) -> tk.Misc:
        return self._contenedor

    @property
    def panel_navegacion(self) -> tk.Frame:
        return self._panel_navegacion

    @property
    def solo_analisis(self) -> bool:
        return self._solo_analisis

    @property
    def indicador_estado_partida(self) -> tk.Label | None:
        return  self._indicador_estado_partida

    @property
    def botones_abandono(self) -> dict[Color, tk.Button]:
        return self._botones_abandono

    @property
    def botones_propuesta_tablas(self) -> dict[Color, tk.Button]:
        return self._botones_propuesta_tablas

    @property
    def boton_reclamacion_tablas(self) -> tk.Button:
        return self._boton_reclamacion_tablas

    def proponer_tablas(self,
                        color: Color) -> None:
        if not self.sesion.tablas_por_acuerdo_disponibles:
            return

        self.sesion.proponer_tablas(color)

        self._consultar_respuesta_tablas()

        self._actualizar_botones(self.botones_propuesta_tablas)

    def reclamar_tablas_por_cincuenta_movimientos(self,
                                                  *,
                                                  movimiento_anunciado: tuple[tuple[int, int],
                                                                              tuple[int, int]] |
                                                                              None = None) -> bool:
        reclamacion = self.sesion.reclamar_tablas_por_cincuenta_movimientos(self.sesion.partida.jugador,
                                                                            movimiento_anunciado = movimiento_anunciado)

        if reclamacion:
            self._cancelar_seleccion()

        return reclamacion

    def reclamar_tablas_por_triple_repeticion(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        aceptada = self.sesion.reclamar_tablas_por_triple_repeticion(
            self.sesion.partida.jugador,
            movimiento_anunciado=movimiento_anunciado,
        )
        if aceptada:
            self._cancelar_seleccion()

        return aceptada

    def reclamar_tablas(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        """Envía una reclamación por una de las reglas disponibles."""
        if self.sesion.tablas_por_triple_repeticion_disponible(
            movimiento_anunciado=movimiento_anunciado
        ):
            return self.reclamar_tablas_por_triple_repeticion(
                movimiento_anunciado=movimiento_anunciado
            )
        if self.sesion.tablas_por_cincuenta_movimientos_disponible(
            movimiento_anunciado=movimiento_anunciado
        ):
            return self.reclamar_tablas_por_cincuenta_movimientos(
                movimiento_anunciado=movimiento_anunciado
            )

        return False

    def _ofrecer_reclamacion_con_movimiento(
        self,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        if self.en_analisis:
            return False
        if self.sesion.reclamacion_tablas_disponible():
            return False
        if not self.sesion.reclamacion_tablas_disponible(
            movimiento_anunciado=movimiento_anunciado
        ):
            return False

        if messagebox.askyesno(
            message="Este movimiento permite reclamar tablas. ¿Quieres reclamarlas?",
            parent=self.contenedor,
        ):
            return self.reclamar_tablas(movimiento_anunciado=movimiento_anunciado)

        return False

    def mostrar_estado(self,
                       estado_posicion: EstadoPosicion) -> None:
        self.casillero.mostrar_posicion(self._obtener_distribucion(estado_posicion))

        if self.flecha_seleccionada:
            self._flecha_seleccionada = None

        self.origen_seleccionado = None

        self._origen_anotacion = None

        self.estado_mostrado = estado_posicion

        self.actualizar_resaltados_ultimo_movimiento()

        self.actualizar_resaltado_jaque()

        self._actualizar_indicador_contexto()

    def actualizar_resaltado_jaque(self) -> None:
        """Representa el jaque del estado mostrado, incluidas posiciones históricas."""
        self._cancelar_parpadeo_jaque()

        self._borrar_indicadores_jaque()

        modo = self.opciones_visuales.modo_resaltado_jaque

        if self.estado_mostrado is None or modo is ModoResaltadoJaque.INTERMITENTE_TRAS_RECHAZO:
            return

        tablero = self.estado_mostrado.tablero

        for posicion, pieza in tablero.casillas.items():
            if not isinstance(pieza, Rey):
                continue
            if modo is ModoResaltadoJaque.REY_Y_ATACANTES:
                atacantes = tablero.obtener_atacantes_del_rey(pieza.color)

                en_jaque = bool(atacantes)
            else:
                atacantes = ()

                en_jaque = tablero.el_rey_queda_en_jaque(pieza.color)
            if en_jaque:
                self.casillero.aplicar_marca(posicion, 
                                             "jaque")

                for atacante in atacantes:
                    self.casillero.aplicar_marca(atacante, 
                                                 "atacante_jaque")

    def _borrar_indicadores_jaque(self) -> None:
        for posicion in self.casillero.casillas:
            self.casillero.borrar_marca(posicion, 
                                        "jaque")

            self.casillero.borrar_marca(posicion, 
                                        "atacante_jaque")

    def _cancelar_parpadeo_jaque(self) -> None:
        if self._id_parpadeo_jaque is not None:
            self.casillero.canvas.after_cancel(self._id_parpadeo_jaque)

            self._id_parpadeo_jaque = None

    def _al_destruir_canvas(self, evento: tk.Event) -> None:
        if evento.widget is self.casillero.canvas:
            self._cancelar_parpadeo_jaque()

    def _avisar_rechazo_por_jaque(self, color: Color) -> None:
        """Destaca el rey en su casilla actual, nunca mueve la propuesta rechazada.

        Sólo se llama si el modelo identifica el jaque como motivo del rechazo,
        tanto si el intento no lo resuelve como si expondría a un rey a salvo.
        """
        opciones = self.opciones_visuales

        if opciones.modo_resaltado_jaque is not ModoResaltadoJaque.INTERMITENTE_TRAS_RECHAZO:
            return
        
        self._cancelar_parpadeo_jaque()

        self._borrar_indicadores_jaque()

        estado = self.estado_mostrado

        posicion_rey = next((posicion for posicion, pieza in estado.tablero.casillas.items()
                             if isinstance(pieza, Rey) and pieza.color == color), 
                             None)
        
        if posicion_rey is None:
            return

        def alternar(pasos_restantes: int) -> None:
            self._id_parpadeo_jaque = None

            if self.estado_mostrado is not estado or self.opciones_visuales is not opciones:
                return
            if pasos_restantes % 2 == 0:
                self.casillero.aplicar_marca(posicion_rey, "jaque")
            else:
                self.casillero.borrar_marca(posicion_rey, "jaque")
            if pasos_restantes > 1:
                self._id_parpadeo_jaque = self.casillero.canvas.after(opciones.intervalo_parpadeo_jaque_ms, 
                                                                      alternar, 
                                                                      pasos_restantes - 1)

        alternar(2 * opciones.repeticiones_parpadeo_jaque)

    def _establecer_origen_anotacion(self,
                                     event) -> None:
        if self.promocion_pendiente:
            return

        self.casillero.canvas.focus_set()
        
        self._origen_anotacion = self.casillero.obtener_coordenadas_logicas((event.x,
                                                                             event.y))

    def _definir_anotacion(self,
                          event) -> None:
        casilla_evento = self.casillero.obtener_coordenadas_logicas((event.x,
                                                                    event.y))

        if (
            casilla_evento not in self.casillero.casillas or 
            not self._origen_anotacion or
            self.promocion_pendiente
        ):
            self._origen_anotacion = None

            return

        if self.origen_anotacion == casilla_evento:
            self._alternar_resaltado_estrategico(casilla_evento)

            self._origen_anotacion = None         
        else:
            self._dibujar_flecha(
                self.origen_anotacion,
                casilla_evento
            )
            self._origen_anotacion = None

    def _borrar_ultima_anotacion(self,
                                 event) -> None:
        anotaciones = self.casillero.anotaciones_estrategicas

        if anotaciones:
            id = anotaciones[-1]
        else:
            return

        if "flecha" in self.casillero.canvas.gettags(id):
            self.casillero.borrar_flecha(id)

            if id == self.flecha_seleccionada:
                self._flecha_seleccionada = None

            return

        casilla = self.casillero.obtener_casilla(id)    

        if casilla:
            self.casillero.borrar_elemento(casilla.coordenadas,
                                           id)

    def actualizar_resaltados_ultimo_movimiento(self) -> None:
        """Marca el movimiento del estado mostrado, vigente o histórico.

        El estado mostrado debe ser una posición confirmada o inicial, no una
        propuesta pendiente. No consulta la modalidad ni envía datos a la sesión.
        Sólo retira estas dos marcas: conserva selección, jaque y anotaciones.
        """
        for coordenadas_casilla in self.casillero.casillas:
            self.casillero.borrar_marca(coordenadas_casilla,
                                        "ultima_jugada_origen")
            
            self.casillero.borrar_marca(coordenadas_casilla,
                                        "ultima_jugada_destino")

        estado = self.estado_mostrado

        if estado is None or estado.origen is None or estado.destino is None:
            return

        self.casillero.aplicar_marca(estado.origen,
                                     "ultima_jugada_origen")
        
        self.casillero.aplicar_marca(estado.destino,
                                     "ultima_jugada_destino")


    def _alternar_resaltado_estrategico(self,
                                       casilla: tuple[int, int]) -> None:
        ids_por_clave = self.casillero.casillas[casilla].ids_elementos_por_clave

        id = ids_por_clave.get("marca:fondo_azul")

        if id:
           self.casillero.borrar_marca(casilla,
                                       "fondo_azul")

        else:
            self.casillero.aplicar_marca(casilla,
                                         "fondo_azul")

    def _dibujar_flecha(self,
                        origen: tuple[int, int],
                        destino: tuple[int, int]) -> None:
        self.casillero.aplicar_flecha(origen,
                                      destino,
                                      "flecha_estrategica")

    def gestionar_clic_izquierdo(self,
                                 event) -> None:
        tablero = self.estado_mostrado.tablero

        sesion = self.sesion

        canvas = self.casillero.canvas

        if self.promocion_pendiente:
            return

        canvas.focus_set()

        objeto_señalado = canvas.find_withtag("current")

        if objeto_señalado:
            id = objeto_señalado[0]

            if "flecha" in canvas.gettags(id):  
                if "flecha_seleccionada" in canvas.gettags(id):
                    self._flecha_seleccionada = None

                    self.casillero.alternar_resaltado_flecha(id)

                    return

                if self.flecha_seleccionada:
                    self.casillero.alternar_resaltado_flecha(self.flecha_seleccionada)
                
                self.casillero.alternar_resaltado_flecha(id)

                self._flecha_seleccionada = id

                return

        if (
            not self.en_analisis and
            not self.estado_mostrado == sesion.estado_actual and
            sesion.partida.estado_partida == EstadoPartida.EN_CURSO
        ):
            self.estado_mostrado = sesion.estado_actual

            self.mostrar_estado(self.estado_mostrado)

            return

        casilla = self.casillero.obtener_coordenadas_logicas((event.x,
                                                              event.y))

        if casilla is None:
            return

        casillas = self.estado_mostrado.tablero.casillas

        if self.origen_seleccionado:
            if self.origen_seleccionado == casilla:
                self._cancelar_seleccion()
                
                return

            if (
                casillas[casilla] and
                casillas[casilla].color == casillas[self.origen_seleccionado].color
            ):
                self._cancelar_seleccion()

                self.origen_seleccionado = casilla

                self.casillero.aplicar_marca(casilla,
                                             "seleccion")

                return

            if self._ofrecer_reclamacion_con_movimiento((self.origen_seleccionado,
                                                         casilla)):
                return

            aux_estado = self.estado_mostrado

            if self.en_analisis:
                motivo_rechazo = self._analisis.solicitar_movimiento(
                    self.estado_mostrado, self.origen_seleccionado, casilla)
            else:
                motivo_rechazo = sesion.solicitar_movimiento(self.origen_seleccionado, casilla)

            if motivo_rechazo is MotivoRechazoMovimiento.REY_EN_JAQUE:
                self._avisar_rechazo_por_jaque(casillas[self.origen_seleccionado].color)

                return

            if motivo_rechazo is not None:
                return

            if self.promocion_pendiente:
                self._abrir_selector_promocion(self.promocion_pendiente.pieza.color)

                return

            if (
                self.sesion_movimientos.estado_actual.estado_anterior and
                self.sesion_movimientos.estado_actual is not aux_estado
            ):
                self._mostrar_movimiento(self.origen_seleccionado,
                                         casilla)

                self.estado_mostrado = self.sesion_movimientos.estado_actual

                self.casillero.limpiar_anotaciones_temporales()

                if self.flecha_seleccionada:
                    self._flecha_seleccionada = None

                self.actualizar_resaltados_ultimo_movimiento()

                self.actualizar_resaltado_jaque()

                self._cancelar_seleccion()

                return

            return

        if (
            self.promocion_pendiente or
            not tablero.pieza_en(casilla) or
            (not self.en_analisis and tablero.pieza_en(casilla).color not in sesion.colores_seleccionables)
            ):
                return
        
        self.origen_seleccionado = casilla

        self.casillero.aplicar_marca(casilla,
                                     "seleccion")  

    def retroceder_movimiento(self) -> None:
        estado = self.estado_mostrado

        if self.promocion_pendiente:
            return
        
        anterior = self._analisis.obtener_anterior(estado)

        if anterior is None:
            return
        
        self._origen_anotacion = None

        if not self.sesion.partida.contiene_estado(estado):
            self.mostrar_estado(anterior)
            return

        casillas = self.casillero.casillas

        posiciones = (estado.origen, estado.destino)

        v = (posiciones[1][0] - posiciones[0][0],
             posiciones[1][1] - posiciones[0][1])

        es_enroque = False

        es_promocion = (
            (
                isinstance(estado.estado_anterior.tablero.casillas[posiciones[0]], 
                           PeonBlanco) and
                posiciones[1][0] == 7
            ) or (
                isinstance(estado.estado_anterior.tablero.casillas[posiciones[0]], 
                           PeonNegro) and
                posiciones[1][0] == 0
            )
        )

        if (
            isinstance(estado.pieza, Rey) and
            abs(v[1]) == 2
        ):
            es_enroque = True

            if estado.pieza.color == Color.Blanco:
                if v[1] < 0:
                    posicion_torre = (0, 0)

                    posicion_destino_torre = (0, 3)
                else:
                    posicion_torre = (0, 7)

                    posicion_destino_torre = (0, 5)
            elif estado.pieza.color == Color.Negro:
                if v[1] < 0:
                    posicion_torre = (7, 0)

                    posicion_destino_torre = (7, 3)
                else:
                    posicion_torre = (7, 7)

                    posicion_destino_torre = (7, 5)

            torre = casillas[posicion_destino_torre]

        if (
            abs(v[0]) == 1 and abs(v[1]) == 1 and
            (
                isinstance(estado.pieza, PeonBlanco) or
                isinstance(estado.pieza, PeonNegro)
            ) and 
            estado.estado_anterior.tablero.casillas[posiciones[1]] == None
        ):
            posicion_pieza_capturada = (posiciones[0][0],
                                        posiciones[1][1])

        else:
            posicion_pieza_capturada = posiciones[1]  

        if es_promocion:
            pieza_promocionada = casillas[posiciones[1]].id_pieza

            casillas[posiciones[1]].aplicar_elemento(self.casillero.tema.piezas["peon",
                                                                                estado.pieza.color,
                                                                                "normal"],
                                                     "pieza")

            self.casillero.canvas.delete(pieza_promocionada)
             

        self.casillero.desplazar_pieza(casillas[posiciones[1]].id_pieza,
                                       posiciones[1],
                                       posiciones[0])

        if es_enroque:
            self.casillero.desplazar_pieza(torre.id_pieza,
                                           posicion_destino_torre,
                                           posicion_torre)
        elif estado.estado_anterior:

            pieza_capturada = self._obtener_pieza_visual(posicion_pieza_capturada,
                                                         estado.estado_anterior)

            if pieza_capturada:
                casillas[posicion_pieza_capturada].aplicar_elemento(self.casillero.tema.piezas[pieza_capturada],
                                                                    "pieza") 

        self.estado_mostrado = self.estado_mostrado.estado_anterior         

        self.origen_seleccionado = None 

        self._cancelar_seleccion() 

        self.actualizar_resaltados_ultimo_movimiento()

        self.actualizar_resaltado_jaque()

        self._actualizar_indicador_contexto()

    def solicitar_abandono(self,
                           color: Color,
                           opciones: int) -> None:
        if color == Color.Blanco:
            nombre_color = "blancas"
        else:
            nombre_color = "negras"

        if opciones == 2:
            adicional = f" con las {nombre_color}"
        else:
            adicional = ""

        mensaje = f"¿Quieres abandonar la partida{adicional}?"

        respuesta = messagebox.askyesno(title = "Abandonar partida",
                                        message = mensaje,
                                        parent = self.contenedor)

        if respuesta:
            self.sesion.solicitar_abandono(color)

            self._cancelar_seleccion()
        else:
            return

    def _actualizar_botones(self,
                            botones: dict[Color, tk.Button]) -> None:
        for boton in botones.values():
            if (
                self.sesion.partida.estado_partida == EstadoPartida.EN_CURSO and
                not self.promocion_pendiente and
                (
                    not botones == self.botones_propuesta_tablas or
                    (
                        botones == self.botones_propuesta_tablas and
                        self.sesion.tablas_por_acuerdo_disponibles and
                        not self.sesion.proponente_tablas
                    )
                )
            ):
                boton.configure(state = "normal")
            else:
                boton.configure(state = "disabled")
        
    #Precondición: origen_seleccionado no puede ser None
    def _mostrar_movimiento(self,
                            origen: tuple[int, int],
                            destino: tuple[int, int]) -> None:
        """Método auxiliar interno. Es llamado cuando una jugada ha sido confirmada por el modelo;
        pero el cambio aún no se ha aplicado sobre el tablero gráfico.
        
        Precondición: origen_seleccionado no puede ser None."""

        partida = self.sesion_movimientos.partida

        tablero = self.sesion_movimientos.estado_actual.estado_anterior.tablero
        
        pieza = tablero.casillas[origen]

        casillero = self.casillero

        id = casillero.casillas[origen].id_pieza

        if (
            partida.ultima_jugada and
            isinstance(partida.ultima_jugada,
                       CapturaAlPaso)                   
        ):
            casillero.captura_al_paso(id,
                                      origen,
                                      destino,
                                      self.estado_mostrado.tablero.posicion_de_captura_al_paso)

        elif partida.es_enroque(pieza,
                              origen,
                              destino):
            aux = (destino[1] - origen[1], pieza.color)

            match aux:
                case (-2, Color.Blanco):
                    origen_torre = (0, 0)

                case (2, Color.Blanco):
                    origen_torre = (0, 7)

                case (-2, Color.Negro):
                    origen_torre = (7, 0)

                case (2, Color.Negro):
                    origen_torre = (7, 7)

            casillero.enroque(origen_torre)

        elif (
            tablero.casillas[destino] and
            tablero.casillas[destino].color != pieza.color
        ):
            casillero.captura_ordinaria(id,
                                        origen,
                                        destino)
        else:
            casillero.desplazar_pieza(id,
                                      origen,
                                      destino)

    def _confirmar_promocion(self,
                             pieza: PiezaPromocion,
                             origen: tuple[int, int],
                             destino: tuple[int, int]) -> None:
        if self._analisis.jugada_pendiente:
            self._analisis.confirmar_promocion(pieza)
        else:
            self.sesion.elegir_promocion(pieza)

        if self.estado_mostrado != self.sesion_movimientos.estado_actual:
            self._mostrar_movimiento(origen,
                                     destino)
            
            self.casillero.canvas.delete(self.casillero.casillas[destino].id_pieza)
            
            self.casillero.promocion(destino,
                                     self._obtener_pieza_visual(destino,
                                                                self.sesion_movimientos.estado_actual))

            self.estado_mostrado = self.sesion_movimientos.estado_actual

            self._cancelar_seleccion()

            self.casillero.limpiar_anotaciones_temporales()

            if self.flecha_seleccionada:
                self._flecha_seleccionada = None

            self.actualizar_resaltados_ultimo_movimiento()

            self.actualizar_resaltado_jaque()

    def _abrir_selector_promocion(self,
                                  color: Color) -> None:
        """Abre el panel de selección de piezas.

        Precondición: Existe una jugada pendiente."""
        
        panel = tk.Frame(self.casillero.contenedor)

        panel.place(relx = 0.5,
                    rely = 0.5,
                    anchor = "center")

        if self.promocion_pendiente:
            origen = self.promocion_pendiente.origen

            destino = self.promocion_pendiente.destino

        panel.lift()

        piezas = self.casillero.tema.piezas

        colores = self.casillero.tema.colores

        botones = (
            tk.Button(panel, 
                      image = piezas["caballo",
                                     color,
                                     "normal"],
                      background = colores["marfil"],
                      command = lambda: self._elegir_y_cerrar(PiezaPromocion.CABALLO,
                                                              origen,
                                                              destino,
                                                              panel)),
             tk.Button(panel, 
                       image = piezas["alfil",
                                      color,
                                      "normal"],
                       background = colores["marfil"],
                       command = lambda: self._elegir_y_cerrar(PiezaPromocion.ALFIL,
                                                               origen,
                                                               destino,
                                                               panel)),
            tk.Button(panel, 
                      image = piezas["torre",
                                     color,
                                     "normal"],
                      background = colores["marfil"],
                      command = lambda: self._elegir_y_cerrar(PiezaPromocion.TORRE,
                                                              origen,
                                                              destino,
                                                              panel)),
            tk.Button(panel, 
                      image = piezas["dama",
                                     color,
                                     "normal"],
                      background = colores["marfil"],
                      command = lambda: self._elegir_y_cerrar(PiezaPromocion.REINA,
                                                              origen,
                                                              destino,
                                                              panel))
        )

        self._botones_promocion = {
            (nombre, color, "normal"): boton
            for nombre, boton in zip(("caballo", "alfil", "torre", "dama"), botones)
        }

        c = 0

        for boton in botones:
            boton.grid(row = 0,
                       column = c)
            
            boton.bind("<Enter>", lambda evento: self._resaltar_opcion_promocion(evento,
                                                                                 True))
            
            boton.bind("<Leave>", lambda evento: self._resaltar_opcion_promocion(evento,
                                                                                 False))

            c += 1

        self._actualizar_botones(self.botones_abandono)

        self._actualizar_botones(self.botones_propuesta_tablas)

        self._actualizar_boton_reclamacion_tablas()

    def _resaltar_opcion_promocion(self,
                                   evento: tk.Event,
                                   activo: bool) -> None:
        boton = evento.widget

        if activo:
            boton.configure(background = self.casillero.tema.colores["ambar"])

        else:
            boton.configure(background = self.casillero.tema.colores["marfil"])

    def _elegir_y_cerrar(self,
                         pieza: PiezaPromocion,
                         origen: tuple[int, int],
                         destino: tuple[int, int],
                         panel: tk.Frame) -> None:
        self._confirmar_promocion(pieza,
                                  origen,
                                  destino)

        panel.destroy()
        self._botones_promocion.clear()
        
    def _cancelar_seleccion(self) -> None:
        self.casillero.borrar_seleccion()

        self.origen_seleccionado = None
        
        self._actualizar_indicador_contexto()

    def _borrar_flecha_seleccionada(self,
                                    event) -> None:
        if self.flecha_seleccionada:
            self.casillero.borrar_flecha(self.flecha_seleccionada)

        self._flecha_seleccionada = None

    def _obtener_distribucion(self,
                              estado_posicion: EstadoPosicion) -> dict[tuple[int, int],
                                                                       tuple[str, Color, str]]:
        distribucion = {}

        casillas = estado_posicion.tablero.casillas

        for casilla in casillas:
            if casillas[casilla] is None:
                continue

            distribucion[casilla] = self._obtener_pieza_visual(casilla,
                                                               estado_posicion)

        return distribucion

    def _obtener_pieza_visual(self,
                              posicion: tuple[int, int],
                              estado_posicion: EstadoPosicion) -> tuple[str, Color, str] | None:
        pieza = estado_posicion.tablero.casillas[posicion]

        if pieza is not None:
            if (isinstance(pieza, PeonNegro)
                or isinstance(pieza, PeonBlanco)):
                nombre = "peon"

            if isinstance(pieza, Caballo):
                nombre = "caballo"

            if isinstance(pieza, Alfil):
                nombre = "alfil"

            if isinstance(pieza, Torre):
                nombre = "torre"

            if isinstance(pieza, Reina):
                nombre = "dama"

            if isinstance(pieza, Rey):
                nombre = "rey"

            return (nombre, pieza.color, "normal")

        else:
            return None

    def _crear_panel_navegacion(self) -> tk.Frame:
        panel = tk.Frame(self.contenedor)

        panel.pack(side = "top", 
                   fill = "x",
                   pady = (8, 0))

        self._indicador_contexto = tk.Label(panel, 
                                            anchor = "w")

        self._indicador_contexto.pack(side = "bottom", 
                                      fill = "x")

        if not self.solo_analisis:
            self._indicador_estado_partida = tk.Label(panel,
                                                      anchor = "w")
            
            self.indicador_estado_partida.pack(side = "bottom",
                                               fill = "x")

        for texto, comando in (("Anterior", self.retroceder_movimiento),
                               ("Siguiente", self.avanzar_movimiento),
                               ("Posición actual", self.volver_al_estado_actual)):
            tk.Button(panel, 
                      text = texto, 
                      command = comando).pack(side = "left")

        if not self.solo_analisis:
            num_colores = self.sesion.colores_controlados

            self._boton_modo_analisis = tk.Button(panel, 
                                                  text = "Analizar aquí", 
                                                  command = self.alternar_analisis)

            self._boton_modo_analisis.pack(side = "left")

            tk.Button(panel, 
                      text = "⇄ Análisis separado", 
                      command = self.abrir_panel_analisis).pack(side = "left")
            
            if self.sesion.admite_abandono:
                botones = self.botones_abandono

                def comando(jugador):
                    return lambda: self.solicitar_abandono(jugador,
                                                           len(self.sesion.colores_controlados))

                if len(num_colores) == 1:
                    jugador = next(iter(num_colores))

                    botones[jugador] = tk.Button(panel,
                                                 text = "Abandonar",
                                                 command = comando(jugador))
                    botones[jugador].pack()
                else:
                    botones[Color.Blanco] = tk.Button(panel,
                                                      text = "Abandonar blancas",
                                                      command = comando(Color.Blanco))
                    botones[Color.Blanco].pack()

                    botones[Color.Negro] = tk.Button(panel,
                                                     text = "Abandonar negras",
                                                     command = comando(Color.Negro))
                    botones[Color.Negro].pack()

            if self.sesion.admite_propuestas_tablas:
                botones = self.botones_propuesta_tablas

                def comando(jugador):
                    return lambda: self.proponer_tablas(jugador)

                if len(num_colores) == 1:
                    jugador = next(iter(num_colores))

                    botones[jugador] = tk.Button(panel,
                                                 text = "Proponer tablas",
                                                 command = comando(jugador))
                    botones[jugador].pack()
                else:
                    botones[Color.Blanco] = tk.Button(panel,
                                                      text = "Proponer tablas - Blancas",
                                                      command = comando(Color.Blanco))
                    botones[Color.Blanco].pack()

                    botones[Color.Negro] = tk.Button(panel,
                                                     text = "Proponer tablas - Negras",
                                                     command = comando(Color.Negro))
                    botones[Color.Negro].pack()

            if self.sesion.admite_reclamaciones_tablas:
                self._boton_reclamacion_tablas= tk.Button(panel,
                                                         text = "Reclamar tablas",
                                                         command = self.reclamar_tablas)
                self.boton_reclamacion_tablas.pack()

        return panel

    def _actualizar_boton_reclamacion_tablas(self) -> None:
        if not self.boton_reclamacion_tablas:
            return
        elif (
            not self.en_analisis and
            self.sesion.reclamacion_tablas_disponible()
        ):
            self.boton_reclamacion_tablas.configure(state = "normal")
        else:
            self.boton_reclamacion_tablas.configure(state = "disabled")

    def _actualizar_indicador_contexto(self) -> None:
        if self._indicador_contexto is None:
            return
        
        contexto = "Análisis hipotético" if self.en_analisis else "Partida original"

        try:
            turno = self._analisis.obtener_turno(self.estado_mostrado).name.lower()
             
            texto = f"{contexto} · turno de {turno}"
        except ValueError:
            texto = f"{contexto} · posición externa al historial"

        self._indicador_contexto.configure(text = texto)

        self._actualizar_indicador_estado_partida()

        self._actualizar_botones(self.botones_abandono)

        self._actualizar_botones(self.botones_propuesta_tablas)

        self._actualizar_boton_reclamacion_tablas()

    def _actualizar_indicador_estado_partida(self) -> None:
        if not self.indicador_estado_partida:
            return

        jugador = self.sesion.partida.jugador

        estado = self.sesion.partida.estado_partida

        blancas = "blancas"

        negras = "negras"
        
        if estado == EstadoPartida.EN_CURSO:
            if jugador == Color.Blanco:
                color = blancas
            else:
                color = negras

            texto = f"Turno de {color}"
        elif estado == EstadoPartida.VICTORIA_BLANCA:
            texto = f"Victoria de {blancas}"
        elif estado == EstadoPartida.VICTORIA_NEGRA:
            texto = f"Victoria de {negras}"
        else:
            texto = "Tablas"

        self.indicador_estado_partida.configure(text = texto)

    def avanzar_movimiento(self) -> None:
        if self.promocion_pendiente:
            return
        
        siguiente = self._analisis.obtener_siguiente(self.estado_mostrado)

        if siguiente is not None:
            self.mostrar_estado(siguiente)

    def volver_al_estado_actual(self) -> None:
        if not self.promocion_pendiente:
            self.mostrar_estado(self.sesion.estado_actual)

    def alternar_analisis(self) -> None:
        if self.promocion_pendiente or self._solo_analisis:
            return
        
        self._analizando = not self._analizando

        self._cancelar_seleccion()

        self._origen_anotacion = None

        self._boton_modo_analisis.configure(text = "Salir del análisis" if self._analizando 
                                            else "Analizar aquí")

        if not self._analizando:
            self._analisis.descartar()

            self.volver_al_estado_actual()

    def abrir_panel_analisis(self) -> None:
        if self.promocion_pendiente:
            return        
        if self._panel_analisis is not None and self._panel_analisis.contenedor.winfo_manager():
            self._panel_analisis.casillero.canvas.focus_set()

            return
        if self._panel_analisis is None:
            from .panel_analisis import PanelAnalisis

            self._panel_analisis = PanelAnalisis(self.contenedor, 
                                                 self.estado_mostrado,
                                                 self.casillero.tamanno_casilla,
                                                 self._analisis.obtener_turno(self.estado_mostrado),
                                                 self.casillero.tema, 
                                                 self._volver_del_panel_analisis, 
                                                 self.opciones_visuales,
                                                 obtener_posicion_original = lambda: (self.estado_mostrado,
                                                                                      self._analisis.obtener_turno(self.estado_mostrado)))
            
        self._origen_anotacion = None

        self._disposicion_original = [(widget, widget.pack_info()) for widget in
                                     (self.casillero.contenedor, self.panel_navegacion)]
        
        for widget, _ in self._disposicion_original:
            widget.pack_forget()

        self._panel_analisis.contenedor.pack(fill = "both", 
                                             expand = True)

        self._panel_analisis.casillero.canvas.focus_set()

    def _volver_del_panel_analisis(self) -> None:
        if self._panel_analisis.promocion_pendiente:
            return
        
        self._panel_analisis._origen_anotacion = None

        self._panel_analisis.contenedor.pack_forget()

        for widget, opciones in self._disposicion_original:
            widget.pack(**opciones)

        self.casillero.canvas.focus_set()

    def _consultar_respuesta_tablas(self) -> None:
        if not self.sesion.tablas_por_acuerdo_disponibles:
            return

        proponente = self.sesion.proponente_tablas

        colores = self.sesion.colores_controlados

        if (
            proponente == Color.Blanco and
            Color.Negro in colores
        ):
            color = Color.Negro
        elif (
            proponente == Color.Negro and
            Color.Blanco in colores
        ):
            color = Color.Blanco
        else:
            return

        respuesta = messagebox.askyesno("Proposicion de tablas",
                                        "¿Aceptas las tablas?",
                                        parent = self.contenedor)

        self.sesion.responder_propuesta_tablas(color,
                                               respuesta)

        if respuesta:
            self._cancelar_seleccion()
        else:
            self._actualizar_indicador_contexto()
