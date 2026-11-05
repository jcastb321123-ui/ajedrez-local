"""Contrato de Sesion, integración local y desacoplamiento de la GUI.

La GUI se prueba con un Casillero simulado, sin abrir ventanas. La sesión
alternativa de prueba sólo verifica el contrato; no implementa IA ni red.
"""

import inspect
import pickle
import unittest
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import Mock, patch

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.interfaz_juego import PiezaPromocion
from ajedrez.partida import CapturaAlPaso, Enroque, EstadoPartida, Partida, MotivoRechazoMovimiento
from ajedrez.piezas import Alfil, Caballo, Color, Reina, Rey, Torre
from ajedrez.sesion import AsignacionColores, EmisorJugador, ModalidadAsignacion, Sesion, SesionLocal


def posicion(casilla):
    return int(casilla[1]) - 1, ord(casilla[0]) - ord("a")


def enviar(sesion, movimiento):
    return sesion.solicitar_movimiento(posicion(movimiento[:2]),
                                      posicion(movimiento[2:]))


def nueva_sesion(modalidad=ModalidadAsignacion.BLANCO_NEGRO):
    return SesionLocal(AsignacionColores(modalidad))


class SesionDePrueba(Sesion):
    """Sólo expone el contrato: no tiene juego, autenticador ni dos emisores."""

    def __init__(self, partida):
        self._partida = partida

    @property
    def partida(self):
        return self._partida

    @property
    def jugada_pendiente(self):
        return None

    @property
    def colores_controlados(self):
        return frozenset((Color.Blanco,))

    def solicitar_movimiento(self, origen, destino):
        raise AssertionError("Esta prueba de consulta no debe enviar movimientos.")

    def elegir_promocion(self, pieza):
        raise AssertionError("Esta prueba de consulta no debe enviar promociones.")


class PruebasContratoSesion(unittest.TestCase):
    def test_sesion_es_abstracta_y_local_es_concreta(self):
        self.assertTrue(inspect.isabstract(Sesion))
        self.assertFalse(inspect.isabstract(SesionLocal))
        with self.assertRaises(TypeError):
            Sesion()
        self.assertIsInstance(nueva_sesion(), Sesion)

    def test_exige_implementar_todo_el_contrato(self):
        class SesionIncompleta(Sesion):
            @property
            def partida(self):
                return Partida()

        with self.assertRaises(TypeError):
            SesionIncompleta()

    def test_familia_y_componentes_se_definen_en_el_mismo_modulo(self):
        for clase in (Sesion, SesionLocal, EmisorJugador, AsignacionColores, ModalidadAsignacion):
            with self.subTest(clase=clase):
                self.assertEqual(clase.__module__, "ajedrez.sesion")
        self.assertIn(Sesion, SesionLocal.__bases__)

    def test_estado_actual_se_consulta_sin_crear_copia_ni_cache(self):
        partida = Partida()
        sesion = SesionDePrueba(partida)
        self.assertIsInstance(Sesion.estado_actual, property)
        inicial = sesion.estado_actual
        self.assertIs(inicial, partida.estado_inicial)
        partida.procesar_solicitud((1, 4), (3, 4))
        self.assertIs(sesion.estado_actual, partida.ultima_jugada.estado_posicion)
        self.assertIs(sesion.estado_actual.estado_anterior, inicial)
        self.assertIsNone(sesion.jugada_pendiente)
        self.assertEqual(sesion.colores_controlados, frozenset((Color.Blanco,)))
        self.assertFalse(hasattr(sesion, "juego"))

    def test_contrato_permite_preseleccionar_el_bando_propio_fuera_de_turno(self):
        class SesionUnBando(SesionDePrueba):
            def __init__(self, partida, color):
                super().__init__(partida)
                self.color = color

            @property
            def colores_controlados(self):
                return frozenset((self.color,))

        for color in Color:
            with self.subTest(color=color):
                partida = Partida()
                sesion = SesionUnBando(partida, color)
                for movimiento in ("e2e4", "e7e5"):
                    antes = pickle.dumps(partida)
                    self.assertEqual(sesion.colores_seleccionables, frozenset((color,)))
                    self.assertEqual(pickle.dumps(partida), antes)
                    partida.procesar_solicitud(posicion(movimiento[:2]),
                                              posicion(movimiento[2:]))
                self.assertEqual(sesion.colores_seleccionables, frozenset((color,)))

    def test_promocion_pendiente_bloquea_tambien_la_preseleccion(self):
        class SesionConPendiente(SesionDePrueba):
            @property
            def jugada_pendiente(self):
                return self.pendiente

        sesion = SesionConPendiente(Partida())
        sesion.pendiente = object()
        self.assertEqual(sesion.colores_seleccionables, frozenset())
        sesion.pendiente = None
        self.assertEqual(sesion.colores_seleccionables, frozenset((Color.Blanco,)))


