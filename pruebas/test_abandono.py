"""Abandono: resultado, contrato de sesión y controles gráficos reales."""
import inspect
import pickle
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ajedrez.gráficos.interfaz_partida as modulo_interfaz
from ajedrez.editor_posicion import EditorPosicion
from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.gráficos.temas_graficos import cargar_tema
from ajedrez.partida import Partida, EstadoPartida
from ajedrez.piezas import Color, Rey, PeonBlanco
from ajedrez.sesion import Sesion, SesionLocal, SesionAnalisis, AsignacionColores, ModalidadAsignacion
from pruebas.test_analisis_partida import estado_minimo, posicion, mover
from pruebas.test_sesion import nueva_sesion, enviar


def datos_de_juego(partida):
    """Datos que el abandono debe conservar, excluyendo el resultado."""
    return (partida.estado_inicial, partida.tablero, partida.ultima_jugada,
            partida.registro_turnos, partida.jugador, partida.contador_jugadas,
            partida.promocion_pendiente)


class SesionUnColor(SesionLocal):
    """Doble para comprobar un solo color controlado, sin implementar IA o red."""

    def __init__(self, color):
        self._color_prueba = color
        super().__init__(AsignacionColores(ModalidadAsignacion.BLANCO_NEGRO))

    @property
    def colores_controlados(self):
        return frozenset((self._color_prueba,))


class PruebasAbandonoModelo(unittest.TestCase):
    def test_abandono_resuelve_resultado_y_conserva_posicion_turno_historial(self):
        for movimientos in ((), ('e2e4',), ('e2e4', 'd7d5', 'e4d5')):
            for color, esperado in ((Color.Blanco, EstadoPartida.VICTORIA_NEGRA),
                                    (Color.Negro, EstadoPartida.VICTORIA_BLANCA)):
                with self.subTest(movimientos=movimientos, color=color):
                    partida = Partida()
                    for movimiento in movimientos:
                        self.assertIsNone(mover(partida, movimiento))
                    referencias = datos_de_juego(partida)
                    contenido = pickle.dumps(referencias)
                    self.assertIsNone(partida.abandonar(color))
                    self.assertIs(partida.estado_partida, esperado)
                    self.assertEqual(pickle.dumps(datos_de_juego(partida)), contenido)
                    for anterior, actual in zip(referencias[:4], datos_de_juego(partida)[:4]):
                        self.assertIs(actual, anterior)

    def test_solicitud_por_sesion_identifica_al_jugador_al_margen_del_turno(self):
        for modalidad in ModalidadAsignacion:
            for color in Color:
                for movimientos in ((), ('e2e4',)):
                    with self.subTest(modalidad=modalidad, color=color, movimientos=movimientos):
                        sesion = nueva_sesion(modalidad)
                        for movimiento in movimientos:
                            self.assertIsNone(enviar(sesion, movimiento))
                        antes = pickle.dumps(datos_de_juego(sesion.partida))
                        self.assertTrue(sesion.admite_abandono)
                        self.assertIsNone(sesion.solicitar_abandono(color))
                        esperado = (EstadoPartida.VICTORIA_NEGRA if color is Color.Blanco
                                    else EstadoPartida.VICTORIA_BLANCA)
                        self.assertIs(sesion.partida.estado_partida, esperado)
                        self.assertEqual(pickle.dumps(datos_de_juego(sesion.partida)), antes)
                        self.assertTrue(sesion.admite_abandono)

    def test_el_abandono_es_opcional_en_el_contrato_de_sesion(self):
        self.assertNotIn('solicitar_abandono', Sesion.__abstractmethods__)
        self.assertFalse(inspect.isabstract(SesionAnalisis))
        original = Partida()
        sesion = SesionAnalisis(original.estado_inicial, Color.Blanco)
        antes = pickle.dumps(sesion.partida)
        self.assertFalse(sesion.admite_abandono)
        with self.assertRaises(NotImplementedError):
            sesion.solicitar_abandono(Color.Blanco)
        self.assertEqual(pickle.dumps(sesion.partida), antes)


