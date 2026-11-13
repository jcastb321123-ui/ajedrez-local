"""Biblioteca real de SQLite y widgets de Tkinter con diálogos controlados."""

from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ajedrez.aplicacion import AplicacionAjedrez
from ajedrez.partida import Partida
from ajedrez.persistencia import cargar_partida, guardar_partida, partida_a_datos
from ajedrez.piezas import Color, PeonBlanco, Rey
from ajedrez.repositorio_partidas import RepositorioPartidasSQLite
from pruebas.test_persistencia import jugar, partida_con_piezas
from pruebas.test_sesion import SesionDePrueba


class PruebasBibliotecaAplicacion(unittest.TestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'biblioteca.sqlite3'
        self.repositorio = RepositorioPartidasSQLite(self.ruta)
        self.ventana = tk.Tk()
        self.ventana.withdraw()
        self.errores = []
        self.addCleanup(self.assertFalse, self.errores)
        self.addCleanup(self.ventana.destroy)
        self.ventana.report_callback_exception = lambda tipo, error, traza: self.errores.append(error)
        self.app = AplicacionAjedrez(ventana=self.ventana, repositorio=self.repositorio)

    def abrir_biblioteca(self):
        self.app._boton_biblioteca.invoke()
        biblioteca = self.app._biblioteca
        biblioteca.withdraw()
        self.ventana.update_idletasks()
        return biblioteca

    def guardar_biblioteca(self, titulo='Prueba'):
        with patch('ajedrez.aplicacion.simpledialog.askstring', return_value=titulo):
            self.assertTrue(self.app.solicitar_guardar_en_biblioteca())
        return self.app._id_partida_biblioteca

    def resumen(self, identificador):
        return next(r for r in self.repositorio.listar_partidas() if r.id_partida == identificador)

    def test_biblioteca_vacia_botones_guardado_y_reutilizacion_de_ventana(self):
        biblioteca = self.abrir_biblioteca()
        self.assertEqual(biblioteca._tabla.get_children(), ())
        self.assertTrue(biblioteca._boton_abrir.instate(['disabled']))
        self.assertTrue(biblioteca._boton_eliminar.instate(['disabled']))
        self.app.solicitar_biblioteca()
        self.assertIs(self.app._biblioteca, biblioteca)
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        with patch('ajedrez.aplicacion.simpledialog.askstring', return_value='José ♞'):
            biblioteca._boton_guardar.invoke()
        self.assertEqual(len(biblioteca._tabla.get_children()), 1)
        self.assertFalse(biblioteca._boton_abrir.instate(['disabled']))
        identificador = self.app._id_partida_biblioteca
        self.assertEqual(self.repositorio.cargar_partida(identificador).contador_jugadas, 1)
        self.assertFalse(self.app._hay_cambios_sin_guardar())
        self.assertEqual(self.ventana.title(), 'Ajedrez — José ♞')

    def test_abrir_continuar_y_guardar_actualiza_el_mismo_registro_y_el_tablero(self):
        partida = Partida()
        jugar(partida, 'e2e4')
        identificador = self.repositorio.guardar_partida(partida, 'Continuar')
        fecha = self.resumen(identificador).fecha_creacion
        anterior = self.app.interfaz_partida
        biblioteca = self.abrir_biblioteca()
        biblioteca._boton_abrir.invoke()
        self.assertFalse(biblioteca.winfo_exists())
        vista = self.app.interfaz_partida
        self.assertIsNot(vista, anterior)
        self.assertIsNone(vista.casillero.casillas[(1, 4)].id_pieza)
        self.assertIsNotNone(vista.casillero.casillas[(3, 4)].id_pieza)
        for fila, columna in ((6, 4), (4, 4)):
            lado = vista.casillero.tamanno_casilla
            vista.gestionar_clic_izquierdo(SimpleNamespace(x=(columna + 0.5) * lado, y=(7 - fila + 0.5) * lado))
        self.app._boton_guardar_partida.invoke()
        self.assertEqual(self.repositorio.cargar_partida(identificador).contador_jugadas, 2)
        self.assertEqual(len(self.repositorio.listar_partidas()), 1)
        self.assertEqual(self.resumen(identificador).fecha_creacion, fecha)
        self.assertFalse(self.app._hay_cambios_sin_guardar())
        vista.retroceder_movimiento()
        vista.avanzar_movimiento()
        self.assertIs(vista.estado_mostrado, vista.sesion.estado_actual)

    def test_guardar_copia_cambia_destino_sin_sobrescribir_el_anterior(self):
        primero = self.guardar_biblioteca('Original')
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        biblioteca = self.abrir_biblioteca()
        with patch('ajedrez.aplicacion.simpledialog.askstring', return_value='Variante guardada'):
            biblioteca._boton_copia.invoke()
        segundo = self.app._id_partida_biblioteca
        self.assertNotEqual(primero, segundo)
        self.assertEqual(self.repositorio.cargar_partida(primero).contador_jugadas, 0)
        self.assertEqual(self.repositorio.cargar_partida(segundo).contador_jugadas, 1)
        self.assertEqual(len(biblioteca._tabla.get_children()), 2)

    def test_seleccionar_otra_fila_no_cambia_el_destino_del_guardado_actual(self):
        actual = self.guardar_biblioteca('Actual')
        otro = self.repositorio.guardar_partida(Partida(), 'Otra')
        biblioteca = self.abrir_biblioteca()
        biblioteca._tabla.selection_set(str(otro))
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        biblioteca._boton_guardar.invoke()
        self.assertEqual(self.app._id_partida_biblioteca, actual)
        self.assertEqual(self.repositorio.cargar_partida(actual).contador_jugadas, 1)
        self.assertEqual(self.repositorio.cargar_partida(otro).contador_jugadas, 0)

    def test_dialogo_de_titulo_devuelve_el_control_a_la_biblioteca(self):
        biblioteca = self.abrir_biblioteca()
        for respuesta in (None, 'Título'):
            def responder(*args, **kwargs):
                # Efecto de cerrar el simpledialog que había tomado el grab.
                biblioteca.grab_release()
                return respuesta

            with self.subTest(respuesta=respuesta), patch('ajedrez.aplicacion.simpledialog.askstring', side_effect=responder):
                biblioteca._boton_copia.invoke()
                self.assertIs(biblioteca.grab_current(), biblioteca)

    def test_cancelar_o_titulo_vacio_no_guarda_ni_cambia_el_destino(self):
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        for titulo in (None, '   '):
            with (self.subTest(titulo=titulo),
                  patch('ajedrez.aplicacion.simpledialog.askstring', return_value=titulo),
                  patch('ajedrez.aplicacion.messagebox.showinfo')):
                self.assertFalse(self.app.solicitar_guardar_en_biblioteca())
                self.assertIsNone(self.app._id_partida_biblioteca)
                self.assertEqual(self.repositorio.listar_partidas(), ())
                self.assertTrue(self.app._hay_cambios_sin_guardar())

    def test_cancelar_apertura_conserva_vista_y_descartar_abre_otro_registro(self):
        identificador = self.repositorio.guardar_partida(Partida(), 'Otra partida')
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        anterior = self.app.interfaz_partida
        biblioteca = self.abrir_biblioteca()
        with patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=None):
            biblioteca._boton_abrir.invoke()
        self.assertIs(self.app.interfaz_partida, anterior)
        self.assertTrue(biblioteca.winfo_exists())
        with patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=False):
            biblioteca._boton_abrir.invoke()
        self.assertFalse(biblioteca.winfo_exists())
        self.assertIsNot(self.app.interfaz_partida, anterior)
        self.assertEqual(self.app._id_partida_biblioteca, identificador)

    def test_abrir_mismo_registro_despues_de_guardar_usa_contenido_actualizado(self):
        identificador = self.guardar_biblioteca()
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        biblioteca = self.abrir_biblioteca()
        with patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=True):
            biblioteca._boton_abrir.invoke()
        self.assertEqual(self.app.interfaz_partida.sesion.partida.contador_jugadas, 1)
        self.assertEqual(self.repositorio.cargar_partida(identificador).contador_jugadas, 1)
        self.assertFalse(self.app._hay_cambios_sin_guardar())

    def test_guardado_fallido_impide_cierre_y_sustitucion_sin_perder_datos(self):
        identificador = self.guardar_biblioteca()
        jugar(self.app.interfaz_partida.sesion.partida, 'e2e4')
        vista = self.app.interfaz_partida
        with (patch.object(self.repositorio, 'actualizar_partida', side_effect=sqlite3.OperationalError('Sin acceso')),
              patch('ajedrez.aplicacion.messagebox.showerror') as aviso,
              patch('ajedrez.aplicacion.messagebox.askyesnocancel', return_value=True),
              patch.object(self.ventana, 'destroy') as cerrar):
            self.app.solicitar_cierre()
            self.app.solicitar_nueva_partida()
            cerrar.assert_not_called()
            self.assertEqual(aviso.call_count, 2)
        self.assertIs(self.app.interfaz_partida, vista)
        self.assertEqual(self.repositorio.cargar_partida(identificador).contador_jugadas, 0)
        self.assertTrue(self.app._hay_cambios_sin_guardar())

    def test_eliminar_otro_registro_y_el_actual_conserva_partida_abierta(self):
        actual = self.guardar_biblioteca('Actual')
        otro = self.repositorio.guardar_partida(Partida(), 'Otra')
        biblioteca = self.abrir_biblioteca()
        biblioteca._tabla.selection_set(str(otro))
        with patch('ajedrez.aplicacion.messagebox.askyesno', return_value=False):
            biblioteca._boton_eliminar.invoke()
        self.assertEqual(len(self.repositorio.listar_partidas()), 2)
        with patch('ajedrez.aplicacion.messagebox.askyesno', return_value=True):
            biblioteca._boton_eliminar.invoke()
        self.assertEqual(self.app._id_partida_biblioteca, actual)
        self.assertFalse(self.app._hay_cambios_sin_guardar())
        vista = self.app.interfaz_partida
        with patch('ajedrez.aplicacion.messagebox.askyesno', return_value=True):
            biblioteca._boton_eliminar.invoke()
        self.assertIs(self.app.interfaz_partida, vista)
        self.assertIsNone(self.app._id_partida_biblioteca)
        self.assertTrue(self.app._hay_cambios_sin_guardar())
        self.assertEqual(biblioteca._tabla.get_children(), ())
        self.assertTrue(biblioteca._boton_eliminar.instate(['disabled']))
        self.guardar_biblioteca('Recuperada de la pantalla')
        self.assertEqual(len(self.repositorio.listar_partidas()), 1)

    def test_registro_danado_o_ausente_no_sustituye_partida(self):
        identificador = self.repositorio.guardar_partida(Partida(), 'Dañada')
        resumen = self.resumen(identificador)
        with closing(sqlite3.connect(self.ruta, autocommit=False)) as conexion:
            with conexion:
                conexion.execute('UPDATE partidas SET contenido_json = ? WHERE id_partida = ?', ('{', identificador))
        anterior = self.app.interfaz_partida
        with (patch('ajedrez.aplicacion.messagebox.showerror') as aviso,
              patch('ajedrez.aplicacion.messagebox.askyesnocancel') as confirmar):
            self.assertFalse(self.app._abrir_partida_biblioteca(resumen))
            self.repositorio.eliminar_partida(identificador)
            self.assertFalse(self.app._abrir_partida_biblioteca(resumen))
        self.assertEqual(aviso.call_count, 2)
        confirmar.assert_not_called()
        self.assertIs(self.app.interfaz_partida, anterior)

    def test_error_de_borrado_conserva_registro_y_asociacion_de_la_partida(self):
        identificador = self.guardar_biblioteca()
        biblioteca = self.abrir_biblioteca()
        with (patch('ajedrez.aplicacion.messagebox.askyesno', return_value=True),
              patch.object(self.repositorio, 'eliminar_partida', side_effect=sqlite3.OperationalError('Sin permiso')),
              patch('ajedrez.aplicacion.messagebox.showerror') as aviso):
            biblioteca._boton_eliminar.invoke()
        aviso.assert_called_once()
        self.assertEqual(self.app._id_partida_biblioteca, identificador)
        self.assertEqual(biblioteca._tabla.get_children(), (str(identificador),))
        self.assertFalse(self.app._hay_cambios_sin_guardar())

    def test_partida_finalizada_se_abre_para_navegar_y_analizar(self):
        partida = Partida()
        jugar(partida, 'f2f3 e7e5 g2g4 d8h4')
        identificador = self.repositorio.guardar_partida(partida, 'Mate')
        biblioteca = self.abrir_biblioteca()
        biblioteca._boton_abrir.invoke()
        vista = self.app.interfaz_partida
        self.assertTrue(vista.en_analisis)
        self.assertEqual(vista.sesion.partida.estado_partida, partida.estado_partida)
        vista.retroceder_movimiento()
        self.app.solicitar_guardar_partida()
        self.assertEqual(partida_a_datos(self.repositorio.cargar_partida(identificador)), partida_a_datos(partida))

    def test_promocion_pendiente_se_rechaza_antes_de_pedir_titulo(self):
        partida = partida_con_piezas({'h1': Rey(Color.Blanco), 'h8': Rey(Color.Negro), 'a7': PeonBlanco()})
        self.app._crear_partida_local(partida=partida)
        self.app.interfaz_partida.sesion.solicitar_movimiento((6, 0), (7, 0))
        with (patch('ajedrez.aplicacion.messagebox.showinfo') as aviso,
              patch('ajedrez.aplicacion.simpledialog.askstring') as titulo):
            self.assertFalse(self.app.solicitar_guardar_en_biblioteca())
        aviso.assert_called_once()
        titulo.assert_not_called()
        self.assertEqual(self.repositorio.listar_partidas(), ())

    def test_historial_y_analisis_guardan_siempre_la_partida_original(self):
        vista = self.app.interfaz_partida
        jugar(vista.sesion.partida, 'e2e4')
        vista.mostrar_estado(vista.sesion.partida.estado_inicial)
        identificador = self.guardar_biblioteca()
        vista.alternar_analisis()
        vista.sesion_movimientos.solicitar_movimiento((1, 3), (3, 3))
        self.app.solicitar_guardar_partida()
        recuperada = self.repositorio.cargar_partida(identificador)
        self.assertEqual(recuperada.ultima_jugada.origen, (1, 4))
        self.assertIsNone(recuperada.tablero.pieza_en((3, 3)))

    def test_importar_archivo_y_exportar_biblioteca_conserva_destino_y_cambios_pendientes(self):
        ruta = Path(self.temporal.name) / 'importada.json'
        partida = Partida()
        jugar(partida, 'e2e4')
        guardar_partida(partida, ruta)
        with patch('ajedrez.aplicacion.filedialog.askopenfilename', return_value=str(ruta)):
            self.app._boton_abrir_partida.invoke()
        self.assertEqual(self.app._ruta_partida, ruta)
        identificador = self.guardar_biblioteca('Importada')
        self.assertIsNone(self.app._ruta_partida)
        jugar(self.app.interfaz_partida.sesion.partida, 'e7e5')
        exportada = ruta.with_name('exportada.json')
        with patch('ajedrez.aplicacion.filedialog.asksaveasfilename', return_value=str(exportada)):
            self.app._boton_exportar.invoke()
        self.assertEqual(cargar_partida(exportada).contador_jugadas, 2)
        self.assertEqual(self.repositorio.cargar_partida(identificador).contador_jugadas, 1)
        self.assertEqual(self.app._id_partida_biblioteca, identificador)
        self.assertTrue(self.app._hay_cambios_sin_guardar())
        self.app.solicitar_guardar_partida()
        self.assertEqual(self.repositorio.cargar_partida(identificador).contador_jugadas, 2)

    def test_capacidad_de_sesion_alternativa_gobierna_guardado_sin_autenticacion_local(self):
        class SesionConGuardado(SesionDePrueba):
            @property
            def admite_guardado_local(self):
                return True

        partida = Partida(turno_inicial=Color.Negro)
        self.app._interfaz_partida = SimpleNamespace(sesion=SesionDePrueba(partida))
        biblioteca = self.abrir_biblioteca()
        self.assertTrue(biblioteca._boton_guardar.instate(['disabled']))
        with patch('ajedrez.aplicacion.simpledialog.askstring') as titulo:
            self.assertFalse(self.app.solicitar_guardar_en_biblioteca())
        titulo.assert_not_called()
        self.app._interfaz_partida = SimpleNamespace(sesion=SesionConGuardado(partida))
        biblioteca.refrescar()
        self.assertFalse(biblioteca._boton_guardar.instate(['disabled']))
        identificador = self.guardar_biblioteca('Otra modalidad')
        self.assertEqual(partida_a_datos(self.repositorio.cargar_partida(identificador)), partida_a_datos(partida))

    def test_biblioteca_se_crea_solo_al_abrirla_y_error_de_acceso_no_afecta_partida(self):
        self.app._repositorio = None
        ruta = Path(self.temporal.name) / 'datos usuario' / 'biblioteca.sqlite3'
        self.assertFalse(ruta.exists())
        vista = self.app.interfaz_partida
        with (patch('ajedrez.aplicacion.obtener_ruta_biblioteca_predeterminada', return_value=ruta),
              patch('ajedrez.aplicacion.RepositorioPartidasSQLite', side_effect=sqlite3.OperationalError('Sin acceso')),
              patch('ajedrez.aplicacion.messagebox.showerror') as aviso):
            self.app.solicitar_biblioteca()
        aviso.assert_called_once()
        self.assertIs(self.app.interfaz_partida, vista)
        self.assertIsNone(self.app._repositorio)
        with patch('ajedrez.aplicacion.obtener_ruta_biblioteca_predeterminada', return_value=ruta):
            biblioteca = self.abrir_biblioteca()
        self.assertTrue(ruta.is_file())
        self.assertEqual(biblioteca._tabla.get_children(), ())


if __name__ == '__main__':
    unittest.main()
