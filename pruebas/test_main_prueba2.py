"""Pruebas de la segunda consola con sesiones reales y entrada simulada."""

import unittest

# Permite ejecutar el test directamente, sin depender de la carpeta de trabajo.
if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.partida import EstadoPartida
from ajedrez.piezas import Alfil, Caballo, Color, PeonBlanco, Reina, Rey, Torre
from pruebas.main_prueba2 import convertir_posicion, ejecutar_sesion, main
from ajedrez.sesion import AsignacionColores, ModalidadAsignacion, SesionLocal


PROMOCION_BLANCA = "a2a4 b7b5 a4b5 a7a6 b5a6 h7h6 a6a7 h6h5 a7b8".split()
PROMOCION_NEGRA = "h2h3 a7a5 b2b4 a5b4 a2a3 b4a3 h3h4 a3a2 h4h5 a2b1".split()


def entradas_movimientos(movimientos):
    return [casilla for movimiento in movimientos
            for casilla in (movimiento[:2], movimiento[2:])]


class EntradaSimulada:
    def __init__(self, entradas):
        self.entradas = iter(entradas)
        self.preguntas = []
        self.salidas = []

    def leer(self, pregunta):
        self.preguntas.append(pregunta)
        return next(self.entradas)  # Una lectura inesperada hace fallar la prueba.


def nueva_sesion(modalidad=ModalidadAsignacion.BLANCO_NEGRO):
    return SesionLocal(AsignacionColores(modalidad))