class PruebasSesionLocal(unittest.TestCase):
    def test_preparacion_y_repartos_conservan_las_relaciones(self):
        for modalidad in ModalidadAsignacion:
            with self.subTest(modalidad=modalidad):
                sesion = nueva_sesion(modalidad)
                self.assertIs(sesion.partida, sesion.juego.partida)
                self.assertIs(sesion.jugada_pendiente, sesion.juego.jugada_pendiente)
                self.assertIs(sesion.autenticador, sesion.juego.autenticador)
                emisores = sesion.emisor_1, sesion.emisor_2
                colores = tuple(sesion.autenticador.autenticar(e.clave) for e in emisores)
                self.assertEqual(set(colores), {Color.Blanco, Color.Negro})
                if modalidad.value is not None:
                    self.assertEqual(colores, modalidad.value)
                self.assertNotEqual(emisores[0].clave, emisores[1].clave)
                for emisor in emisores:
                    self.assertIs(emisor.juego, sesion.juego)

    def test_las_sesiones_son_independientes(self):
        primera, segunda = nueva_sesion(), nueva_sesion()
        self.assertIsNot(primera.partida, segunda.partida)
        self.assertIsNot(primera.autenticador, segunda.autenticador)
        enviar(primera, "e2e4")
        self.assertEqual(segunda.partida.contador_jugadas, 0)
        self.assertIsNone(segunda.autenticador.autenticar(primera.emisor_1.clave))

    def test_ambos_colores_controlados_no_dependen_del_turno_ni_del_resultado(self):
        sesion = nueva_sesion()
        colores = frozenset((Color.Blanco, Color.Negro))
        self.assertEqual(sesion.colores_controlados, colores)
        self.assertIsInstance(sesion.colores_controlados, frozenset)
        enviar(sesion, "e2e4")
        self.assertEqual(sesion.partida.jugador, Color.Negro)
        self.assertEqual(sesion.colores_controlados, colores)
        sesion.partida.estado_partida = EstadoPartida.TABLAS
        self.assertEqual(sesion.colores_controlados, colores)

    def test_seleccion_local_sigue_el_turno_sin_cambiar_los_colores_controlados(self):
        for modalidad in ModalidadAsignacion:
            with self.subTest(modalidad=modalidad):
                sesion = nueva_sesion(modalidad)
                for movimiento, color in (("e2e4", Color.Blanco), ("e7e5", Color.Negro)):
                    antes = pickle.dumps(sesion.partida)
                    self.assertEqual(sesion.colores_seleccionables, frozenset((color,)))
                    self.assertEqual(sesion.colores_controlados,
                                     frozenset((Color.Blanco, Color.Negro)))
                    self.assertEqual(pickle.dumps(sesion.partida), antes)
                    enviar(sesion, movimiento)
                self.assertEqual(sesion.colores_seleccionables, frozenset((Color.Blanco,)))

    def test_partida_local_finalizada_permite_seleccionar_ambos_bandos(self):
        sesion = nueva_sesion()
        for estado in (EstadoPartida.TABLAS, EstadoPartida.VICTORIA_BLANCA,
                       EstadoPartida.VICTORIA_NEGRA):
            with self.subTest(estado=estado):
                sesion.partida.estado_partida = estado
                antes = pickle.dumps(sesion.partida)
                self.assertEqual(sesion.colores_seleccionables,
                                 frozenset((Color.Blanco, Color.Negro)))
                self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_solicitud_elige_emisor_por_turno_y_pasa_por_autenticacion(self):
        sesion = nueva_sesion(ModalidadAsignacion.NEGRO_BLANCO)
        with patch.object(sesion.juego, "solicitar_movimiento",
                          wraps=sesion.juego.solicitar_movimiento) as solicitar:
            # Pulsar una pieza negra no debe cambiar la identidad a negras.
            self.assertIs(enviar(sesion, "e7e5"), MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO)
            solicitar.assert_called_once_with(sesion.emisor_2.clave, (6, 4), (4, 4))
            self.assertEqual(sesion.partida.contador_jugadas, 0)
            solicitar.reset_mock()
            self.assertIsNone(enviar(sesion, "e2e4"))
            solicitar.assert_called_once_with(sesion.emisor_2.clave, (1, 4), (3, 4))
            solicitar.reset_mock()
            self.assertIsNone(enviar(sesion, "e7e5"))
            solicitar.assert_called_once_with(sesion.emisor_1.clave, (6, 4), (4, 4))
        self.assertEqual(sesion.partida.contador_jugadas, 2)

    def test_rechazos_no_modifican_la_partida(self):
        sesion = nueva_sesion()
        antes = pickle.dumps(sesion.partida)
        for movimiento in ("e3e4", "e7e5", "e2f3", "e2e5"):
            with self.subTest(movimiento=movimiento):
                self.assertIs(enviar(sesion, movimiento), MotivoRechazoMovimiento.MOVIMIENTO_INVALIDO)
                self.assertEqual(pickle.dumps(sesion.partida), antes)
                self.assertIs(sesion.estado_actual, sesion.partida.estado_inicial)

    def test_enroque_y_captura_al_paso_a_traves_de_sesion(self):
        casos = (
            ("e2e4 a7a6 g1f3 a6a5 f1e2 b7b6 e1g1", Enroque),
            ("e2e4 a7a6 e4e5 d7d5 e5d6", CapturaAlPaso),
        )
        for movimientos, clase in casos:
            with self.subTest(clase=clase):
                sesion = nueva_sesion()
                for numero, movimiento in enumerate(movimientos.split(), 1):
                    enviar(sesion, movimiento)
                    self.assertEqual(sesion.partida.contador_jugadas, numero)
                self.assertIsInstance(sesion.partida.ultima_jugada, clase)
                if clase is Enroque:
                    self.assertIsInstance(sesion.partida.tablero.pieza_en((0, 6)), Rey)
                    self.assertIsInstance(sesion.partida.tablero.pieza_en((0, 5)), Torre)
                else:
                    self.assertIsNone(sesion.partida.tablero.pieza_en((4, 3)))

    def test_promociones_de_ambos_colores_y_todos_los_repartos(self):
        casos = (
            ("a2a4 b7b5 a4b5 a7a6 b5a6 h7h6 a6a7 h6h5 a7b8", "h5h4"),
            ("h2h3 a7a5 b2b4 a5b4 a2a3 b4a3 h3h4 a3a2 h4h5 a2b1", "h5h6"),
        )
        opciones = ((PiezaPromocion.REINA, Reina), (PiezaPromocion.TORRE, Torre),
                    (PiezaPromocion.ALFIL, Alfil), (PiezaPromocion.CABALLO, Caballo))
        for modalidad in ModalidadAsignacion:
            for movimientos, siguiente in casos:
                for opcion, clase in opciones:
                    with self.subTest(modalidad=modalidad, ultimo=movimientos[-4:], opcion=opcion):
                        sesion = nueva_sesion(modalidad)
                        lista = movimientos.split()
                        for movimiento in lista:
                            enviar(sesion, movimiento)
                        pendiente = sesion.jugada_pendiente
                        self.assertIsNotNone(pendiente)
                        self.assertEqual(sesion.colores_seleccionables, frozenset())
                        self.assertIs(pendiente, sesion.juego.jugada_pendiente)
                        aceptado = sesion.estado_actual
                        self.assertIs(aceptado, sesion.partida.ultima_jugada.estado_posicion)
                        self.assertIsNot(aceptado, pendiente.estado_posicion)
                        self.assertEqual(sesion.partida.contador_jugadas, len(lista) - 1)
                        enviar(sesion, siguiente)
                        self.assertIs(sesion.estado_actual, aceptado)
                        self.assertIs(sesion.jugada_pendiente, pendiente)
                        emisor = next(e for e in (sesion.emisor_1, sesion.emisor_2)
                                      if sesion.autenticador.autenticar(e.clave) == pendiente.pieza.color)
                        with patch.object(sesion.juego, "aplicar_promocion",
                                          wraps=sesion.juego.aplicar_promocion) as aplicar:
                            sesion.elegir_promocion(opcion)
                            aplicar.assert_called_once_with(emisor.clave, opcion)
                        self.assertIsNone(sesion.jugada_pendiente)
                        self.assertEqual(sesion.colores_seleccionables,
                                         frozenset((sesion.partida.jugador,)))
                        self.assertIs(sesion.estado_actual, pendiente.estado_posicion)
                        self.assertIsInstance(sesion.partida.tablero.pieza_en(pendiente.destino), clase)
                        self.assertEqual(sesion.partida.contador_jugadas, len(lista))
                        enviar(sesion, siguiente)
                        self.assertEqual(sesion.partida.contador_jugadas, len(lista) + 1)


