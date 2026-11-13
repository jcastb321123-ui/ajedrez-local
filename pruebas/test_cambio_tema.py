"""Cambio de temas reales conservando dibujos, modelo y contextos de interacción."""

import gc
import json
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ajedrez.aplicacion import AplicacionAjedrez
from ajedrez.gráficos.graficos_tablero import Casillero
from ajedrez.gráficos.opciones_visuales import ModoResaltadoJaque as Modo
from ajedrez.gráficos.temas_graficos import (
    CARPETA_RECURSOS_PREDETERMINADA, IDENTIFICADOR_TEMA_PREDETERMINADO,
    cargar_tema, obtener_temas_disponibles,
)
from ajedrez.persistencia import partida_a_datos
from ajedrez.piezas import Color, PeonBlanco, PeonNegro, Reina, Rey, Torre
from pruebas.test_dialogo_preferencias import VentanaDePrueba
from pruebas.test_persistencia import partida_con_piezas
from pruebas.test_sesion import posicion


class PruebasCatalogoTemas(unittest.TestCase):
    def test_listado_procede_del_catalogo_y_no_crea_imagenes(self):
        with (CARPETA_RECURSOS_PREDETERMINADA / 'catalogo.json').open(encoding='utf-8') as archivo:
            catalogo = json.load(archivo)
        with patch('tkinter.PhotoImage', side_effect=AssertionError('No debe cargar PNG')):
            temas = obtener_temas_disponibles()
        self.assertEqual(tuple(temas), tuple(catalogo['temas']))
        self.assertEqual(len(temas), 12)
        self.assertEqual(temas['taller.veta_fina'], 'Taller · Veta fina')
        catalogo['temas']['nuevo.liso'] = {'paleta': 'nuevo', 'acabado': 'liso'}
        with patch('ajedrez.gráficos.temas_graficos.json.load', return_value=catalogo):
            self.assertEqual(obtener_temas_disponibles()['nuevo.liso'], 'Nuevo · Liso')


