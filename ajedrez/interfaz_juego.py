from .partida import Partida, Jugada, MotivoRechazoMovimiento, EstadoPartida
from .piezas import Pieza, Caballo, Alfil, Torre, Reina, Color
from .autenticacion import AutenticadorJugadores
from enum import Enum, auto

class PiezaPromocion(Enum):
    CABALLO = auto()
    ALFIL = auto()
    TORRE = auto()
    REINA = auto()

class InterfazJuego:
    def __init__(self,
                 autenticador: AutenticadorJugadores[Color],
                 *,
                 partida: Partida | None = None):
        self._autenticador = autenticador
        self._partida = Partida() if partida is None else partida
        self._jugada_pendiente = None
        self._proponente_tablas: Color | None = None

    @property
    def autenticador(self) -> AutenticadorJugadores:
        return self._autenticador

    @property
    def partida(self) -> Partida:
        return self._partida

    @property
    def jugada_pendiente(self) -> Jugada | None:
        return self._jugada_pendiente

    @jugada_pendiente.setter
    def jugada_pendiente(self,
                         jugada: Jugada | None) -> None:
        self._jugada_pendiente = jugada

    @property
    def proponente_tablas(self) -> Color | None:
        return self._proponente_tablas

    @proponente_tablas.setter
    def proponente_tablas(self,
                          proponente: Color | None) -> None:
        self._proponente_tablas = proponente

    def aplicar_promocion(self,
                          clave: str,
                          tipo: PiezaPromocion) -> None:
        color = self.autenticador.autenticar(clave)

        if color is None or color != self.partida.jugador:
            return
        
        self.partida.promocionar(self.jugada_pendiente.destino, 
                                 self._pieza_promocion(tipo, 
                                                       self.jugada_pendiente), 
                                                       self.jugada_pendiente)

        self.jugada_pendiente = None
        self._actualizar_propuesta_tras_movimiento(color)

    def solicitar_movimiento(self,
                             clave: str,
                             origen: tuple[int, int],
                             destino: tuple[int, int]) -> MotivoRechazoMovimiento | None:
        if self.jugada_pendiente is not None:
            return MotivoRechazoMovimiento.PROMOCION_PENDIENTE
        
        color = self.autenticador.autenticar(clave)

        if color is None or color != self.partida.jugador:
            return MotivoRechazoMovimiento.NO_AUTORIZADO

        if self.partida.estado_partida != EstadoPartida.EN_CURSO:
            return MotivoRechazoMovimiento.PARTIDA_FINALIZADA

        jugada = self.partida.procesar_solicitud(origen, destino)

        if isinstance(jugada, Jugada):
            self.jugada_pendiente = jugada
        elif isinstance(jugada, MotivoRechazoMovimiento):
            return jugada

        self._actualizar_propuesta_tras_movimiento(color)

    def _actualizar_propuesta_tras_movimiento(self, color: Color) -> None:
        """Retira la oferta al jugar el adversario o al finalizar la partida.

        Se llama sólo tras aceptar un movimiento o confirmar su promoción.
        El movimiento del proponente conserva la oferta si la partida continúa.
        """
        if (
            self.partida.estado_partida is not EstadoPartida.EN_CURSO
            or self.proponente_tablas is not color
        ):
            self.proponente_tablas = None

    def solicitar_abandono(self,
                           clave: str) -> None:
        self.partida.abandonar(self.autenticador.autenticar(clave))
        self.proponente_tablas = None

    def reclamar_tablas_por_cincuenta_movimientos(self,
                                                  clave: str,
                                                  *,
                                                  movimiento_anunciado: tuple[tuple[int, int],
                                                                              tuple[int, int]] |
                                                                              None = None) -> bool:
        color = self.autenticador.autenticar(clave)

        if color != self.partida.jugador:
            return False

        resultado_llamada = self.partida.reclamar_tablas_por_cincuenta_movimientos(movimiento_anunciado = movimiento_anunciado)

        if resultado_llamada:
            self.proponente_tablas = None

        return resultado_llamada

    def reclamar_tablas_por_triple_repeticion(
        self,
        clave: str,
        *,
        movimiento_anunciado: tuple[tuple[int, int], tuple[int, int]] | None = None,
    ) -> bool:
        color = self.autenticador.autenticar(clave)
        if color != self.partida.jugador:
            return False

        aceptada = self.partida.reclamar_tablas_por_triple_repeticion(
            movimiento_anunciado=movimiento_anunciado
        )
        if aceptada:
            self.proponente_tablas = None

        return aceptada

    def _pieza_promocion(self,
                         pieza: PiezaPromocion,
                         jugada: Jugada) -> Pieza:
        match pieza:
            case PiezaPromocion.CABALLO:
                return Caballo(jugada.pieza.color)
            case PiezaPromocion.ALFIL:
                return Alfil(jugada.pieza.color)
            case PiezaPromocion.TORRE:
                return Torre(jugada.pieza.color)
            case PiezaPromocion.REINA:
                return Reina(jugada.pieza.color)

    def proponer_tablas(self,
                        clave: str) -> None:
        self.proponente_tablas = self.autenticador.jugadores_por_clave[clave]

    def responder_propuesta_tablas(self,
                                   clave: str,
                                   aceptar: bool) -> None:
        if (
            self.proponente_tablas is None
            or self.autenticador.jugadores_por_clave[clave] == self.proponente_tablas
        ):
            return

        if aceptar:
            if not self.partida.tablas_por_acuerdo_disponibles:
                return
            self.partida.estado_partida = EstadoPartida.TABLAS

        self.proponente_tablas = None
