from __future__ import annotations
from enum import Enum, auto
from abc import ABC, abstractmethod

class Color(Enum):
    Blanco = 0
    Negro = 1

class Pieza(ABC):
    def __init__(self, 
                 color: Color, 
                 valor_material: int, 
                 movimientos: tuple[Movimiento, ...],
                 es_deslizante: bool):
        self._color = color
        self._valor_material = valor_material
        self._movimientos = movimientos
        self._es_deslizante = es_deslizante

    @property
    def color(self) -> Color:
        return self._color

    @property
    def valor_material(self) -> int:
        return self._valor_material

    @property
    def movimientos(self) -> tuple[Movimiento, ...]:
        return self._movimientos

    @property
    def es_deslizante(self) -> bool:
        return self._es_deslizante

class PiezaConPrimerMovimiento(Pieza):
    def __init__(self, color: Color, 
                 valor_material: int, 
                 movimientos: tuple[Movimiento, ...],
                 es_deslizante: bool):
        super().__init__(color, valor_material, movimientos, es_deslizante)
        self._ha_movido = False

    @property
    def ha_movido(self) -> bool:
        return self._ha_movido


    def movimiento_realizado(self) -> None:
        if not self._ha_movido:
            self._ha_movido = True

class PeonBlanco(PiezaConPrimerMovimiento):
    def __init__(self):
        super().__init__(Color.Blanco, 
                         1, 
                         (AvanceSimpleBlanco(),
                          AvanceDobleBlanco(),
                          CapturaBlancoDerecha(),
                          CapturaBlancoIzquierda(),
                          AlPasoBlancoDerecha(),
                          AlPasoBlancoIzquierda()),
                          False)

class PeonNegro(PiezaConPrimerMovimiento):
    def __init__(self):
        super().__init__(Color.Negro,
                         1,
                         (AvanceSimpleNegro(),
                          AvanceDobleNegro(),
                          CapturaNegroDerecha(),
                          CapturaNegroIzquierda(),
                          AlPasoNegroDerecha(),
                          AlPasoNegroIzquierda()),
                          False)

class Torre(PiezaConPrimerMovimiento):
    def __init__(self, color: Color):
        super().__init__(color,
                         5,
                         (OrtogonalArriba(),
                          OrtogonalAbajo(),
                          OrtogonalDerecha(),
                          OrtogonalIzquierda()),
                          True)

class Rey(PiezaConPrimerMovimiento):
    def __init__(self, color: Color):
        super().__init__(color,
                         0,
                         (OrtogonalArriba(),
                          OrtogonalAbajo(),
                          OrtogonalDerecha(),
                          OrtogonalIzquierda(),
                          DiagonalArribaDerecha(),
                          DiagonalAbajoDerecha(),
                          DiagonalAbajoIzquierda(),
                          DiagonalArribaIzquierda(),
                          EnroqueCorto(),
                          EnroqueLargo()),
                          False)

class Caballo(Pieza):
    def __init__(self, color: Color):
        super().__init__(color,
                         3,
                         (CaballoArribaDerecha(),
                          CaballoDerechaArriba(),
                          CaballoDerechaAbajo(),
                          CaballoAbajoDerecha(),
                          CaballoAbajoIzquierda(),
                          CaballoIzquierdaAbajo(),
                          CaballoIzquierdaArriba(),
                          CaballoArribaIzquierda()),
                          False)

class Alfil(Pieza):
    def __init__(self, color: Color):
        super().__init__(color,
                         3,
                         (DiagonalArribaDerecha(),
                          DiagonalAbajoDerecha(),
                          DiagonalAbajoIzquierda(),
                          DiagonalArribaIzquierda()),
                          True)

class Reina(Pieza):
    def __init__(self, color: Color):
        super().__init__(color,
                         9,
                         (OrtogonalArriba(),
                          OrtogonalAbajo(),
                          OrtogonalDerecha(),
                          OrtogonalIzquierda(),
                          DiagonalArribaDerecha(),
                          DiagonalAbajoDerecha(),
                          DiagonalAbajoIzquierda(),
                          DiagonalArribaIzquierda()),
                         True)

"""*MOVIMIENTOS*"""

class Movimiento(ABC):
    def __init__(self):
        self._condiciones = ()

    @property
    def vector(self) -> Vector:
        return self._vector

    @property
    def condiciones(self) -> tuple[CondicionMovimiento, ...]:
        return self._condiciones

"""*Movimientos del peón*"""

