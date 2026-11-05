"""Tablas por acuerdo: sesiones, diálogo y disponibilidad de botones.

Las sesiones de un color son dobles de prueba; no implementan IA ni red.
Las ventanas se mantienen ocultas y las respuestas al diálogo se simulan.
"""
import pickle
import unittest
from unittest.mock import patch

import pruebas.test_abandono as apoyo
from ajedrez.partida import EstadoPartida
from ajedrez.piezas import Color
from ajedrez.sesion import ModalidadAsignacion
from pruebas.test_sesion import nueva_sesion, enviar, posicion

def completar_primer_turno(sesion):
    for movimiento in ('e2e4', 'e7e5'):
        resultado = enviar(sesion, movimiento)
        if resultado is not None:
            raise AssertionError(f'No se pudo preparar la partida: {resultado}')
    return sesion


def datos(partida):
    return (partida.estado_inicial, partida.tablero, partida.ultima_jugada,
            partida.registro_turnos, partida.jugador, partida.contador_jugadas,
            partida.promocion_pendiente)

class PruebasNegociacionTablas(unittest.TestCase):
    def test_aceptar_y_rechazar_ambos_colores_repartos_y_turnos(self):
        for modalidad in ModalidadAsignacion:
            for color in Color:
                for movimientos in ((), ('g1f3',)):
                    for aceptar in (False, True):
                        with self.subTest(modalidad=modalidad, color=color,
                                          movimientos=movimientos, aceptar=aceptar):
                            sesion = completar_primer_turno(nueva_sesion(modalidad))
                            for movimiento in movimientos:
                                self.assertIsNone(enviar(sesion, movimiento))
                            antes = pickle.dumps(datos(sesion.partida))
                            self.assertTrue(sesion.admite_propuestas_tablas)
                            self.assertIsNone(sesion.proponente_tablas)
                            self.assertIsNone(sesion.proponer_tablas(color))
                            self.assertIs(sesion.proponente_tablas, color)
                            self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                            rival = Color.Negro if color is Color.Blanco else Color.Blanco
                            self.assertIsNone(sesion.responder_propuesta_tablas(rival, aceptar))
                            esperado = EstadoPartida.TABLAS if aceptar else EstadoPartida.EN_CURSO
                            self.assertIs(sesion.partida.estado_partida, esperado)
                            self.assertIsNone(sesion.proponente_tablas)
                            self.assertIsNone(sesion.juego.proponente_tablas)
                            self.assertEqual(pickle.dumps(datos(sesion.partida)), antes)

    def test_proponente_no_resuelve_su_propia_oferta(self):
        for modalidad in ModalidadAsignacion:
            for color in Color:
                with self.subTest(modalidad=modalidad, color=color):
                    sesion = completar_primer_turno(nueva_sesion(modalidad))
                    sesion.proponer_tablas(color)
                    for aceptar in (False, True):
                        self.assertIsNone(sesion.responder_propuesta_tablas(color, aceptar))
                        self.assertIs(sesion.proponente_tablas, color)
                        self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)

    def test_rechazo_permite_seguir_jugando_y_proponer_de_nuevo(self):
        for modalidad in ModalidadAsignacion:
            with self.subTest(modalidad=modalidad):
                sesion = completar_primer_turno(nueva_sesion(modalidad))
                sesion.proponer_tablas(Color.Blanco)
                sesion.responder_propuesta_tablas(Color.Negro, False)
                self.assertIsNone(enviar(sesion, 'g1f3'))
                self.assertIs(sesion.partida.jugador, Color.Negro)
                sesion.proponer_tablas(Color.Negro)
                self.assertIs(sesion.proponente_tablas, Color.Negro)
                sesion.responder_propuesta_tablas(Color.Blanco, True)
                self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                self.assertIsNone(sesion.proponente_tablas)


