"""Captura al paso legal al comparar posiciones para la repetición."""
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPosicion, Partida
from ajedrez.piezas import Caballo, Color, PeonBlanco, PeonNegro, Rey, Torre
from pruebas.test_analisis_partida import estado_minimo, mover, posicion


class PruebasCapturaAlPasoRepeticion(unittest.TestCase):
    def setUp(self):
        self.partida = Partida()

    def crear_estado(self, piezas, turno, peon_al_paso):
        return EditorPosicion(estado_minimo(piezas), turno).construir_estado(
            turno=turno,
            enroques=set(),
            peon_al_paso=posicion(peon_al_paso),
        )

    def comprobar_consulta(self, estado, turno, esperado):
        antes = pickle.dumps((self.partida, estado))
        self.assertEqual(
            self.partida._obtener_peon_capturable_al_paso(estado, turno),
            None if esperado is None else posicion(esperado),
        )
        self.assertEqual(pickle.dumps((self.partida, estado)), antes)

    def test_sin_marca_o_sin_peon_vecino(self):
        self.comprobar_consulta(EstadoPosicion(), Color.Blanco, None)
        self.assertIsNone(mover(self.partida, "e2e4"))
        self.comprobar_consulta(
            self.partida.ultima_jugada.estado_posicion, Color.Negro, None
        )

    def test_ambos_colores_lados_y_columnas_extremas(self):
        for turno, fila, propio, enemigo in (
            (Color.Blanco, "5", PeonBlanco, PeonNegro),
            (Color.Negro, "4", PeonNegro, PeonBlanco),
        ):
            for capturado, capturador in (("d", "c"), ("d", "e"), ("a", "b"), ("h", "g")):
                with self.subTest(turno=turno, capturado=capturado, capturador=capturador):
                    casilla_peon = capturado + fila
                    estado = self.crear_estado(
                        {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                         casilla_peon: enemigo(), capturador + fila: propio()},
                        turno, casilla_peon,
                    )
                    self.comprobar_consulta(estado, turno, casilla_peon)

    def test_vecino_debe_ser_peon_del_turno(self):
        for vecino in (Caballo(Color.Blanco), PeonNegro()):
            with self.subTest(vecino=type(vecino).__name__):
                estado = self.crear_estado(
                    {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                     "d5": PeonNegro(), "e5": vecino},
                    Color.Blanco, "d5",
                )
                self.comprobar_consulta(estado, Color.Blanco, None)

    def test_rechaza_captura_que_expone_al_rey(self):
        for turno, piezas, casilla_peon in (
            (Color.Blanco,
             {"e1": Rey(Color.Blanco), "a8": Rey(Color.Negro),
              "e8": Torre(Color.Negro), "e5": PeonBlanco(), "d5": PeonNegro()},
             "d5"),
            (Color.Negro,
             {"a1": Rey(Color.Blanco), "e8": Rey(Color.Negro),
              "e1": Torre(Color.Blanco), "e4": PeonNegro(), "d4": PeonBlanco()},
             "d4"),
            (Color.Blanco,
             {"h5": Rey(Color.Blanco), "h8": Rey(Color.Negro),
              "a5": Torre(Color.Negro), "g5": PeonBlanco(), "f5": PeonNegro()},
             "f5"),
        ):
            with self.subTest(turno=turno, casilla_peon=casilla_peon):
                estado = self.crear_estado(piezas, turno, casilla_peon)
                self.comprobar_consulta(estado, turno, None)

    def test_primer_vecino_clavado_no_descarta_segundo_legal(self):
        estado = self.crear_estado(
            {"c1": Rey(Color.Blanco), "a8": Rey(Color.Negro),
             "c8": Torre(Color.Negro), "c5": PeonBlanco(),
             "d5": PeonNegro(), "e5": PeonBlanco()},
            Color.Blanco, "d5",
        )
        self.comprobar_consulta(estado, Color.Blanco, "d5")

    def test_jaque_debe_quedar_resuelto_tras_la_captura(self):
        for piezas, esperado in (
            ({"h1": Rey(Color.Blanco), "a8": Rey(Color.Negro),
              "h8": Torre(Color.Negro), "e5": PeonBlanco(), "d5": PeonNegro()},
             None),
            ({"e4": Rey(Color.Blanco), "a8": Rey(Color.Negro),
              "e5": PeonBlanco(), "d5": PeonNegro()},
             "d5"),
        ):
            with self.subTest(esperado=esperado):
                estado = self.crear_estado(piezas, Color.Blanco, "d5")
                self.assertTrue(estado.tablero.el_rey_queda_en_jaque(Color.Blanco))
                self.comprobar_consulta(estado, Color.Blanco, esperado)

    def test_estado_historico_independiente_del_tablero_actual(self):
        for movimiento in ("e2e4", "a7a6", "e4e5", "d7d5"):
            self.assertIsNone(mover(self.partida, movimiento))
        historico = self.partida.ultima_jugada.estado_posicion
        for movimiento in ("g1f3", "a6a5"):
            self.assertIsNone(mover(self.partida, movimiento))
        actual = self.partida.ultima_jugada.estado_posicion
        self.comprobar_consulta(historico, Color.Blanco, "d5")
        self.comprobar_consulta(actual, Color.Blanco, None)


if __name__ == "__main__":
    unittest.main()
