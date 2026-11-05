"""Tablas a los 150 movimientos individuales y continuidad del análisis."""
import pickle
import unittest
from unittest.mock import patch

from ajedrez.analisis_partida import AnalisisPartida
from ajedrez.partida import EstadoPartida, EstadoPosicion, MotivoRechazoMovimiento, Partida
from ajedrez.piezas import Caballo, Color, Reina, Rey, Torre
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import enviar, nueva_sesion


class PruebasRegla75Movimientos(unittest.TestCase):
    def test_cien_y_ciento_cuarenta_y_nueve_no_finalizan_ciento_cincuenta_si(self):
        for contador, esperado in ((99, EstadoPartida.EN_CURSO),
                                   (148, EstadoPartida.EN_CURSO),
                                   (149, EstadoPartida.TABLAS)):
            with self.subTest(contador=contador):
                partida = Partida(estado_inicial=EstadoPosicion(
                    jugadas_sin_captura_ni_peon=contador))
                self.assertIsNone(mover(partida, 'g1f3'))
                self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon,
                                 contador + 1)
                self.assertIs(partida.estado_partida, esperado)

    def test_mate_en_el_movimiento_ciento_cincuenta_tiene_prioridad(self):
        for color, piezas, movimiento, esperado in (
            (Color.Blanco, {'f6': Rey(Color.Blanco), 'g6': Reina(Color.Blanco),
                            'h8': Rey(Color.Negro)}, 'g6g7', EstadoPartida.VICTORIA_BLANCA),
            (Color.Negro, {'f3': Rey(Color.Negro), 'g3': Reina(Color.Negro),
                           'h1': Rey(Color.Blanco)}, 'g3g2', EstadoPartida.VICTORIA_NEGRA)):
            with self.subTest(color=color):
                partida = Partida(estado_inicial=preparar(piezas, 149, color),
                                  turno_inicial=color)
                self.assertIsNone(mover(partida, movimiento))
                self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 150)
                self.assertIs(partida.estado_partida, esperado)

    def test_peon_y_captura_reinician_la_cuenta_al_borde_del_limite(self):
        partida = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=149))
        self.assertIsNone(mover(partida, 'e2e4'))
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 0)
        self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
        partida = Partida(estado_inicial=preparar(
            {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
             'a2': Torre(Color.Blanco), 'a7': Caballo(Color.Negro)}, 149))
        self.assertIsNone(mover(partida, 'a2a7'))
        self.assertEqual(partida.ultima_jugada.estado_posicion.jugadas_sin_captura_ni_peon, 0)
        self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_sesion_local_rechaza_tras_tablas_sin_construir_otra_jugada(self):
        sesion = nueva_sesion()
        # La sesión local aún no recibe una posición inicial en su constructor.
        sesion.juego._partida = Partida(estado_inicial=EstadoPosicion(
            jugadas_sin_captura_ni_peon=149))
        self.assertIsNone(enviar(sesion, 'g1f3'))
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        antes = pickle.dumps(sesion.partida)
        with patch.object(sesion.partida, 'procesar_solicitud',
                          wraps=sesion.partida.procesar_solicitud) as procesar:
            self.assertIs(enviar(sesion, 'g8f6'), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
            procesar.assert_not_called()
        self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_bloqueo_local_tras_abandono_o_acuerdo(self):
        for cierre in ('abandono_blanco', 'abandono_negro', 'acuerdo'):
            with self.subTest(cierre=cierre):
                sesion = nueva_sesion()
                for movimiento in ('e2e4', 'e7e5'):
                    self.assertIsNone(enviar(sesion, movimiento))
                if cierre == 'acuerdo':
                    sesion.proponer_tablas(Color.Blanco)
                    sesion.responder_propuesta_tablas(Color.Negro, True)
                    esperado = EstadoPartida.TABLAS
                else:
                    color = Color.Blanco if cierre == 'abandono_blanco' else Color.Negro
                    sesion.solicitar_abandono(color)
                    esperado = (EstadoPartida.VICTORIA_NEGRA if color is Color.Blanco
                                else EstadoPartida.VICTORIA_BLANCA)
                self.assertIs(sesion.partida.estado_partida, esperado)
                antes = pickle.dumps(sesion.partida)
                self.assertIs(enviar(sesion, 'g1f3'), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
                self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_revision_desde_partida_finalizada_conserva_original(self):
        original = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=149))
        self.assertIsNone(mover(original, 'g1f3'))
        self.assertIs(original.estado_partida, EstadoPartida.TABLAS)
        antes = pickle.dumps(original)
        analisis = AnalisisPartida(original)
        self.assertIsNone(analisis.solicitar_movimiento(
            original.ultima_jugada.estado_posicion, posicion('g8'), posicion('f6')))
        variante = analisis.sesion_hipotetica
        self.assertIsNot(variante.partida, original)
        self.assertEqual(variante.estado_actual.jugadas_sin_captura_ni_peon, 151)
        self.assertEqual(pickle.dumps(original), antes)
        self.assertIs(variante.partida.estado_partida, EstadoPartida.TABLAS)

    def test_variante_que_alcanza_tablas_admite_seguir_sin_perder_el_resultado(self):
        original = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=148))
        self.assertIsNone(mover(original, 'g1f3'))
        antes = pickle.dumps(original)
        analisis = AnalisisPartida(original)
        self.assertIsNone(analisis.solicitar_movimiento(
            original.ultima_jugada.estado_posicion, posicion('g8'), posicion('f6')))
        variante = analisis.sesion_hipotetica
        self.assertIs(variante.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(analisis.solicitar_movimiento(
            variante.estado_actual, posicion('b1'), posicion('c3')))
        self.assertIs(analisis.sesion_hipotetica, variante)
        self.assertEqual(variante.estado_actual.jugadas_sin_captura_ni_peon, 151)
        self.assertEqual(pickle.dumps(original), antes)
        self.assertIs(variante.partida.estado_partida, EstadoPartida.TABLAS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
