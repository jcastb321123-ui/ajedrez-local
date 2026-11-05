"""Configuración, consultas de jaque e integración con un Canvas real oculto.

Las imágenes de prueba no verifican el aspecto artístico. Los temporizadores
se prueban tanto de forma controlada como mediante el bucle real de Tk.
"""

from contextlib import contextmanager
from dataclasses import FrozenInstanceError, dataclass, replace
import pickle
import time
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.gráficos.opciones_visuales import (
    ModoResaltadoJaque as Modo, OpcionesVisuales, OPCIONES_VISUALES_PREDETERMINADAS,
)
from ajedrez.gráficos.temas_graficos import EstiloMarca
from ajedrez.partida import EstadoPosicion, Jugada, Enroque, MotivoRechazoMovimiento as Rechazo
from ajedrez.piezas import Color, Rey, Torre, Alfil, Caballo, Reina
from ajedrez.tablero import Tablero
from pruebas.test_marcas_graficas import crear_tema
from pruebas.test_sesion import enviar, nueva_sesion, posicion


class PruebasOpcionesVisuales(unittest.TestCase):
    def test_predeterminadas_inmutables_y_solo_por_nombre(self):
        opciones = OpcionesVisuales()
        self.assertEqual(opciones, OPCIONES_VISUALES_PREDETERMINADAS)
        self.assertIs(opciones.modo_resaltado_jaque, Modo.REY_PERMANENTE)
        with self.assertRaises(FrozenInstanceError):
            opciones.modo_resaltado_jaque = Modo.REY_Y_ATACANTES
        with self.assertRaises(TypeError):
            OpcionesVisuales(Modo.REY_Y_ATACANTES)

    def test_replace_conserva_los_campos_no_modificados(self):
        originales = OpcionesVisuales(intervalo_parpadeo_jaque_ms=400,
                                     repeticiones_parpadeo_jaque=2)
        nuevas = replace(originales, modo_resaltado_jaque=Modo.REY_Y_ATACANTES)
        self.assertIsNot(nuevas, originales)
        self.assertEqual(nuevas.intervalo_parpadeo_jaque_ms, 400)
        self.assertEqual(nuevas.repeticiones_parpadeo_jaque, 2)
        self.assertIs(originales.modo_resaltado_jaque, Modo.REY_PERMANENTE)
        self.assertEqual(OPCIONES_VISUALES_PREDETERMINADAS, OpcionesVisuales())

    def test_clase_ampliable_con_campos_y_metodos(self):
        @dataclass(frozen=True, kw_only=True)
        class Ampliadas(OpcionesVisuales):
            mostrar_coordenadas: bool = True

            def coordenadas_activadas(self):
                return self.mostrar_coordenadas

        opciones = Ampliadas(mostrar_coordenadas=False)
        self.assertTrue(hasattr(opciones, '__dict__'))
        self.assertFalse(opciones.coordenadas_activadas())
        self.assertIsInstance(replace(opciones, repeticiones_parpadeo_jaque=1), Ampliadas)

    def test_valores_invalidos_no_crean_configuraciones(self):
        with self.assertRaises(TypeError):
            OpcionesVisuales(modo_resaltado_jaque='desconocido')
        for campo in ('intervalo_parpadeo_jaque_ms', 'repeticiones_parpadeo_jaque'):
            for valor in (0, -1, True, 0.5):
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    OpcionesVisuales(**{campo: valor})


def tablero_con_piezas(piezas):
    tablero = Tablero()
    for casilla in tablero.casillas:
        tablero.colocar(None, casilla)
    for casilla, pieza in piezas.items():
        tablero.colocar(pieza, posicion(casilla))
    return tablero