class PruebasCambioTemaCasillero(VentanaDePrueba):
    def test_todos_los_temas_actualizan_todos_los_recursos_sin_recrear_ids(self):
        tema = cargar_tema(self.ventana)
        casillero = Casillero(self.ventana, tema, distribucion={})
        recursos = {}
        casillas = tuple(casillero.casillas)
        for indice, clave in enumerate(tema.piezas):
            casilla = casillas[indice]
            casillero.promocion(casilla, clave)
            recursos[casillero.casillas[casilla].id_pieza] = ('piezas', clave)
        for grupo, metodo in (
            ('proyecciones', casillero.aplicar_proyeccion),
            ('marcas', casillero.aplicar_marca),
            ('distintivos', casillero.aplicar_distintivo),
            ('secuencias', casillero.aplicar_marcador_de_secuencia),
        ):
            for indice, clave in enumerate(getattr(tema, grupo)):
                metodo(casillas[indice], clave)
                # Ordenar capas puede cambiar el último ID; el nuevo es siempre el mayor.
                recursos[max(casillero.canvas.find_all())] = (grupo, clave)
        casillero.aplicar_flecha((1, 0), (3, 1), 'flecha_estrategica')
        flecha = casillero.anotaciones_estrategicas[-1]
        casillero.alternar_resaltado_flecha(flecha)
        ids = casillero.canvas.find_all()
        coordenadas = {id: casillero.canvas.coords(id) for id in ids}
        anotaciones = tuple(casillero.anotaciones_estrategicas)
        registros = {p: {k: tuple(v) for k, v in c.variables_id.items()}
                     for p, c in casillero.casillas.items()}
        recorrido = {p for p, c in casillero.casillas.items() if flecha in c.ids_flechas}
        for identificador in obtener_temas_disponibles():
            with self.subTest(tema=identificador):
                nuevo = cargar_tema(self.ventana, identificador=identificador)
                casillero.aplicar_tema(nuevo)
                self.assertIs(casillero.tema, nuevo)
                self.assertEqual(casillero.canvas.find_all(), ids)
                self.assertEqual(tuple(casillero.anotaciones_estrategicas), anotaciones)
                self.assertEqual({id: casillero.canvas.coords(id) for id in ids}, coordenadas)
                self.assertEqual({p: {k: tuple(v) for k, v in c.variables_id.items()}
                                  for p, c in casillero.casillas.items()}, registros)
                self.assertEqual({p for p, c in casillero.casillas.items() if flecha in c.ids_flechas}, recorrido)
                for id, (grupo, clave) in recursos.items():
                    self.assertEqual(casillero.canvas.itemcget(id, 'image'), str(getattr(nuevo, grupo)[clave]))
                for (fila, columna), casilla in casillero.casillas.items():
                    color = 'oscura' if (fila + columna) % 2 == 0 else 'clara'
                    self.assertEqual(casillero.canvas.itemcget(casilla.id_imagen, 'image'), str(nuevo.casillas[color]))
                self.assertIn('flecha_seleccionada', casillero.canvas.gettags(flecha))
        casillero.borrar_flecha(flecha)
        self.assertNotIn(flecha, casillero.anotaciones_estrategicas)
        self.assertFalse(any(flecha in c.ids_flechas for c in casillero.casillas.values()))

    def test_flechas_conservan_su_clave_de_color_y_la_seleccion(self):
        original = cargar_tema(self.ventana)
        casillero = Casillero(self.ventana, original, distribucion={})
        nuevo = cargar_tema(self.ventana, identificador='taller.veta_fina',
                           colores={'flecha_estrategica': '#234567',
                                    'flecha_estrategica_seleccionada': '#56789a', 'rojo': '#a04040'})
        for indice, clave in enumerate(('flecha_estrategica', 'rojo')):
            casillero.aplicar_flecha((1, indice), (4, indice), clave)
        primera, segunda = casillero.anotaciones_estrategicas
        casillero.alternar_resaltado_flecha(primera)
        casillero.aplicar_tema(nuevo)
        self.assertEqual(casillero.canvas.itemcget(primera, 'fill'), '#56789a')
        self.assertEqual(casillero.canvas.itemcget(segunda, 'fill'), '#a04040')
        casillero.alternar_resaltado_flecha(primera)
        self.assertEqual(casillero.canvas.itemcget(primera, 'fill'), '#234567')
        self.assertIn('color_original:#234567', casillero.canvas.gettags(primera))


