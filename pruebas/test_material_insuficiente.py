"""Casos de posición muerta demostrables por material e integración gráfica."""
import pickle
import unittest

from ajedrez.editor_posicion import EditorPosicion
from ajedrez.partida import EstadoPartida, Partida, MotivoRechazoMovimiento
from ajedrez.piezas import Alfil, Caballo, Color, PeonBlanco, PeonNegro, Reina, Rey, Torre
from ajedrez.sesion import SesionAnalisis, PiezaPromocion
from pruebas import test_abandono as apoyo
from pruebas import test_disponibilidad_reclamacion_tablas as apoyo_reclamacion
from pruebas.test_analisis_partida import estado_minimo, mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import enviar, nueva_sesion


class PruebasMaterialInsuficiente(unittest.TestCase):
    def comprobar(self, adicionales, esperado):
        estado = estado_minimo(
            {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro), **adicionales})
        antes = pickle.dumps(estado)
        self.assertIs(estado.tablero.es_posicion_muerta_por_material(), esperado)
        self.assertEqual(pickle.dumps(estado), antes)

    def test_reyes_y_unica_pieza_menor_de_cualquier_color(self):
        self.comprobar({}, True)
        for color in Color:
            for clase in (Alfil, Caballo):
                with self.subTest(color=color, pieza=clase.__name__):
                    self.comprobar({"c1": clase(color)}, True)

    def test_alfiles_sobre_un_unico_color_de_casilla_incluidas_promociones(self):
        for casillas in (("c1", "e3", "g5", "a3"), ("d1", "f3", "h5", "b3")):
            for colores in ((Color.Blanco,) * 4, (Color.Negro,) * 4,
                            (Color.Blanco, Color.Negro, Color.Blanco, Color.Negro)):
                with self.subTest(casillas=casillas, colores=colores):
                    self.comprobar(
                        {casilla: Alfil(color) for casilla, color in zip(casillas, colores)},
                        True,
                    )

    def test_peon_torre_o_dama_impiden_decidir_tablas_por_material(self):
        for pieza in (PeonBlanco(), PeonNegro(), Torre(Color.Blanco),
                      Torre(Color.Negro), Reina(Color.Blanco), Reina(Color.Negro)):
            with self.subTest(tipo=type(pieza).__name__, color=pieza.color):
                self.comprobar({"c2": pieza}, False)

    def test_combinaciones_con_mate_posible_no_se_declaran_muertas(self):
        casos = (
            {"b1": Caballo(Color.Blanco), "g1": Caballo(Color.Blanco)},
            {"b1": Caballo(Color.Blanco), "g8": Caballo(Color.Negro)},
            {"c1": Alfil(Color.Blanco), "b1": Caballo(Color.Blanco)},
            {"c1": Alfil(Color.Blanco), "g8": Caballo(Color.Negro)},
            {"c1": Alfil(Color.Blanco), "f1": Alfil(Color.Negro)},
            {"c1": Alfil(Color.Blanco), "f1": Alfil(Color.Blanco)},
            {"c1": Alfil(Color.Blanco), "e3": Alfil(Color.Negro), "c2": PeonBlanco()},
        )
        for piezas in casos:
            with self.subTest(piezas=tuple(piezas)):
                self.comprobar(piezas, False)