class PruebasDiagnosticoJaque(unittest.TestCase):
    def test_todos_los_atacantes_sin_mutar_el_tablero(self):
        tablero = tablero_con_piezas({
            'e1': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
            'e8': Torre(Color.Negro), 'b4': Alfil(Color.Negro),
        })
        antes = pickle.dumps(tablero)
        self.assertEqual(set(tablero.obtener_atacantes_del_rey(Color.Blanco)),
                         {posicion('e8'), posicion('b4')})
        self.assertTrue(tablero.el_rey_queda_en_jaque(Color.Blanco))
        self.assertFalse(tablero.el_rey_queda_en_jaque(Color.Negro))
        self.assertEqual(tablero.obtener_atacantes_del_rey(Color.Negro), ())
        self.assertEqual(pickle.dumps(tablero), antes)

    def test_rechazo_por_jaque_distinto_de_movimiento_imposible(self):
        sesion = nueva_sesion()
        for movimiento in 'e2e4 f7f6 d1h5'.split():
            self.assertIsNone(enviar(sesion, movimiento))
        antes = pickle.dumps(sesion.partida)
        self.assertIs(enviar(sesion, 'g7g5'), Rechazo.REY_EN_JAQUE)
        self.assertIsNone(sesion.jugada_pendiente)
        self.assertEqual(pickle.dumps(sesion.partida), antes)
        self.assertIs(enviar(sesion, 'g7g4'), Rechazo.MOVIMIENTO_INVALIDO)
        self.assertEqual(pickle.dumps(sesion.partida), antes)
        self.assertIs(sesion.juego.solicitar_movimiento('desconocida', posicion('g7'), posicion('g5')),
                      Rechazo.NO_AUTORIZADO)
        self.assertEqual(pickle.dumps(sesion.partida), antes)
        self.assertIsNone(enviar(sesion, 'g7g6'))
        self.assertFalse(sesion.estado_actual.tablero.el_rey_queda_en_jaque(Color.Negro))

    def test_mover_una_pieza_clavada_comunica_jaque(self):
        tablero = tablero_con_piezas({
            'e1': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
            'e8': Torre(Color.Negro), 'e2': Torre(Color.Blanco),
        })
        raiz = EstadoPosicion(tablero=tablero)
        antes = pickle.dumps(raiz)
        jugada = Jugada(1, posicion('e2'), posicion('f2'), None, estado_inicial=raiz)
        self.assertFalse(jugada.estado_posicion.movimiento_valido)
        self.assertIs(jugada.estado_posicion.motivo_rechazo, Rechazo.REY_EN_JAQUE)
        self.assertEqual(pickle.dumps(raiz), antes)

    def test_enroque_desde_jaque_comunica_el_motivo(self):
        tablero = tablero_con_piezas({
            'e1': Rey(Color.Blanco), 'h1': Torre(Color.Blanco),
            'a8': Rey(Color.Negro), 'e8': Torre(Color.Negro),
        })
        jugada = Enroque(1, posicion('e1'), posicion('g1'), None,
                        estado_inicial=EstadoPosicion(tablero=tablero))
        self.assertFalse(jugada.estado_posicion.movimiento_valido)
        self.assertIs(jugada.estado_posicion.motivo_rechazo, Rechazo.REY_EN_JAQUE)