class PruebasBotonesAbandono(unittest.TestCase):
    def setUp(self):
        try:
            self.raiz = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f'Tkinter no dispone de pantalla: {error}')
        self.raiz.withdraw()
        self.addCleanup(self.raiz.destroy)
        self.errores = []
        self.raiz.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)
        self.tema = cargar_tema(self.raiz)

    def tearDown(self):
        self.assertFalse(self.errores)

    def crear(self, sesion):
        contenedor = tk.Frame(self.raiz)
        contenedor.pack()
        vista = InterfazPartida(sesion, Casillero(contenedor, self.tema), contenedor=contenedor)
        vista.mostrar_estado(sesion.estado_actual)
        return vista

    def clic(self, vista, casilla):
        fila, columna = posicion(casilla)
        vista.gestionar_clic_izquierdo(SimpleNamespace(x=60 * columna + 30, y=60 * (7 - fila) + 30))

    def test_confirmar_y_cancelar_con_uno_y_dos_colores(self):
        for unico in (None, Color.Blanco, Color.Negro):
            colores = tuple(Color) if unico is None else (unico,)
            for color in colores:
                for respuesta in (False, True):
                    with self.subTest(unico=unico, color=color, respuesta=respuesta):
                        sesion = nueva_sesion() if unico is None else SesionUnColor(unico)
                        self.assertIsNone(enviar(sesion, 'e2e4'))
                        vista = self.crear(sesion)
                        vista.origen_seleccionado = posicion('e7')
                        vista.casillero.aplicar_marca(posicion('e7'), 'seleccion')
                        antes = pickle.dumps(sesion.partida)
                        datos = pickle.dumps(datos_de_juego(sesion.partida))
                        dibujos = vista.casillero.canvas.find_all()
                        mostrado = vista.estado_mostrado
                        with patch.object(modulo_interfaz.messagebox, 'askyesno', return_value=respuesta) as dialogo:
                            vista.botones_abandono[color].invoke()
                        dialogo.assert_called_once()
                        self.assertIs(dialogo.call_args.kwargs['parent'], vista.contenedor)
                        self.assertFalse(self.errores)
                        if respuesta:
                            esperado = (EstadoPartida.VICTORIA_NEGRA if color is Color.Blanco
                                        else EstadoPartida.VICTORIA_BLANCA)
                            self.assertIs(sesion.partida.estado_partida, esperado)
                            self.assertEqual(pickle.dumps(datos_de_juego(sesion.partida)), datos)
                            self.assertIsNone(vista.origen_seleccionado)
                            self.assertIs(vista.estado_mostrado, mostrado)
                            self.assertTrue(all(b.cget('state') == 'disabled' for b in vista.botones_abandono.values()))
                            self.assertEqual(vista.indicador_estado_partida.cget('text'),
                                             'Victoria de negras' if color is Color.Blanco else 'Victoria de blancas')
                        else:
                            self.assertEqual(pickle.dumps(sesion.partida), antes)
                            self.assertEqual(vista.origen_seleccionado, posicion('e7'))
                            self.assertEqual(vista.casillero.canvas.find_all(), dibujos)
                        vista.contenedor.destroy()

    def test_botones_colocados_y_registrados_por_color(self):
        for unico in (None, Color.Blanco, Color.Negro):
            with self.subTest(unico=unico):
                sesion = nueva_sesion() if unico is None else SesionUnColor(unico)
                vista = self.crear(sesion)
                self.assertEqual(set(vista.botones_abandono), set(sesion.colores_controlados))
                for color, boton in vista.botones_abandono.items():
                    self.assertIn(boton.winfo_manager(), ('pack', 'grid'))
                    esperado = ('Abandonar' if unico is not None else
                                'Abandonar blancas' if color is Color.Blanco else 'Abandonar negras')
                    self.assertEqual(boton.cget('text'), esperado)
                vista.contenedor.destroy()

    def test_analisis_no_ofrece_abandono(self):
        sesion = SesionAnalisis(Partida().estado_inicial, Color.Blanco)
        vista = self.crear(sesion)
        self.assertEqual(vista.botones_abandono, {})

    def test_promocion_bloquea_y_actualiza_los_botones(self):
        for indice, resultado in ((0, EstadoPartida.TABLAS), (3, EstadoPartida.VICTORIA_BLANCA)):
            with self.subTest(eleccion=indice):
                piezas = {'h6': Rey(Color.Blanco), 'h8': Rey(Color.Negro), 'f7': PeonBlanco()}
                estado = EditorPosicion(estado_minimo(piezas), Color.Blanco).construir_estado(
                    turno=Color.Blanco, enroques=set())
                sesion = nueva_sesion()
                sesion.juego._partida = Partida(estado_inicial=estado, turno_inicial=Color.Blanco)
                vista = self.crear(sesion)
                self.clic(vista, 'f7')
                self.clic(vista, 'f8')
                self.assertIsNotNone(vista.promocion_pendiente)
                self.assertTrue(all(b.cget('state') == 'disabled' for b in vista.botones_abandono.values()))
                selector = next(w for w in vista.casillero.contenedor.winfo_children()
                                if isinstance(w, tk.Frame) and w.winfo_manager() == 'place')
                opciones = [w for w in selector.winfo_children() if isinstance(w, tk.Button)]
                opciones[indice].invoke()
                self.assertIsNone(vista.promocion_pendiente)
                self.assertIs(sesion.partida.estado_partida, resultado)
                estado_boton = 'normal' if resultado is EstadoPartida.EN_CURSO else 'disabled'
                self.assertTrue(all(b.cget('state') == estado_boton for b in vista.botones_abandono.values()))
                vista.contenedor.destroy()

    def test_tras_abandonar_se_puede_analizar_sin_modificar_la_partida(self):
        sesion = nueva_sesion()
        self.assertIsNone(enviar(sesion, 'e2e4'))
        vista = self.crear(sesion)
        with patch.object(modulo_interfaz.messagebox, 'askyesno', return_value=True):
            vista.botones_abandono[Color.Negro].invoke()
        self.assertIs(sesion.partida.estado_partida, EstadoPartida.VICTORIA_BLANCA)
        original = pickle.dumps(sesion.partida)
        with patch.object(modulo_interfaz.messagebox, 'askyesno') as dialogo:
            vista.botones_abandono[Color.Blanco].invoke()
        dialogo.assert_not_called()
        self.clic(vista, 'e7')
        self.clic(vista, 'e5')
        self.assertIsNot(vista.sesion_movimientos.partida, sesion.partida)
        self.assertEqual(pickle.dumps(sesion.partida), original)
        hipotetico = vista.estado_mostrado
        vista.retroceder_movimiento()
        self.assertIs(vista.estado_mostrado, sesion.estado_actual)
        vista.avanzar_movimiento()
        self.assertIs(vista.estado_mostrado, hipotetico)
        self.assertEqual(pickle.dumps(sesion.partida), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