class PruebasDialogoTablas(unittest.TestCase):
    setUp = apoyo.PruebasBotonesAbandono.setUp
    tearDown = apoyo.PruebasBotonesAbandono.tearDown
    crear = apoyo.PruebasBotonesAbandono.crear

    def test_respuesta_local_directa_acepta_y_rechaza(self):
        for color in Color:
            for aceptar in (False, True):
                with self.subTest(color=color, aceptar=aceptar):
                    sesion = completar_primer_turno(nueva_sesion())
                    vista = self.crear(sesion)
                    origen = posicion('g1')
                    vista.origen_seleccionado = origen
                    vista.casillero.aplicar_marca(origen, 'seleccion')
                    antes = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                    sesion.proponer_tablas(color)
                    with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno',
                                      return_value=aceptar) as dialogo:
                        vista._consultar_respuesta_tablas()
                    dialogo.assert_called_once()
                    self.assertIs(dialogo.call_args.kwargs['parent'], vista.contenedor)
                    self.assertIsNone(sesion.proponente_tablas)
                    esperado = EstadoPartida.TABLAS if aceptar else EstadoPartida.EN_CURSO
                    self.assertIs(sesion.partida.estado_partida, esperado)
                    self.assertEqual(vista.origen_seleccionado, None if aceptar else origen)
                    texto = 'Tablas' if aceptar else 'Turno de blancas'
                    self.assertEqual(vista.indicador_estado_partida.cget('text'), texto)
                    self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), antes)
                    estado_boton = 'disabled' if aceptar else 'normal'
                    self.assertTrue(all(b.cget('state') == estado_boton
                                        for b in vista.botones_abandono.values()))
                    vista.contenedor.destroy()

    def test_proponer_abre_la_consulta(self):
        for color in Color:
            with self.subTest(color=color):
                sesion = completar_primer_turno(nueva_sesion())
                vista = self.crear(sesion)
                with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno',
                                  return_value=False) as dialogo:
                    vista.proponer_tablas(color)
                dialogo.assert_called_once()
                self.assertIsNone(sesion.proponente_tablas)

    def test_no_responde_por_un_color_que_no_controla(self):
        for color in Color:
            with self.subTest(color=color):
                sesion = completar_primer_turno(apoyo.SesionUnColor(color))
                vista = self.crear(sesion)
                sesion.proponer_tablas(color)
                with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno',
                                  return_value=True) as dialogo:
                    vista._consultar_respuesta_tablas()
                dialogo.assert_not_called()
                self.assertIs(sesion.proponente_tablas, color)
                self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)


    def test_consulta_propuesta_recibida_por_el_color_controlado(self):
        for color in Color:
            with self.subTest(color=color):
                sesion = completar_primer_turno(apoyo.SesionUnColor(color))
                vista = self.crear(sesion)
                rival = Color.Negro if color is Color.Blanco else Color.Blanco
                sesion.proponer_tablas(rival)
                with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno',
                                  return_value=False) as dialogo:
                    vista._consultar_respuesta_tablas()
                dialogo.assert_called_once()
                self.assertIsNone(sesion.proponente_tablas)
                self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)




    def test_botones_segun_capacidad_colores_y_colocacion(self):
        for unico in (None, Color.Blanco, Color.Negro):
            with self.subTest(unico=unico):
                sesion = completar_primer_turno(nueva_sesion()) if unico is None else completar_primer_turno(apoyo.SesionUnColor(unico))
                vista = self.crear(sesion)
                self.assertEqual(set(vista.botones_propuesta_tablas), set(sesion.colores_controlados))
                for color, boton in vista.botones_propuesta_tablas.items():
                    self.assertIn(boton.winfo_manager(), ('pack', 'grid'))
                    self.assertEqual(boton.cget('state'), 'normal')
                    if unico is not None:
                        self.assertEqual(boton.cget('text'), 'Proponer tablas')
                    else:
                        self.assertIn('blancas' if color is Color.Blanco else 'negras',
                                      boton.cget('text').lower())
                vista.contenedor.destroy()
        class SesionSinTablas(apoyo.SesionUnColor):
            @property
            def admite_propuestas_tablas(self):
                return False
        for sesion in (SesionSinTablas(Color.Blanco),
                       apoyo.SesionAnalisis(apoyo.Partida().estado_inicial, Color.Blanco)):
            vista = self.crear(sesion)
            self.assertEqual(vista.botones_propuesta_tablas, {})
            vista.contenedor.destroy()

    def test_botones_locales_envian_color_y_actualizan_resultado(self):
        for color in Color:
            for aceptar in (False, True):
                with self.subTest(color=color, aceptar=aceptar):
                    sesion = completar_primer_turno(nueva_sesion())
                    vista = self.crear(sesion)
                    vista.origen_seleccionado = posicion('g1')
                    vista.casillero.aplicar_marca(posicion('g1'), 'seleccion')
                    antes = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                    def responder(*args, **kwargs):
                        self.assertIs(sesion.proponente_tablas, color)
                        return aceptar
                    with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno',
                                      side_effect=responder) as dialogo:
                        vista.botones_propuesta_tablas[color].invoke()
                    dialogo.assert_called_once()
                    self.assertIsNone(sesion.proponente_tablas)
                    esperado = EstadoPartida.TABLAS if aceptar else EstadoPartida.EN_CURSO
                    self.assertIs(sesion.partida.estado_partida, esperado)
                    self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), antes)
                    self.assertEqual(vista.origen_seleccionado,
                                     None if aceptar else posicion('g1'))
                    estado = 'disabled' if aceptar else 'normal'
                    for b in (*vista.botones_propuesta_tablas.values(), *vista.botones_abandono.values()):
                        self.assertEqual(b.cget('state'), estado)
                    vista.contenedor.destroy()

    def test_oferta_pendiente_impide_repetir_y_respuesta_actualiza(self):
        for color in Color:
            for aceptar in (False, True):
                with self.subTest(color=color, aceptar=aceptar):
                    sesion = completar_primer_turno(apoyo.SesionUnColor(color))
                    vista = self.crear(sesion)
                    boton = vista.botones_propuesta_tablas[color]
                    with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno') as dialogo:
                        with patch.object(sesion, 'proponer_tablas', wraps=sesion.proponer_tablas) as propuesta:
                            boton.invoke()
                            self.assertEqual(boton.cget('state'), 'disabled')
                            boton.invoke()
                        propuesta.assert_called_once_with(color)
                    dialogo.assert_not_called()
                    self.assertIs(sesion.proponente_tablas, color)
                    self.assertEqual(vista.botones_abandono[color].cget('state'), 'normal')
                    rival = Color.Negro if color is Color.Blanco else Color.Blanco
                    sesion.responder_propuesta_tablas(rival, aceptar)
                    vista._actualizar_indicador_contexto()
                    self.assertIsNone(sesion.proponente_tablas)
                    self.assertEqual(boton.cget('state'), 'disabled' if aceptar else 'normal')
                    vista.contenedor.destroy()

    def test_promocion_bloquea_propuestas_hasta_completar(self):
        for indice, resultado in ((0, EstadoPartida.TABLAS), (3, EstadoPartida.VICTORIA_BLANCA)):
            with self.subTest(opcion=indice):
                piezas = {'h6': apoyo.Rey(Color.Blanco), 'h8': apoyo.Rey(Color.Negro),
                          'f7': apoyo.PeonBlanco()}
                estado = apoyo.EditorPosicion(apoyo.estado_minimo(piezas), Color.Blanco).construir_estado(
                    turno=Color.Blanco, enroques=set())
                sesion = completar_primer_turno(nueva_sesion())
                sesion.juego._partida = apoyo.Partida(estado_inicial=estado, turno_inicial=Color.Blanco)
                vista = self.crear(sesion)
                apoyo.PruebasBotonesAbandono.clic(self, vista, 'f7')
                apoyo.PruebasBotonesAbandono.clic(self, vista, 'f8')
                self.assertIsNotNone(vista.promocion_pendiente)
                self.assertTrue(all(b.cget('state') == 'disabled'
                                    for b in vista.botones_propuesta_tablas.values()))
                with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno') as dialogo:
                    for boton in vista.botones_propuesta_tablas.values():
                        boton.invoke()
                dialogo.assert_not_called()
                self.assertIsNone(sesion.proponente_tablas)
                selector = next(w for w in vista.casillero.contenedor.winfo_children()
                                if isinstance(w, apoyo.tk.Frame) and w.winfo_manager() == 'place')
                opciones = [w for w in selector.winfo_children() if isinstance(w, apoyo.tk.Button)]
                opciones[indice].invoke()
                self.assertIsNone(vista.promocion_pendiente)
                self.assertIs(sesion.partida.estado_partida, resultado)
                esperado = 'normal' if resultado is EstadoPartida.EN_CURSO else 'disabled'
                self.assertTrue(all(b.cget('state') == esperado
                                    for b in vista.botones_propuesta_tablas.values()))
                vista.contenedor.destroy()

    def test_acuerdo_conserva_navegacion_y_analisis(self):
        sesion = completar_primer_turno(nueva_sesion())
        vista = self.crear(sesion)
        vigente = sesion.estado_actual
        with patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno', return_value=True):
            vista.botones_propuesta_tablas[Color.Blanco].invoke()
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        original = pickle.dumps(sesion.partida)
        vista.retroceder_movimiento()
        vista.retroceder_movimiento()
        self.assertIs(vista.estado_mostrado, sesion.partida.estado_inicial)
        vista.avanzar_movimiento()
        vista.avanzar_movimiento()
        self.assertIs(vista.estado_mostrado, vigente)
        apoyo.PruebasBotonesAbandono.clic(self, vista, 'g1')
        apoyo.PruebasBotonesAbandono.clic(self, vista, 'f3')
        self.assertIsNot(vista.sesion_movimientos.partida, sesion.partida)
        self.assertEqual(pickle.dumps(sesion.partida), original)
        self.assertTrue(all(b.cget('state') == 'disabled'
                            for b in vista.botones_propuesta_tablas.values()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
