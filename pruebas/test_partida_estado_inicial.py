"""Inicio desde estados reales, alternancia y registro de turnos de Partida."""

import unittest

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.partida import CapturaAlPaso, Enroque, EstadoPosicion, Partida
from ajedrez.piezas import Color, Rey, Torre


def posicion(texto):
    return int(texto[1]) - 1, ord(texto[0]) - ord("a")


def firma_tablero(tablero):
    return (
        tuple((casilla, type(pieza), getattr(pieza, "color", None),
               getattr(pieza, "ha_movido", None))
              for casilla, pieza in tablero.casillas.items()),
        tablero.posicion_de_captura_al_paso,
    )


def registro(partida):
    return [(turno.numero,
             turno.jugada_blanco.numero if turno.jugada_blanco else None,
             turno.jugada_negro.numero if turno.jugada_negro else None)
            for turno in partida.registro_turnos]


class PruebasPartidaConEstadoInicial(unittest.TestCase):
    def jugar(self, partida, movimiento):
        numero = partida.contador_jugadas + 1
        color = partida.jugador
        partida.procesar_solicitud(posicion(movimiento[:2]), posicion(movimiento[2:]))
        self.assertEqual(partida.contador_jugadas, numero)
        self.assertEqual(partida.ultima_jugada.pieza.color, color)
        self.assertNotEqual(partida.jugador, color)
        return partida.ultima_jugada

    def estado_tras(self, movimientos):
        partida = Partida()
        for movimiento in movimientos.split():
            self.jugar(partida, movimiento)
        return partida.ultima_jugada.estado_posicion

    def comprobar_linea(self, partida, movimientos, esperado):
        inicial = partida.estado_inicial
        firma_inicial = firma_tablero(partida.tablero)
        anteriores = []
        for movimiento in movimientos.split():
            jugada = self.jugar(partida, movimiento)
            if anteriores:
                anterior = anteriores[-1]
                self.assertIs(jugada.anterior, anterior)
                self.assertIs(anterior.siguiente, jugada)
                self.assertIs(jugada.estado_posicion.estado_anterior, anterior.estado_posicion)
            else:
                self.assertIsNone(jugada.anterior)
                if inicial is not None:
                    self.assertIs(jugada.estado_posicion.estado_anterior, inicial)
            anteriores.append(jugada)
            # Ninguna jugada debe perderse o duplicarse, tampoco en turnos incompletos.
            guardadas = [j for turno in partida.registro_turnos
                         for j in (turno.jugada_blanco, turno.jugada_negro) if j is not None]
            self.assertEqual(guardadas, anteriores)
            for turno in partida.registro_turnos:
                if turno.jugada_blanco:
                    self.assertEqual(turno.jugada_blanco.pieza.color, Color.Blanco)
                if turno.jugada_negro:
                    self.assertEqual(turno.jugada_negro.pieza.color, Color.Negro)
        self.assertEqual(registro(partida), esperado)
        self.assertIsNone(partida.ultima_jugada.siguiente)
        if inicial is not None:
            self.assertIs(partida.estado_inicial, inicial)
            self.assertEqual(firma_tablero(inicial.tablero), firma_inicial)

    def test_partida_normal_y_none_explicito(self):
        for partida in (Partida(), Partida(estado_inicial=None)):
            with self.subTest(partida=partida):
                self.assertEqual(partida.jugador, Color.Blanco)
                self.assertIsInstance(partida.estado_inicial, EstadoPosicion)
                self.assertIs(partida.tablero, partida.estado_inicial.tablero)
                self.assertIsNone(partida.estado_inicial.pieza)
                self.assertIsNone(partida.estado_inicial.origen)
                self.assertIsNone(partida.estado_inicial.destino)
                self.assertIsNone(partida.estado_inicial.estado_anterior)
                self.assertIsNone(partida.ultima_jugada)
                self.assertEqual(partida.contador_jugadas, 0)
                self.assertEqual(partida.registro_turnos, [])
                self.comprobar_linea(partida, "e2e4 e7e5 g1f3 b8c6",
                                     [(1, 1, 2), (2, 3, 4)])

    def test_estado_explicito_con_inicio_de_blancas(self):
        inicial = self.estado_tras("e2e4 e7e5")
        partida = Partida(estado_inicial=inicial)
        self.assertEqual(partida.jugador, Color.Blanco)
        self.comprobar_linea(partida, "g1f3 b8c6 f1c4 g8f6", [(1, 1, 2), (2, 3, 4)])

    def test_estado_explicito_con_inicio_de_negras(self):
        inicial = self.estado_tras("e2e4")
        partida = Partida(estado_inicial=inicial)
        self.assertEqual(partida.jugador, Color.Negro)
        self.comprobar_linea(partida, "e7e5 g1f3 b8c6 f1c4",
                             [(1, None, 1), (2, 2, 3), (3, 4, None)])

    def test_rechazos_no_consumen_turno_ni_alteran_historial(self):
        partida = Partida(estado_inicial=self.estado_tras("e2e4"))
        for intentos in (("g1f3", "e7e4"), ("b8c6", "f1g3")):
            tablero = partida.tablero
            firma = firma_tablero(tablero)
            ultima = partida.ultima_jugada
            numero = partida.contador_jugadas
            jugador = partida.jugador
            turnos = registro(partida)
            for intento in intentos:
                partida.procesar_solicitud(posicion(intento[:2]), posicion(intento[2:]))
                self.assertIs(partida.tablero, tablero)
                self.assertEqual(firma_tablero(tablero), firma)
                self.assertIs(partida.ultima_jugada, ultima)
                self.assertEqual(partida.contador_jugadas, numero)
                self.assertEqual(partida.jugador, jugador)
                self.assertEqual(registro(partida), turnos)
                if ultima:
                    self.assertIsNone(ultima.siguiente)
            if ultima is None:
                self.jugar(partida, "e7e5")

    def test_primera_jugada_captura_al_paso_de_ambos_colores(self):
        casos = (("e2e4 a7a6 e4e5 d7d5", "e5d6", "d5"),
                 ("a2a3 e7e5 a3a4 e5e4 d2d4", "e4d3", "d4"))
        for preparacion, movimiento, capturada in casos:
            with self.subTest(movimiento=movimiento):
                inicial = self.estado_tras(preparacion)
                partida = Partida(estado_inicial=inicial)
                jugada = self.jugar(partida, movimiento)
                self.assertIsInstance(jugada, CapturaAlPaso)
                self.assertIs(jugada.estado_posicion.estado_anterior, inicial)
                self.assertIsNone(jugada.anterior)
                self.assertIsNone(partida.tablero.pieza_en(posicion(capturada)))
                self.assertIsNotNone(inicial.tablero.pieza_en(posicion(capturada)))
                self.assertTrue(inicial.captura_al_paso_disponible)
                self.assertFalse(jugada.estado_posicion.captura_al_paso_disponible)
                turno = partida.registro_turnos[0]
                guardada = turno.jugada_blanco if jugada.pieza.color == Color.Blanco else turno.jugada_negro
                self.assertIs(guardada, jugada)

    def test_primera_jugada_enroque_desde_estado_proporcionado(self):
        inicial = self.estado_tras("e2e4 e7e5 g1f3 b8c6 f1c4 g8f6")
        partida = Partida(estado_inicial=inicial)
        jugada = self.jugar(partida, "e1g1")
        self.assertIsInstance(jugada, Enroque)
        self.assertIs(jugada.estado_posicion.estado_anterior, inicial)
        self.assertIsInstance(partida.tablero.pieza_en(posicion("g1")), Rey)
        self.assertIsInstance(partida.tablero.pieza_en(posicion("f1")), Torre)
        self.assertFalse(inicial.tablero.pieza_en(posicion("e1")).ha_movido)
        self.assertFalse(inicial.tablero.pieza_en(posicion("h1")).ha_movido)


if __name__ == "__main__":
    unittest.main()
