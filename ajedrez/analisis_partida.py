"""Navegación y variantes provisionales, independientes del toolkit gráfico."""

from .partida import EstadoPosicion, Partida
from .piezas import Color
from .sesion import SesionAnalisis, PiezaPromocion


class AnalisisPartida:
    """Conserva una línea hipotética sin escribir en el historial original. 

    Algunos apuntes:

    - Nodos: Lista de tuplas con el estado del tablero y el color.

    - Los nuevos nodos pertenecen a la partida hipotética, permaneciendo aislados de la partida histórica real
    (si la hay).

    - Prefijo pendiente:
    """

    def __init__(self, partida_original: Partida):
        self.partida_original = partida_original
        self.sesion_hipotetica: SesionAnalisis | None = None
        self._nodos: list[tuple[EstadoPosicion, Color]] = []
        self._prefijo_pendiente = None

    @property
    def jugada_pendiente(self):
        return self.sesion_hipotetica.jugada_pendiente if self.sesion_hipotetica else None

    @property
    def estados_hipoteticos(self) -> tuple[EstadoPosicion, ...]:
        return tuple(estado for estado, _ in self._nodos)

    def descartar(self) -> None:
        if self.jugada_pendiente:
            return
        
        self._nodos = []

        self.sesion_hipotetica = None

        self._prefijo_pendiente = None

    def _indice(self, estado) -> int | None:
        return next(
            (i for i, (guardado, _) in enumerate(self._nodos) if guardado is estado), 
            None
             )

    def obtener_turno(self, estado: EstadoPosicion) -> Color:
        indice = self._indice(estado)

        if indice:
            return self._nodos[indice][1]
        
        return self.partida_original.obtener_turno_en_estado(estado)

    def obtener_anterior(self, estado: EstadoPosicion) -> EstadoPosicion | None:
        indice = self._indice(estado)
        if indice is not None and indice > 0:
            return self._nodos[indice - 1][0]
        if estado is self.partida_original.estado_inicial:
            return None
        if self.partida_original.contiene_estado(estado):
            return estado.estado_anterior
        return None

    def obtener_siguiente(self, estado: EstadoPosicion) -> EstadoPosicion | None:
        if self.jugada_pendiente:
            return None
        real = self.partida_original.obtener_estado_siguiente(estado)
        if real is not None:
            # Volver a la continuación real descarta la hipótesis provisional.
            self.descartar()
            return real
        indice = self._indice(estado)
        if indice is not None and indice + 1 < len(self._nodos):
            return self._nodos[indice + 1][0]
        return None

    def solicitar_movimiento(self, estado, origen, destino):
        if self.jugada_pendiente:
            return self.sesion_hipotetica.solicitar_movimiento(origen, destino)
        turno = self.obtener_turno(estado)
        indice = self._indice(estado)
        prefijo = self._nodos[:indice + 1] if indice is not None else [(estado, turno)]
        candidata = self.sesion_hipotetica
        if candidata is None or candidata.estado_actual is not estado:
            candidata = SesionAnalisis(estado, turno)
        anterior = candidata.estado_actual
        motivo = candidata.solicitar_movimiento(origen, destino)
        if candidata.jugada_pendiente:
            self.sesion_hipotetica = candidata
            self._prefijo_pendiente = prefijo
        elif candidata.estado_actual is not anterior:
            self.sesion_hipotetica = candidata
            self._nodos = prefijo + [(candidata.estado_actual, candidata.partida.jugador)]
        return motivo

    def confirmar_promocion(self, pieza: PiezaPromocion) -> None:
        if not self.jugada_pendiente:
            return
        self.sesion_hipotetica.elegir_promocion(pieza)
        if not self.jugada_pendiente:
            sesion = self.sesion_hipotetica
            self._nodos = self._prefijo_pendiente + [(sesion.estado_actual, sesion.partida.jugador)]
            self._prefijo_pendiente = None
