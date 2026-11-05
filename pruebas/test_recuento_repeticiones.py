"""Recuento de posiciones registradas y consulta de la posición vigente."""
import pickle
import unittest

from ajedrez.partida import Partida
from ajedrez.piezas import Color, PeonBlanco, Rey
from ajedrez.sesion import SesionAnalisis, PiezaPromocion
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar


CICLO_BLANCAS = ("g1f3", "g8f6", "f3g1", "f6g8")
CICLO_NEGRAS = ("g8f6", "g1f3", "f6g8", "f3g1")


class PruebasRecuentoRepeticiones(unittest.TestCase):
    def jugar(self, partida, movimientos):
        for movimiento in movimientos:
            self.assertIsNone(mover(partida, movimiento))

    def comprobar_actual(self, partida, esperado):
        antes = pickle.dumps(partida)
        self.assertEqual(partida.apariciones_posicion_actual, esperado)
        self.assertEqual(pickle.dumps(partida), antes)

    def comprobar_consulta(self, partida, estado, turno, esperado):
        antes = pickle.dumps((partida, estado))
        self.assertEqual(
            partida._contar_apariciones_posicion(estado, turno), esperado
        )
        self.assertEqual(pickle.dumps((partida, estado)), antes)

    def test_raiz_cuenta_una_vez_con_cualquiera_de_los_turnos(self):
        for turno in Color:
            with self.subTest(turno=turno):
                partida = Partida(turno_inicial=turno)
                self.comprobar_actual(partida, 1)

    def test_ciclos_cuentan_raiz_y_estados_intermedios_con_ambos_turnos(self):
        for turno, ciclo in ((Color.Blanco, CICLO_BLANCAS),
                             (Color.Negro, CICLO_NEGRAS)):
            with self.subTest(turno=turno):
                partida = Partida(turno_inicial=turno)
                for repeticion in range(2):
                    for indice, movimiento in enumerate(ciclo):
                        self.jugar(partida, (movimiento,))
                        esperado = repeticion + (2 if indice == 3 else 1)
                        self.comprobar_actual(partida, esperado)

    def test_consulta_historica_independiente_de_la_posicion_vigente(self):
        partida = Partida()
        raiz = partida.estado_inicial
        self.jugar(partida, CICLO_BLANCAS * 2 + ("e2e4",))
        self.comprobar_actual(partida, 1)
        self.comprobar_consulta(partida, raiz, Color.Blanco, 3)

    def test_estado_no_registrado_o_turno_distinto_devuelven_cero(self):
        partida = Partida()
        otra = Partida()
        self.jugar(otra, ("e2e4",))
        self.comprobar_consulta(
            partida, otra.ultima_jugada.estado_posicion, Color.Negro, 0
        )
        self.comprobar_consulta(partida, partida.estado_inicial, Color.Negro, 0)

    def test_jugada_provisional_no_se_suma_como_aparicion_registrada(self):
        partida = Partida()
        self.jugar(partida, CICLO_BLANCAS + CICLO_BLANCAS[:3])
        antes = pickle.dumps(partida)
        propuesta = partida._nueva_jugada(posicion("f6"), posicion("g8"))
        self.assertTrue(propuesta.estado_posicion.movimiento_valido)
        self.comprobar_consulta(
            partida, propuesta.estado_posicion, Color.Blanco, 2
        )
        self.assertEqual(pickle.dumps(partida), antes)
        self.jugar(partida, ("f6g8",))
        self.comprobar_actual(partida, 3)

    def test_analisis_cuenta_solo_su_propia_linea(self):
        original = Partida()
        self.jugar(original, CICLO_BLANCAS * 2)
        antes = pickle.dumps(original)
        sesion = SesionAnalisis(
            original.ultima_jugada.estado_posicion, original.jugador
        )
        self.comprobar_actual(sesion.partida, 1)
        for movimiento in CICLO_BLANCAS:
            self.assertIsNone(sesion.solicitar_movimiento(
                posicion(movimiento[:2]), posicion(movimiento[2:])
            ))
        self.comprobar_actual(sesion.partida, 2)
        self.comprobar_actual(original, 3)
        self.assertEqual(pickle.dumps(original), antes)

    def test_promocion_pendiente_no_se_cuenta_hasta_confirmarla(self):
        raiz = preparar(
            {"h1": Rey(Color.Blanco), "h8": Rey(Color.Negro), "a7": PeonBlanco()},
            0,
        )
        sesion = SesionAnalisis(raiz, Color.Blanco)
        vigente = sesion.estado_actual
        self.assertIsNone(sesion.solicitar_movimiento(posicion("a7"), posicion("a8")))
        self.assertIsNotNone(sesion.jugada_pendiente)
        self.assertIs(sesion.estado_actual, vigente)
        self.comprobar_actual(sesion.partida, 1)
        self.comprobar_consulta(
            sesion.partida, sesion.jugada_pendiente.estado_posicion, Color.Negro, 0
        )
        sesion.elegir_promocion(PiezaPromocion.REINA)
        self.assertIsNone(sesion.jugada_pendiente)
        self.comprobar_actual(sesion.partida, 1)


if __name__ == "__main__":
    unittest.main()
