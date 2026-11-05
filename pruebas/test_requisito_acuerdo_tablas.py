"""Acuerdo de tablas después de un movimiento confirmado de cada jugador."""
import pickle
import unittest
from unittest.mock import patch

from ajedrez.partida import Partida, EstadoPartida
from ajedrez.piezas import Color, Rey, Torre, PeonBlanco
from ajedrez.sesion import SesionAnalisis, PiezaPromocion
from pruebas import test_abandono as apoyo
from pruebas.test_analisis_partida import mover
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import nueva_sesion, enviar


class PruebasRequisitoAcuerdo(unittest.TestCase):
    def test_consulta_pura_cero_una_y_dos_jugadas_con_cualquiera_empezando(self):
        for primero, movimientos in (
            (Color.Blanco, ('e2e4', 'e7e5')),
            (Color.Negro, ('e7e5', 'e2e4')),
        ):
            with self.subTest(primero=primero):
                partida = Partida(turno_inicial=primero)
                self.assertFalse(partida.tablas_por_acuerdo_disponibles)
                self.assertIsNone(mover(partida, movimientos[0]))
                antes = pickle.dumps(partida)
                self.assertFalse(partida.tablas_por_acuerdo_disponibles)
                self.assertEqual(pickle.dumps(partida), antes)
                self.assertIsNotNone(mover(partida, 'a1a8'))
                self.assertEqual(partida.contador_jugadas, 1)
                self.assertFalse(partida.tablas_por_acuerdo_disponibles)
                self.assertIsNone(mover(partida, movimientos[1]))
                antes = pickle.dumps(partida)
                self.assertTrue(partida.tablas_por_acuerdo_disponibles)
                self.assertEqual(pickle.dumps(partida), antes)

    def test_estado_inicial_de_otra_partida_no_cuenta_como_historial_propio(self):
        original = Partida()
        for movimiento in ('e2e4', 'e7e5', 'g1f3', 'b8c6'):
            self.assertIsNone(mover(original, movimiento))
        antes = pickle.dumps(original)
        partida = Partida(estado_inicial=original.ultima_jugada.estado_posicion)
        self.assertEqual(partida.contador_jugadas, 0)
        self.assertFalse(partida.tablas_por_acuerdo_disponibles)
        self.assertIsNone(mover(partida, 'd2d4'))
        self.assertFalse(partida.tablas_por_acuerdo_disponibles)
        self.assertIsNone(mover(partida, 'd7d5'))
        self.assertTrue(partida.tablas_por_acuerdo_disponibles)
        self.assertEqual(pickle.dumps(original), antes)

    def test_una_promocion_cuenta_solo_al_confirmar_la_pieza(self):
        for primero in Color:
            with self.subTest(primero=primero):
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(estado_inicial=preparar(
                    {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
                     'a7': PeonBlanco(), 'c8': Torre(Color.Negro)}, 0, primero),
                    turno_inicial=primero)
                if primero is Color.Negro:
                    self.assertIsNone(enviar(sesion, 'h8g8'))
                confirmadas = sesion.partida.contador_jugadas
                self.assertIsNone(enviar(sesion, 'a7a8'))
                self.assertIsNotNone(sesion.jugada_pendiente)
                self.assertEqual(sesion.partida.contador_jugadas, confirmadas)
                self.assertFalse(sesion.tablas_por_acuerdo_disponibles)
                sesion.elegir_promocion(PiezaPromocion.REINA)
                self.assertEqual(sesion.partida.contador_jugadas, confirmadas + 1)
                self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                self.assertEqual(sesion.tablas_por_acuerdo_disponibles, primero is Color.Negro)
                if primero is Color.Blanco:
                    self.assertIsNone(enviar(sesion, 'h8g8'))
                    self.assertTrue(sesion.tablas_por_acuerdo_disponibles)

    def test_aceptacion_temprana_no_finaliza_y_rechazo_sigue_disponible(self):
        # La regla limita el acuerdo, no la existencia de una oferta temprana
        # recibida por otra interfaz. La GUI evita proponerla antes de tiempo.
        for primero, movimiento in ((Color.Blanco, 'e2e4'), (Color.Negro, 'e7e5')):
            for cantidad in (0, 1):
                for proponente in Color:
                    with self.subTest(primero=primero, cantidad=cantidad, proponente=proponente):
                        sesion = nueva_sesion()
                        sesion.juego._partida = Partida(turno_inicial=primero)
                        if cantidad:
                            self.assertIsNone(enviar(sesion, movimiento))
                        sesion.proponer_tablas(proponente)
                        contrario = Color.Negro if proponente is Color.Blanco else Color.Blanco
                        antes = pickle.dumps(sesion)
                        sesion.responder_propuesta_tablas(contrario, True)
                        self.assertEqual(pickle.dumps(sesion), antes)
                        self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                        sesion.responder_propuesta_tablas(contrario, False)
                        self.assertIsNone(sesion.proponente_tablas)
                        self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_despues_de_dos_jugadas_el_acuerdo_no_depende_del_turno(self):
        for primero, movimientos in (
            (Color.Blanco, ('e2e4', 'e7e5')),
            (Color.Negro, ('e7e5', 'e2e4')),
        ):
            for proponente in Color:
                with self.subTest(primero=primero, proponente=proponente):
                    sesion = nueva_sesion()
                    sesion.juego._partida = Partida(turno_inicial=primero)
                    for movimiento in movimientos:
                        self.assertIsNone(enviar(sesion, movimiento))
                    antes = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                    sesion.proponer_tablas(proponente)
                    contrario = Color.Negro if proponente is Color.Blanco else Color.Blanco
                    sesion.responder_propuesta_tablas(contrario, True)
                    self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                    self.assertIsNone(sesion.proponente_tablas)
                    self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), antes)

    def test_una_respuesta_tardia_no_sustituye_el_resultado_del_abandono(self):
        sesion = nueva_sesion()
        for movimiento in ('e2e4', 'e7e5'):
            self.assertIsNone(enviar(sesion, movimiento))
        sesion.proponer_tablas(Color.Blanco)
        sesion.solicitar_abandono(Color.Blanco)
        antes = pickle.dumps(sesion)
        self.assertFalse(sesion.tablas_por_acuerdo_disponibles)
        sesion.responder_propuesta_tablas(Color.Negro, True)
        self.assertEqual(pickle.dumps(sesion), antes)
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.VICTORIA_NEGRA)

    def test_la_capacidad_de_la_sesion_se_mantiene_separada_de_la_disponibilidad(self):
        sesion = nueva_sesion()
        self.assertTrue(sesion.admite_propuestas_tablas)
        self.assertFalse(sesion.tablas_por_acuerdo_disponibles)
        analisis = SesionAnalisis(sesion.estado_actual, Color.Blanco)
        for movimiento in ('e2e4', 'e7e5'):
            self.assertIsNone(enviar(analisis, movimiento))
        self.assertTrue(analisis.partida.tablas_por_acuerdo_disponibles)
        self.assertFalse(analisis.tablas_por_acuerdo_disponibles)
        self.assertFalse(analisis.admite_propuestas_tablas)


