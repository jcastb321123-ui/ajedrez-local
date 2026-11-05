"""Resultados desde una raíz sin jugadas, incluida la edición de posiciones."""
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPartida, EstadoPosicion, MotivoRechazoMovimiento, Partida
from ajedrez.piezas import Alfil, Color, PeonBlanco, PeonNegro, Reina, Rey, Torre
from ajedrez.sesion import PiezaPromocion, SesionAnalisis
from pruebas import test_panel_analisis as apoyo_panel
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import enviar, nueva_sesion


def final_inicial(turno, *, mate, contador=0):
    ganador = Color.Blanco if turno is Color.Negro else Color.Negro
    if turno is Color.Negro:
        rey, dama, vencido = ('f6', 'g7', 'h8') if mate else ('f7', 'g6', 'h8')
    else:
        rey, dama, vencido = ('f3', 'g2', 'h1') if mate else ('f2', 'g3', 'h1')
    return preparar({rey: Rey(ganador), dama: Reina(ganador), vencido: Rey(turno)},
                    contador, turno)


class PruebasResultadoInicial(unittest.TestCase):
    def comprobar_raiz(self, estado, turno, esperado):
        antes = pickle.dumps(estado)
        partida = Partida(estado_inicial=estado, turno_inicial=turno)
        self.assertIs(partida.estado_partida, esperado)
        self.assertIs(partida.estado_inicial, estado)
        self.assertIs(partida.tablero, estado.tablero)
        self.assertIs(partida.jugador, turno)
        self.assertIsNone(partida.ultima_jugada)
        self.assertEqual(partida.contador_jugadas, 0)
        self.assertEqual(partida.registro_turnos, [])
        self.assertFalse(partida.promocion_pendiente)
        self.assertEqual(tuple(partida.iterar_estados()), (estado,))
        resultado = pickle.dumps(partida)
        partida.actualizar_estado()
        self.assertEqual(pickle.dumps(partida), resultado)
        self.assertEqual(pickle.dumps(estado), antes)
        return partida

    def test_mate_inicial_de_ambos_colores_y_prioridad_sobre_contador(self):
        for turno in Color:
            for contador in (0, 150):
                with self.subTest(turno=turno, contador=contador):
                    esperado = (EstadoPartida.VICTORIA_BLANCA if turno is Color.Negro
                                else EstadoPartida.VICTORIA_NEGRA)
                    self.comprobar_raiz(final_inicial(turno, mate=True, contador=contador),
                                        turno, esperado)

    def test_ahogado_inicial_de_ambos_colores(self):
        for turno in Color:
            with self.subTest(turno=turno):
                self.comprobar_raiz(final_inicial(turno, mate=False), turno, EstadoPartida.TABLAS)

    def test_jaque_con_salida_no_se_declara_mate(self):
        for turno, piezas, salida in (
            (Color.Negro, {'a1': Rey(Color.Blanco), 'h1': Torre(Color.Blanco),
                           'h8': Rey(Color.Negro)}, 'h8g8'),
            (Color.Blanco, {'a8': Rey(Color.Negro), 'h8': Torre(Color.Negro),
                            'h1': Rey(Color.Blanco)}, 'h1g1'),
        ):
            with self.subTest(turno=turno):
                estado = preparar(piezas, 0, turno)
                self.assertTrue(estado.tablero.el_rey_queda_en_jaque(turno))
                partida = self.comprobar_raiz(estado, turno, EstadoPartida.EN_CURSO)
                self.assertIsNone(mover(partida, salida))
                self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_contador_recibido_distingue_reclamacion_y_final_automatico(self):
        for turno in Color:
            for contador in (0, 99, 100, 149, 150, 151):
                with self.subTest(turno=turno, contador=contador):
                    estado = EstadoPosicion(jugadas_sin_captura_ni_peon=contador)
                    esperado = EstadoPartida.TABLAS if contador >= 150 else EstadoPartida.EN_CURSO
                    partida = self.comprobar_raiz(estado, turno, esperado)
                    self.assertIs(partida.tablas_por_cincuenta_movimientos_disponible(),
                                  100 <= contador < 150)

    def test_salida_por_captura_al_paso_evita_el_ahogado_inicial(self):
        for turno, piezas, peon, movimiento in (
            (Color.Blanco, {'a4': Rey(Color.Blanco), 'b5': PeonBlanco(),
                            'b6': Rey(Color.Negro), 'a5': PeonNegro(),
                            'c3': Torre(Color.Negro)}, 'a5', 'b5a6'),
            (Color.Negro, {'a5': Rey(Color.Negro), 'b4': PeonNegro(),
                           'b3': Rey(Color.Blanco), 'a4': PeonBlanco(),
                           'c6': Torre(Color.Blanco)}, 'a4', 'b4a3'),
        ):
            with self.subTest(turno=turno):
                sin_al_paso = preparar(piezas, 0, turno)
                self.comprobar_raiz(sin_al_paso, turno, EstadoPartida.TABLAS)
                estado = EditorPosicion(sin_al_paso, turno).construir_estado(
                    turno=turno, enroques=set(), peon_al_paso=posicion(peon))
                partida = self.comprobar_raiz(estado, turno, EstadoPartida.EN_CURSO)
                self.assertIsNone(mover(partida, movimiento))
                self.assertIsNone(partida.tablero.pieza_en(posicion(peon)))

    def test_promocion_como_unica_salida_no_se_aplica_al_evaluar(self):
        estado = preparar({'a1': Rey(Color.Blanco), 'h7': PeonBlanco(),
                           'c2': Rey(Color.Negro), 'b3': Alfil(Color.Negro)}, 0)
        self.comprobar_raiz(estado, Color.Blanco, EstadoPartida.EN_CURSO)
        sesion = SesionAnalisis(estado, Color.Blanco)
        self.assertIsNone(sesion.solicitar_movimiento(posicion('h7'), posicion('h8')))
        self.assertIsNotNone(sesion.jugada_pendiente)
        self.assertIsNone(sesion.partida.ultima_jugada)
        sesion.elegir_promocion(PiezaPromocion.REINA)
        self.assertEqual(sesion.partida.contador_jugadas, 1)
        self.assertIsInstance(sesion.estado_actual.tablero.pieza_en(posicion('h8')), Reina)

    def test_raiz_historica_en_mate_infiere_turno_sin_arrastrar_registro(self):
        original = Partida()
        for movimiento in ('f2f3', 'e7e5', 'g2g4', 'd8h4'):
            self.assertIsNone(mover(original, movimiento))
        antes = pickle.dumps(original)
        raiz = original.ultima_jugada.estado_posicion
        partida = Partida(estado_inicial=raiz)
        self.assertIs(partida.estado_partida, EstadoPartida.VICTORIA_NEGRA)
        self.assertIs(partida.jugador, Color.Blanco)
        self.assertIsNone(partida.ultima_jugada)
        self.assertEqual(partida.contador_jugadas, 0)
        self.assertEqual(partida.apariciones_posicion_actual, 1)
        self.assertEqual(pickle.dumps(original), antes)

    def test_la_sesion_local_reconoce_el_final_desde_la_raiz(self):
        for estado, turno, movimiento in (
            (final_inicial(Color.Negro, mate=True), Color.Negro, 'h8g8'),
            (final_inicial(Color.Blanco, mate=False), Color.Blanco, 'h1g1'),
            (EstadoPosicion(jugadas_sin_captura_ni_peon=150), Color.Blanco, 'g1f3'),
        ):
            with self.subTest(turno=turno, movimiento=movimiento):
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(estado_inicial=estado, turno_inicial=turno)
                antes = pickle.dumps(sesion.partida)
                self.assertIs(enviar(sesion, movimiento), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
                self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_el_analisis_puede_continuar_desde_tablas_iniciales(self):
        original = Partida(estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=150))
        antes = pickle.dumps(original)
        analisis = SesionAnalisis(original.estado_inicial, Color.Blanco)
        self.assertIs(analisis.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(analisis.solicitar_movimiento(posicion('g1'), posicion('f3')))
        self.assertEqual(analisis.partida.contador_jugadas, 1)
        self.assertIs(analisis.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(pickle.dumps(original), antes)


class PruebasResultadoInicialEnEditor(unittest.TestCase):
    setUp = apoyo_panel.PruebasPanelAnalisis.setUp
    tearDown = apoyo_panel.PruebasPanelAnalisis.tearDown
    panel = apoyo_panel.PruebasPanelAnalisis.panel

    def test_aplicar_posicion_terminal_en_editor_respeta_partida_original(self):
        original = pickle.dumps(self.sesion.partida)
        panel = self.panel()
        for mate in (True, False):
            with self.subTest(mate=mate):
                panel.iniciar_edicion()
                panel.editor.vaciar()
                rey, dama = ('f6', 'g7') if mate else ('f7', 'g6')
                for casilla, nombre, color in ((rey, 'rey', Color.Blanco),
                                                (dama, 'dama', Color.Blanco),
                                                ('h8', 'rey', Color.Negro)):
                    panel.editor.colocar(posicion(casilla), nombre, color)
                panel.turno_edicion.set('Negro')
                for variable in panel.enroques_edicion.values():
                    variable.set(False)
                panel.aplicar_edicion()
                self.assertIsNone(panel.editor, panel.mensaje.get())
                esperado = EstadoPartida.VICTORIA_BLANCA if mate else EstadoPartida.TABLAS
                self.assertIs(panel.sesion.partida.estado_partida, esperado)
                self.assertIs(panel.estado_mostrado, panel.sesion.estado_actual)
                self.assertEqual(panel.sesion.partida.contador_jugadas, 0)
                self.assertEqual(len(panel.casillero.canvas.find_withtag('pieza')), 3)
                self.assertEqual(pickle.dumps(self.sesion.partida), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
