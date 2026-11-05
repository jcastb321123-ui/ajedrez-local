"""Contrato del estado inicial de Jugada, sin modificar el modelo probado."""

import unittest

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.partida import CapturaAlPaso, Enroque, EstadoPosicion, Jugada, Partida
from ajedrez.piezas import Color, PeonBlanco, PeonNegro, Rey, Torre
from ajedrez.tablero import Tablero


class PruebasEstadosIniciales(unittest.TestCase):
    def test_primera_jugada_crea_raiz_sin_movimiento(self):
        jugada = Jugada(1, (1, 4), (3, 4), None)
        raiz = jugada.estado_posicion.estado_anterior

        self.assertTrue(jugada.estado_posicion.movimiento_valido)
        self.assertIsNone(jugada.anterior)
        self.assertIsNone(raiz.estado_anterior)
        self.assertIsNone(raiz.origen)
        self.assertIsNone(raiz.destino)
        self.assertIsNone(raiz.pieza)
        self.assertIsNone(raiz.movimiento_valido)
        self.assertIsInstance(raiz.tablero.pieza_en((1, 4)), PeonBlanco)
        self.assertIsNone(raiz.tablero.pieza_en((3, 4)))
        self.assertFalse(raiz.tablero.pieza_en((1, 4)).ha_movido)
        self.assertTrue(jugada.pieza.ha_movido)
        self.assertIsNot(jugada.tablero, raiz.tablero)
        self.assertIsNot(jugada.pieza, raiz.tablero.pieza_en((1, 4)))

    def test_estado_proporcionado_conserva_disposicion_y_datos_previos(self):
        tablero = Tablero()
        tablero.trasladar_pieza((1, 4), (3, 4))
        tablero.pieza_en((3, 4)).movimiento_realizado()
        tablero.posicion_de_captura_al_paso = (3, 4)
        raiz = EstadoPosicion(tablero=tablero)

        jugada = Jugada(1, (7, 6), (5, 5), None, estado_inicial=raiz)

        self.assertTrue(jugada.estado_posicion.movimiento_valido)
        self.assertIs(jugada.estado_posicion.estado_anterior, raiz)
        self.assertIsNone(jugada.anterior)
        self.assertIsNone(jugada.tablero.pieza_en((1, 4)))
        self.assertTrue(jugada.tablero.pieza_en((3, 4)).ha_movido)
        self.assertTrue(raiz.captura_al_paso_disponible)
        self.assertEqual(raiz.tablero.posicion_de_captura_al_paso, (3, 4))
        self.assertIsNotNone(raiz.tablero.pieza_en((7, 6)))
        self.assertIsNone(raiz.tablero.pieza_en((5, 5)))
        self.assertIsNot(raiz.tablero, tablero)
        self.assertIsNot(jugada.tablero, raiz.tablero)
        self.assertIsNot(jugada.tablero.pieza_en((3, 4)), raiz.tablero.pieza_en((3, 4)))

    def test_jugada_anterior_tiene_prioridad_sobre_estado_inicial(self):
        primera = Jugada(1, (1, 4), (3, 4), None)
        alternativo = Tablero()
        alternativo.colocar(None, (6, 4))
        raiz_alternativa = EstadoPosicion(tablero=alternativo)

        segunda = Jugada(2, (6, 4), (4, 4), primera,
                         estado_inicial=raiz_alternativa)

        self.assertTrue(segunda.estado_posicion.movimiento_valido)
        self.assertIs(segunda.anterior, primera)
        self.assertIs(segunda.estado_posicion.estado_anterior, primera.estado_posicion)
        self.assertIsNotNone(segunda.tablero.pieza_en((3, 4)))
        self.assertIsNone(primera.tablero.pieza_en((4, 4)))
        self.assertFalse(primera.tablero.pieza_en((6, 4)).ha_movido)
        self.assertTrue(segunda.pieza.ha_movido)
        # El enlace hacia delante se establece al registrar, no al proponer.
        self.assertIsNone(primera.siguiente)

    def test_primera_jugada_invalida_tiene_valor_false(self):
        jugada = Jugada(1, (1, 4), (4, 4), None)
        self.assertIs(jugada.estado_posicion.movimiento_valido, False)
        self.assertIsNone(jugada.estado_posicion.estado_anterior.movimiento_valido)
        self.assertIsNotNone(jugada.tablero.pieza_en((1, 4)))
        self.assertIsNone(jugada.tablero.pieza_en((4, 4)))

    def test_respetar_ha_movido_del_peon_en_estado_proporcionado(self):
        tablero = Tablero()
        tablero.pieza_en((1, 4)).movimiento_realizado()
        raiz = EstadoPosicion(tablero=tablero)

        doble = Jugada(1, (1, 4), (3, 4), None, estado_inicial=raiz)
        simple = Jugada(1, (1, 4), (2, 4), None, estado_inicial=raiz)

        self.assertIs(doble.estado_posicion.movimiento_valido, False)
        self.assertIs(simple.estado_posicion.movimiento_valido, True)
        self.assertTrue(raiz.tablero.pieza_en((1, 4)).ha_movido)
        self.assertIsNone(raiz.tablero.pieza_en((2, 4)))

    def test_raices_predeterminadas_independientes(self):
        primera = Jugada(1, (1, 4), (3, 4), None)
        otra = Jugada(1, (1, 3), (3, 3), None)
        raiz_primera = primera.estado_posicion.estado_anterior
        raiz_otra = otra.estado_posicion.estado_anterior

        self.assertIsNot(raiz_primera, raiz_otra)
        self.assertIsNot(raiz_primera.tablero, raiz_otra.tablero)
        self.assertIsNot(raiz_primera.tablero.pieza_en((0, 4)),
                         raiz_otra.tablero.pieza_en((0, 4)))

    def test_estado_inicial_solo_se_admite_por_nombre(self):
        raiz = EstadoPosicion(tablero=Tablero())
        with self.assertRaises(TypeError):
            Jugada(1, (1, 4), (3, 4), None, raiz)

    def test_enroque_desde_raiz_respeta_historial_de_rey_y_torre(self):
        for rey_movido, torre_movida in ((False, False), (True, False), (False, True)):
            with self.subTest(rey_movido=rey_movido, torre_movida=torre_movida):
                tablero = Tablero()
                for posicion in tablero.casillas:
                    tablero.colocar(None, posicion)
                rey = Rey(Color.Blanco)
                torre = Torre(Color.Blanco)
                if rey_movido:
                    rey.movimiento_realizado()
                if torre_movida:
                    torre.movimiento_realizado()
                tablero.colocar(rey, (0, 4))
                tablero.colocar(torre, (0, 7))
                tablero.colocar(Rey(Color.Negro), (7, 4))
                raiz = EstadoPosicion(tablero=tablero)

                jugada = Enroque(1, (0, 4), (0, 6), None, estado_inicial=raiz)

                self.assertIs(jugada.estado_posicion.movimiento_valido,
                              not rey_movido and not torre_movida)
                self.assertEqual(raiz.tablero.pieza_en((0, 4)).ha_movido, rey_movido)
                self.assertEqual(raiz.tablero.pieza_en((0, 7)).ha_movido, torre_movida)
                if jugada.estado_posicion.movimiento_valido:
                    self.assertIsInstance(jugada.tablero.pieza_en((0, 6)), Rey)
                    self.assertIsInstance(jugada.tablero.pieza_en((0, 5)), Torre)
                    self.assertTrue(jugada.tablero.pieza_en((0, 6)).ha_movido)
                    self.assertTrue(jugada.tablero.pieza_en((0, 5)).ha_movido)

