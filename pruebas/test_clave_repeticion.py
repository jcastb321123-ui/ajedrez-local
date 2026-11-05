"""Identidad de posiciones para el futuro recuento de repeticiones."""
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPosicion, Partida
from ajedrez.piezas import Color, PeonBlanco, PeonNegro, Rey, Torre
from pruebas.test_analisis_partida import estado_minimo, mover, posicion


class PruebasClaveRepeticion(unittest.TestCase):
    def setUp(self):
        self.partida = Partida()

    def clave(self, estado, turno):
        antes = pickle.dumps((self.partida, estado))
        resultado = self.partida._obtener_clave_repeticion(estado, turno)
        self.assertEqual(pickle.dumps((self.partida, estado)), antes)
        return resultado

    def test_estados_equivalentes_comparten_entrada_de_diccionario(self):
        primera = self.clave(EstadoPosicion(), Color.Blanco)
        segunda = self.clave(EstadoPosicion(jugadas_sin_captura_ni_peon=99), Color.Blanco)
        registro = {primera: 1}
        registro[segunda] += 1
        self.assertEqual(len(registro), 1)
        self.assertEqual(registro[primera], 2)

    def test_turno_distingue_la_misma_distribucion(self):
        estado = EstadoPosicion()
        self.assertNotEqual(
            self.clave(estado, Color.Blanco),
            self.clave(estado, Color.Negro),
        )

    def test_ciclo_real_recupera_clave_aunque_cambien_historial_y_contador(self):
        raiz = self.partida.estado_inicial
        inicial = self.clave(raiz, Color.Blanco)
        for movimiento in ("g1f3", "g8f6", "f3g1", "f6g8"):
            self.assertIsNone(mover(self.partida, movimiento))
            if movimiento == "g8f6":
                self.assertNotEqual(
                    self.clave(self.partida.ultima_jugada.estado_posicion, Color.Blanco),
                    inicial,
                )
        actual = self.partida.ultima_jugada.estado_posicion
        self.assertEqual(actual.jugadas_sin_captura_ni_peon, 4)
        self.assertEqual(self.clave(actual, self.partida.jugador), inicial)
        self.assertEqual(self.clave(raiz, Color.Blanco), inicial)

    def test_derechos_enroque_distinguen_posiciones_con_piezas_iguales(self):
        for color, fila in ((Color.Blanco, "1"), (Color.Negro, "8")):
            piezas = {"e1": Rey(Color.Blanco), "e8": Rey(Color.Negro),
                      "a" + fila: Torre(color), "h" + fila: Torre(color)}
            editor = EditorPosicion(estado_minimo(piezas), color)
            derechos = {(color, 0), (color, 7)}
            con_derechos = editor.construir_estado(turno=color, enroques=derechos)
            for retirados in ({(color, 0)}, {(color, 7)}, derechos):
                with self.subTest(color=color, retirados=retirados):
                    sin_derechos = editor.construir_estado(
                        turno=color, enroques=derechos - retirados
                    )
                    self.assertEqual(
                        con_derechos.tablero.obtener_clave_distribucion(),
                        sin_derechos.tablero.obtener_clave_distribucion(),
                    )
                    self.assertNotEqual(
                        self.clave(con_derechos, color),
                        self.clave(sin_derechos, color),
                    )

    def test_captura_al_paso_solo_distingue_si_es_legal(self):
        for turno, propio, enemigo, fila, rey_propio, torre_enemiga, rey_enemigo in (
            (Color.Blanco, PeonBlanco, PeonNegro, "5", "e1", "e8", "a8"),
            (Color.Negro, PeonNegro, PeonBlanco, "4", "e8", "e1", "a1"),
        ):
            contrario = Color.Negro if turno is Color.Blanco else Color.Blanco
            for caso in ("legal", "sin_vecino", "clavado"):
                with self.subTest(turno=turno, caso=caso):
                    piezas = {rey_propio: Rey(turno), rey_enemigo: Rey(contrario),
                              "d" + fila: enemigo()}
                    if caso != "sin_vecino":
                        piezas["e" + fila] = propio()
                    if caso == "clavado":
                        piezas[torre_enemiga] = Torre(contrario)
                    editor = EditorPosicion(estado_minimo(piezas), turno)
                    con_marca = editor.construir_estado(
                        turno=turno, enroques=set(),
                        peon_al_paso=posicion("d" + fila),
                    )
                    sin_marca = editor.construir_estado(turno=turno, enroques=set())
                    self.assertEqual(
                        self.clave(con_marca, turno) == self.clave(sin_marca, turno),
                        caso != "legal",
                    )


if __name__ == "__main__":
    unittest.main()