class PruebasInterfazConSesion(unittest.TestCase):
    def setUp(self):
        # Estos tests aíslan el contrato de sesión; los paneles reales se prueban
        # por separado con Tk, no se construyen widgets a partir de un Mock.
        parche = patch.object(InterfazPartida, "_crear_panel_navegacion")
        parche.start()
        self.addCleanup(parche.stop)

    def test_interfaz_depende_del_contrato_no_de_sesion_local(self):
        self.assertIs(get_type_hints(InterfazPartida.__init__)["sesion"], Sesion)
        sesion = SesionDePrueba(Partida())
        casillero = Mock()
        casillero.casillas = {}
        vista = InterfazPartida(sesion, casillero)
        self.assertIs(vista.sesion, sesion)
        self.assertIs(vista.casillero, casillero)
        self.assertIs(vista.estado_mostrado, sesion.estado_actual)
        casillero.canvas.bind.assert_any_call("<Button-1>", vista.gestionar_clic_izquierdo)
        casillero.canvas.bind.assert_any_call("<Destroy>", vista._al_destruir_canvas, add="+")
        casillero.mostrar_posicion.assert_not_called()

    def test_constructor_y_navegacion_no_cambian_el_estado_actual(self):
        partida = Partida()
        partida.procesar_solicitud((1, 4), (3, 4))
        sesion = SesionDePrueba(partida)
        casillero = Mock()
        casillero.casillas = {}
        vista = InterfazPartida(sesion, casillero)
        actual = sesion.estado_actual
        self.assertIs(vista.estado_mostrado, actual)
        antes = pickle.dumps(partida)
        vista.origen_seleccionado = (3, 4)
        vista.mostrar_estado(partida.estado_inicial)
        self.assertIs(vista.estado_mostrado, partida.estado_inicial)
        self.assertIs(sesion.estado_actual, actual)
        self.assertIsNone(vista.origen_seleccionado)
        self.assertEqual(pickle.dumps(partida), antes)
        distribucion = casillero.mostrar_posicion.call_args.args[0]
        self.assertEqual(distribucion[(1, 4)], ("peon", Color.Blanco, "normal"))
        self.assertNotIn((3, 4), distribucion)

    def test_constructor_declara_widgets_aunque_no_se_construya_el_panel(self):
        casillero = Mock()
        casillero.casillas = {}
        vista = InterfazPartida(SesionDePrueba(Partida()), casillero)
        for nombre in ('_indicador_contexto', '_indicador_estado_partida',
                       '_boton_modo_analisis', '_panel_analisis'):
            with self.subTest(atributo=nombre):
                self.assertIn(nombre, vars(vista))
                self.assertIsNone(getattr(vista, nombre))
        self.assertEqual(vista._disposicion_original, [])
        vista._actualizar_indicador_contexto()

    def test_retroceso_consulta_partida_sin_requerir_juego_local(self):
        partida = Partida()
        partida.procesar_solicitud((1, 4), (3, 4))
        sesion = SesionDePrueba(partida)
        casillero = Mock()
        casillero.casillas = {(3, 4): SimpleNamespace(id_pieza=42)}
        vista = InterfazPartida(sesion, casillero)
        antes = pickle.dumps(partida)
        vista.origen_seleccionado = (3, 4)
        vista.retroceder_movimiento()
        casillero.desplazar_pieza.assert_called_once_with(42, (3, 4), (1, 4))
        self.assertIs(vista.estado_mostrado, partida.estado_inicial)
        self.assertIsNone(vista.origen_seleccionado)
        self.assertEqual(pickle.dumps(partida), antes)
        vista.retroceder_movimiento()
        self.assertEqual(casillero.desplazar_pieza.call_count, 1)


if __name__ == "__main__":
    unittest.main()