class PruebasCapturaAlPasoConEstadoInicial(unittest.TestCase):
    @staticmethod
    def preparar_estado(blancas=True, disponible=True):
        tablero = Tablero()
        for posicion in tablero.casillas:
            tablero.colocar(None, posicion)
        tablero.colocar(Rey(Color.Blanco), (0, 4))
        tablero.colocar(Rey(Color.Negro), (7, 4))
        if blancas:
            origen, destino, capturada = (4, 4), (5, 3), (4, 3)
            atacante, victima = PeonBlanco(), PeonNegro()
        else:
            origen, destino, capturada = (3, 4), (2, 3), (3, 3)
            atacante, victima = PeonNegro(), PeonBlanco()
        atacante.movimiento_realizado()
        victima.movimiento_realizado()
        tablero.colocar(atacante, origen)
        tablero.colocar(victima, capturada)
        tablero.posicion_de_captura_al_paso = capturada if disponible else None
        return EstadoPosicion(tablero=tablero), origen, destino, capturada

    def test_captura_como_primera_jugada_de_ambos_colores(self):
        for blancas in (True, False):
            with self.subTest(blancas=blancas):
                raiz, origen, destino, capturada = self.preparar_estado(blancas)
                atacante_previo = raiz.tablero.pieza_en(origen)
                victima_previa = raiz.tablero.pieza_en(capturada)

                jugada = CapturaAlPaso(1, origen, destino, None, estado_inicial=raiz)

                self.assertTrue(jugada.estado_posicion.movimiento_valido)
                self.assertIsNone(jugada.anterior)
                self.assertIs(jugada.estado_posicion.estado_anterior, raiz)
                self.assertIsNone(jugada.tablero.pieza_en(origen))
                self.assertIsNone(jugada.tablero.pieza_en(capturada))
                self.assertIs(jugada.tablero.pieza_en(destino), jugada.pieza)
                self.assertIsNot(jugada.pieza, atacante_previo)
                self.assertEqual(jugada.pieza.color, atacante_previo.color)
                self.assertIs(raiz.tablero.pieza_en(origen), atacante_previo)
                self.assertIs(raiz.tablero.pieza_en(capturada), victima_previa)
                self.assertIsNone(raiz.tablero.pieza_en(destino))
                # La actualización corresponde al registro de la jugada aceptada.
                jugada.estado_posicion._actualizar_captura_al_paso()
                self.assertFalse(jugada.estado_posicion.captura_al_paso_disponible)
                self.assertIsNone(jugada.tablero.posicion_de_captura_al_paso)
                self.assertTrue(raiz.captura_al_paso_disponible)
                self.assertEqual(raiz.tablero.posicion_de_captura_al_paso, capturada)

    def test_distribucion_sin_disponibilidad_no_permite_captura(self):
        for blancas in (True, False):
            with self.subTest(blancas=blancas):
                raiz, origen, destino, capturada = self.preparar_estado(
                    blancas, disponible=False
                )
                jugada = CapturaAlPaso(1, origen, destino, None, estado_inicial=raiz)

                self.assertIs(jugada.estado_posicion.movimiento_valido, False)
                self.assertIsNotNone(jugada.tablero.pieza_en(origen))
                self.assertIsNotNone(jugada.tablero.pieza_en(capturada))
                self.assertIsNone(jugada.tablero.pieza_en(destino))

    def test_captura_inicial_que_descubre_jaque_se_rechaza_sin_alterar_raiz(self):
        raiz, origen, destino, capturada = self.preparar_estado()
        tablero = raiz.tablero
        tablero.trasladar_pieza((7, 4), (7, 0))
        tablero.colocar(Torre(Color.Negro), (7, 4))
        self.assertFalse(tablero.el_rey_queda_en_jaque(Color.Blanco))

        jugada = CapturaAlPaso(1, origen, destino, None, estado_inicial=raiz)

        self.assertIs(jugada.estado_posicion.movimiento_valido, False)
        self.assertIsInstance(tablero.pieza_en(origen), PeonBlanco)
        self.assertIsInstance(tablero.pieza_en(capturada), PeonNegro)
        self.assertIsNone(tablero.pieza_en(destino))
        self.assertTrue(raiz.captura_al_paso_disponible)
        self.assertFalse(tablero.el_rey_queda_en_jaque(Color.Blanco))

    def test_captura_tras_jugadas_registradas_de_ambos_colores(self):
        casos = (
            ([(1, 4), (6, 0), (3, 4), (6, 3), (4, 4)],
             [(3, 4), (5, 0), (4, 4), (4, 3), (5, 3)], (4, 3)),
            ([(1, 0), (6, 4), (2, 0), (4, 4), (1, 3), (3, 4)],
             [(2, 0), (4, 4), (3, 0), (3, 4), (3, 3), (2, 3)], (3, 3)),
        )
        for origenes, destinos, capturada in casos:
            with self.subTest(destino=destinos[-1]):
                partida = Partida()
                for numero, (origen, destino) in enumerate(zip(origenes, destinos), 1):
                    partida.procesar_solicitud(origen, destino)
                    self.assertEqual(partida.contador_jugadas, numero)
                ultima = partida.ultima_jugada
                self.assertIsInstance(ultima, CapturaAlPaso)
                self.assertIs(ultima.estado_posicion.estado_anterior,
                              ultima.anterior.estado_posicion)
                self.assertIsNone(partida.tablero.pieza_en(capturada))
                self.assertIsNotNone(ultima.anterior.tablero.pieza_en(capturada))
                self.assertFalse(ultima.estado_posicion.captura_al_paso_disponible)

    def test_disponibilidad_caduca_tras_otro_movimiento_aceptado(self):
        partida = Partida()
        movimientos = (
            ((1, 4), (3, 4)), ((6, 0), (5, 0)),
            ((3, 4), (4, 4)), ((6, 3), (4, 3)),
        )
        for numero, (origen, destino) in enumerate(movimientos, 1):
            partida.procesar_solicitud(origen, destino)
            self.assertEqual(partida.contador_jugadas, numero)
        disponible = partida.ultima_jugada.estado_posicion
        self.assertTrue(disponible.captura_al_paso_disponible)

        partida.procesar_solicitud((0, 6), (2, 5))
        self.assertEqual(partida.contador_jugadas, 5)
        self.assertFalse(partida.ultima_jugada.estado_posicion.captura_al_paso_disponible)
        partida.procesar_solicitud((7, 1), (5, 2))
        self.assertEqual(partida.contador_jugadas, 6)
        ultima = partida.ultima_jugada
        tablero = partida.tablero
        partida.procesar_solicitud((4, 4), (5, 3))

        self.assertEqual(partida.contador_jugadas, 6)
        self.assertIs(partida.ultima_jugada, ultima)
        self.assertIs(partida.tablero, tablero)
        self.assertIsNotNone(tablero.pieza_en((4, 3)))
        self.assertIsNotNone(tablero.pieza_en((4, 4)))
        self.assertTrue(disponible.captura_al_paso_disponible)


if __name__ == "__main__":
    unittest.main()
