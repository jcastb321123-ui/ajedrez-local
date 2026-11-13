"""Familia de sesiones y componentes reutilizables de preparación y envío.

La base no crea autenticadores, claves ni dos emisores: cada modalidad decide
cómo obtiene su partida y cómo hace llegar las solicitudes al modelo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
import random
import secrets
from copy import copy, deepcopy
from collections.abc import Callable
from typing import Any

from .autenticacion import AutenticadorJugadores
from .interfaz_juego import InterfazJuego, PiezaPromocion
from .partida import EstadoPartida, EstadoPosicion, Jugada, Partida, MotivoRechazoMovimiento
from .piezas import Color, Caballo, Alfil, Torre, Reina


class Sesion(ABC):
    """Consultas y acciones comunes a las distintas modalidades.

    Los colores controlados indican qué bandos maneja esta interfaz; los
    seleccionables aplican la política de cada modalidad. No se guardan copias del turno,
    de la posición ni del resultado: se consultan en la partida.
    """

    @property
    @abstractmethod
    def partida(self) -> Partida:
        """Partida consultable, sin exigir que se administre en este equipo."""
        raise NotImplementedError

    @property
    def estado_actual(self) -> EstadoPosicion:
        """Estado vigente; no es el estado histórico que muestra la GUI."""
        partida = self.partida
        if partida.ultima_jugada is None:
            return partida.estado_inicial
        return partida.ultima_jugada.estado_posicion

    @property
    @abstractmethod
    def jugada_pendiente(self) -> Jugada | None:
        """Jugada que espera la elección de promoción, si existe."""
        raise NotImplementedError

    @property
    @abstractmethod
    def colores_controlados(self) -> frozenset[Color]:
        """Bandos controlados desde esta interfaz, al margen del turno."""
        raise NotImplementedError

    @property
    def colores_seleccionables(self) -> frozenset[Color]:
        """Permite preseleccionar los bandos propios, pero no durante promoción.

        Las modalidades que restrinjan la selección por turno redefinen esta
        consulta. Seleccionar no autoriza a enviar un movimiento fuera de turno.
        """
        if self.jugada_pendiente is not None:
            return frozenset()
        return self.colores_controlados

    @property
    def admite_abandono(self) -> bool:
        return False

    @property
    def admite_guardado_local(self) -> bool:
        """Permite guardar el modelo en este equipo, según la política de la sesión.

        «Local» se refiere al almacenamiento: una sesión remota o contra IA
        también puede habilitarlo. No implica poder reanudar esa sesión desde
        el modelo guardado; sus datos de conexión o configuración son aparte.
        """
        return False

    @property
    def admite_propuestas_tablas(self) -> bool:
        return False

    @property
    def tablas_por_acuerdo_disponibles(self) -> bool:
        """Combina la capacidad de la modalidad con la situación de la partida."""
        return (
            self.admite_propuestas_tablas
            and self.partida.tablas_por_acuerdo_disponibles
        )

    @property
    def proponente_tablas(self) -> None | Color:
        return None

    @property
    def admite_reclamaciones_tablas(self) -> bool:
        return False

    @abstractmethod
    def solicitar_movimiento(self,
                             origen: tuple[int, int],
                             destino: tuple[int, int]) -> MotivoRechazoMovimiento | None:
        """Devuelve el motivo de rechazo, o None si se acepta o falta promocionar.

        La modalidad conserva el paso por la autenticación y la validación.
        """
        raise NotImplementedError

    @abstractmethod
    def elegir_promocion(self, 
                         pieza: PiezaPromocion) -> None:
        """Envía la elección. Precondición: hay una promoción pendiente."""
        raise NotImplementedError

    def solicitar_abandono(self,
                           color: Color) -> None:
        raise NotImplementedError

    def proponer_tablas(self,
                        color: Color) -> None:
        raise NotImplementedError

    def responder_propuesta_tablas(self,
                                   color: Color,
                                   aceptar: bool) -> None:
        raise NotImplementedError

    def reclamar_tablas_por_cincuenta_movimientos(self,
                                                  color: Color,
                                                  *,
                                                  movimiento_anunciado: tuple[tuple[int, int],
                                                                              tuple[int, int]] |
                                                                              None = None) -> bool:
        raise NotImplementedError

    def tablas_por_cincuenta_movimientos_disponible(self,
                                                    movimiento_anunciado: tuple[tuple[int, int],
                                                                               tuple[int, int]] |
                                                                               None = None) -> bool:
        return (
            self.admite_reclamaciones_tablas and
            self.partida.jugador in self.colores_controlados and
            self.partida.tablas_por_cincuenta_movimientos_disponible(movimiento_anunciado = movimiento_anunciado)
        ) 

    def reclamar_tablas_por_triple_repeticion(
        self,
        color: Color,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        raise NotImplementedError

    def tablas_por_triple_repeticion_disponible(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        return (
            self.admite_reclamaciones_tablas
            and self.partida.jugador in self.colores_controlados
            and self.partida.tablas_por_triple_repeticion_disponible(
                movimiento_anunciado=movimiento_anunciado
            )
        )

    def reclamacion_tablas_disponible(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        """Consulta las reglas reclamables para el jugador de esta sesión."""
        return (
            self.tablas_por_triple_repeticion_disponible(
                movimiento_anunciado=movimiento_anunciado
            )
            or self.tablas_por_cincuenta_movimientos_disponible(
                movimiento_anunciado=movimiento_anunciado
            )
        )

class ModalidadAsignacion(Enum):
    ALEATORIA = None
    BLANCO_NEGRO = (Color.Blanco, Color.Negro)
    NEGRO_BLANCO = (Color.Negro, Color.Blanco)


class SesionAnalisis(Sesion):
    """Partida local aislada para explorar ambos colores; no modifica su fuente.

    Copia tablero y metadatos de la posición, pero no arrastra su historial.
    No es un motor de IA: las jugadas siguen siendo propuestas por el usuario.
    """

    def __init__(self, estado_inicial: EstadoPosicion, turno: Color):
        raiz = copy(estado_inicial)
        raiz._tablero, raiz._pieza = deepcopy((estado_inicial.tablero, estado_inicial.pieza))
        raiz._estado_anterior = None
        self._partida = Partida(estado_inicial = raiz, turno_inicial = turno)
        self._jugada_pendiente = None

    @property
    def partida(self) -> Partida:
        return self._partida

    @property
    def jugada_pendiente(self) -> Jugada | None:
        return self._jugada_pendiente

    @property
    def colores_controlados(self) -> frozenset[Color]:
        return frozenset((Color.Blanco, Color.Negro))

    def solicitar_movimiento(self, origen, destino):
        if self.jugada_pendiente is not None:
            return MotivoRechazoMovimiento.PROMOCION_PENDIENTE
        if (
            origen not in self.partida.tablero.casillas or 
            destino not in self.partida.tablero.casillas
        ):
            return MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO
        
        resultado = self.partida.procesar_solicitud(origen, destino)

        if isinstance(resultado, Jugada):
            self._jugada_pendiente = resultado

            return None
        
        return resultado

    def elegir_promocion(self, pieza: PiezaPromocion) -> None:
        if self.jugada_pendiente is None:
            return
        
        clases = {PiezaPromocion.CABALLO: Caballo, 
                  PiezaPromocion.ALFIL: Alfil,
                  PiezaPromocion.TORRE: Torre,
                  PiezaPromocion.REINA: Reina}
        
        if pieza not in clases:
            raise ValueError("Pieza de promoción no válida.")
        
        jugada = self.jugada_pendiente

        self.partida.promocionar(jugada.destino, 
                                 clases[pieza](jugada.pieza.color), 
                                 jugada)
        
        self._jugada_pendiente = None

    def tablas_por_cincuenta_movimientos_disponible(self, 
                                                    movimiento_anunciado: tuple[tuple[int, int],
                                                                                tuple[int, int]] |
                                                                                None = None) -> bool:
        return False

class AsignacionColores:
    def __init__(self,
                 modalidad: ModalidadAsignacion):
        self._modalidad = modalidad

    @property
    def modalidad(self) -> ModalidadAsignacion:
        return self._modalidad

    def asignar_colores(self,
                autenticador: AutenticadorJugadores,
                asignacion: ModalidadAsignacion) -> tuple[str, str]:
        if asignacion == ModalidadAsignacion.ALEATORIA:
            return self._asignar_colores_aleatorios(autenticador)
        else:
            return self.obtener_claves_pactadas(autenticador,
                                               self.modalidad)

    """Precondición: No podrá prosperar ninguna asignación con los dos jugadores del mismo color"""
    def obtener_claves_pactadas(self,
                               autenticador: AutenticadorJugadores,
                               modalidad: ModalidadAsignacion) -> tuple[str, str]:
        claves = []

        for color_acordado in modalidad.value:
            for clave, color in autenticador.jugadores_por_clave.items():
                if color_acordado == color:
                    claves.append(clave)

        return (claves[0], claves[1])

    def _asignar_colores_aleatorios(self,
                                    autenticador: AutenticadorJugadores) -> tuple[str, str]: 
        claves = tuple(autenticador.jugadores_por_clave.keys())

        return tuple(random.sample(claves, 2))

class EmisorJugador:
    def __init__(self,
                 juego: InterfazJuego,
                 clave: str):
        self._juego = juego
        self._clave = clave

    @property
    def juego(self) -> InterfazJuego:
        return self._juego

    @property
    def clave(self) -> str:
        return self._clave

    def enviar_solicitud(self,
                         origen: tuple[int, int],
                         destino: tuple[int, int]) -> MotivoRechazoMovimiento | None:
        return self.juego.solicitar_movimiento(self.clave,
                                               origen,
                                               destino)

    def elegir_promocion(self,
                         pieza: PiezaPromocion) -> None:
        self.juego.aplicar_promocion(self.clave,
                                     pieza)

    def solicitar_abandono(self) -> None:
        self.juego.solicitar_abandono(self.clave)

    def proponer_tablas(self) -> None:
        self.juego.proponer_tablas(self.clave)

    def responder_propuesta_tablas(self,
                                   aceptar: bool) -> None:
        self.juego.responder_propuesta_tablas(self.clave,
                                              aceptar)

    def reclamar_tablas_por_cincuenta_movimientos(self,
                                                  *,
                                                  movimiento_anunciado: tuple[tuple[int, int],
                                                                              tuple[int, int]] |
                                                                              None = None) -> bool:
        return self.juego.reclamar_tablas_por_cincuenta_movimientos(self.clave,
                                                                    movimiento_anunciado = movimiento_anunciado)

    def reclamar_tablas_por_triple_repeticion(
        self,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        return self.juego.reclamar_tablas_por_triple_repeticion(
            self.clave, movimiento_anunciado=movimiento_anunciado
        )

class SesionLocal(Sesion):
    def __init__(self,
                 asignacion_colores: AsignacionColores,
                 *,
                 partida: Partida | None = None):
        self._autenticador = self._preparar_autenticador()

        self._asignacion_colores = asignacion_colores

        claves = self._asignacion_colores.asignar_colores(self.autenticador,
                                                          asignacion_colores.modalidad)
        
        self._juego = InterfazJuego(self.autenticador, partida=partida)

        self._emisor_1 = EmisorJugador(self.juego,
                                       claves[0])
        
        self._emisor_2 = EmisorJugador(self.juego,
                                       claves[1])

    @property
    def autenticador(self) -> AutenticadorJugadores[Color]:
        return self._autenticador

    @property
    def juego(self) -> InterfazJuego:
        return self._juego

    @property
    def partida(self) -> Partida:
        return self.juego.partida

    @property
    def jugada_pendiente(self) -> Jugada | None:
        return self.juego.jugada_pendiente

    @property
    def colores_controlados(self) -> frozenset[Color]:
        return frozenset((Color.Blanco, Color.Negro))

    @property
    def colores_seleccionables(self) -> frozenset[Color]:
        """En juego local sólo selecciona quien tiene el turno.

        Tras finalizar se pueden seleccionar ambos bandos para consultar la
        posición mostrada; esto no reabre la partida ni permite mover en ella.
        """
        colores = super().colores_seleccionables

        if self.partida.estado_partida == EstadoPartida.EN_CURSO:
            return colores & frozenset((self.partida.jugador,))
        
        return colores

    @property
    def emisor_1(self) -> EmisorJugador:
        return self._emisor_1

    @property
    def emisor_2(self) -> EmisorJugador:
        return self._emisor_2

    @property
    def admite_abandono(self) -> bool:
        return True

    @property
    def admite_guardado_local(self) -> bool:
        return True

    @property
    def admite_propuestas_tablas(self) -> bool:
        return True

    @property
    def proponente_tablas(self) -> Color | None:
        return self.juego.proponente_tablas

    @property
    def admite_reclamaciones_tablas(self) -> bool:
        return True

    def _accion_emisor(self,
                       funcion: Callable[..., Any],
                       *,
                       jugador: Color | None = None,
                       argumentos: tuple[Any, ...] = ()) -> Any: 
        emisor = self._obtener_emisor(color = jugador)

        objeto = funcion(emisor,
                         *argumentos)

        return objeto

    def solicitar_movimiento(self,
                             origen: tuple[int, int],
                             destino: tuple[int, int]) -> MotivoRechazoMovimiento | None:
        return self._accion_emisor(EmisorJugador.enviar_solicitud,
                                   argumentos = (origen,
                                                 destino))

    def elegir_promocion(self, 
                         pieza: PiezaPromocion) -> None:
        self._accion_emisor(EmisorJugador.elegir_promocion,
                            argumentos = (pieza,))
        
    def proponer_tablas(self, 
                        color: Color) -> None:
        self._accion_emisor(EmisorJugador.proponer_tablas,
                            jugador = color)

    def responder_propuesta_tablas(self, 
                                   color: Color, 
                                   aceptar: bool) -> None:
        self._accion_emisor(EmisorJugador.responder_propuesta_tablas,
                            jugador = color,
                            argumentos = (aceptar,))
    
    def solicitar_abandono(self,
                           color: Color) -> None:
        self._accion_emisor(EmisorJugador.solicitar_abandono,
                                   jugador = color)

    def reclamar_tablas_por_cincuenta_movimientos(self, 
                                                  color: Color,
                                                  *,
                                                  movimiento_anunciado: tuple[tuple[int, int],
                                                                              tuple[int, int]] |
                                                                              None = None) -> bool:
        return self._accion_emisor(lambda emisor: 
                                   emisor.reclamar_tablas_por_cincuenta_movimientos(movimiento_anunciado = movimiento_anunciado),
                                   jugador = color)

    def tablas_por_cincuenta_movimientos_disponible(self,
                                                    movimiento_anunciado: tuple[tuple[int, int],
                                                                                tuple[int, int]] |
                                                                                None = None) -> bool:
        return super().tablas_por_cincuenta_movimientos_disponible(movimiento_anunciado = movimiento_anunciado)
        
    def reclamar_tablas_por_triple_repeticion(
        self,
        color: Color,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        return self._accion_emisor(
            lambda emisor: emisor.reclamar_tablas_por_triple_repeticion(
                movimiento_anunciado=movimiento_anunciado
            ),
            jugador=color,
        )

    def _preparar_autenticador(self) -> AutenticadorJugadores[Color]:
        autenticador = AutenticadorJugadores[Color]()

        self._registrar_claves(autenticador)

        return autenticador

    def _registrar_claves(self, 
                          autenticador: AutenticadorJugadores[Color]) -> None:
        while True:
            clave_1 = secrets.token_urlsafe()

            clave_2 = secrets.token_urlsafe()

            if clave_1 != clave_2:
                break

        autenticador.registrar(clave_1, 
                               Color.Blanco)
        
        autenticador.registrar(clave_2, 
                               Color.Negro)

    def _obtener_emisor(self,
                        *,
                        color: Color | None = None) -> EmisorJugador:
        if not color:
            jugador = self.partida.jugador
        else:
            jugador = color

        for emisor in (self.emisor_1, self.emisor_2):
            if self.autenticador.autenticar(emisor.clave) == jugador:
                return emisor