class PruebasTemasEnPreferencias(VentanaDePrueba):
    def setUp(self):
        super().setUp()
        self.app = AplicacionAjedrez(ventana=self.ventana, ruta_preferencias=self.ruta_preferencias)

    def abrir(self):
        self.app._boton_preferencias.invoke()
        return self.app._dialogo_preferencias

    def elegir(self, identificador, modo=None):
        dialogo = self.abrir()
        dialogo._selector_tema.current(dialogo._identificadores_temas.index(identificador))
        if modo is not None:
            dialogo._opciones_jaque[modo].invoke()
        dialogo._boton_aplicar.invoke()
        return dialogo

    def clic(self, casilla, vista=None):
        vista = vista or self.app.interfaz_partida
        fila, columna = posicion(casilla)
        vista.gestionar_clic_izquierdo(SimpleNamespace(x=columna*60+30, y=(7-fila)*60+30))

    def jugar(self, movimientos, vista=None):
        for movimiento in movimientos.split():
            self.clic(movimiento[:2], vista)
            self.clic(movimiento[2:], vista)

    def test_selector_solo_lectura_cancelacion_y_restablecimiento_pendiente_de_aplicar(self):
        anterior = self.app.tema
        dialogo = self.abrir()
        self.assertEqual(str(dialogo._selector_tema.cget('state')), 'readonly')
        self.assertEqual(tuple(dialogo._selector_tema.cget('values')), tuple(obtener_temas_disponibles().values()))
        dialogo._selector_tema.current(5)
        dialogo._boton_cancelar.invoke()
        self.assertIs(self.app.tema, anterior)
        self.elegir('taller.veta_fina', Modo.REY_Y_ATACANTES)
        dialogo = self.abrir()
        self.assertEqual(dialogo._identificadores_temas[dialogo._selector_tema.current()], 'taller.veta_fina')
        dialogo._boton_restablecer.invoke()
        self.assertEqual(self.app.tema.identificador, 'taller.veta_fina')
        dialogo._boton_cancelar.invoke()
        self.assertEqual(self.app.tema.identificador, 'taller.veta_fina')
        dialogo = self.abrir()
        dialogo._boton_restablecer.invoke()
        dialogo._boton_aplicar.invoke()
        self.assertEqual(self.app.tema.identificador, IDENTIFICADOR_TEMA_PREDETERMINADO)
        self.assertIs(self.app.interfaz_partida.opciones_visuales.modo_resaltado_jaque, Modo.REY_PERMANENTE)

    def test_aplicar_mismo_tema_no_recarga_imagenes_ni_recrea_los_indicadores(self):
        self.jugar('e2e4 f7f6 d1h5')
        vista = self.app.interfaz_partida
        ids = vista.casillero.canvas.find_all()
        with patch('ajedrez.aplicacion.cargar_tema', side_effect=AssertionError('Recarga innecesaria')):
            self.elegir(self.app.tema.identificador)
        self.assertEqual(vista.casillero.canvas.find_all(), ids)

    def test_cambio_conserva_modelo_ids_seleccion_anotaciones_y_destino_de_guardado(self):
        self.jugar('e2e4 f7f6 d1h5')
        vista = self.app.interfaz_partida
        self.clic('g7')
        vista.casillero.aplicar_marca((2, 2), 'fondo_azul')
        vista.casillero.aplicar_flecha((2, 0), (3, 1), 'flecha_estrategica')
        flecha = vista.casillero.anotaciones_estrategicas[-1]
        vista.casillero.alternar_resaltado_flecha(flecha)
        vista._flecha_seleccionada = flecha
        partida, estado = vista.sesion.partida, vista.estado_mostrado
        datos = partida_a_datos(partida)
        ids = vista.casillero.canvas.find_all()
        notas = tuple(vista.casillero.anotaciones_estrategicas)
        guardado = self.app._datos_ultimo_guardado
        self.app._id_partida_biblioteca = 27
        self.elegir('pizarra.microfibra')
        gc.collect()
        self.assertIs(self.app.interfaz_partida, vista)
        self.assertIs(vista.sesion.partida, partida)
        self.assertIs(vista.estado_mostrado, estado)
        self.assertEqual(partida_a_datos(partida), datos)
        self.assertEqual(vista.casillero.canvas.find_all(), ids)
        self.assertEqual(tuple(vista.casillero.anotaciones_estrategicas), notas)
        self.assertEqual(vista.origen_seleccionado, posicion('g7'))
        self.assertEqual(vista.flecha_seleccionada, flecha)
        self.assertIs(self.app._datos_ultimo_guardado, guardado)
        self.assertEqual(self.app._id_partida_biblioteca, 27)
        imagenes_vivas = self.ventana.tk.call('image', 'names')
        for id in ids:
            if vista.casillero.canvas.type(id) == 'image':
                self.assertIn(vista.casillero.canvas.itemcget(id, 'image'), imagenes_vivas)
        vista._borrar_flecha_seleccionada(None)
        self.assertNotIn(flecha, vista.casillero.canvas.find_all())
        self.clic('g6')
        self.assertIsNot(vista.estado_mostrado, estado)

    def test_posicion_historica_y_siguiente_se_conservan(self):
        self.jugar('e2e4 f7f6 d1h5 g7g6')
        vista = self.app.interfaz_partida
        actual = vista.sesion.estado_actual
        vista.retroceder_movimiento()
        historico = vista.estado_mostrado
        self.elegir('taller.mineral_suave')
        self.assertIs(vista.estado_mostrado, historico)
        self.assertIs(vista.sesion.estado_actual, actual)
        rey = vista.casillero.casillas[posicion('e8')].id_pieza
        self.assertEqual(vista.casillero.canvas.itemcget(rey, 'image'), str(self.app.tema.piezas['rey', Color.Negro, 'normal']))
        self.assertTrue(vista.casillero.canvas.find_withtag('marca:jaque'))
        vista.avanzar_movimiento()
        self.assertIs(vista.estado_mostrado, actual)

    def test_analisis_independiente_visible_y_oculto_conserva_su_posicion_propia(self):
        self.jugar('e2e4 f7f6 d1h5')
        vista = self.app.interfaz_partida
        vista.abrir_panel_analisis()
        panel = vista._panel_analisis
        self.jugar('g7g6', panel)
        estado = panel.estado_mostrado
        original = partida_a_datos(vista.sesion.partida)
        hipotetica = partida_a_datos(panel.sesion.partida)
        ids = panel.casillero.canvas.find_all()
        for oculto, tema in ((False, 'club.microfibra'), (True, 'taller.veta_fina')):
            with self.subTest(oculto=oculto):
                if oculto:
                    vista._volver_del_panel_analisis()
                self.elegir(tema)
                self.assertIs(panel.estado_mostrado, estado)
                self.assertIs(panel.casillero.tema, self.app.tema)
                self.assertEqual(panel.casillero.canvas.find_all(), ids)
                self.assertEqual(partida_a_datos(panel.sesion.partida), hipotetica)
                self.assertEqual(partida_a_datos(vista.sesion.partida), original)
        vista.abrir_panel_analisis()
        self.assertIs(vista._panel_analisis, panel)

    def test_cambio_durante_edicion_conserva_borrador_y_tablero_oculto(self):
        vista = self.app.interfaz_partida
        vista.abrir_panel_analisis()
        panel = vista._panel_analisis
        panel.casillero.aplicar_marca((2, 2), 'fondo_azul')
        original = panel.casillero
        ids_originales = original.canvas.find_all()
        panel.iniciar_edicion()
        panel.vaciar_borrador()
        editor, borrador = panel.editor, panel.casillero
        ids_borrador = borrador.canvas.find_all()
        self.elegir('pizarra.veta_fina')
        self.assertIs(panel.editor, editor)
        self.assertIs(panel.casillero, borrador)
        self.assertEqual(borrador.canvas.find_all(), ids_borrador)
        self.assertIs(borrador.tema, self.app.tema)
        self.assertIs(original.tema, self.app.tema)
        panel.cancelar_edicion()
        self.assertIs(panel.casillero, original)
        self.assertEqual(original.canvas.find_all(), ids_originales)
        self.assertIn('marca:fondo_azul', original.casillas[(2, 2)].ids_elementos_por_clave)

    def test_promocion_pendiente_conserva_botones_y_confirma_con_el_tema_nuevo(self):
        for color, origen, destino, peon in (
            (Color.Blanco, 'a7', 'b8', PeonBlanco()),
            (Color.Negro, 'a2', 'b1', PeonNegro()),
        ):
            with self.subTest(color=color):
                adversario = Color.Negro if color is Color.Blanco else Color.Blanco
                partida = partida_con_piezas({'e1': Rey(Color.Blanco), 'e8': Rey(Color.Negro),
                                              origen: peon, destino: Torre(adversario)}, turno=color)
                self.app._crear_partida_local(partida=partida)
                vista = self.app.interfaz_partida
                self.jugar(origen + destino)
                pendiente = vista.promocion_pendiente
                self.assertIsNotNone(pendiente)
                botones = dict(vista._botones_promocion)
                nuevo = 'taller.microfibra' if color is Color.Blanco else 'pizarra.mineral_suave'
                self.elegir(nuevo)
                self.assertIs(vista.promocion_pendiente, pendiente)
                self.assertEqual(vista._botones_promocion, botones)
                for clave, boton in botones.items():
                    self.assertEqual(str(boton.cget('image')), str(self.app.tema.piezas[clave]))
                botones['dama', color, 'normal'].invoke()
                self.assertIsNone(vista.promocion_pendiente)
                self.assertFalse(vista._botones_promocion)
                self.assertIsInstance(vista.sesion.estado_actual.tablero.pieza_en(posicion(destino)), Reina)
                self.assertIsNone(vista.casillero.casillas[posicion(origen)].id_pieza)

    def test_error_de_carga_conserva_tema_modo_partida_y_dialogo_para_reintentar(self):
        vista = self.app.interfaz_partida
        tema, opciones = self.app.tema, vista.opciones_visuales
        ids = vista.casillero.canvas.find_all()
        for error in (FileNotFoundError('Imagen ausente'), tk.TclError('PNG no válido')):
            with self.subTest(error=type(error)), patch('ajedrez.aplicacion.cargar_tema', side_effect=error), \
                 patch('ajedrez.aplicacion.messagebox.showerror') as aviso:
                dialogo = self.elegir('pizarra.veta_fina', Modo.REY_Y_ATACANTES)
                self.assertTrue(dialogo.winfo_exists())
                self.assertIs(dialogo.grab_current(), dialogo)
                self.assertIs(self.app.tema, tema)
                self.assertIs(vista.opciones_visuales, opciones)
                self.assertEqual(vista.casillero.canvas.find_all(), ids)
                aviso.assert_called_once()
        self.elegir('pizarra.veta_fina', Modo.REY_Y_ATACANTES)
        self.assertFalse(dialogo.winfo_exists())
        self.assertEqual(self.app.tema.identificador, 'pizarra.veta_fina')

    def test_nueva_partida_y_apertura_heredan_tema_sin_cambios_pendientes(self):
        self.elegir('taller.veta_fina')
        self.assertFalse(self.app._hay_cambios_sin_guardar())
        tema = self.app.tema
        with patch('ajedrez.aplicacion.messagebox.askyesno', return_value=True):
            self.app.boton_nueva_partida.invoke()
        self.assertIs(self.app.interfaz_partida.casillero.tema, tema)
        partida = self.app.interfaz_partida.sesion.partida
        self.app._crear_partida_local(partida=partida)
        self.assertIs(self.app.interfaz_partida.casillero.tema, tema)
        self.assertFalse(self.app._hay_cambios_sin_guardar())
        self.app.interfaz_partida.abrir_panel_analisis()
        self.assertIs(self.app.interfaz_partida._panel_analisis.casillero.tema, tema)

    def test_hipotesis_en_tablero_principal_conserva_su_estado_y_el_parpadeo_en_curso(self):
        self.jugar('e2e4 f7f6 d1h5')
        vista = self.app.interfaz_partida
        original = partida_a_datos(vista.sesion.partida)
        vista.alternar_analisis()
        self.elegir(self.app.tema.identificador, Modo.INTERMITENTE_TRAS_RECHAZO)
        self.jugar('g7g5')  # Rechazo que activa el aviso, sin alterar la hipótesis.
        temporizador = vista._id_parpadeo_jaque
        self.assertIsNotNone(temporizador)
        sesion, estado = vista.sesion_movimientos, vista.estado_mostrado
        self.elegir('taller.microfibra')
        self.assertTrue(vista.en_analisis)
        self.assertIs(vista.sesion_movimientos, sesion)
        self.assertIs(vista.estado_mostrado, estado)
        self.assertEqual(vista._id_parpadeo_jaque, temporizador)
        self.assertIn(temporizador, self.ventana.tk.call('after', 'info'))
        self.clic('g6')
        self.assertIsNone(vista._id_parpadeo_jaque)
        self.assertIsNot(vista.estado_mostrado, estado)
        self.assertEqual(partida_a_datos(vista.sesion.partida), original)


if __name__ == '__main__':
    unittest.main()
