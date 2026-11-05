"""Interacción con widgets y Canvas reales, sin abrir ventanas visibles."""
import pickle
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.interfaz_partida import InterfazPartida
from ajedrez.gráficos.temas_graficos import cargar_tema
from ajedrez.partida import EstadoPartida
from ajedrez.piezas import Color, Reina
from pruebas.test_marcas_graficas import crear_tema
from pruebas.test_sesion import nueva_sesion, enviar
from pruebas.test_analisis_partida import posicion


class PruebasPanelAnalisis(unittest.TestCase):
    def setUp(self):
        self.raiz = tk.Tk()
        self.raiz.withdraw()
        self.addCleanup(self.raiz.destroy)
        self.errores = []
        self.raiz.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)
        self.imagen = tk.PhotoImage(master=self.raiz, width=60, height=60)
        self.tema = crear_tema(self.imagen)
        for nombre in ('peon', 'caballo', 'alfil', 'torre', 'dama', 'rey'):
            for color in Color:
                self.tema.piezas[nombre, color, 'normal'] = self.imagen
        self.sesion = nueva_sesion()
        self.contenedor = tk.Frame(self.raiz)
        self.contenedor.pack()
        self.vista = InterfazPartida(self.sesion, Casillero(self.contenedor, self.tema),
                                     contenedor=self.contenedor)

    def tearDown(self):
        self.assertFalse(self.errores)

    def clic(self, vista, casilla):
        fila, columna = posicion(casilla)
        vista.gestionar_clic_izquierdo(SimpleNamespace(x=columna * 60 + 30, y=(7 - fila) * 60 + 30))

    def mover(self, vista, notacion):
        self.clic(vista, notacion[:2])
        self.clic(vista, notacion[2:])

    def panel(self):
        self.vista.abrir_panel_analisis()
        return self.vista._panel_analisis

    def test_contenedor_comun_no_reempaqueta_al_padre(self):
        self.assertIs(self.vista.panel_navegacion.master, self.contenedor)
        self.assertIs(self.vista.casillero.contenedor.master, self.contenedor)
        self.assertEqual(self.contenedor.pack_slaves(),
                         [self.vista.casillero.contenedor, self.vista.panel_navegacion])
        botones = [w.cget('text') for w in self.vista.panel_navegacion.winfo_children()]
        self.assertIn('Siguiente', botones)

    def test_panel_y_editor_conservan_tamanno_de_casilla(self):
        for tamanno in (120, 240):
            with self.subTest(tamanno=tamanno):
                tema = cargar_tema(self.raiz, dimension_casilla=tamanno)
                contenedor = tk.Frame(self.raiz)
                contenedor.pack()
                try:
                    casillero = Casillero(contenedor, tema, tamanno_casilla=tamanno)
                    vista = InterfazPartida(nueva_sesion(), casillero, contenedor=contenedor)
                    vista.abrir_panel_analisis()
                    panel = vista._panel_analisis
                    centro_e2 = (4 * tamanno + tamanno // 2,
                                 6 * tamanno + tamanno // 2)
                    for editar in (False, True):
                        if editar:
                            panel.iniciar_edicion()
                        self.assertEqual(panel.casillero.tamanno_casilla, tamanno)
                        self.assertEqual(int(panel.casillero.canvas.cget('width')), 8 * tamanno)
                        self.assertEqual(panel.casillero.obtener_coordenadas_logicas(centro_e2),
                                         posicion('e2'))
                finally:
                    contenedor.destroy()

    def test_hipotesis_inline_y_prioridad_real(self):
        for notacion in ('e2e4', 'e7e5'):
            self.mover(self.vista, notacion)
        original = pickle.dumps(self.sesion.partida)
        real = self.vista.estado_mostrado
        self.vista.retroceder_movimiento()
        self.vista.alternar_analisis()
        self.mover(self.vista, 'c7c5')
        self.assertIsNot(self.vista.estado_mostrado, real)
        self.vista.retroceder_movimiento()
        self.vista.avanzar_movimiento()
        self.assertIs(self.vista.estado_mostrado, real)
        self.assertIsNone(self.vista._analisis.sesion_hipotetica)
        self.assertEqual(pickle.dumps(self.sesion.partida), original)

    def test_abrir_panel_no_crea_atributos_nuevos_en_la_interfaz(self):
        atributos = set(vars(self.vista))
        self.assertEqual(self.vista._disposicion_original, [])
        panel = self.panel()
        self.assertEqual(set(vars(self.vista)), atributos)
        self.assertIsInstance(panel._indicador_contexto, tk.Label)
        self.assertIsNone(panel._boton_modo_analisis)
        self.vista._volver_del_panel_analisis()
        self.assertEqual(set(vars(self.vista)), atributos)

    def test_editor_tiene_sus_atributos_desde_la_construccion(self):
        panel = self.panel()
        atributos = set(vars(panel))
        self.assertIsNone(panel._casillero_antes_de_editar)
        self.assertIsNone(panel._flecha_antes_de_editar)
        self.assertIsInstance(panel._herramientas, tk.Frame)
        self.assertIsInstance(panel._panel_editor, tk.Frame)
        valores_iniciales = {
            'herramienta': 'Jugar', 'accion_edicion': 'Colocar',
            'pieza_edicion': 'peon', 'color_edicion': 'Blanco',
            'turno_edicion': 'Blanco', 'al_paso_edicion': '', 'mensaje': '',
        }
        for nombre, esperado in valores_iniciales.items():
            with self.subTest(atributo=nombre):
                variable = getattr(panel, nombre)
                self.assertIsInstance(variable, tk.StringVar)
                self.assertEqual(variable.get(), esperado)
        self.assertEqual(len(panel.enroques_edicion), 4)
        panel.iniciar_edicion()
        self.assertEqual(set(vars(panel)), atributos)
        panel.cancelar_edicion()
        self.assertEqual(set(vars(panel)), atributos)

    def test_avanza_hipotesis_al_final_y_sale_sin_mutar_original(self):
        self.vista.alternar_analisis()
        self.mover(self.vista, 'e2e4')
        hipotetico = self.vista.estado_mostrado
        self.vista.retroceder_movimiento()
        self.vista.avanzar_movimiento()
        self.assertIs(self.vista.estado_mostrado, hipotetico)
        self.vista.alternar_analisis()
        self.assertIs(self.vista.estado_mostrado, self.sesion.estado_actual)
        self.assertEqual(self.sesion.partida.contador_jugadas, 0)
        self.mover(self.vista, 'd2d4')
        self.assertEqual(self.sesion.partida.contador_jugadas, 1)

    def test_partida_finalizada_se_explora_sin_cambiar_el_resultado(self):
        self.sesion.partida.estado_partida = EstadoPartida.TABLAS
        antes = pickle.dumps(self.sesion.partida)
        self.mover(self.vista, 'e2e4')
        self.assertEqual(pickle.dumps(self.sesion.partida), antes)
        self.assertIsNot(self.vista.estado_mostrado, self.sesion.estado_actual)

    def test_historico_en_partida_activa_vuelve_al_presente(self):
        self.mover(self.vista, 'e2e4')
        actual = self.vista.estado_mostrado
        self.vista.retroceder_movimiento()
        self.clic(self.vista, 'a2')
        self.assertIs(self.vista.estado_mostrado, actual)
        self.assertIsNone(self.vista.origen_seleccionado)

    def test_cambiar_panel_conserva_ambos_estados_y_anotaciones(self):
        self.vista.casillero.aplicar_marca(posicion('a3'), 'fondo_azul')
        dibujos = self.vista.casillero.canvas.find_all()
        panel = self.panel()
        self.assertIsNot(panel.sesion.partida, self.sesion.partida)
        self.vista.abrir_panel_analisis()  # Reabrir el panel ya visible es inocuo.
        self.assertIs(panel, self.vista._panel_analisis)
        self.mover(panel, 'e2e4')
        panel.casillero.aplicar_marca(posicion('b3'), 'fondo_verde')
        analisis_dibujos = panel.casillero.canvas.find_all()
        estado = panel.estado_mostrado
        self.vista._volver_del_panel_analisis()
        self.assertEqual(self.vista.casillero.canvas.find_all(), dibujos)
        self.vista.abrir_panel_analisis()
        self.assertIs(panel, self.vista._panel_analisis)
        self.assertIs(panel.estado_mostrado, estado)
        self.assertEqual(panel.casillero.canvas.find_all(), analisis_dibujos)
        self.assertEqual(self.sesion.partida.contador_jugadas, 0)

    def test_herramientas_anotaciones_y_limpieza(self):
        panel = self.panel()
        for herramienta in ('Marca', 'Proyección', 'Distintivo', 'Secuencia'):
            panel.herramienta.set(herramienta)
            self.clic(panel, 'a3')
        panel._dibujar_flecha(posicion('a3'), posicion('b5'))
        self.assertEqual(len(panel.casillero.anotaciones_estrategicas), 5)
        panel._borrar_ultima_anotacion(None)
        self.assertEqual(len(panel.casillero.anotaciones_estrategicas), 4)
        panel.limpiar_anotaciones()
        self.assertFalse(panel.casillero.anotaciones_estrategicas)
        self.assertIsNone(panel.flecha_seleccionada)

    def test_copiar_nueva_posicion_exige_confirmacion_y_no_mutacion(self):
        panel = self.panel()
        self.mover(panel, 'd2d4')
        hipotetico = panel.estado_mostrado
        self.vista._volver_del_panel_analisis()
        self.mover(self.vista, 'e2e4')
        antes = pickle.dumps(self.sesion.partida)
        self.vista.abrir_panel_analisis()
        with patch('ajedrez.gráficos.panel_analisis.messagebox.askyesno', return_value=False):
            panel.copiar_posicion_original()
        self.assertIs(panel.estado_mostrado, hipotetico)
        with patch('ajedrez.gráficos.panel_analisis.messagebox.askyesno', return_value=True):
            panel.copiar_posicion_original()
        self.assertIsNot(panel.estado_mostrado, self.sesion.estado_actual)
        self.assertIsNotNone(panel.estado_mostrado.tablero.pieza_en(posicion('e4')))
        self.assertIsNone(panel.estado_mostrado.tablero.pieza_en(posicion('d4')))
        self.assertIs(panel.sesion.partida.jugador, Color.Negro)
        self.assertEqual(pickle.dumps(self.sesion.partida), antes)

    def test_indicador_de_turno_sigue_estado_mostrado(self):
        self.mover(self.vista, 'e2e4')
        self.assertIn('negro', self.vista._indicador_contexto.cget('text'))
        self.vista.retroceder_movimiento()
        self.assertIn('blanco', self.vista._indicador_contexto.cget('text'))
        self.vista.avanzar_movimiento()
        self.assertIn('negro', self.vista._indicador_contexto.cget('text'))

    def test_indicador_estado_conserva_turno_vigente_en_el_historial(self):
        indicador = self.vista.indicador_estado_partida
        self.assertIsNotNone(indicador)
        self.assertEqual(indicador.cget('text'), 'Turno de blancas')
        self.mover(self.vista, 'e2e4')
        self.assertEqual(indicador.cget('text'), 'Turno de negras')
        self.vista.retroceder_movimiento()
        self.assertIn('blanco', self.vista._indicador_contexto.cget('text'))
        self.assertEqual(indicador.cget('text'), 'Turno de negras')
        self.vista.volver_al_estado_actual()
        self.assertEqual(indicador.cget('text'), 'Turno de negras')

    def test_indicador_estado_conserva_resultado_al_navegar(self):
        self.mover(self.vista, 'e2e4')
        for estado, texto in (
            (EstadoPartida.VICTORIA_BLANCA, 'Victoria de blancas'),
            (EstadoPartida.VICTORIA_NEGRA, 'Victoria de negras'),
            (EstadoPartida.TABLAS, 'Tablas'),
        ):
            with self.subTest(estado=estado):
                self.sesion.partida.estado_partida = estado
                self.vista._actualizar_indicador_contexto()
                self.assertEqual(self.vista.indicador_estado_partida.cget('text'), texto)
                self.vista.retroceder_movimiento()
                self.assertEqual(self.vista.indicador_estado_partida.cget('text'), texto)
                self.vista.volver_al_estado_actual()
                self.assertEqual(self.vista.indicador_estado_partida.cget('text'), texto)

    def test_indicador_estado_se_actualiza_al_confirmarse_jaque_mate(self):
        for movimiento in ('f2f3', 'e7e5', 'g2g4', 'd8h4'):
            self.mover(self.vista, movimiento)
        self.assertIs(self.sesion.partida.estado_partida, EstadoPartida.VICTORIA_NEGRA)
        self.assertEqual(self.vista.indicador_estado_partida.cget('text'), 'Victoria de negras')
        self.vista.retroceder_movimiento()
        self.assertEqual(self.vista.indicador_estado_partida.cget('text'), 'Victoria de negras')

    def test_indicador_estado_refleja_partida_original_durante_analisis(self):
        self.vista.alternar_analisis()
        self.mover(self.vista, 'e2e4')
        self.assertIn('negro', self.vista._indicador_contexto.cget('text'))
        self.assertEqual(self.vista.indicador_estado_partida.cget('text'), 'Turno de blancas')
        panel = self.panel()
        self.assertIsNone(panel.indicador_estado_partida)
        botones = {w.cget('text') for w in panel.panel_navegacion.winfo_children()
                   if isinstance(w, tk.Button)}
        self.assertTrue({'Anterior', 'Siguiente', 'Posición actual'}.issubset(botones))
        self.mover(panel, 'e7e5')
        self.assertIs(panel.sesion_movimientos.partida.jugador, Color.Blanco)
        self.vista._volver_del_panel_analisis()
        self.assertEqual(self.vista.indicador_estado_partida.cget('text'), 'Turno de blancas')
        self.assertEqual(self.sesion.partida.contador_jugadas, 0)

    def test_editor_mover_reemplazar_y_deshacer_con_clics(self):
        panel = self.panel()
        panel.iniciar_edicion()
        panel.accion_edicion.set('Mover')
        self.clic(panel, 'a2')
        self.clic(panel, 'a4')
        self.assertIsNone(panel.editor.tablero.pieza_en(posicion('a2')))
        self.assertIsNotNone(panel.editor.tablero.pieza_en(posicion('a4')))
        panel.accion_edicion.set('Colocar')
        panel.pieza_edicion.set('dama')
        self.clic(panel, 'a4')
        self.assertIsInstance(panel.editor.tablero.pieza_en(posicion('a4')), Reina)
        panel.deshacer_edicion()
        self.assertNotIsInstance(panel.editor.tablero.pieza_en(posicion('a4')), Reina)
        panel.cancelar_edicion()

    def test_enroque_y_captura_al_paso_hipoteticos_en_canvas(self):
        for secuencia, movimiento, vacias, ocupadas in (
            ('e2e4 a7a6 e4e5 d7d5', 'e5d6', ('e5', 'd5'), ('d6',)),
            ('e2e4 a7a6 g1f3 a6a5 f1e2 b7b6', 'e1g1', ('e1', 'h1'), ('f1', 'g1')),
        ):
            with self.subTest(movimiento=movimiento):
                sesion = nueva_sesion()
                for notacion in secuencia.split():
                    self.assertIsNone(enviar(sesion, notacion))
                casillero = Casillero(self.contenedor, self.tema, distribucion={})
                vista = InterfazPartida(sesion, casillero)
                vista.mostrar_estado(sesion.estado_actual)
                vista.alternar_analisis()
                anterior = vista.estado_mostrado
                antes = pickle.dumps(sesion.partida)
                self.mover(vista, movimiento)
                for casilla in vacias:
                    self.assertIsNone(casillero.casillas[posicion(casilla)].id_pieza)
                for casilla in ocupadas:
                    self.assertIsNotNone(casillero.casillas[posicion(casilla)].id_pieza)
                vista.retroceder_movimiento()
                self.assertIs(vista.estado_mostrado, anterior)
                vista.avanzar_movimiento()
                for casilla in vacias:
                    self.assertIsNone(casillero.casillas[posicion(casilla)].id_pieza)
                self.assertEqual(pickle.dumps(sesion.partida), antes)

    def test_color_flecha_se_conserva_al_deseleccionar(self):
        panel = self.panel()
        panel.color_flecha.set('rojo')
        panel._dibujar_flecha(posicion('a3'), posicion('b5'))
        identificador = panel.casillero.anotaciones_estrategicas[-1]
        color = panel.casillero.canvas.itemcget(identificador, 'fill')
        panel.casillero.alternar_resaltado_flecha(identificador)
        self.assertNotEqual(panel.casillero.canvas.itemcget(identificador, 'fill'), color)
        panel.casillero.alternar_resaltado_flecha(identificador)
        self.assertEqual(panel.casillero.canvas.itemcget(identificador, 'fill'), color)

    def test_cancelar_edicion_conserva_historial_y_dibujos(self):
        panel = self.panel()
        self.mover(panel, 'e2e4')
        panel.casillero.aplicar_marca(posicion('a3'), 'fondo_azul')
        casillero = panel.casillero
        dibujos = casillero.canvas.find_all()
        estado = panel.estado_mostrado
        panel.iniciar_edicion()
        panel.vaciar_borrador()
        panel.avanzar_movimiento()
        panel.retroceder_movimiento()
        self.assertIs(panel.estado_mostrado, estado)
        panel.cancelar_edicion()
        self.assertIs(panel.casillero, casillero)
        # El indicador de jaque se recalcula; las piezas y las notas conservan IDs.
        self.assertEqual(panel.casillero.canvas.find_all(), dibujos)
        self.assertIs(panel.estado_mostrado, estado)

    def test_editor_aplica_piezas_turno_y_bloquea_posicion_invalida(self):
        original = pickle.dumps(self.sesion.partida)
        panel = self.panel()
        panel.iniciar_edicion()
        panel.accion_edicion.set('Quitar')
        self.clic(panel, 'e1')
        panel.aplicar_edicion()
        self.assertIsNotNone(panel.editor)
        self.assertIn('rey', panel.mensaje.get())
        panel.deshacer_edicion()
        panel.accion_edicion.set('Colocar')
        panel.pieza_edicion.set('dama')
        panel.color_edicion.set('Blanco')
        self.clic(panel, 'a3')
        panel.turno_edicion.set('Negro')
        panel.aplicar_edicion()
        self.assertIsNone(panel.editor)
        self.assertIs(panel.sesion.partida.jugador, Color.Negro)
        self.assertIsInstance(panel.estado_mostrado.tablero.pieza_en(posicion('a3')), Reina)
        self.assertIsNone(panel.estado_mostrado.origen)
        self.mover(panel, 'e7e5')
        self.assertIsNotNone(panel.estado_mostrado.tablero.pieza_en(posicion('e5')))
        self.assertEqual(pickle.dumps(self.sesion.partida), original)

    def test_promocion_hipotetica_bloquea_navegacion_y_editor(self):
        panel = self.panel()
        original = pickle.dumps(self.sesion.partida)
        for notacion in 'a2a4 b7b5 a4b5 a7a6 b5a6 h7h6 a6a7 h6h5 a7b8'.split():
            self.mover(panel, notacion)
        self.assertIsNotNone(panel.promocion_pendiente)
        estado = panel.estado_mostrado
        panel.retroceder_movimiento()
        panel.avanzar_movimiento()
        panel.iniciar_edicion()
        self.assertIsNone(panel.editor)
        self.assertIs(panel.estado_mostrado, estado)
        selector = next(w for w in panel.casillero.contenedor.winfo_children() if isinstance(w, tk.Frame))
        selector.winfo_children()[-1].invoke()
        self.assertIsNone(panel.promocion_pendiente)
        self.assertIsInstance(panel.estado_mostrado.tablero.pieza_en(posicion('b8')), Reina)
        self.assertIsNone(panel.casillero.casillas[posicion('a7')].id_pieza)
        panel.retroceder_movimiento()
        self.assertIs(panel.estado_mostrado, estado)
        panel.avanzar_movimiento()
        self.assertIsInstance(panel.estado_mostrado.tablero.pieza_en(posicion('b8')), Reina)
        self.assertEqual(pickle.dumps(self.sesion.partida), original)


if __name__ == '__main__':
    unittest.main()
