"""Preferencias con widgets reales y su aplicación sin alterar las partidas."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ajedrez.aplicacion import AplicacionAjedrez
from ajedrez.gráficos.dialogo_preferencias import DialogoPreferencias
from ajedrez.gráficos.opciones_visuales import (
    ModoResaltadoJaque as Modo, OpcionesVisuales, OPCIONES_VISUALES_PREDETERMINADAS,
)
from ajedrez.persistencia import partida_a_datos


class VentanaDePrueba(unittest.TestCase):
    def setUp(self):
        self.temporal_preferencias = TemporaryDirectory()
        self.addCleanup(self.temporal_preferencias.cleanup)
        self.ruta_preferencias = Path(self.temporal_preferencias.name) / 'preferencias.json'
        self.ventana = tk.Tk()
        self.ventana.withdraw()
        self.errores = []
        self.addCleanup(self.assertFalse, self.errores)
        self.addCleanup(self.ventana.destroy)
        self.ventana.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)


class PruebasDialogoPreferencias(VentanaDePrueba):
    def abrir(self, opciones=OPCIONES_VISUALES_PREDETERMINADAS):
        self.recibidas = []
        def recibir(opciones, identificador):
            self.recibidas.append(opciones)
            return True
        dialogo = DialogoPreferencias(
            self.ventana, opciones, temas={'club.liso_mate': 'Club · Liso mate'},
            tema_actual='club.liso_mate', aplicar=recibir,
        )
        self.ventana.update_idletasks()
        return dialogo

    def test_muestra_la_eleccion_vigente_y_solo_aplicar_confirma_cada_modo(self):
        for modo in Modo:
            with self.subTest(modo=modo):
                originales = OpcionesVisuales(modo_resaltado_jaque=Modo.REY_Y_ATACANTES)
                dialogo = self.abrir(originales)
                self.assertEqual(dialogo._modo_jaque.get(), Modo.REY_Y_ATACANTES.value)
                self.assertIs(dialogo.grab_current(), dialogo)
                dialogo._opciones_jaque[modo].invoke()
                self.assertFalse(self.recibidas)
                self.assertIs(originales.modo_resaltado_jaque, Modo.REY_Y_ATACANTES)
                dialogo._boton_aplicar.invoke()
                self.assertEqual(len(self.recibidas), 1)
                self.assertIs(self.recibidas[0].modo_resaltado_jaque, modo)
                self.assertFalse(dialogo.winfo_exists())
                self.assertIsNone(self.ventana.grab_current())

    def test_cancelar_cerrar_y_escape_descartan_la_eleccion(self):
        for cierre in ('boton', 'ventana', 'escape'):
            with self.subTest(cierre=cierre):
                dialogo = self.abrir()
                dialogo._opciones_jaque[Modo.REY_Y_ATACANTES].invoke()
                if cierre == 'boton':
                    dialogo._boton_cancelar.invoke()
                elif cierre == 'ventana':
                    dialogo.tk.call(dialogo.protocol('WM_DELETE_WINDOW'))
                else:
                    # Tk no entrega eventos de teclado a una ventana sin mapear.
                    self.ventana.geometry('+30000+30000')
                    self.ventana.deiconify()
                    dialogo.deiconify()
                    self.ventana.update()
                    dialogo.focus_force()
                    self.ventana.update()
                    dialogo.event_generate('<Escape>')
                self.assertFalse(dialogo.winfo_exists())
                self.assertFalse(self.recibidas)
                self.assertIsNone(self.ventana.grab_current())

    def test_restablecer_es_un_borrador_y_cancelar_conserva_la_configuracion(self):
        originales = OpcionesVisuales(modo_resaltado_jaque=Modo.INTERMITENTE_TRAS_RECHAZO)
        dialogo = self.abrir(originales)
        dialogo._boton_restablecer.invoke()
        self.assertEqual(dialogo._modo_jaque.get(), Modo.REY_PERMANENTE.value)
        self.assertFalse(self.recibidas)
        dialogo._boton_cancelar.invoke()
        self.assertIs(originales.modo_resaltado_jaque, Modo.INTERMITENTE_TRAS_RECHAZO)

    def test_aplicar_y_restablecer_conservan_campos_no_editados_y_subclases(self):
        @dataclass(frozen=True, kw_only=True)
        class Ampliadas(OpcionesVisuales):
            mostrar_coordenadas: bool = False

        originales = Ampliadas(modo_resaltado_jaque=Modo.REY_Y_ATACANTES,
                              intervalo_parpadeo_jaque_ms=450, repeticiones_parpadeo_jaque=5)
        for restablecer in (False, True):
            with self.subTest(restablecer=restablecer):
                dialogo = self.abrir(originales)
                if restablecer:
                    dialogo._boton_restablecer.invoke()
                else:
                    dialogo._opciones_jaque[Modo.INTERMITENTE_TRAS_RECHAZO].invoke()
                dialogo._boton_aplicar.invoke()
                nuevas = self.recibidas[0]
                self.assertIsInstance(nuevas, Ampliadas)
                self.assertEqual(nuevas.intervalo_parpadeo_jaque_ms, 450)
                self.assertEqual(nuevas.repeticiones_parpadeo_jaque, 5)
                self.assertFalse(nuevas.mostrar_coordenadas)
                self.assertIs(nuevas.modo_resaltado_jaque,
                              Modo.REY_PERMANENTE if restablecer else Modo.INTERMITENTE_TRAS_RECHAZO)


class PruebasPreferenciasAplicacion(VentanaDePrueba):
    def setUp(self):
        super().setUp()
        self.app = AplicacionAjedrez(ventana=self.ventana, ruta_preferencias=self.ruta_preferencias)

    def abrir(self):
        self.app._boton_preferencias.invoke()
        return self.app._dialogo_preferencias

    def elegir(self, modo):
        dialogo = self.abrir()
        dialogo._opciones_jaque[modo].invoke()
        dialogo._boton_aplicar.invoke()

    def clic(self, casilla, vista=None):
        vista = vista or self.app.interfaz_partida
        fila, columna = int(casilla[1])-1, ord(casilla[0])-ord('a')
        vista.gestionar_clic_izquierdo(SimpleNamespace(x=columna*60+30, y=(7-fila)*60+30))

    def preparar_jaque(self):
        for movimiento in ('e2e4', 'f7f6', 'd1h5'):
            self.clic(movimiento[:2])
            self.clic(movimiento[2:])

    def marcadas(self, vista, clave):
        return {posicion for posicion, casilla in vista.casillero.casillas.items()
                if f'marca:{clave}' in casilla.ids_elementos_por_clave}

    def test_boton_abre_un_solo_dialogo_y_reabrir_recupera_lo_confirmado(self):
        dialogo = self.abrir()
        dialogo._opciones_jaque[Modo.REY_Y_ATACANTES].invoke()
        self.assertIs(self.abrir(), dialogo)
        dialogo._boton_cancelar.invoke()
        self.assertEqual(self.abrir()._modo_jaque.get(), Modo.REY_PERMANENTE.value)
        self.app._dialogo_preferencias._boton_cancelar.invoke()
        self.elegir(Modo.REY_Y_ATACANTES)
        self.assertEqual(self.abrir()._modo_jaque.get(), Modo.REY_Y_ATACANTES.value)

    def test_aplicar_actualiza_marcas_sin_cambiar_partida_seleccion_ni_notas(self):
        self.preparar_jaque()
        vista = self.app.interfaz_partida
        self.clic('g7')
        vista.casillero.aplicar_marca((2, 2), 'fondo_azul')
        vista.casillero.aplicar_flecha((2, 2), (3, 3), 'flecha_estrategica')
        partida = vista.sesion.partida
        datos = partida_a_datos(partida)
        estado = vista.estado_mostrado
        ajenos = set(vista.casillero.canvas.find_all()) - set(vista.casillero.canvas.find_withtag('marca:jaque'))
        self.elegir(Modo.REY_Y_ATACANTES)
        self.assertEqual(self.marcadas(vista, 'jaque'), {(7, 4)})
        self.assertEqual(self.marcadas(vista, 'atacante_jaque'), {(4, 7)})
        self.assertTrue(ajenos <= set(vista.casillero.canvas.find_all()))
        self.assertEqual(vista.origen_seleccionado, (6, 6))
        self.assertIs(vista.estado_mostrado, estado)
        self.assertIs(vista.sesion.partida, partida)
        self.assertEqual(partida_a_datos(partida), datos)

    def test_intermitente_se_activa_ante_rechazo_y_aplicar_otro_modo_cancela_el_reloj(self):
        self.preparar_jaque()
        vista = self.app.interfaz_partida
        self.elegir(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.assertFalse(self.marcadas(vista, 'jaque'))
        self.clic('g7')
        self.clic('g5')
        temporizador = vista._id_parpadeo_jaque
        self.assertIsNotNone(temporizador)
        self.assertEqual(self.marcadas(vista, 'jaque'), {(7, 4)})
        self.elegir(Modo.REY_Y_ATACANTES)
        self.assertIsNone(vista._id_parpadeo_jaque)
        self.assertNotIn(temporizador, self.ventana.tk.call('after', 'info'))
        self.assertEqual(self.marcadas(vista, 'atacante_jaque'), {(4, 7)})

    def test_restablecer_y_aplicar_borra_solo_los_atacantes(self):
        self.preparar_jaque()
        self.elegir(Modo.REY_Y_ATACANTES)
        vista = self.app.interfaz_partida
        dialogo = self.abrir()
        dialogo._boton_restablecer.invoke()
        self.assertTrue(self.marcadas(vista, 'atacante_jaque'))
        dialogo._boton_aplicar.invoke()
        self.assertEqual(self.marcadas(vista, 'jaque'), {(7, 4)})
        self.assertFalse(self.marcadas(vista, 'atacante_jaque'))

    def test_nueva_partida_y_apertura_conservan_opciones_sin_marcar_cambios_de_partida(self):
        datos = self.app._datos_ultimo_guardado
        self.elegir(Modo.INTERMITENTE_TRAS_RECHAZO)
        self.assertIs(self.app._datos_ultimo_guardado, datos)
        self.assertFalse(self.app._hay_cambios_sin_guardar())
        opciones = self.app.interfaz_partida.opciones_visuales
        with patch('ajedrez.aplicacion.messagebox.askyesno', return_value=True):
            self.app.boton_nueva_partida.invoke()
        self.assertIs(self.app.interfaz_partida.opciones_visuales, opciones)
        self.preparar_jaque()
        partida = self.app.interfaz_partida.sesion.partida
        self.app._crear_partida_local(partida=partida)
        self.assertIs(self.app.interfaz_partida.opciones_visuales, opciones)
        self.assertFalse(self.marcadas(self.app.interfaz_partida, 'jaque'))

    def test_nuevos_paneles_y_analisis_existentes_visibles_u_ocultos_reciben_la_eleccion(self):
        self.preparar_jaque()
        self.elegir(Modo.INTERMITENTE_TRAS_RECHAZO)
        vista = self.app.interfaz_partida
        vista.abrir_panel_analisis()
        panel = vista._panel_analisis
        self.assertIs(panel.opciones_visuales.modo_resaltado_jaque, Modo.INTERMITENTE_TRAS_RECHAZO)
        for oculto in (False, True):
            with self.subTest(oculto=oculto):
                if oculto:
                    vista._volver_del_panel_analisis()
                estado = panel.estado_mostrado
                datos = partida_a_datos(panel.sesion.partida)
                self.elegir(Modo.REY_Y_ATACANTES)
                self.assertEqual(self.marcadas(panel, 'atacante_jaque'), {(4, 7)})
                self.assertIs(panel.opciones_visuales, vista.opciones_visuales)
                self.assertIs(panel.estado_mostrado, estado)
                self.assertEqual(partida_a_datos(panel.sesion.partida), datos)
                self.elegir(Modo.INTERMITENTE_TRAS_RECHAZO)
                self.assertFalse(self.marcadas(panel, 'jaque'))

    def test_cambio_de_preferencias_en_editor_no_marca_el_borrador_con_el_jaque_anterior(self):
        self.preparar_jaque()
        vista = self.app.interfaz_partida
        vista.abrir_panel_analisis()
        panel = vista._panel_analisis
        panel.iniciar_edicion()
        panel.vaciar_borrador()
        editor = panel.editor
        dibujos = panel.casillero.canvas.find_all()
        self.elegir(Modo.REY_Y_ATACANTES)
        self.assertIs(panel.editor, editor)
        self.assertEqual(panel.casillero.canvas.find_all(), dibujos)
        panel.cancelar_edicion()
        self.assertEqual(self.marcadas(panel, 'jaque'), {(7, 4)})
        self.assertEqual(self.marcadas(panel, 'atacante_jaque'), {(4, 7)})

    def test_navegacion_historica_no_regresa_al_estado_vigente_al_aplicar(self):
        self.preparar_jaque()
        vista = self.app.interfaz_partida
        self.clic('g7')
        self.clic('g6')
        vigente = vista.sesion.estado_actual
        vista.retroceder_movimiento()
        historico = vista.estado_mostrado
        self.elegir(Modo.REY_Y_ATACANTES)
        self.assertIs(vista.estado_mostrado, historico)
        self.assertIs(vista.sesion.estado_actual, vigente)
        self.assertEqual(self.marcadas(vista, 'atacante_jaque'), {(4, 7)})


if __name__ == '__main__':
    unittest.main()