class PruebasFinalMaterialInsuficiente(unittest.TestCase):
    def test_posicion_inicial_se_reconoce_sin_exigir_una_jugada(self):
        for turno in Color:
            for adicional in ({}, {"c1": Alfil(Color.Blanco)}, {"g8": Caballo(Color.Negro)}):
                with self.subTest(turno=turno, adicional=tuple(adicional)):
                    estado = preparar(
                        {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro), **adicional}, 0, turno)
                    antes = pickle.dumps(estado)
                    partida = Partida(estado_inicial=estado, turno_inicial=turno)
                    self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
                    self.assertEqual(partida.contador_jugadas, 0)
                    self.assertIsNone(partida.ultima_jugada)
                    partida.actualizar_estado()
                    self.assertEqual(pickle.dumps(estado), antes)

    def test_captura_finaliza_y_conserva_la_posicion_anterior(self):
        casos = (
            (Color.Blanco, {"b2": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                           "b3": Torre(Color.Negro)}, "b2b3"),
            (Color.Negro, {"a1": Rey(Color.Blanco), "g7": Rey(Color.Negro),
                          "g6": Torre(Color.Blanco)}, "g7g6"),
            (Color.Blanco, {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                           "c1": Alfil(Color.Blanco), "d2": Torre(Color.Negro)}, "c1d2"),
            (Color.Negro, {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                          "f8": Alfil(Color.Negro), "e7": Torre(Color.Blanco)}, "f8e7"),
            (Color.Blanco, {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                           "b1": Caballo(Color.Blanco), "c3": Torre(Color.Negro)}, "b1c3"),
            (Color.Negro, {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
                          "g8": Caballo(Color.Negro), "f6": Torre(Color.Blanco)}, "g8f6"),
        )
        for turno, piezas, movimiento in casos:
            with self.subTest(turno=turno, movimiento=movimiento):
                estado = preparar(piezas, 0, turno)
                antes = pickle.dumps(estado)
                partida = Partida(estado_inicial=estado, turno_inicial=turno)
                self.assertIs(partida.estado_partida, EstadoPartida.EN_CURSO)
                self.assertIsNone(mover(partida, movimiento))
                self.assertIs(partida.estado_partida, EstadoPartida.TABLAS)
                self.assertEqual(partida.contador_jugadas, 1)
                self.assertEqual(pickle.dumps(estado), antes)
                final = pickle.dumps(partida)
                partida.actualizar_estado()
                self.assertEqual(pickle.dumps(partida), final)

    def test_promocion_se_evalua_solo_despues_de_elegir_pieza(self):
        for turno, origen, destino, peon in (
            (Color.Blanco, "a7", "a8", PeonBlanco()),
            (Color.Negro, "a2", "a1", PeonNegro()),
        ):
            for opcion in PiezaPromocion:
                with self.subTest(turno=turno, opcion=opcion):
                    raiz = preparar(
                        {"h1": Rey(Color.Blanco), "h8": Rey(Color.Negro), origen: peon}, 0, turno)
                    sesion = nueva_sesion()
                    sesion.juego._partida = Partida(estado_inicial=raiz, turno_inicial=turno)
                    self.assertIsNone(enviar(sesion, origen + destino))
                    self.assertIsNotNone(sesion.jugada_pendiente)
                    self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                    self.assertEqual(sesion.partida.contador_jugadas, 0)
                    sesion.elegir_promocion(opcion)
                    self.assertIsNone(sesion.jugada_pendiente)
                    esperado = (EstadoPartida.TABLAS if opcion in (PiezaPromocion.ALFIL, PiezaPromocion.CABALLO)
                                else EstadoPartida.EN_CURSO)
                    self.assertIs(sesion.partida.estado_partida, esperado)
                    self.assertEqual(sesion.partida.contador_jugadas, 1)

    def test_mates_con_dos_caballos_o_con_bloqueo_de_pieza_adversaria(self):
        casos = (
            ({"c7": Rey(Color.Blanco), "a8": Rey(Color.Negro),
              "c6": Caballo(Color.Blanco), "c4": Caballo(Color.Blanco)}, "c4b6"),
            ({"c7": Rey(Color.Blanco), "a8": Rey(Color.Negro),
              "c4": Caballo(Color.Blanco), "a7": Caballo(Color.Negro)}, "c4b6"),
            ({"c7": Rey(Color.Blanco), "a8": Rey(Color.Negro),
              "c8": Alfil(Color.Blanco), "a7": Alfil(Color.Negro)}, "c8b7"),
        )
        for piezas, movimiento in casos:
            with self.subTest(movimiento=movimiento, piezas=tuple(piezas)):
                partida = Partida(estado_inicial=preparar(piezas, 0))
                self.assertIsNone(mover(partida, movimiento))
                self.assertIs(partida.estado_partida, EstadoPartida.VICTORIA_BLANCA)
                self.assertFalse(partida.tablero.es_posicion_muerta_por_material())

    def test_sesion_local_se_detiene_y_analisis_permite_continuar(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
             "c1": Alfil(Color.Blanco), "d2": Torre(Color.Negro)}, 0))
        self.assertIsNone(enviar(sesion, "c1d2"))
        antes = pickle.dumps(sesion.partida)
        self.assertIs(enviar(sesion, "h8g8"), MotivoRechazoMovimiento.PARTIDA_FINALIZADA)
        analisis = SesionAnalisis(sesion.estado_actual, Color.Negro)
        self.assertIsNone(analisis.solicitar_movimiento(posicion("h8"), posicion("g8")))
        self.assertIs(analisis.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(pickle.dumps(sesion.partida), antes)


class PruebasInterfazMaterialInsuficiente(unittest.TestCase):
    setUp = apoyo_reclamacion.PruebasBotonReclamacion.setUp
    tearDown = apoyo_reclamacion.PruebasBotonReclamacion.tearDown
    crear = apoyo_reclamacion.PruebasBotonReclamacion.crear
    clic = apoyo_reclamacion.PruebasBotonReclamacion.clic

    def test_captura_actualiza_resultado_controles_y_permite_analizar(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro),
             "c1": Alfil(Color.Blanco), "d2": Torre(Color.Negro)}, 0))
        vista = self.crear(sesion)
        self.clic(vista, "c1")
        self.clic(vista, "d2")
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(vista.indicador_estado_partida.cget("text"), "Tablas")
        self.assertIsNone(vista.origen_seleccionado)
        botones = (*vista.botones_abandono.values(), *vista.botones_propuesta_tablas.values(),
                   vista.boton_reclamacion_tablas)
        self.assertTrue(all(boton.cget("state") == "disabled" for boton in botones))
        original = pickle.dumps(sesion.partida)
        self.clic(vista, "h8")
        self.clic(vista, "g8")
        self.assertIsNot(vista.sesion_movimientos.partida, sesion.partida)
        self.assertEqual(pickle.dumps(sesion.partida), original)

    def test_tablero_cargado_muestra_tablas_desde_el_inicio(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {"a1": Rey(Color.Blanco), "h8": Rey(Color.Negro)}, 0))
        vista = self.crear(sesion)
        self.assertEqual(vista.indicador_estado_partida.cget("text"), "Tablas")
        self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "disabled")


if __name__ == "__main__":
    unittest.main()