class PruebasConsolaLocal(unittest.TestCase):
    def test_conversion_de_coordenadas(self):
        for texto, posicion in [("a1", (0, 0)), ("H8", (7, 7)), (" e2 ", (1, 4)),
                                ("1,4", (1, 4)), (" (1, 4) ", (1, 4))]:
            with self.subTest(texto=texto):
                self.assertEqual(convertir_posicion(texto), posicion)

    def test_conversion_invalida_devuelve_none(self):
        for texto in ("", " ", "8,0", "-1,0", "1", "1,2,3", "a0", "i2", "a9",
                      "1.0,2", "(1,2", "1,2)", "1,,2", "(),2", "__import__('os')"):
            with self.subTest(texto=texto):
                self.assertIsNone(convertir_posicion(texto))

    def test_main_arranca_las_tres_modalidades_y_predeterminada(self):
        for opcion in ("", "1", "2", "3"):
            with self.subTest(opcion=opcion):
                consola = EntradaSimulada(["invalida", opcion, "e2", "e4", "salir"])
                main(consola.leer, consola.salidas.append)
                self.assertIn("Movimiento aceptado: e2 -> e4.", consola.salidas)
                if opcion == "2":
                    self.assertIn("Turno: jugador 1 (blancas).", consola.salidas)
                elif opcion == "3":
                    self.assertIn("Turno: jugador 2 (blancas).", consola.salidas)

    def test_rechazos_silenciosos_y_turnos_sin_mostrar_claves(self):
        sesion = nueva_sesion(ModalidadAsignacion.NEGRO_BLANCO)
        consola = EntradaSimulada([
            "fuera", "8,0", "e2", "8,0", "e7", "e5", "e3", "e4",
            "e2", "f3", "(1,4)", "(3,4)", "e7", "e5", "salir",
        ])
        ejecutar_sesion(sesion, consola.leer, consola.salidas.append)
        p = sesion.juego.partida
        self.assertEqual(p.contador_jugadas, 2)
        self.assertEqual(p.jugador, Color.Blanco)
        self.assertIn("Turno: jugador 2 (blancas).", consola.salidas)
        self.assertIn("Turno: jugador 1 (negras).", consola.salidas)
        self.assertEqual(sum(s.startswith("Movimiento aceptado") for s in consola.salidas), 2)
        for emisor in (sesion.emisor_1, sesion.emisor_2):
            self.assertNotIn(emisor.clave, "\n".join(consola.salidas + consola.preguntas))
        self.assertFalse(any("error" in s.lower() or "inválid" in s.lower()
                             for s in consola.salidas))

    def test_mates_de_ambos_colores_no_piden_mas_entrada(self):
        casos = [
            ("f2f3 e7e5 g2g4 d8h4".split(), EstadoPartida.VICTORIA_NEGRA,
             "Victoria de las negras."),
            ("e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7".split(), EstadoPartida.VICTORIA_BLANCA,
             "Victoria de las blancas."),
        ]
        for movimientos, estado, mensaje in casos:
            with self.subTest(estado=estado):
                sesion = nueva_sesion()
                consola = EntradaSimulada(entradas_movimientos(movimientos))
                ejecutar_sesion(sesion, consola.leer, consola.salidas.append)
                self.assertEqual(sesion.juego.partida.estado_partida, estado)
                self.assertEqual(consola.salidas[-1], mensaje)
                self.assertEqual(len(consola.preguntas), 2 * len(movimientos))

    def test_ocho_promociones_espera_y_continuacion(self):
        for movimientos in (PROMOCION_BLANCA, PROMOCION_NEGRA):
            for letra, clase in (("d", Reina), ("t", Torre), ("a", Alfil), ("c", Caballo)):
                with self.subTest(movimiento=movimientos[-1], letra=letra):
                    sesion = nueva_sesion()
                    p = sesion.juego.partida
                    siguiente = "h5h4" if movimientos is PROMOCION_BLANCA else "h5h6"
                    consola = EntradaSimulada(entradas_movimientos(movimientos)
                                              + ["e2", letra]
                                              + entradas_movimientos([siguiente]) + ["salir"])
                    pendientes = []

                    def leer(pregunta):
                        if pregunta.startswith("Promoción en"):
                            pendiente = sesion.juego.jugada_pendiente
                            self.assertIsNotNone(pendiente)
                            self.assertEqual(p.contador_jugadas, len(movimientos) - 1)
                            self.assertEqual(p.jugador, pendiente.pieza.color)
                            self.assertIsNot(p.tablero, pendiente.tablero)
                            self.assertIsNone(p.ultima_jugada.siguiente)
                            pendientes.append(pendiente)
                        return consola.leer(pregunta)

                    ejecutar_sesion(sesion, leer, consola.salidas.append)
                    self.assertEqual(len(pendientes), 2)
                    self.assertIs(pendientes[0], pendientes[1])
                    self.assertIsNone(sesion.juego.jugada_pendiente)
                    self.assertFalse(p.promocion_pendiente)
                    self.assertIsInstance(p.tablero.pieza_en(pendientes[0].destino), clase)
                    self.assertEqual(p.contador_jugadas, len(movimientos) + 1)
                    self.assertIs(pendientes[0].siguiente, p.ultima_jugada)

    def test_salir_durante_promocion_no_la_registra(self):
        sesion = nueva_sesion()
        consola = EntradaSimulada(entradas_movimientos(PROMOCION_BLANCA) + ["salir"])
        ejecutar_sesion(sesion, consola.leer, consola.salidas.append)
        p = sesion.juego.partida
        self.assertEqual(p.contador_jugadas, 8)
        self.assertEqual(p.jugador, Color.Blanco)
        self.assertIsInstance(p.tablero.pieza_en((6, 0)), PeonBlanco)
        self.assertIsNone(p.ultima_jugada.siguiente)
        self.assertIsNotNone(sesion.juego.jugada_pendiente)

    def test_resultado_de_promocion_se_muestra_despues_de_elegir(self):
        # Posición preparada sólo para comprobar el cierre de la consola.
        for letra, resultado, mensaje in (("d", EstadoPartida.VICTORIA_BLANCA,
                                          "Victoria de las blancas."),
                                         ("t", EstadoPartida.TABLAS, "Tablas.")):
            with self.subTest(letra=letra):
                sesion = nueva_sesion()
                sesion.emisor_1.enviar_solicitud((1, 4), (3, 4))
                sesion.emisor_2.enviar_solicitud((6, 4), (4, 4))
                p = sesion.juego.partida
                for posicion in p.tablero.casillas:
                    p.tablero.colocar(None, posicion)
                for posicion, pieza in [((6, 5), Rey(Color.Blanco)),
                                        ((2, 4), Alfil(Color.Blanco)),
                                        ((6, 6), PeonBlanco()), ((6, 7), Rey(Color.Negro))]:
                    if hasattr(pieza, "ha_movido"):
                        pieza.movimiento_realizado()
                    p.tablero.colocar(pieza, posicion)
                p.tablero.posicion_de_captura_al_paso = None
                p.ultima_jugada.estado_posicion._captura_al_paso_disponible = False
                consola = EntradaSimulada(["g7", "g8", letra])
                ejecutar_sesion(sesion, consola.leer, consola.salidas.append)
                self.assertEqual(p.estado_partida, resultado)
                self.assertEqual(consola.salidas[-2:], ["Promoción completada.", mensaje])

    def test_sesion_terminada_no_recibe_movimientos(self):
        sesion = nueva_sesion()
        sesion.juego.partida.estado_partida = EstadoPartida.TABLAS
        consola = EntradaSimulada([])
        ejecutar_sesion(sesion, consola.leer, consola.salidas.append)
        self.assertEqual(consola.preguntas, [])
        self.assertEqual(consola.salidas[-1], "Tablas.")

    def test_salir_en_menu_origen_y_destino(self):
        consola = EntradaSimulada(["salir"])
        main(consola.leer, consola.salidas.append)
        self.assertEqual(len(consola.preguntas), 1)
        for entradas in (["salir"], ["e2", "SALIR"]):
            sesion = nueva_sesion()
            consola = EntradaSimulada(entradas)
            ejecutar_sesion(sesion, consola.leer, consola.salidas.append)
            self.assertEqual(sesion.juego.partida.contador_jugadas, 0)

    def test_fin_de_entrada_e_interrupcion_son_salidas_normales(self):
        for excepcion in (EOFError, KeyboardInterrupt):
            def leer(_):
                raise excepcion
            main(leer, lambda _: None)
            sesion = nueva_sesion()
            ejecutar_sesion(sesion, leer, lambda _: None)
            self.assertEqual(sesion.juego.partida.contador_jugadas, 0)

    def test_no_oculta_errores_de_programacion(self):
        def leer(_):
            raise RuntimeError("Fallo interno de prueba")
        with self.assertRaises(RuntimeError):
            main(leer, lambda _: None)


if __name__ == "__main__":
    unittest.main()
