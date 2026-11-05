
"""Contador por estado para las reglas de 50 y 75 movimientos.

Cada jugada contada es el movimiento de un solo jugador.
Estas pruebas verifican el contador; no declaran todavía resultados por tablas.
"""
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPosicion, Partida, Jugada, Enroque, CapturaAlPaso, MotivoRechazoMovimiento
from ajedrez.piezas import Color, Rey, Torre, Caballo, PeonBlanco, PeonNegro
from ajedrez.sesion import SesionAnalisis, PiezaPromocion
from pruebas.test_analisis_partida import estado_minimo, posicion, mover


def preparar(piezas, contador, turno=Color.Blanco, enroques=None):
    estado = EditorPosicion(estado_minimo(piezas), turno).construir_estado(
        turno=turno, enroques=set() if enroques is None else enroques)
    return EstadoPosicion(tablero=estado.tablero, jugadas_sin_captura_ni_peon=contador)


def estado_vigente(partida):
    return partida.estado_inicial if partida.ultima_jugada is None else partida.ultima_jugada.estado_posicion


class PruebasContadorTablas(unittest.TestCase):
    def jugar(self, partida, movimiento):
        self.assertIsNone(mover(partida, movimiento))
        return estado_vigente(partida)

    def test_valor_inicial_y_continuacion_desde_ambos_turnos(self):
        self.assertEqual(EstadoPosicion().jugadas_sin_captura_ni_peon, 0)
        for contador in (0, 99, 149):
            for turno, movimiento in ((Color.Blanco, 'g1f3'), (Color.Negro, 'g8f6')):
                with self.subTest(contador=contador, turno=turno):
                    raiz = EstadoPosicion(jugadas_sin_captura_ni_peon=contador)
                    partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                    antes = pickle.dumps(raiz)
                    nuevo = self.jugar(partida, movimiento)
                    self.assertEqual(nuevo.jugadas_sin_captura_ni_peon, contador + 1)
                    self.assertEqual(pickle.dumps(raiz), antes)

    def test_secuencia_y_conservacion_de_todos_los_estados(self):
        partida = Partida()
        estados = [(partida.estado_inicial, pickle.dumps(partida.estado_inicial), 0)]
        for movimiento, esperado in (('g1f3', 1), ('g8f6', 2), ('e2e4', 0),
                                     ('b8c6', 1), ('b1c3', 2), ('f6e4', 0)):
            estado = self.jugar(partida, movimiento)
            self.assertEqual(estado.jugadas_sin_captura_ni_peon, esperado)
            estados.append((estado, pickle.dumps(estado), esperado))
        for estado, antes, esperado in estados:
            self.assertEqual(estado.jugadas_sin_captura_ni_peon, esperado)
            self.assertEqual(pickle.dumps(estado), antes)

    def test_avances_de_peon_reinician_para_ambos_colores(self):
        for turno, movimientos in ((Color.Blanco, ('e2e3', 'e2e4')),
                                   (Color.Negro, ('e7e6', 'e7e5'))):
            for movimiento in movimientos:
                with self.subTest(turno=turno, movimiento=movimiento):
                    raiz = EstadoPosicion(jugadas_sin_captura_ni_peon=17)
                    partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                    nuevo = self.jugar(partida, movimiento)
                    self.assertEqual(nuevo.jugadas_sin_captura_ni_peon, 0)
                    self.assertEqual(raiz.jugadas_sin_captura_ni_peon, 17)

    def test_capturas_de_torre_reinician_para_ambos_colores(self):
        for turno, origen, destino, contrario in (
                (Color.Blanco, 'a2', 'a7', Color.Negro),
                (Color.Negro, 'a7', 'a2', Color.Blanco)):
            with self.subTest(turno=turno):
                raiz = preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                                  origen: Torre(turno), destino: Caballo(contrario)}, 23, turno)
                partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                nuevo = self.jugar(partida, origen + destino)
                self.assertEqual(nuevo.jugadas_sin_captura_ni_peon, 0)
                self.assertEqual(raiz.jugadas_sin_captura_ni_peon, 23)
                self.assertIsInstance(raiz.tablero.pieza_en(posicion(destino)), Caballo)
                self.assertIsInstance(nuevo.tablero.pieza_en(posicion(destino)), Torre)

    def test_rechazos_no_actualizan_contadores(self):
        raiz = EstadoPosicion(jugadas_sin_captura_ni_peon=16)
        partida = Partida(estado_inicial=raiz)
        antes = pickle.dumps(partida)
        for movimiento in ('e2e5', 'e7e5', 'c1h6'):
            with self.subTest(movimiento=movimiento):
                self.assertIsInstance(mover(partida, movimiento), MotivoRechazoMovimiento)
                self.assertEqual(pickle.dumps(partida), antes)
        raiz = preparar({'e1': Rey(Color.Blanco), 'e2': Torre(Color.Blanco),
                          'a8': Rey(Color.Negro), 'e8': Torre(Color.Negro)}, 16)
        antes = pickle.dumps(raiz)
        jugada = Jugada(1, posicion('e2'), posicion('d2'), None, estado_inicial=raiz)
        self.assertFalse(jugada.estado_posicion.movimiento_valido)
        self.assertIs(jugada.estado_posicion.motivo_rechazo, MotivoRechazoMovimiento.REY_EN_JAQUE)
        self.assertEqual(jugada.estado_posicion.jugadas_sin_captura_ni_peon, 16)
        self.assertEqual(pickle.dumps(raiz), antes)

    def test_enroques_cortos_y_largos_incrementan_una_sola_vez(self):
        for turno, fila in ((Color.Blanco, '1'), (Color.Negro, '8')):
            for columna, letra, destino in ((7, 'h', 'g'), (0, 'a', 'c')):
                with self.subTest(turno=turno, columna=columna):
                    raiz = preparar({'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro),
                                      letra + fila: Torre(turno)}, 13, turno, {(turno, columna)})
                    partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                    nuevo = self.jugar(partida, 'e' + fila + destino + fila)
                    self.assertIsInstance(partida.ultima_jugada, Enroque)
                    self.assertEqual(nuevo.jugadas_sin_captura_ni_peon, 14)
                    self.assertEqual(raiz.jugadas_sin_captura_ni_peon, 13)

    def test_captura_al_paso_reinicia_y_conserva_historial(self):
        for secuencia in ('e2e4 a7a6 e4e5 d7d5 e5d6',
                          'a2a3 e7e5 a3a4 e5e4 d2d4 e4d3'):
            with self.subTest(secuencia=secuencia):
                partida = Partida()
                movimientos = secuencia.split()
                for movimiento in movimientos[:-1]:
                    self.jugar(partida, movimiento)
                anterior = estado_vigente(partida)
                antes = pickle.dumps(anterior)
                nuevo = self.jugar(partida, movimientos[-1])
                self.assertIsInstance(partida.ultima_jugada, CapturaAlPaso)
                self.assertEqual(nuevo.jugadas_sin_captura_ni_peon, 0)
                self.assertEqual(pickle.dumps(anterior), antes)

    def test_promocion_pendiente_y_confirmada_en_ambos_colores(self):
        for turno, peon, salida, llegada, victima in (
                (Color.Blanco, PeonBlanco, 'a7', 'a8', 'b8'),
                (Color.Negro, PeonNegro, 'a2', 'a1', 'b1')):
            contrario = Color.Negro if turno is Color.Blanco else Color.Blanco
            for captura in (False, True):
                for opcion in PiezaPromocion:
                    with self.subTest(turno=turno, captura=captura, opcion=opcion):
                        raiz = preparar({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                                          salida: peon(), victima: Torre(contrario)}, 17, turno)
                        antes = pickle.dumps(raiz)
                        sesion = SesionAnalisis(raiz, turno)
                        actual = sesion.estado_actual
                        destino = victima if captura else llegada
                        self.assertIsNone(sesion.solicitar_movimiento(posicion(salida), posicion(destino)))
                        self.assertIsNotNone(sesion.jugada_pendiente)
                        self.assertIs(sesion.estado_actual, actual)
                        self.assertEqual(actual.jugadas_sin_captura_ni_peon, 17)
                        self.assertEqual(sesion.jugada_pendiente.estado_posicion.jugadas_sin_captura_ni_peon, 0)
                        sesion.elegir_promocion(opcion)
                        self.assertIsNone(sesion.jugada_pendiente)
                        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 0)
                        self.assertEqual(actual.jugadas_sin_captura_ni_peon, 17)
                        self.assertEqual(pickle.dumps(raiz), antes)

    def test_variante_hereda_cuenta_sin_modificar_original(self):
        partida = Partida()
        for movimiento in ('g1f3', 'g8f6', 'b1c3', 'b8c6'):
            self.jugar(partida, movimiento)
        antes = pickle.dumps(partida)
        raiz = estado_vigente(partida)
        sesion = SesionAnalisis(raiz, partida.jugador)
        self.assertIsNot(sesion.estado_actual, raiz)
        self.assertIsNone(sesion.estado_actual.estado_anterior)
        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 4)
        self.assertIsNone(sesion.solicitar_movimiento(posicion('f3'), posicion('g1')))
        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 5)
        self.assertEqual(pickle.dumps(partida), antes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