class PruebasBotonesRequisitoAcuerdo(unittest.TestCase):
    setUp = apoyo.PruebasBotonesAbandono.setUp
    tearDown = apoyo.PruebasBotonesAbandono.tearDown
    crear = apoyo.PruebasBotonesAbandono.crear
    clic = apoyo.PruebasBotonesAbandono.clic

    def comprobar_botones(self, vista, esperado):
        for boton in vista.botones_propuesta_tablas.values():
            self.assertEqual(boton.cget('state'), esperado)

    def test_botones_se_habilitan_tras_dos_movimientos_confirmados(self):
        for primero, movimientos in (
            (Color.Blanco, ('e2e4', 'e7e5')),
            (Color.Negro, ('e7e5', 'e2e4')),
        ):
            with self.subTest(primero=primero):
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(turno_inicial=primero)
                vista = self.crear(sesion)
                self.comprobar_botones(vista, 'disabled')
                for indice, movimiento in enumerate(movimientos):
                    with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno') as dialogo:
                        for boton in vista.botones_propuesta_tablas.values():
                            boton.invoke()
                        vista.proponer_tablas(Color.Blanco)
                    dialogo.assert_not_called()
                    self.assertIsNone(sesion.proponente_tablas)
                    self.clic(vista, movimiento[:2])
                    self.clic(vista, movimiento[2:])
                    self.comprobar_botones(vista, 'disabled' if indice == 0 else 'normal')
                # Consultar el historial no modifica el requisito del juego vigente.
                vista.retroceder_movimiento()
                vista.retroceder_movimiento()
                self.assertIs(vista.estado_mostrado, sesion.partida.estado_inicial)
                self.comprobar_botones(vista, 'normal')
                vista.contenedor.destroy()

    def test_mismo_requisito_para_las_sesiones_que_controlan_un_solo_color(self):
        for color in Color:
            with self.subTest(color=color):
                sesion = apoyo.SesionUnColor(color)
                vista = self.crear(sesion)
                self.assertEqual(set(vista.botones_propuesta_tablas), {color})
                self.comprobar_botones(vista, 'disabled')
                for indice, movimiento in enumerate(('e2e4', 'e7e5')):
                    self.assertIsNone(enviar(sesion, movimiento))
                    vista.mostrar_estado(sesion.estado_actual)
                    self.comprobar_botones(vista, 'disabled' if indice == 0 else 'normal')
                vista.contenedor.destroy()

    def test_no_pregunta_por_una_propuesta_recibida_antes_de_cumplirse_el_requisito(self):
        sesion = nueva_sesion()
        vista = self.crear(sesion)
        sesion.proponer_tablas(Color.Blanco)
        antes = pickle.dumps(sesion)
        with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno') as dialogo:
            vista._consultar_respuesta_tablas()
        dialogo.assert_not_called()
        self.assertEqual(pickle.dumps(sesion), antes)

    def test_segundo_movimiento_con_promocion_habilita_solo_al_elegir_pieza(self):
        sesion = nueva_sesion()
        sesion.juego._partida = Partida(estado_inicial=preparar(
            {'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
             'a7': PeonBlanco(), 'c8': Torre(Color.Negro)}, 0, Color.Negro),
            turno_inicial=Color.Negro)
        vista = self.crear(sesion)
        for origen, destino in (('h8', 'g8'), ('a7', 'a8')):
            self.clic(vista, origen)
            self.clic(vista, destino)
        self.assertIsNotNone(sesion.jugada_pendiente)
        self.assertEqual(sesion.partida.contador_jugadas, 1)
        self.comprobar_botones(vista, 'disabled')
        selector = next(w for w in vista.casillero.contenedor.winfo_children()
                        if isinstance(w, apoyo.tk.Frame) and w.winfo_manager() == 'place')
        opciones = [w for w in selector.winfo_children() if isinstance(w, apoyo.tk.Button)]
        opciones[3].invoke()
        self.assertIsNone(sesion.jugada_pendiente)
        self.assertEqual(sesion.partida.contador_jugadas, 2)
        self.comprobar_botones(vista, 'normal')


if __name__ == '__main__':
    unittest.main()