class PruebasIndicadoresJaque(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ventana = tk.Tk()
        except tk.TclError as error:
            raise unittest.SkipTest(str(error)) from error
        cls.ventana.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.ventana.destroy()

    def setUp(self):
        self.errores = []
        self.ventana.report_callback_exception = lambda tipo, valor, traza: self.errores.append(valor)
        self.imagen = tk.PhotoImage(master=self.ventana, width=60, height=60)
        self.tema = crear_tema(self.imagen)
        for nombre in ('peon', 'caballo', 'alfil', 'torre', 'dama', 'rey'):
            for color in Color:
                self.tema.piezas[nombre, color, 'normal'] = self.imagen
        self.sesion = nueva_sesion()
        self.casillero = Casillero(self.ventana, self.tema)
        self.interfaz = InterfazPartida(self.sesion, self.casillero)
        self.addCleanup(self.casillero.contenedor.destroy)

    def clic(self, casilla):
        fila, columna = posicion(casilla)
        self.interfaz.gestionar_clic_izquierdo(
            SimpleNamespace(x=columna * 60 + 30, y=(7-fila) * 60 + 30))

    def jugar(self, movimientos):
        for movimiento in movimientos.split():
            self.clic(movimiento[:2])
            self.clic(movimiento[2:])

    def marcadas(self, clave):
        return {posicion for posicion, casilla in self.casillero.casillas.items()
                if f'marca:{clave}' in casilla.ids_elementos_por_clave}

    def modo(self, modo, **cambios):
        self.interfaz.aplicar_opciones_visuales(
            replace(self.interfaz.opciones_visuales, modo_resaltado_jaque=modo, **cambios))

    @contextmanager
    def reloj_controlado(self):
        pendientes = {}
        contador = 0

        def programar(intervalo, funcion, *argumentos):
            nonlocal contador
            contador += 1
            identificador = f'prueba-{contador}'
            pendientes[identificador] = (funcion, argumentos)
            return identificador

        with patch.object(self.casillero.canvas, 'after', side_effect=programar), \
             patch.object(self.casillero.canvas, 'after_cancel', side_effect=lambda id: pendientes.pop(id, None)):
            try:
                yield pendientes
            finally:
                self.interfaz._cancelar_parpadeo_jaque()

    def test_defecto_jaque_resuelto_historial_y_rechazo_conservan_modelo(self):
        self.assertFalse(self.marcadas('jaque'))
        self.jugar('e2e4 f7f6 d1h5')
        self.assertEqual(self.marcadas('jaque'), {posicion('e8')})
        self.assertFalse(self.marcadas('atacante_jaque'))
        antes = pickle.dumps(self.sesion.partida)
        id_jaque = self.casillero.canvas.find_withtag('marca:jaque')
        self.jugar('g7g5')
        self.assertEqual(pickle.dumps(self.sesion.partida), antes)
        self.assertEqual(self.interfaz.origen_seleccionado, posicion('g7'))
        self.assertEqual(self.casillero.canvas.find_withtag('marca:jaque'), id_jaque)
        self.clic('g6')
        self.assertFalse(self.marcadas('jaque'))
        vigente = self.sesion.estado_actual
        self.interfaz.retroceder_movimiento()
        self.assertEqual(self.marcadas('jaque'), {posicion('e8')})
        self.assertIs(self.sesion.estado_actual, vigente)
        self.interfaz.mostrar_estado(self.sesion.partida.estado_inicial)
        self.assertFalse(self.marcadas('jaque'))

    def test_sustitucion_y_restauracion_conservan_notas_piezas_y_seleccion(self):
        self.jugar('e2e4 f7f6 d1h5')
        self.clic('g7')
        self.casillero.aplicar_marca(posicion('h5'), 'circulo_ambar')
        self.casillero.aplicar_marca(posicion('c3'), 'fondo_azul')
        antes = pickle.dumps(self.sesion.partida)
        ajenos = set(self.casillero.canvas.find_all()) - set(self.casillero.canvas.find_withtag('marca:jaque'))
        self.modo(Modo.REY_Y_ATACANTES)
        self.assertEqual(self.marcadas('atacante_jaque'), {posicion('h5')})
        self.assertEqual(self.marcadas('jaque'), {posicion('e8')})
        self.assertTrue(ajenos <= set(self.casillero.canvas.find_all()))
        self.interfaz.restablecer_opciones_visuales()
        self.assertIs(self.interfaz.opciones_visuales, OPCIONES_VISUALES_PREDETERMINADAS)
        self.assertFalse(self.marcadas('atacante_jaque'))
        self.assertEqual(self.marcadas('circulo_ambar'), {posicion('h5')})
        self.assertEqual(self.interfaz.origen_seleccionado, posicion('g7'))
        self.assertEqual(pickle.dumps(self.sesion.partida), antes)
        self.assertTrue(ajenos <= set(self.casillero.canvas.find_all()))

    def test_jaque_doble_marca_ambos_atacantes_y_limpieza_es_selectiva(self):
        tablero = tablero_con_piezas({'e1': Rey(Color.Blanco), 'a8': Rey(Color.Negro),
                                     'e8': Torre(Color.Negro), 'b4': Alfil(Color.Negro)})
        self.interfaz.mostrar_estado(EstadoPosicion(tablero=tablero))
        self.modo(Modo.REY_Y_ATACANTES)
        self.assertEqual(self.marcadas('jaque'), {posicion('e1')})
        self.assertEqual(self.marcadas('atacante_jaque'), {posicion('e8'), posicion('b4')})
        for _ in range(5):
            self.interfaz.actualizar_resaltado_jaque()
        self.assertEqual(len(self.casillero.canvas.find_withtag('marca:jaque')), 1)
        self.assertEqual(len(self.casillero.canvas.find_withtag('marca:atacante_jaque')), 2)
        self.casillero.limpiar_anotaciones_temporales()
        self.assertEqual(len(self.marcadas('atacante_jaque')), 2)

    def test_parpadeo_solo_ante_rechazo_por_jaque_y_finaliza(self):
        self.modo(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.jugar('e2e4 f7f6 d1h5')
        self.assertFalse(self.marcadas('jaque'))
        with self.reloj_controlado() as pendientes:
            self.jugar('g7g4')
            self.assertFalse(pendientes)
            self.assertFalse(self.marcadas('jaque'))
            antes = pickle.dumps(self.sesion.partida)
            self.clic('g5')
            visibilidad = [bool(self.marcadas('jaque'))]
            while pendientes:
                identificador = next(iter(pendientes))
                funcion, argumentos = pendientes.pop(identificador)
                funcion(*argumentos)
                visibilidad.append(bool(self.marcadas('jaque')))
            self.assertEqual(visibilidad, [True, False, True, False, True, False])
            self.assertIsNone(self.interfaz._id_parpadeo_jaque)
            self.assertEqual(pickle.dumps(self.sesion.partida), antes)
            self.assertEqual(self.interfaz.origen_seleccionado, posicion('g7'))

    def test_repetir_rechazo_no_acumula_temporizadores(self):
        self.modo(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.jugar('e2e4 f7f6 d1h5')
        with self.reloj_controlado() as pendientes:
            self.jugar('g7g5')
            anterior = next(iter(pendientes))
            self.clic('g5')
            self.assertEqual(len(pendientes), 1)
            self.assertNotIn(anterior, pendientes)
            self.assertEqual(len(self.casillero.canvas.find_withtag('marca:jaque')), 1)

    def test_cambio_de_opciones_y_movimiento_cancelan_parpadeo(self):
        self.modo(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.jugar('e2e4 f7f6 d1h5')
        with self.reloj_controlado() as pendientes:
            self.jugar('g7g5')
            self.interfaz.restablecer_opciones_visuales()
            self.assertFalse(pendientes)
            self.assertEqual(self.marcadas('jaque'), {posicion('e8')})
            self.modo(Modo.INTERMITENTE_TRAS_RECHAZO)
            self.clic('g5')
            self.assertTrue(pendientes)
            self.clic('g6')
            self.assertFalse(pendientes)
            self.assertFalse(self.marcadas('jaque'))

    def test_navegacion_y_destruccion_cancelan_parpadeo(self):
        self.modo(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.jugar('e2e4 f7f6 d1h5')
        with self.reloj_controlado() as pendientes:
            self.jugar('g7g5')
            self.interfaz.retroceder_movimiento()
            self.assertFalse(pendientes)
            self.assertFalse(self.marcadas('jaque'))
            self.interfaz.mostrar_estado(self.sesion.estado_actual)
            self.jugar('g7g5')
            self.assertTrue(pendientes)
            self.casillero.canvas.destroy()
            self.assertFalse(pendientes)
        self.assertFalse(self.errores)

    def test_temporizador_real_de_tk(self):
        self.modo(Modo.INTERMITENTE_TRAS_RECHAZO,
                  intervalo_parpadeo_jaque_ms=5, repeticiones_parpadeo_jaque=1)
        self.jugar('e2e4 f7f6 d1h5 g7g5')
        self.assertEqual(self.marcadas('jaque'), {posicion('e8')})
        limite = time.monotonic() + 2
        while self.interfaz._id_parpadeo_jaque is not None and time.monotonic() < limite:
            self.ventana.update()
            time.sleep(0.001)
        self.assertIsNone(self.interfaz._id_parpadeo_jaque)
        self.assertFalse(self.marcadas('jaque'))
        self.assertFalse(self.errores)

    def test_dos_vistas_tienen_preferencias_independientes(self):
        self.jugar('e2e4 f7f6 d1h5')
        otro = Casillero(self.ventana, self.tema,
                        distribucion=self.interfaz._obtener_distribucion(self.sesion.estado_actual))
        self.addCleanup(otro.contenedor.destroy)
        vista = InterfazPartida(self.sesion, otro,
                               opciones_visuales=OpcionesVisuales(modo_resaltado_jaque=Modo.INTERMITENTE_TRAS_RECHAZO))
        self.assertFalse(otro.canvas.find_withtag('marca:jaque'))
        self.modo(Modo.REY_Y_ATACANTES)
        self.assertIs(vista.opciones_visuales.modo_resaltado_jaque, Modo.INTERMITENTE_TRAS_RECHAZO)
        self.assertEqual(self.marcadas('atacante_jaque'), {posicion('h5')})

    def test_tema_reutiliza_recurso_sin_modificar_diccionario_del_llamador(self):
        marcas = dict(self.tema.marcas)
        marcas.pop('atacante_jaque')
        from ajedrez.gráficos.temas_graficos import TemaGrafico
        tema = TemaGrafico('alternativo', 60, {}, {}, {}, marcas, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})
        self.assertNotIn('atacante_jaque', marcas)
        self.assertIs(tema.marcas['atacante_jaque'], marcas['circulo_ambar'])
        self.assertEqual(tema.estilos_marcas['atacante_jaque'], EstiloMarca('marca', 'estado'))

    def test_constructor_aplica_el_modo_a_una_posicion_ya_en_jaque(self):
        self.jugar('e2e4 f7f6 d1h5')
        otro = Casillero(self.ventana, self.tema,
                        distribucion=self.interfaz._obtener_distribucion(self.sesion.estado_actual))
        self.addCleanup(otro.contenedor.destroy)
        InterfazPartida(self.sesion, otro,
                       opciones_visuales=OpcionesVisuales(modo_resaltado_jaque=Modo.REY_Y_ATACANTES))
        self.assertEqual(len(otro.canvas.find_withtag('marca:jaque')), 1)
        self.assertIn('marca:jaque', otro.casillas[posicion('e8')].ids_elementos_por_clave)
        self.assertIn('marca:atacante_jaque', otro.casillas[posicion('h5')].ids_elementos_por_clave)

    def test_destruccion_con_temporizador_real_no_deja_callback(self):
        self.modo(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.jugar('e2e4 f7f6 d1h5 g7g5')
        identificador = self.interfaz._id_parpadeo_jaque
        self.assertIn(identificador, self.ventana.tk.call('after', 'info'))
        self.casillero.canvas.destroy()
        self.assertIsNone(self.interfaz._id_parpadeo_jaque)
        self.assertNotIn(identificador, self.ventana.tk.call('after', 'info'))
        self.ventana.update()
        self.assertFalse(self.errores)

    def test_promociones_y_bloqueo_con_los_tres_modos(self):
        casos = (
            (Color.Blanco, 'a2a4 b7b5 a4b5 a7a6 b5a6 h7h6 a6a7 h6h5 a7b8', 'h5h4'),
            (Color.Negro, 'h2h3 a7a5 b2b4 a5b4 a2a3 b4a3 h3h4 a3a2 h4h5 a2b1', 'h5h6'),
            (Color.Blanco, 'a2a4 b7b5 a4b5 a7a6 b5a6 b8c6 a6a7 a8b8 a7a8', 'h7h6'),
            (Color.Negro, 'b1c3 a7a5 b2b4 a5b4 a2a3 b4a3 a1b1 a3a2 h2h3 a2a1', 'h3h4'),
        )
        clases = (Caballo, Alfil, Torre, Reina)
        for modo in Modo:
            for color, movimientos, siguiente in casos:
                for indice, clase in enumerate(clases):
                    with self.subTest(modo=modo, color=color, ultimo=movimientos[-4:], pieza=clase):
                        sesion = nueva_sesion()
                        lista = movimientos.split()
                        for movimiento in lista[:-1]:
                            enviar(sesion, movimiento)
                        aceptado = sesion.estado_actual
                        casillero = Casillero(self.ventana, self.tema,
                            distribucion=self.interfaz._obtener_distribucion(aceptado))
                        try:
                            vista = InterfazPartida(sesion, casillero,
                                opciones_visuales=OpcionesVisuales(modo_resaltado_jaque=modo))

                            def pulsar(casilla):
                                fila, columna = posicion(casilla)
                                vista.gestionar_clic_izquierdo(
                                    SimpleNamespace(x=columna*60+30, y=(7-fila)*60+30))

                            origen, destino = lista[-1][:2], lista[-1][2:]
                            peon_id = casillero.casillas[posicion(origen)].id_pieza
                            capturada_id = casillero.casillas[posicion(destino)].id_pieza
                            pulsar(origen)
                            pulsar(destino)
                            pendiente = sesion.jugada_pendiente
                            self.assertIsNotNone(pendiente)
                            paneles = [w for w in casillero.contenedor.winfo_children() if isinstance(w, tk.Frame)]
                            self.assertEqual(len(paneles), 1)
                            dibujos = casillero.canvas.find_all()
                            for casilla in (origen, destino, 'e2', 'e7', 'd4'):
                                pulsar(casilla)
                                self.assertEqual(vista.origen_seleccionado, posicion(origen))
                                self.assertEqual(casillero.canvas.find_all(), dibujos)
                                self.assertIs(sesion.estado_actual, aceptado)
                                self.assertIs(sesion.jugada_pendiente, pendiente)
                            self.assertIs(enviar(sesion, siguiente), Rechazo.PROMOCION_PENDIENTE)
                            self.assertEqual(len(casillero.contenedor.winfo_children()), 2)
                            paneles[0].winfo_children()[indice].invoke()
                            self.assertFalse(self.errores)
                            self.assertFalse(paneles[0].winfo_exists())
                            self.assertIsNone(sesion.jugada_pendiente)
                            self.assertIs(vista.estado_mostrado, sesion.estado_actual)
                            self.assertIs(sesion.partida.ultima_jugada, pendiente)
                            pieza = sesion.estado_actual.tablero.pieza_en(posicion(destino))
                            self.assertIsInstance(pieza, clase)
                            self.assertIs(pieza.color, color)
                            self.assertIsNone(casillero.casillas[posicion(origen)].id_pieza)
                            self.assertNotIn(peon_id, casillero.canvas.find_all())
                            if capturada_id is not None:
                                self.assertNotIn(capturada_id, casillero.canvas.find_all())
                            self.assertIsNone(vista.origen_seleccionado)
                            reyes_en_jaque = {
                                casilla for casilla, pieza in vista.estado_mostrado.tablero.casillas.items()
                                if isinstance(pieza, Rey) and vista.estado_mostrado.tablero.el_rey_queda_en_jaque(pieza.color)
                            }
                            marcadas = {casilla for casilla, visual in casillero.casillas.items()
                                        if 'marca:jaque' in visual.ids_elementos_por_clave}
                            self.assertEqual(marcadas, set() if modo is Modo.INTERMITENTE_TRAS_RECHAZO else reyes_en_jaque)
                            anterior = sesion.estado_actual
                            pulsar(siguiente[:2])
                            pulsar(siguiente[2:])
                            self.assertIsNot(sesion.estado_actual, anterior)
                            self.assertIs(vista.estado_mostrado, sesion.estado_actual)
                        finally:
                            casillero.contenedor.destroy()


if __name__ == '__main__':
    unittest.main()
