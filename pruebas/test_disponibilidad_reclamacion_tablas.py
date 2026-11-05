"""Disponibilidad de reclamaciones y botón real de Tkinter, con ventanas ocultas."""
import pickle
import unittest
from unittest.mock import patch

from ajedrez.partida import EstadoPartida, EstadoPosicion, Partida
from ajedrez.piezas import Caballo, Color, PeonBlanco, Rey, Torre
from ajedrez.sesion import SesionAnalisis
from pruebas import test_abandono as apoyo
from pruebas.test_analisis_partida import mover, posicion
from pruebas.test_contador_tablas import preparar
from pruebas.test_sesion import nueva_sesion


class PruebasConsultaReclamacion(unittest.TestCase):
    def test_modelo_consulta_sin_modificar_y_respeta_limite_y_finalizacion(self):
        for contador in (0, 99, 100, 149):
            for terminada in (False, True):
                with self.subTest(contador=contador, terminada=terminada):
                    partida = Partida(estado_inicial=EstadoPosicion(
                        jugadas_sin_captura_ni_peon=contador))
                    if terminada:
                        partida.abandonar(Color.Blanco)
                    antes = pickle.dumps(partida)
                    resultado = partida.tablas_por_cincuenta_movimientos_disponible()
                    self.assertEqual(pickle.dumps(partida), antes)
                    self.assertIs(resultado, contador >= 100 and not terminada)

    def test_sesion_consulta_posicion_inicial_sin_pieza_movida(self):
        for contador in (0, 99, 100):
            with self.subTest(contador=contador):
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(estado_inicial=EstadoPosicion(
                    jugadas_sin_captura_ni_peon=contador))
                antes = pickle.dumps(sesion)
                self.assertIs(sesion.tablas_por_cincuenta_movimientos_disponible(), contador >= 100)
                self.assertEqual(pickle.dumps(sesion), antes)

    def test_un_color_consulta_el_turno_actual_y_no_el_ultimo_movimiento(self):
        for color in Color:
            with self.subTest(controlado=color):
                sesion = apoyo.SesionUnColor(color)
                sesion.juego._partida = Partida(
                    estado_inicial=EstadoPosicion(jugadas_sin_captura_ni_peon=99),
                    turno_inicial=Color.Negro)
                self.assertIsNone(mover(sesion.partida, 'g8f6'))
                self.assertIs(sesion.partida.jugador, Color.Blanco)
                self.assertIs(sesion.estado_actual.pieza.color, Color.Negro)
                antes = pickle.dumps(sesion)
                self.assertIs(sesion.tablas_por_cincuenta_movimientos_disponible(), color is Color.Blanco)
                self.assertEqual(pickle.dumps(sesion), antes)


