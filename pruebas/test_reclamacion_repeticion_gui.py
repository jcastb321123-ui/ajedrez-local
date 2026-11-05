"""Botón común y diálogo de reclamación por repetición con Tkinter real."""
import pickle
import unittest

from ajedrez.partida import EstadoPartida, EstadoPosicion, Partida
from ajedrez.piezas import Color
from pruebas import test_abandono as apoyo
from pruebas.test_analisis_partida import posicion
from pruebas import test_disponibilidad_reclamacion_tablas as apoyo_reclamacion
from pruebas.test_reclamacion_repeticion_sesion import preparar_sesion
from pruebas.test_sesion import nueva_sesion


class PruebasInterfazReclamacionRepeticion(unittest.TestCase):
    setUp = apoyo_reclamacion.PruebasBotonReclamacion.setUp
    tearDown = apoyo_reclamacion.PruebasBotonReclamacion.tearDown
    crear = apoyo_reclamacion.PruebasBotonReclamacion.crear
    clic = apoyo_reclamacion.PruebasBotonReclamacion.clic

    def test_boton_unico_reclama_tercera_limpia_seleccion_y_actualiza_resultado(self):
        for turno in Color:
            with self.subTest(turno=turno):
                sesion, _ = preparar_sesion(turno)
                vista = self.crear(sesion)
                origen = "g1" if turno is Color.Blanco else "g8"
                self.clic(vista, origen)
                self.assertIsNotNone(vista.origen_seleccionado)
                boton = vista.boton_reclamacion_tablas
                botones = [w for w in vista.panel_navegacion.winfo_children()
                           if isinstance(w, apoyo.tk.Button) and "Reclamar tablas" in w.cget("text")]
                self.assertEqual(botones, [boton])
                self.assertEqual(boton.cget("text"), "Reclamar tablas")
                self.assertEqual(boton.cget("state"), "normal")
                datos = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                boton.invoke()
                self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)
                self.assertIsNone(vista.origen_seleccionado)
                self.assertEqual(vista.indicador_estado_partida.cget("text"), "Tablas")
                self.assertEqual(boton.cget("state"), "disabled")
                self.pregunta_tablas.assert_not_called()
                vista.contenedor.destroy()

    def test_anuncio_pregunta_una_vez_y_respeta_si_o_no_con_ambas_reglas(self):
        for turno in Color:
            for contador in (0, 92):
                for aceptar in (False, True):
                    with self.subTest(turno=turno, contador=contador, aceptar=aceptar):
                        sesion, anuncio = preparar_sesion(turno, True, contador=contador)
                        vista = self.crear(sesion)
                        origen, destino = (("f6", "g8") if turno is Color.Blanco else ("f3", "g1"))
                        self.clic(vista, origen)
                        datos = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                        self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "disabled")

                        def responder(**opciones):
                            self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)
                            self.assertIs(opciones["parent"], vista.contenedor)
                            return aceptar

                        self.pregunta_tablas.reset_mock()
                        self.pregunta_tablas.side_effect = responder
                        self.clic(vista, destino)
                        self.pregunta_tablas.assert_called_once()
                        self.assertIsNone(vista.origen_seleccionado)
                        self.assertIs(vista.estado_mostrado, sesion.estado_actual)
                        if aceptar:
                            self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                            self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)
                            self.assertEqual(vista.indicador_estado_partida.cget("text"), "Tablas")
                        else:
                            self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                            self.assertEqual(sesion.partida.contador_jugadas, 8)
                            self.assertEqual(sesion.partida.apariciones_posicion_actual, 3)
                            self.assertIsNone(sesion.partida.tablero.pieza_en(anuncio[0]))
                            self.assertIsNotNone(sesion.partida.tablero.pieza_en(anuncio[1]))
                            self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "normal")
                        vista.contenedor.destroy()

    def test_ya_reclamable_no_repite_pregunta_al_jugar(self):
        sesion, _ = preparar_sesion()
        vista = self.crear(sesion)
        self.clic(vista, "g1")
        self.clic(vista, "f3")
        self.pregunta_tablas.assert_not_called()
        self.assertEqual(sesion.partida.contador_jugadas, 9)
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_sin_disponibilidad_no_pregunta_y_rechazo_conserva_seleccion(self):
        sesion, _ = preparar_sesion(ciclos=1)
        vista = self.crear(sesion)
        self.clic(vista, "g1")
        antes = pickle.dumps(sesion)
        self.assertIs(vista.reclamar_tablas(), False)
        self.assertIs(vista.reclamar_tablas_por_triple_repeticion(), False)
        self.clic(vista, "g3")
        self.assertEqual(vista.origen_seleccionado, posicion("g1"))
        self.assertEqual(pickle.dumps(sesion), antes)
        self.pregunta_tablas.assert_not_called()

    def test_analisis_y_color_sin_turno_deshabilitan_reclamacion(self):
        fuente, _ = preparar_sesion()
        vista = self.crear(fuente)
        antes = pickle.dumps(fuente)
        vista.alternar_analisis()
        self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "disabled")
        self.assertIs(vista._ofrecer_reclamacion_con_movimiento(
            (posicion("g1"), posicion("f3"))), False)
        vista.boton_reclamacion_tablas.invoke()
        self.assertEqual(pickle.dumps(fuente), antes)
        vista.alternar_analisis()
        self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "normal")
        vista.contenedor.destroy()

        sesion = apoyo.SesionUnColor(Color.Negro)
        sesion.juego._partida = fuente.partida
        vista = self.crear(sesion)
        self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "disabled")
        antes = pickle.dumps(sesion)
        self.assertIs(vista._ofrecer_reclamacion_con_movimiento(
            (posicion("g1"), posicion("f3"))), False)
        self.assertEqual(pickle.dumps(sesion), antes)
        self.pregunta_tablas.assert_not_called()

    def test_quinta_aparicion_actualiza_resultado_y_boton_sin_pregunta(self):
        sesion, _ = preparar_sesion(anunciada=True, ciclos=4)
        vista = self.crear(sesion)
        self.clic(vista, "f6")
        self.clic(vista, "g8")
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(vista.indicador_estado_partida.cget("text"), "Tablas")
        self.assertEqual(vista.boton_reclamacion_tablas.cget("state"), "disabled")
        self.pregunta_tablas.assert_not_called()

    def test_boton_comun_sigue_reclamando_cincuenta_movimientos(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(
            estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=100))
        vista = self.crear(sesion)
        self.assertFalse(sesion.tablas_por_triple_repeticion_disponible())
        self.assertTrue(sesion.reclamacion_tablas_disponible())
        vista.boton_reclamacion_tablas.invoke()
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertEqual(vista.indicador_estado_partida.cget("text"), "Tablas")


if __name__ == "__main__":
    unittest.main()
