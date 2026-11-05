"""Borrador de posición para análisis; nunca edita un estado del historial."""

from copy import deepcopy

from .partida import EstadoPosicion
from .piezas import Color, Rey, Torre, Reina, Alfil, Caballo, PeonBlanco, PeonNegro


class EditorPosicion:
    def __init__(self, 
                 estado: EstadoPosicion, 
                 turno: Color):
        self.tablero = deepcopy(estado.tablero)
        self.turno = turno
        self._deshacer = []

    def _guardar(self):
        self._deshacer.append((deepcopy(self.tablero), self.turno))

    def _comprobar_casilla(self, posicion):
        if posicion not in self.tablero.casillas:
            raise ValueError("La casilla debe pertenecer al tablero.")

    def colocar(self, posicion, nombre: str, color: Color):
        self._comprobar_casilla(posicion)
        clases = {"rey": Rey, "dama": Reina, "torre": Torre, "alfil": Alfil, "caballo": Caballo}
        if nombre == "peon":
            pieza = PeonBlanco() if color is Color.Blanco else PeonNegro()
            if posicion[0] != (1 if color is Color.Blanco else 6):
                pieza.movimiento_realizado()
        else:
            pieza = clases[nombre](color)
            if isinstance(pieza, (Rey, Torre)):
                pieza.movimiento_realizado()
        self._guardar()
        self.tablero.colocar(pieza, posicion)
        self.tablero.posicion_de_captura_al_paso = None

    def quitar(self, posicion):
        self._comprobar_casilla(posicion)
        self._guardar()
        self.tablero.colocar(None, posicion)
        self.tablero.posicion_de_captura_al_paso = None

    def mover(self, origen, destino):
        self._comprobar_casilla(origen)
        self._comprobar_casilla(destino)
        pieza = self.tablero.pieza_en(origen)
        if pieza is None or origen == destino:
            return
        self._guardar()
        self.tablero.trasladar_pieza(origen, destino)
        if isinstance(pieza, (Rey, Torre, PeonBlanco, PeonNegro)):
            pieza.movimiento_realizado()
        self.tablero.posicion_de_captura_al_paso = None

    def vaciar(self):
        self._guardar()
        for posicion in self.tablero.casillas:
            self.tablero.colocar(None, posicion)
        self.tablero.posicion_de_captura_al_paso = None

    def deshacer(self):
        if self._deshacer:
            self.tablero, self.turno = self._deshacer.pop()

    def derechos_enroque(self) -> frozenset[tuple[Color, int]]:
        return set(self.tablero.obtener_derechos_enroque())

    def construir_estado(self, 
                         *, 
                         turno: Color,
                         enroques: set,
                         peon_al_paso: tuple[int, int] |
                         None = None) -> EstadoPosicion:
        """Valida coherencia básica, no demuestra que exista una partida que llegue aquí.

        Los enroques son derechos, no la posibilidad de ejecutarlos ahora. El
        modelo sigue comprobando obstáculos y amenazas cuando se solicita mover.
        """
        if not isinstance(turno, Color):
            raise ValueError("Elige el turno de blancas o negras.")
        tablero = deepcopy(self.tablero)
        reyes = {}
        for color in Color:
            posiciones = [p for p, pieza in tablero.casillas.items()
                          if isinstance(pieza, Rey) and pieza.color is color]
            if len(posiciones) != 1:
                raise ValueError("Debe haber exactamente un rey de cada color.")
            reyes[color] = posiciones[0]
        blanco, negro = reyes[Color.Blanco], reyes[Color.Negro]
        if max(abs(blanco[0] - negro[0]), abs(blanco[1] - negro[1])) <= 1:
            raise ValueError("Los reyes no pueden ocupar casillas adyacentes.")
        for posicion, pieza in tablero.casillas.items():
            if isinstance(pieza, (PeonBlanco, PeonNegro)) and posicion[0] in (0, 7):
                raise ValueError("No puede haber peones sin promocionar en la primera o última fila.")
        enemigo = Color.Negro if turno is Color.Blanco else Color.Blanco
        if tablero.el_rey_queda_en_jaque(enemigo):
            raise ValueError("El rey del bando que no tiene el turno no puede quedar en jaque.")
        permitidos = {(color, columna) for color in Color for columna in (0, 7)}
        if not enroques <= permitidos:
            raise ValueError("Derechos de enroque no válidos.")
        for pieza in tablero.casillas.values():
            if isinstance(pieza, (Rey, Torre)):
                pieza.movimiento_realizado()
        for color, columna in enroques:
            fila = 0 if color is Color.Blanco else 7
            rey, torre = tablero.pieza_en((fila, 4)), tablero.pieza_en((fila, columna))
            if not (isinstance(rey, Rey) and rey.color is color and
                    isinstance(torre, Torre) and torre.color is color):
                raise ValueError("El enroque exige rey y torre del mismo color en sus casillas iniciales.")
            # Son piezas nuevas del borrador, no se restaura el pasado de piezas reales.
            tablero.colocar(Rey(color), (fila, 4))
            tablero.colocar(Torre(color), (fila, columna))
        if peon_al_paso is not None:
            peon = tablero.pieza_en(peon_al_paso)
            fila = 3 if enemigo is Color.Blanco else 4
            inicio = 1 if enemigo is Color.Blanco else 6
            paso = 2 if enemigo is Color.Blanco else 5
            if not (isinstance(peon, (PeonBlanco, PeonNegro)) and peon.color is enemigo and
                    peon_al_paso[0] == fila and
                    tablero.pieza_en((inicio, peon_al_paso[1])) is None and
                    tablero.pieza_en((paso, peon_al_paso[1])) is None):
                raise ValueError("Indica la casilla del peón adversario que acaba de avanzar dos pasos.")
            peon.movimiento_realizado()
        tablero.posicion_de_captura_al_paso = peon_al_paso
        return EstadoPosicion(tablero=tablero)