class PruebasBotonReclamacion(unittest.TestCase):
    def setUp(self):
        apoyo.PruebasBotonesAbandono.setUp(self)
        pregunta = patch.object(apoyo.modulo_interfaz.messagebox, 'askyesno', return_value=False)
        self.pregunta_tablas = pregunta.start()
        self.addCleanup(pregunta.stop)

    tearDown = apoyo.PruebasBotonesAbandono.tearDown
    clic = apoyo.PruebasBotonesAbandono.clic

    def sesion_con_contador(self, contador, piezas=None):
        sesion = nueva_sesion()
        estado = (EstadoPosicion(jugadas_sin_captura_ni_peon=contador)
                  if piezas is None else preparar(piezas, contador))
        sesion.juego._partida = Partida(estado_inicial=estado)
        return sesion

    def crear(self, sesion, solo_analisis=False):
        contenedor = apoyo.tk.Frame(self.raiz)
        contenedor.pack()
        vista = apoyo.InterfazPartida(
            sesion, apoyo.Casillero(contenedor, self.tema),
            contenedor=contenedor, solo_analisis=solo_analisis)
        vista.mostrar_estado(sesion.estado_actual)
        return vista

    def test_boton_guardado_colocado_y_desactivado_al_iniciar(self):
        vista = self.crear(nueva_sesion())
        boton = vista.boton_reclamacion_tablas
        self.assertIsInstance(boton, apoyo.tk.Button)
        self.assertIn(boton.winfo_manager(), ('pack', 'grid'))
        self.assertEqual(boton.cget('state'), 'disabled')
        botones = [w for w in vista.panel_navegacion.winfo_children()
                   if isinstance(w, apoyo.tk.Button) and 'Reclamar tablas' in w.cget('text')]
        self.assertEqual(botones, [boton])

    def test_sin_boton_en_analisis_o_sesion_que_no_admite_reclamaciones(self):
        class SesionSinReclamaciones(apoyo.SesionUnColor):
            @property
            def admite_reclamaciones_tablas(self):
                return False
        casos = ((SesionAnalisis(Partida().estado_inicial, Color.Blanco), False),
                 (SesionSinReclamaciones(Color.Blanco), False),
                 (nueva_sesion(), True))
        for sesion, solo in casos:
            with self.subTest(sesion=type(sesion).__name__, solo=solo):
                vista = self.crear(sesion, solo)
                self.assertIsNone(vista.boton_reclamacion_tablas)
                vista._actualizar_boton_reclamacion_tablas()
                vista.contenedor.destroy()

    def test_paso_de_noventa_y_nueve_a_cien_y_reinicio_por_peon(self):
        sesion = self.sesion_con_contador(99)
        vista = self.crear(sesion)
        boton = vista.boton_reclamacion_tablas
        self.assertEqual(boton.cget('state'), 'disabled')
        self.clic(vista, 'g1')
        self.clic(vista, 'f3')
        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 100)
        self.assertEqual(boton.cget('state'), 'normal')
        self.clic(vista, 'e7')
        self.clic(vista, 'e5')
        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 0)
        self.assertEqual(boton.cget('state'), 'disabled')

    def test_captura_reinicia_y_desactiva_el_boton(self):
        sesion = self.sesion_con_contador(100, {
            'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
            'a2': Torre(Color.Blanco), 'a7': Caballo(Color.Negro)})
        vista = self.crear(sesion)
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'normal')
        self.clic(vista, 'a2')
        self.clic(vista, 'a7')
        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 0)
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'disabled')

    def test_promocion_pendiente_y_confirmada_desactivan_boton(self):
        sesion = self.sesion_con_contador(100, {
            'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro),
            'a7': PeonBlanco(), 'b8': Torre(Color.Negro)})
        vista = self.crear(sesion)
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'normal')
        self.clic(vista, 'a7')
        self.clic(vista, 'a8')
        self.assertIsNotNone(vista.promocion_pendiente)
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'disabled')
        selector = next(w for w in vista.casillero.contenedor.winfo_children()
                        if isinstance(w, apoyo.tk.Frame) and w.winfo_manager() == 'place')
        opciones = [w for w in selector.winfo_children() if isinstance(w, apoyo.tk.Button)]
        opciones[0].invoke()
        self.assertIsNone(vista.promocion_pendiente)
        self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 0)
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'disabled')

    def test_analisis_en_el_mismo_panel_deshabilita_y_al_salir_habilita(self):
        sesion = self.sesion_con_contador(100)
        vista = self.crear(sesion)
        antes = pickle.dumps(sesion.partida)
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'normal')
        vista.alternar_analisis()
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'disabled')
        vista.alternar_analisis()
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'normal')
        self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_actualizador_reconoce_analisis_en_panel_no_exclusivo(self):
        # Aísla el actualizador para que un fallo del constructor no oculte esta regla.
        sesion = self.sesion_con_contador(99)
        self.assertIsNone(mover(sesion.partida, 'g1f3'))
        vista = apoyo.InterfazPartida.__new__(apoyo.InterfazPartida)
        vista._sesion = sesion
        vista._solo_analisis = False
        vista._analizando = True
        vista._boton_reclamacion_tablas = apoyo.tk.Button(self.raiz)
        vista._actualizar_boton_reclamacion_tablas()
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'disabled')

    def test_clic_finaliza_limpia_seleccion_y_actualiza_indicadores(self):
        sesion = self.sesion_con_contador(100)
        vista = self.crear(sesion)
        self.clic(vista, 'g1')
        self.assertEqual(vista.origen_seleccionado, posicion('g1'))
        antes = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
        vista.boton_reclamacion_tablas.invoke()
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(vista.origen_seleccionado)
        self.assertEqual(vista.indicador_estado_partida.cget('text'), 'Tablas')
        self.assertEqual(vista.boton_reclamacion_tablas.cget('state'), 'disabled')
        self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), antes)

    def test_reclamacion_anunciada_devuelve_booleano_y_conserva_tablero(self):
        anuncio = (posicion('g1'), posicion('f3'))
        for contador, esperado in ((98, False), (99, True)):
            with self.subTest(contador=contador):
                sesion = self.sesion_con_contador(contador)
                vista = self.crear(sesion)
                self.clic(vista, 'g1')
                datos = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
                resultado = vista.reclamar_tablas_por_cincuenta_movimientos(
                    movimiento_anunciado=anuncio)
                self.assertIs(resultado, esperado)
                self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)
                self.assertIs(sesion.partida.estado_partida,
                              EstadoPartida.TABLAS if esperado else EstadoPartida.EN_CURSO)
                self.assertEqual(vista.origen_seleccionado,
                                 None if esperado else posicion('g1'))
                vista.contenedor.destroy()

    def test_oferta_aceptada_termina_y_actualiza_la_interfaz(self):
        sesion = self.sesion_con_contador(99)
        vista = self.crear(sesion)
        self.clic(vista, 'g1')
        antes = pickle.dumps(apoyo.datos_de_juego(sesion.partida))
        self.pregunta_tablas.return_value = True
        resultado = vista._ofrecer_reclamacion_con_movimiento(
            (posicion('g1'), posicion('f3')))
        self.assertIs(resultado, True)
        self.pregunta_tablas.assert_called_once()
        self.assertIs(self.pregunta_tablas.call_args.kwargs.get('parent'), vista.contenedor)
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
        self.assertIsNone(vista.origen_seleccionado)
        self.assertEqual(vista.indicador_estado_partida.cget('text'), 'Tablas')
        self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), antes)

    def test_oferta_rechazada_conserva_seleccion_y_asocia_dialogo_al_contenedor(self):
        sesion = self.sesion_con_contador(99)
        vista = self.crear(sesion)
        self.clic(vista, 'g1')
        antes = pickle.dumps(sesion)
        self.assertIs(vista._ofrecer_reclamacion_con_movimiento(
            (posicion('g1'), posicion('f3'))), False)
        self.pregunta_tablas.assert_called_once()
        self.assertIs(self.pregunta_tablas.call_args.kwargs.get('parent'), vista.contenedor)
        self.assertEqual(vista.origen_seleccionado, posicion('g1'))
        self.assertEqual(pickle.dumps(sesion), antes)

    def test_clic_pregunta_antes_de_mover_y_respeta_la_respuesta(self):
        for aceptar in (False, True):
            with self.subTest(aceptar=aceptar):
                sesion = self.sesion_con_contador(99)
                vista = self.crear(sesion)
                self.clic(vista, 'g1')
                datos = pickle.dumps(apoyo.datos_de_juego(sesion.partida))

                def responder(**opciones):
                    self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)
                    self.assertIs(opciones.get('parent'), vista.contenedor)
                    return aceptar

                self.pregunta_tablas.reset_mock()
                self.pregunta_tablas.side_effect = responder
                self.clic(vista, 'f3')
                self.pregunta_tablas.assert_called_once()
                if aceptar:
                    self.assertIs(sesion.partida.estado_partida, EstadoPartida.TABLAS)
                    self.assertEqual(pickle.dumps(apoyo.datos_de_juego(sesion.partida)), datos)
                    self.assertEqual(vista.indicador_estado_partida.cget('text'), 'Tablas')
                else:
                    self.assertIs(sesion.partida.estado_partida, EstadoPartida.EN_CURSO)
                    self.assertEqual(sesion.estado_actual.jugadas_sin_captura_ni_peon, 100)
                    self.assertIsNone(sesion.partida.tablero.casillas[posicion('g1')])
                    self.assertIsInstance(sesion.partida.tablero.casillas[posicion('f3')], Caballo)
                self.assertIsNone(vista.origen_seleccionado)
                self.assertIs(vista.estado_mostrado, sesion.estado_actual)
                vista.contenedor.destroy()

    def test_no_pregunta_si_no_corresponde_la_reclamacion_anunciada(self):
        casos = ((98, 'g1f3', False), (100, 'g1f3', False),
                 (99, 'e2e4', False), (99, 'g1g3', False), (99, 'g1f3', True))
        for contador, movimiento, analisis in casos:
            with self.subTest(contador=contador, movimiento=movimiento, analisis=analisis):
                sesion = self.sesion_con_contador(contador)
                vista = self.crear(sesion)
                if analisis:
                    vista.alternar_analisis()
                antes = pickle.dumps(sesion)
                self.pregunta_tablas.reset_mock()
                anuncio = (posicion(movimiento[:2]), posicion(movimiento[2:]))
                self.assertIs(vista._ofrecer_reclamacion_con_movimiento(anuncio), False)
                self.pregunta_tablas.assert_not_called()
                self.assertEqual(pickle.dumps(sesion), antes)
                vista.contenedor.destroy()


if __name__ == '__main__':
    unittest.main(verbosity=2)
