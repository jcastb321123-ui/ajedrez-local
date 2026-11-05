"""Invariantes de finalización y promoción mediante recorridos válidos."""
import pickle
import unittest
from unittest.mock import patch

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import Partida, EstadoPartida, MotivoRechazoMovimiento
from ajedrez.piezas import Color, Rey, Reina, PeonBlanco
from ajedrez.sesion import SesionAnalisis, PiezaPromocion
from pruebas.test_analisis_partida import estado_minimo, mover, posicion
from pruebas import test_panel_analisis as panel_tests


class PruebasInvariantesFinalizacion(unittest.TestCase):
    def preparar_posicion(self, piezas):
        # El editor prepara también los derechos de enroque y ha_movido.
        editor = EditorPosicion(estado_minimo(piezas), Color.Blanco)
        return editor.construir_estado(turno=Color.Blanco, enroques=set())

    def comprobar_final_sin_movimientos(self, partida, estado):
        self.assertIs(partida.estado_partida, estado)
        self.assertFalse(partida.promocion_pendiente)
        antes = pickle.dumps(partida)
        origenes = [casilla for casilla, pieza in partida.tablero.casillas.items()
                    if pieza is not None and pieza.color == partida.jugador]
        destinos = tuple(partida.tablero.casillas)
        for origen in origenes:
            for destino in destinos:
                with self.subTest(origen=origen, destino=destino):
                    resultado = partida.procesar_solicitud(origen, destino)
                    self.assertIsInstance(resultado, MotivoRechazoMovimiento)
                    self.assertFalse(partida.promocion_pendiente)
        self.assertEqual(pickle.dumps(partida), antes)
        partida.actualizar_estado()
        self.assertEqual(pickle.dumps(partida), antes)

    def test_mate_real_no_admite_movimientos_ni_cambia_al_recalcular(self):
        partida = Partida()
        for notacion in ('f2f3', 'e7e5', 'g2g4', 'd8h4'):
            self.assertIsNone(mover(partida, notacion))
        self.comprobar_final_sin_movimientos(partida, EstadoPartida.VICTORIA_NEGRA)

    def test_ahogado_real_no_admite_movimientos_ni_cambia_al_recalcular(self):
        estado = self.preparar_posicion({'c6': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
                                'c7': Reina(Color.Blanco)})
        partida = Partida(estado_inicial=estado, turno_inicial=Color.Blanco)
        self.assertIsNone(mover(partida, 'c7b6'))
        self.comprobar_final_sin_movimientos(partida, EstadoPartida.TABLAS)

    def test_resultado_de_promocion_depende_de_la_eleccion_confirmada(self):
        casos = (
            ('h6', 'h8', 'f7', 'f8', PiezaPromocion.REINA, EstadoPartida.VICTORIA_BLANCA),
            ('h6', 'h8', 'f7', 'f8', PiezaPromocion.CABALLO, EstadoPartida.TABLAS),
            ('c6', 'a7', 'c7', 'c8', PiezaPromocion.REINA, EstadoPartida.TABLAS),
            ('c6', 'a7', 'c7', 'c8', PiezaPromocion.TORRE, EstadoPartida.EN_CURSO),
        )
        for rey_blanco, rey_negro, origen, destino, pieza, resultado in casos:
            with self.subTest(origen=origen, pieza=pieza):
                estado = self.preparar_posicion({rey_blanco: Rey(Color.Blanco),
                                        rey_negro: Rey(Color.Negro),
                                        origen: PeonBlanco()})
                sesion = SesionAnalisis(estado, Color.Blanco)
                partida = sesion.partida
                with patch.object(partida, 'actualizar_estado',
                                  wraps=partida.actualizar_estado) as evaluar:
                    self.assertIsNone(sesion.solicitar_movimiento(posicion(origen), posicion(destino)))
                    evaluar.assert_not_called()
                    self.assertIsNotNone(sesion.jugada_pendiente)
                    self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
                    self.assertEqual(partida.contador_jugadas, 0)
                    self.assertIsNone(partida.ultima_jugada)
                    self.assertIsInstance(partida.tablero.pieza_en(posicion(origen)), PeonBlanco)
                    self.assertIsNone(partida.tablero.pieza_en(posicion(destino)))
                    self.assertIs(sesion.solicitar_movimiento(posicion(rey_blanco), posicion('e4')),
                                  MotivoRechazoMovimiento.PROMOCION_PENDIENTE)
                    evaluar.assert_not_called()
                    sesion.elegir_promocion(pieza)
                    evaluar.assert_called_once_with()
                    self.assertIsNone(sesion.jugada_pendiente)
                    self.assertFalse(partida.promocion_pendiente)
                    self.assertEqual(partida.contador_jugadas, 1)
                    self.assertIs(partida.estado_partida, resultado)
                if resultado is not EstadoPartida.EN_CURSO:
                    if pieza is PiezaPromocion.CABALLO:
                        # Material insuficiente: aún hay movimientos legales para analizar.
                        antes = pickle.dumps(partida)
                        partida.actualizar_estado()
                        self.assertEqual(pickle.dumps(partida), antes)
                    else:
                        self.comprobar_final_sin_movimientos(partida, resultado)

    def test_revision_tras_mate_real_crea_variante_sin_modificar_original(self):
        interfaz = panel_tests.PruebasPanelAnalisis('test_contenedor_comun_no_reempaqueta_al_padre')
        self.addCleanup(interfaz.doCleanups)
        interfaz.setUp()
        for notacion in ('f2f3', 'e7e5', 'g2g4', 'd8h4'):
            interfaz.mover(interfaz.vista, notacion)
        partida = interfaz.sesion.partida
        self.assertIs(partida.estado_partida, EstadoPartida.VICTORIA_NEGRA)
        antes = pickle.dumps(partida)
        interfaz.vista.retroceder_movimiento()
        interfaz.mover(interfaz.vista, 'b8c6')
        variante = interfaz.vista.sesion_movimientos.partida
        self.assertIsNot(variante, partida)
        self.assertEqual(variante.ultima_jugada.origen, posicion('b8'))
        self.assertEqual(variante.ultima_jugada.destino, posicion('c6'))
        self.assertEqual(pickle.dumps(partida), antes)
        self.assertEqual(interfaz.vista.indicador_estado_partida.cget('text'), 'Victoria de negras')
        interfaz.tearDown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