class AvanceDobleBlanco(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = Arriba().suma(Arriba())
        self._condiciones = self._condiciones + (
            CondicionMovimiento.PRIMER_MOVIMIENTO_NO_REALIZADO,
            CondicionMovimiento.TRAYECTORIA_DESPEJADA,
            CondicionMovimiento.MOVIMIENTO_PEON
        )

class AvanceDobleNegro(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = Abajo().suma(Abajo())
        self._condiciones = self._condiciones + (
            CondicionMovimiento.PRIMER_MOVIMIENTO_NO_REALIZADO,
            CondicionMovimiento.TRAYECTORIA_DESPEJADA,
            CondicionMovimiento.MOVIMIENTO_PEON
        )

class CapturaBlancoIzquierda(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = ArribaIzquierda()
        self._condiciones = self._condiciones + (CondicionMovimiento.MOVIMIENTO_PEON,)

class AlPasoBlancoIzquierda(CapturaBlancoIzquierda):
    def __init__(self):
        super().__init__()

class CapturaBlancoDerecha(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = ArribaDerecha()
        self._condiciones = self._condiciones + (CondicionMovimiento.MOVIMIENTO_PEON,)

class AlPasoBlancoDerecha(CapturaBlancoDerecha):
    def __init__(self):
        super().__init__()

class CapturaNegroIzquierda(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = AbajoIzquierda()
        self._condiciones = self._condiciones + (CondicionMovimiento.MOVIMIENTO_PEON,)

class AlPasoNegroIzquierda(CapturaNegroIzquierda):
    def __init__(self):
        super().__init__()

class CapturaNegroDerecha(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = AbajoDerecha()
        self._condiciones = self._condiciones + (CondicionMovimiento.MOVIMIENTO_PEON,)

class AlPasoNegroDerecha(CapturaNegroDerecha):
    def __init__(self):
        super().__init__()

"""*Movimientos del caballo*"""

class MovimientoCaballo(Movimiento):
    def __init__(self):
        super().__init__()

class CaballoArribaDerecha(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Arriba().suma(ArribaDerecha())

class CaballoArribaIzquierda(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Arriba().suma(ArribaIzquierda())

class CaballoDerechaArriba(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Derecha().suma(ArribaDerecha())

class CaballoDerechaAbajo(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Derecha().suma(AbajoDerecha())

class CaballoAbajoDerecha(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Abajo().suma(AbajoDerecha())

class CaballoAbajoIzquierda(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Abajo().suma(AbajoIzquierda())

class CaballoIzquierdaAbajo(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Izquierda().suma(AbajoIzquierda())

class CaballoIzquierdaArriba(MovimientoCaballo):
    def __init__(self):
        super().__init__()
        self._vector = Izquierda().suma(ArribaIzquierda())

"""*Movimientos del alfil, la torre, el rey, la reina y avance individual de los peones*"""

class DiagonalArribaIzquierda(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = ArribaIzquierda()

class DiagonalArribaDerecha(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = ArribaDerecha()

class DiagonalAbajoDerecha(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = AbajoDerecha()

class DiagonalAbajoIzquierda(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = AbajoIzquierda()

class OrtogonalArriba(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = Arriba()

class OrtogonalDerecha(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = Derecha()

class OrtogonalAbajo(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = Abajo()

class OrtogonalIzquierda(Movimiento):
    def __init__(self):
        super().__init__()
        self._vector = Izquierda()

"""*Avances simples del peón*"""

class AvanceSimpleBlanco(OrtogonalArriba):
    def __init__(self):
        super().__init__()
        self._condiciones = self._condiciones + (CondicionMovimiento.MOVIMIENTO_PEON,)

class AvanceSimpleNegro(OrtogonalAbajo):
    def __init__(self):
        super().__init__()
        self._condiciones = self._condiciones + (CondicionMovimiento.MOVIMIENTO_PEON,)

"""*Movimientos del enroque*"""

class Enroque(Movimiento):
    def __init__(self):
        super().__init__()
        self._condiciones = self._condiciones + (
            CondicionMovimiento.PRIMER_MOVIMIENTO_NO_REALIZADO,
            CondicionMovimiento.TRAYECTORIA_DESPEJADA,
        )

    @property
    def vector_torre(self) -> Vector:
        return self._vector_torre

class EnroqueCorto(Enroque):
    def __init__(self):
        super().__init__()
        self._vector = Derecha().suma(Derecha())
        self._vector_torre = Izquierda().suma(Izquierda())

class EnroqueLargo(Enroque):
    def __init__(self):
        super().__init__()
        self._vector = Izquierda().suma(Izquierda())
        self._vector_torre = Derecha().suma(Derecha()).suma(Derecha())

"""*Vectores de movimiento*"""

class Vector(ABC):
    def __init__(self, desplazamiento: tuple[int, int]):
        self._desplazamiento = desplazamiento

    @property
    def desplazamiento(self) -> tuple[int, int]:
        return self._desplazamiento

    def suma(self, vector: Vector) -> Vector:
        return Vector((self.desplazamiento[0] + vector.desplazamiento[0],
                       self.desplazamiento[1] + vector.desplazamiento[1]))

    def por_escalar(self, escalar: int) -> Vector:
        return Vector((self.desplazamiento[0]*escalar,
                       self.desplazamiento[1]*escalar))

class Arriba(Vector):
    def __init__(self):
        super().__init__((1, 0))

class ArribaDerecha(Vector):
    def __init__(self):
        super().__init__((1, 1))

class Derecha(Vector):
    def __init__(self):
        super().__init__((0, 1))

class AbajoDerecha(Vector):
    def __init__(self):
        super().__init__((-1, 1))

class Abajo(Vector):
    def __init__(self):
        super().__init__((-1, 0))

class AbajoIzquierda(Vector):
    def __init__(self):
        super().__init__((-1, -1))

class Izquierda(Vector):
    def __init__(self):
        super().__init__((0, -1))

class ArribaIzquierda(Vector):
    def __init__(self):
        super().__init__((1, -1))

"""*Condiciones de movimiento*"""

class CondicionMovimiento(Enum):
    TRAYECTORIA_DESPEJADA = auto()
    PRIMER_MOVIMIENTO_NO_REALIZADO = auto()
    MOVIMIENTO_PEON = auto()


